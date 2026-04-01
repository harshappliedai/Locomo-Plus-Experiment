from __future__ import annotations

from typing import Any, Dict, List

from config import Settings


class LettaRunner:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = self._build_client()

    def _build_client(self):  # type: ignore[no-untyped-def]
        try:
            from letta_client import Letta
        except Exception as e:  # pragma: no cover
            raise RuntimeError("letta-client import failed. Install dependencies from requirements.txt") from e

        kwargs = {"base_url": self.settings.letta_base_url}
        if self.settings.letta_api_key:
            kwargs["api_key"] = self.settings.letta_api_key
        return Letta(**kwargs)

    def create_agent(self, conversation_id: str) -> str:
        agent = self.client.agents.create(
            model=f"openai/{self.settings.backbone_model}",
            embedding="openai/text-embedding-3-large",
            memory_blocks=[
                {"label": "human", "value": "User participating in a long conversation."},
                {"label": "persona", "value": "You are a helpful conversational assistant with long-term memory."},
            ],
            name=f"locomo-{conversation_id}",
        )
        return agent.id

    def ingest(self, agent_id: str, turns: List[Dict[str, str]]) -> None:
        batch_size = max(1, self.settings.ingest_batch_size)
        for i in range(0, len(turns), batch_size):
            batch = turns[i : i + batch_size]
            payload = "\n".join(f"{t.get('speaker', 'A')}: {t.get('text', '')}" for t in batch)
            self.client.agents.messages.create(agent_id=agent_id, input=payload)

    def query(self, agent_id: str, trigger: str) -> Dict[str, Any]:
        response = self.client.agents.messages.create(agent_id=agent_id, input=trigger)
        text = self._extract_assistant_text(response)
        return {"response": text}

    @staticmethod
    def _extract_assistant_text(response: Any) -> str:
        # The SDK shape can vary by version; this defensive parser keeps scaffold compatible.
        if hasattr(response, "messages"):
            msgs = getattr(response, "messages") or []
            for msg in reversed(msgs):
                role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
                if role == "assistant":
                    content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else "")
                    if isinstance(content, str):
                        return content
        if isinstance(response, dict):
            return str(response.get("output", ""))
        return str(response)
