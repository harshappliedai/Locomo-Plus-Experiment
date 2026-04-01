from __future__ import annotations

import os
from typing import Any, Dict, List

from openai import OpenAI

from config import Settings


class Mem0Runner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        # Force explicit telemetry behavior for local/offline reproducibility.
        os.environ["MEM0_TELEMETRY"] = "true" if settings.mem0_telemetry else "false"
        client_kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self.openai_client = OpenAI(**client_kwargs)
        self.memory = self._build_mem0_memory()

    def _build_mem0_memory(self):  # type: ignore[no-untyped-def]
        try:
            from mem0 import Memory
        except Exception as e:  # pragma: no cover
            raise RuntimeError("mem0 import failed. Install dependencies from requirements.txt") from e

        config = {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": self.settings.backbone_model,
                    "temperature": self.settings.backbone_temperature,
                    "max_tokens": self.settings.max_tokens,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {"model": "text-embedding-3-large"},
            },
            "vector_store": {
                "provider": "chroma",
                "config": {
                    "collection_name": self.settings.mem0_collection_name,
                    "path": self.settings.mem0_chroma_path,
                },
            },
        }
        return Memory.from_config(config)

    def reset(self, conversation_id: str) -> None:
        try:
            self.memory.delete_all(user_id=conversation_id)
        except Exception:
            # Some versions don't support delete_all; continue with logical isolation by user_id.
            pass

    def ingest(self, conversation_id: str, turns: List[Dict[str, str]]) -> None:
        batch_size = max(1, self.settings.ingest_batch_size)
        for i in range(0, len(turns), batch_size):
            batch = turns[i : i + batch_size]
            content = "\n".join(f"{t.get('speaker', 'A')}: {t.get('text', '')}" for t in batch)
            self.memory.add(
                messages=[{"role": "user", "content": content}],
                user_id=conversation_id,
                infer=self.settings.mem0_infer,
            )

    def query(self, conversation_id: str, trigger: str, limit: int | None = None) -> Dict[str, Any]:
        if limit is None:
            limit = self.settings.mem0_search_limit
        retrieved = self.memory.search(query=trigger, user_id=conversation_id, limit=limit)
        results = retrieved.get("results", []) if isinstance(retrieved, dict) else []
        memories = [r.get("memory", "") for r in results if isinstance(r, dict)]
        memories_str = "\n".join(f"- {m}" for m in memories)

        completion = self.openai_client.chat.completions.create(
            model=self.settings.backbone_model,
            temperature=self.settings.backbone_temperature,
            max_tokens=self.settings.max_tokens,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant. Here are relevant memories about this user:\n"
                    + memories_str,
                },
                {"role": "user", "content": trigger},
            ],
        )
        answer = completion.choices[0].message.content or ""
        return {"response": answer, "retrieved_memories": memories}
