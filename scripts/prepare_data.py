from __future__ import annotations

import argparse
import json
import random
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List


def _parse_locomo_session_time(s: str) -> datetime:
    return datetime.strptime(s, "%I:%M %p on %d %B, %Y")


_NUM_WORD = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
}


def _parse_time_gap(time_gap: str) -> int:
    s = time_gap.lower().strip()
    m = re.search(
        r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|a|an)\b\s*"
        r"(week|weeks|month|months|year|years)\b",
        s,
    )
    if not m:
        return 0
    num, unit = m.groups()
    if num.isdigit():
        count = int(num)
    elif num in {"a", "an"}:
        count = 1
    else:
        count = _NUM_WORD.get(num, 0)
    if unit.startswith("week"):
        return count * 7
    if unit.startswith("month"):
        return count * 30
    if unit.startswith("year"):
        return count * 365
    return 0


def _parse_ab_dialogue(text: str) -> List[Dict[str, str]]:
    turns: List[Dict[str, str]] = []
    for line in text.split("\n"):
        line = line.strip()
        if line.startswith("A:"):
            turns.append({"speaker": "A", "text": line[2:].strip()})
        elif line.startswith("B:"):
            turns.append({"speaker": "B", "text": line[2:].strip()})
    return turns


def _map_speaker(dialogue: List[Dict[str, str]], speaker_a: str, speaker_b: str) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    for t in dialogue:
        mapped = {"speaker": speaker_a if t["speaker"] == "A" else speaker_b, "text": t["text"]}
        out.append(mapped)
    return out


def _analyze_conversation(conv: Dict[str, Any]) -> tuple[str, str, List[List[Dict[str, Any]]], List[datetime]]:
    speaker_a = conv["speaker_a"]
    speaker_b = conv["speaker_b"]
    sessions: List[List[Dict[str, Any]]] = []
    session_times: List[datetime] = []
    idx = 1
    while True:
        sk = f"session_{idx}"
        tk = f"session_{idx}_date_time"
        if sk not in conv:
            break
        sessions.append(conv[sk])
        session_times.append(_parse_locomo_session_time(conv[tk]))
        idx += 1
    return speaker_a, speaker_b, sessions, session_times


def _compute_insertion(session_times: List[datetime], time_gap: str) -> tuple[int | None, datetime, datetime]:
    query_time = session_times[-1] + timedelta(days=7)
    back_days = _parse_time_gap(time_gap)
    cue_time = query_time - timedelta(days=back_days)
    cue_idx = None
    for i, t in enumerate(session_times):
        if t <= cue_time:
            cue_idx = i
        else:
            break
    return cue_idx, cue_time, query_time


def _build_context(plus_item: Dict[str, Any], locomo_item: Dict[str, Any]) -> Dict[str, Any]:
    conv = locomo_item["conversation"]
    speaker_a, speaker_b, sessions, session_times = _analyze_conversation(conv)
    cue_idx, cue_time, query_time = _compute_insertion(session_times, plus_item["time_gap"])

    cue_turns = _map_speaker(_parse_ab_dialogue(plus_item["cue_dialogue"]), speaker_a, speaker_b)
    query_turns = _map_speaker(_parse_ab_dialogue(plus_item["trigger_query"]), speaker_a, speaker_b)

    events: List[tuple[datetime, List[Dict[str, Any]], str]] = []
    for sess, t in zip(sessions, session_times):
        events.append((t, sess, "original"))
    events.append((cue_time, cue_turns, "cue"))
    events.append((query_time, query_turns, "query"))
    events.sort(key=lambda x: x[0])

    stitched: List[Dict[str, str]] = []
    cue_start = None
    query_start = None
    for _, content, tag in events:
        start_idx = len(stitched)
        normalized = [{"speaker": str(turn["speaker"]), "text": str(turn["text"])} for turn in content]
        stitched.extend(normalized)
        if tag == "cue":
            cue_start = start_idx
        if tag == "query":
            query_start = start_idx

    return {
        "full_dialogue_history": stitched,
        "cue_position": cue_start,
        "trigger_position": query_start,
        "cue_time": cue_time.strftime("%Y-%m-%d %H:%M"),
        "query_time": query_time.strftime("%Y-%m-%d %H:%M"),
    }


def prepare(
    input_path: str,
    locomo_path: str,
    output_path: str,
    sample_size: int,
    seed: int,
) -> None:
    with open(input_path, "r", encoding="utf-8") as f:
        plus_items = json.load(f)
    with open(locomo_path, "r", encoding="utf-8") as f:
        locomo_items = json.load(f)

    if not isinstance(plus_items, list) or not isinstance(locomo_items, list):
        raise ValueError("Unexpected input schema. Expected lists in both json files.")
    if sample_size <= 0:
        raise ValueError("sample_size must be > 0")
    if sample_size > len(plus_items):
        raise ValueError(f"sample_size {sample_size} exceeds dataset size {len(plus_items)}")

    rng = random.Random(seed)
    sampled_plus = rng.sample(plus_items, sample_size)

    out: List[Dict[str, Any]] = []
    for i, plus in enumerate(sampled_plus, start=1):
        locomo_item = rng.choice(locomo_items)
        ctx = _build_context(plus, locomo_item)
        out.append(
            {
                "sample_id": f"cog_{i:04d}",
                "conversation_id": f"conv_{i:04d}",
                "relation_type": plus.get("relation_type", "unknown"),
                "full_dialogue_history": ctx["full_dialogue_history"],
                "cue_dialogue": plus.get("cue_dialogue", ""),
                "cue_position": ctx["cue_position"],
                "trigger_query": plus.get("trigger_query", ""),
                "trigger_position": ctx["trigger_position"],
                "time_gap": plus.get("time_gap", "unknown"),
                "stitch_meta": {
                    "cue_time": ctx["cue_time"],
                    "query_time": ctx["query_time"],
                },
            }
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=True, indent=2)

    print(f"Wrote {len(out)} cognitive samples to: {output_path}")
    relation_counts: Dict[str, int] = {}
    for row in out:
        relation = row["relation_type"]
        relation_counts[relation] = relation_counts.get(relation, 0) + 1
    print(f"Relation distribution: {relation_counts}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare stitched cognitive samples for benchmark runs.")
    parser.add_argument("--input", required=True, help="Path to Locomo-Plus cognitive json")
    parser.add_argument("--locomo", required=True, help="Path to locomo10.json")
    parser.add_argument("--output", default="./data/cognitive_samples.json", help="Output path")
    parser.add_argument("--sample-size", type=int, default=100, help="Random sample size")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()
    prepare(args.input, args.locomo, args.output, args.sample_size, args.seed)


if __name__ == "__main__":
    main()
