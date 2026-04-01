from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict

from openai import OpenAI

from config import Settings
from evaluation.judge_prompts import COGNITIVE_AWARENESS_PROMPT


class Judge:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        client_kwargs = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            client_kwargs["base_url"] = settings.openai_base_url
        self.client = OpenAI(**client_kwargs)

    def evaluate(self, cue_dialogue: str, trigger_query: str, model_response: str) -> Dict[str, Any]:
        prompt = COGNITIVE_AWARENESS_PROMPT.format(
            cue_dialogue=cue_dialogue,
            trigger_query=trigger_query,
            model_response=model_response,
        )
        raw = self._run_judge_call(prompt)
        parsed = self._safe_parse(raw)
        label = parsed.get("label", "").strip().lower()
        if label not in {"correct", "wrong"}:
            raise ValueError(f"Judge returned invalid label: {label!r} | raw={raw!r}")
        return {
            "label": label,
            "reason": parsed.get("reason", ""),
            "raw": raw,
        }

    def _run_judge_call(self, prompt: str) -> str:
        if self.settings.judge_provider == "openai":
            completion = self.client.chat.completions.create(
                model=self.settings.judge_model,
                temperature=self.settings.judge_temperature,
                max_tokens=self.settings.max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return completion.choices[0].message.content or ""

        if self.settings.judge_provider == "google":
            return self._google_generate(prompt)

        raise ValueError(f"Unsupported JUDGE_PROVIDER: {self.settings.judge_provider}")

    def _google_generate(self, prompt: str) -> str:
        if not self.settings.google_api_key:
            raise ValueError("GOOGLE_API_KEY is required for Google judge provider.")

        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{urllib.parse.quote(self.settings.judge_model)}:generateContent"
            f"?key={urllib.parse.quote(self.settings.google_api_key)}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.settings.judge_temperature,
                "maxOutputTokens": self.settings.max_tokens,
            },
        }
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.settings.request_timeout_seconds) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            err_text = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Google judge HTTP error {e.code}: {err_text}") from e

        data = json.loads(body)
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError(f"Google judge returned no candidates: {body[:800]}")
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        return "\n".join(t for t in texts if t).strip()

    @staticmethod
    def _safe_parse(raw: str) -> Dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            lines = [ln for ln in text.splitlines() if not ln.strip().startswith("```")]
            text = "\n".join(lines).strip()
        try:
            obj = json.loads(text)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            pass
        m = re.search(r'"label"\s*:\s*"(correct|wrong)"', text, flags=re.IGNORECASE)
        if m:
            return {"label": m.group(1).lower(), "reason": f"Partial judge JSON: {text[:300]}"}
        return {"label": "wrong", "reason": f"Invalid JSON from judge: {raw[:400]}"}
