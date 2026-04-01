from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List

from openai import OpenAI

from config import Settings


class ZepRunner:
    _MAX_MESSAGE_CHARS = 2400

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.base_api_url = self.settings.zep_base_url.rstrip("/") + "/api/v2"
        self.auth_header = self._build_auth_header()
        client_kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self.openai_client = OpenAI(**client_kwargs)

    def _build_auth_header(self) -> str:
        if not self.settings.zep_api_key:
            raise ValueError("Missing ZEP_API_KEY in environment.")
        return f"Api-Key {self.settings.zep_api_key}"

    def _request(
        self,
        method: str,
        path: str,
        payload: Dict[str, Any] | None = None,
        expected_statuses: tuple[int, ...] = (200,),
    ) -> Any:
        url = self.base_api_url + path
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        max_attempts = max(1, self.settings.retry_max_attempts)
        for attempt in range(1, max_attempts + 1):
            req = urllib.request.Request(
                url=url,
                data=data,
                headers={
                    "Authorization": self.auth_header,
                    "Content-Type": "application/json",
                },
                method=method,
            )
            try:
                with urllib.request.urlopen(req, timeout=self.settings.request_timeout_seconds) as resp:
                    status = resp.getcode()
                    body = resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                status = e.code
                body = e.read().decode("utf-8", errors="ignore")
                if status in expected_statuses:
                    return body
                if self._is_transient_error(status=status, body=body) and attempt < max_attempts:
                    # Let graphiti/zep restart and then retry request.
                    time.sleep(min(2 * attempt, 8))
                    continue
                raise RuntimeError(f"Zep HTTP {status} for {method} {path}: {body[:600]}")
            except urllib.error.URLError as e:
                if attempt < max_attempts:
                    time.sleep(min(2 * attempt, 8))
                    continue
                raise RuntimeError(f"Zep connection error for {method} {path}: {e}") from e

            if status not in expected_statuses:
                if self._is_transient_error(status=status, body=body) and attempt < max_attempts:
                    time.sleep(min(2 * attempt, 8))
                    continue
                raise RuntimeError(f"Zep HTTP {status} for {method} {path}: {body[:600]}")
            if not body.strip():
                return None
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return body

        raise RuntimeError(f"Zep request exhausted retries for {method} {path}")

    def reset(self, user_id: str) -> None:
        safe_user_id = urllib.parse.quote(user_id, safe="")
        try:
            self._request("DELETE", f"/users/{safe_user_id}", expected_statuses=(200, 204, 404))
        except Exception:
            # Some local CE deployments may timeout on graph cleanup; continue with logical reuse.
            pass
        self._request("POST", "/users", payload={"user_id": user_id}, expected_statuses=(200, 201, 409))

    def ingest(self, user_id: str, turns: List[Dict[str, str]]) -> None:
        safe_session_id = urllib.parse.quote(user_id, safe="")
        batch_size = max(1, self.settings.ingest_batch_size)
        for i in range(0, len(turns), batch_size):
            batch = turns[i : i + batch_size]
            content = "\n".join(f"{t.get('speaker', 'A')}: {t.get('text', '')}" for t in batch)
            for chunk in self._chunk_text(content, max_chars=self._MAX_MESSAGE_CHARS):
                self._request(
                    "POST",
                    f"/sessions/{safe_session_id}/memory",
                    payload={"messages": [{"role_type": "user", "content": chunk}]},
                    expected_statuses=(200, 201),
                )

    def query(self, user_id: str, trigger: str, limit: int | None = None) -> Dict[str, Any]:
        safe_session_id = urllib.parse.quote(user_id, safe="")
        memory_payload = self._request("GET", f"/sessions/{safe_session_id}/memory", expected_statuses=(200,))
        memories = self._extract_memories(memory_payload, limit=limit or self.settings.zep_search_limit)
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

    @staticmethod
    def _extract_memories(memory_payload: Any, limit: int) -> List[str]:
        out: List[str] = []
        if isinstance(memory_payload, dict):
            facts = memory_payload.get("relevant_facts", [])
            if isinstance(facts, list):
                for fact_row in facts:
                    if isinstance(fact_row, dict) and fact_row.get("fact"):
                        out.append(str(fact_row["fact"]))

            messages = memory_payload.get("messages", [])
            if isinstance(messages, list):
                for msg in messages:
                    if isinstance(msg, dict) and msg.get("content"):
                        out.append(str(msg["content"]))

        # Keep ordering but drop duplicates.
        return list(dict.fromkeys(out))[: max(1, limit)]

    @staticmethod
    def _chunk_text(text: str, max_chars: int) -> List[str]:
        if len(text) <= max_chars:
            return [text]
        lines = text.split("\n")
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0
        for line in lines:
            line_len = len(line) + 1  # + newline
            if current and current_len + line_len > max_chars:
                chunks.append("\n".join(current))
                current = [line]
                current_len = line_len
            else:
                current.append(line)
                current_len += line_len
        if current:
            chunks.append("\n".join(current))
        return chunks

    @staticmethod
    def _is_transient_error(status: int, body: str) -> bool:
        text = (body or "").lower()
        if status >= 500:
            return True
        indicators = (
            "connect: connection refused",
            "no such host",
            "timeout",
            "request canceled",
            "client.timeout",
            "eof",
            "temporarily unavailable",
        )
        return any(token in text for token in indicators)
