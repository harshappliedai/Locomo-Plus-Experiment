from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Dict, List

from config import assert_protocol_compliance, dump_json, ensure_paths, load_settings, settings_as_dict
from evaluation.judge import Judge
from evaluation.judge_prompts import COGNITIVE_AWARENESS_PROMPT
from evaluation.metrics import compute_metrics
from systems.letta_runner import LettaRunner
from systems.mem0_runner import Mem0Runner
from systems.zep_runner import ZepRunner


def _format_turns_before_trigger(sample: Dict[str, Any]) -> List[Dict[str, str]]:
    turns: List[Dict[str, str]] = []
    trigger_idx = sample.get("trigger_position")
    history = sample.get("full_dialogue_history", [])

    if isinstance(trigger_idx, int) and isinstance(history, list):
        sliced = history[:trigger_idx]
    else:
        sliced = history

    for item in sliced:
        if isinstance(item, dict):
            speaker = item.get("speaker", "A")
            text = item.get("text", item.get("content", ""))
            turns.append({"speaker": str(speaker), "text": str(text)})
        else:
            turns.append({"speaker": "A", "text": str(item)})
    return turns


def run() -> None:
    settings = load_settings()
    ensure_paths(settings)
    lock = assert_protocol_compliance(settings, COGNITIVE_AWARENESS_PROMPT)
    enabled_systems = tuple(dict.fromkeys(settings.bench_systems))
    valid_systems = {"mem0", "letta", "zep"}
    invalid_systems = [s for s in enabled_systems if s not in valid_systems]
    if invalid_systems:
        raise ValueError(f"Unsupported BENCH_SYSTEMS values: {invalid_systems}")
    if not enabled_systems:
        raise ValueError("BENCH_SYSTEMS must include at least one of: mem0, letta, zep")

    with open(settings.cognitive_samples_path, "r", encoding="utf-8") as f:
        samples = json.load(f)
    if not isinstance(samples, list):
        raise ValueError("cognitive_samples.json must be a list")

    mem0 = Mem0Runner(settings) if "mem0" in enabled_systems else None
    letta = LettaRunner(settings) if "letta" in enabled_systems else None
    zep = ZepRunner(settings) if "zep" in enabled_systems else None
    judge = Judge(settings)

    responses: List[Dict[str, Any]] = []
    judgments: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    for idx, sample in enumerate(samples, start=1):
        conv_id = str(sample["conversation_id"])
        trigger = str(sample["trigger_query"])
        turns = _format_turns_before_trigger(sample)
        relation_type = sample.get("relation_type", "unknown")
        time_gap = sample.get("time_gap", "unknown")
        cue_dialogue = str(sample.get("cue_dialogue", ""))
        sample_id = str(sample.get("sample_id", f"sample_{idx}"))

        system_responses: Dict[str, str] = {}

        # Mem0 pipeline
        if mem0 is not None:
            try:
                mem0.reset(conv_id)
                start = time.time()
                mem0.ingest(conv_id, turns)
                mem0_result = mem0.query(conv_id, trigger=trigger)
                mem0_latency = time.time() - start
                mem0_response = mem0_result["response"]
                system_responses["mem0"] = mem0_response
                responses.append(
                    {
                        "sample_id": sample_id,
                        "system": "mem0",
                        "response": mem0_response,
                        "retrieved_memories": mem0_result.get("retrieved_memories", []),
                        "relation_type": relation_type,
                        "time_gap": time_gap,
                        "latency_seconds": mem0_latency,
                    }
                )
            except Exception as e:
                errors.append({"sample_id": sample_id, "system": "mem0", "error": str(e)})

        # Letta pipeline
        if letta is not None:
            try:
                agent_id = letta.create_agent(conv_id)
                start = time.time()
                letta.ingest(agent_id, turns)
                letta_result = letta.query(agent_id, trigger=trigger)
                letta_latency = time.time() - start
                letta_response = letta_result["response"]
                system_responses["letta"] = letta_response
                responses.append(
                    {
                        "sample_id": sample_id,
                        "system": "letta",
                        "response": letta_response,
                        "relation_type": relation_type,
                        "time_gap": time_gap,
                        "latency_seconds": letta_latency,
                    }
                )
            except Exception as e:
                errors.append({"sample_id": sample_id, "system": "letta", "error": str(e)})

        # Zep graph + vector pipeline
        if zep is not None:
            try:
                zep.reset(conv_id)
                start = time.time()
                zep.ingest(conv_id, turns)
                zep_result = zep.query(conv_id, trigger=trigger)
                zep_latency = time.time() - start
                zep_response = zep_result["response"]
                system_responses["zep"] = zep_response
                responses.append(
                    {
                        "sample_id": sample_id,
                        "system": "zep",
                        "response": zep_response,
                        "retrieved_memories": zep_result.get("retrieved_memories", []),
                        "relation_type": relation_type,
                        "time_gap": time_gap,
                        "latency_seconds": zep_latency,
                    }
                )
            except Exception as e:
                errors.append({"sample_id": sample_id, "system": "zep", "error": str(e)})

        judgments_before = len(judgments)
        for system_name, model_response in system_responses.items():
            if not model_response:
                continue
            try:
                j = judge.evaluate(
                    cue_dialogue=cue_dialogue,
                    trigger_query=trigger,
                    model_response=model_response,
                )
                judgments.append(
                    {
                        "sample_id": sample_id,
                        "system": system_name,
                        "relation_type": relation_type,
                        "time_gap": time_gap,
                        "label": j["label"],
                        "reason": j["reason"],
                        "raw_judge_output": j["raw"],
                    }
                )
            except Exception as e:
                errors.append({"sample_id": sample_id, "system": system_name, "error": f"judge: {e}"})

        judged_systems = {j["system"] for j in judgments[judgments_before:]}
        status_parts = []
        for system in enabled_systems:
            label = "ok" if system in judged_systems else "err"
            status_parts.append(f"{system} = {label}")
        print(f"[{idx}/{len(samples)}] sample_id={sample_id}  " + ", ".join(status_parts), flush=True)

    metrics = compute_metrics(judgments)

    run_meta = {
        "settings": settings_as_dict(settings),
        "protocol_lock": lock,
    }

    results_dir = Path(settings.results_dir)
    dump_json(results_dir / "responses.json", responses)
    dump_json(results_dir / "judge_results.json", judgments)
    dump_json(results_dir / "summary.json", metrics)
    dump_json(results_dir / "paper_alignment_report.json", {"status": "pass", "protocol_lock": lock})
    dump_json(results_dir / "run_meta.json", run_meta)
    dump_json(results_dir / "errors.json", errors)

    print(f"Done. Wrote results to {results_dir}")


if __name__ == "__main__":
    run()
