from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_base_url: str | None
    google_api_key: str | None
    backbone_model: str
    judge_provider: str
    judge_model: str
    backbone_temperature: float
    judge_temperature: float
    max_tokens: int
    mem0_chroma_path: str
    mem0_collection_name: str
    letta_base_url: str
    letta_api_key: str | None
    cognitive_samples_path: str
    results_dir: str
    request_timeout_seconds: int
    retry_max_attempts: int
    ingest_batch_size: int
    mem0_infer: bool
    mem0_search_limit: int
    zep_base_url: str
    zep_api_key: str | None
    zep_search_limit: int
    bench_systems: tuple[str, ...]
    mem0_telemetry: bool


def _read_float(name: str, default: str) -> float:
    return float(os.getenv(name, default))


def _read_int(name: str, default: str) -> int:
    return int(os.getenv(name, default))

def _read_bool(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "y", "on"}


def _read_csv(name: str, default: str) -> tuple[str, ...]:
    raw = os.getenv(name, default)
    values = tuple(v.strip().lower() for v in raw.split(",") if v.strip())
    return values


def load_settings() -> Settings:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing OPENAI_API_KEY in environment.")

    return Settings(
        openai_api_key=api_key,
        openai_base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None,
        google_api_key=os.getenv("GOOGLE_API_KEY", "").strip() or None,
        backbone_model=os.getenv("BACKBONE_MODEL", "gpt-4o-mini").strip(),
        judge_provider=os.getenv("JUDGE_PROVIDER", "google").strip().lower(),
        judge_model=os.getenv("JUDGE_MODEL", "gemini-2.5-flash").strip(),
        backbone_temperature=_read_float("BACKBONE_TEMPERATURE", "0"),
        judge_temperature=_read_float("JUDGE_TEMPERATURE", "0"),
        max_tokens=_read_int("MAX_TOKENS", "512"),
        mem0_chroma_path=os.getenv("MEM0_CHROMA_PATH", "./mem0_store").strip(),
        mem0_collection_name=os.getenv("MEM0_COLLECTION_NAME", "locomo_bench").strip(),
        letta_base_url=os.getenv("LETTA_BASE_URL", "http://localhost:8283").strip(),
        letta_api_key=os.getenv("LETTA_API_KEY", "").strip() or None,
        cognitive_samples_path=os.getenv("COGNITIVE_SAMPLES_PATH", "./data/cognitive_samples.json").strip(),
        results_dir=os.getenv("RESULTS_DIR", "./results").strip(),
        request_timeout_seconds=_read_int("REQUEST_TIMEOUT_SECONDS", "60"),
        retry_max_attempts=_read_int("RETRY_MAX_ATTEMPTS", "3"),
        ingest_batch_size=_read_int("INGEST_BATCH_SIZE", "20"),
        mem0_infer=_read_bool("MEM0_INFER", "true"),
        mem0_search_limit=_read_int("MEM0_SEARCH_LIMIT", "10"),
        zep_base_url=os.getenv("ZEP_BASE_URL", "http://localhost:8000").strip(),
        zep_api_key=os.getenv("ZEP_API_KEY", "").strip() or None,
        zep_search_limit=_read_int("ZEP_SEARCH_LIMIT", "10"),
        bench_systems=_read_csv("BENCH_SYSTEMS", "mem0,letta"),
        mem0_telemetry=_read_bool("MEM0_TELEMETRY", "false"),
    )


def protocol_lock(settings: Settings, judge_prompt: str) -> Dict[str, Any]:
    prompt_hash = hashlib.sha256(judge_prompt.encode("utf-8")).hexdigest()
    return {
        "backbone_model": settings.backbone_model,
        "judge_provider": settings.judge_provider,
        "judge_model": settings.judge_model,
        "backbone_temperature": settings.backbone_temperature,
        "judge_temperature": settings.judge_temperature,
        "max_tokens": settings.max_tokens,
        "query_mode": "unified_conversational_no_task_disclosure",
        "cognitive_labels": ["correct", "wrong"],
        "judge_output_schema": {"label": "string", "reason": "string"},
        "judge_prompt_sha256": prompt_hash,
    }


def assert_protocol_compliance(settings: Settings, judge_prompt: str) -> Dict[str, Any]:
    lock = protocol_lock(settings, judge_prompt)
    failures: list[str] = []

    if settings.backbone_model != "gpt-4o-mini":
        failures.append(f"BACKBONE_MODEL must be gpt-4o-mini, got: {settings.backbone_model}")
    if settings.judge_provider not in {"google", "openai"}:
        failures.append(f"JUDGE_PROVIDER must be one of google/openai, got: {settings.judge_provider}")
    if settings.backbone_temperature != 0:
        failures.append(f"BACKBONE_TEMPERATURE must be 0, got: {settings.backbone_temperature}")
    if settings.judge_temperature != 0:
        failures.append(f"JUDGE_TEMPERATURE must be 0, got: {settings.judge_temperature}")
    if settings.max_tokens != 512:
        failures.append(f"MAX_TOKENS must be 512, got: {settings.max_tokens}")
    if settings.judge_provider == "google" and not settings.google_api_key:
        failures.append("GOOGLE_API_KEY is required when JUDGE_PROVIDER=google")

    if failures:
        raise ValueError("Protocol compliance failed:\n- " + "\n- ".join(failures))

    return lock


def ensure_paths(settings: Settings) -> None:
    Path(settings.results_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.mem0_chroma_path).mkdir(parents=True, exist_ok=True)


def dump_json(path: str | Path, obj: Any) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=True, indent=2)


def settings_as_dict(settings: Settings) -> Dict[str, Any]:
    data = asdict(settings)
    for key in ("openai_api_key", "google_api_key", "letta_api_key", "zep_api_key"):
        if data.get(key):
            data[key] = "***REDACTED***"
    return data
