#!/usr/bin/env python3
"""
Draw a random subset from an existing cognitive_samples*.json list.

Use this AFTER prepare_data.py so the pool is fixed; this script only controls
which rows you benchmark (reproducible via --seed).

Example (smoke, all three systems):
  COGNITIVE_SAMPLES_PATH=./data/cognitive_smoke3_seed2026.json \\
  RESULTS_DIR=./results_smoke3_all3 \\
  BENCH_SYSTEMS=mem0,letta,zep ZEP_API_KEY=... \\
  ./.venv/bin/python -m scripts.run_benchmark
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any, Dict, List, Set


def cognitive_fingerprint(row: Dict[str, Any]) -> str:
    """Stable identity for Locomo-Plus cognitive rows (same as in the 150 / 401 pools)."""
    parts = (
        str(row.get("relation_type", "")),
        str(row.get("time_gap", "")),
        str(row.get("cue_dialogue", "")),
        str(row.get("trigger_query", "")),
    )
    return hashlib.sha256("\n---\n".join(parts).encode("utf-8")).hexdigest()


def _load_exclusion_fingerprints(paths: List[str]) -> Set[str]:
    out: Set[str] = set()
    for path in paths:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            raise ValueError(f"Exclude file must be a JSON list: {path}")
        for row in raw:
            if isinstance(row, dict):
                out.add(cognitive_fingerprint(row))
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Random subset of cognitive JSON list.")
    p.add_argument("--input", required=True, help="Path to cognitive samples JSON (list).")
    p.add_argument("--output", required=True, help="Output path for subset JSON.")
    p.add_argument("--n", type=int, required=True, help="Number of samples to draw.")
    p.add_argument("--seed", type=int, required=True, help="Random seed (subset selection only).")
    p.add_argument(
        "--exclude-from",
        action="append",
        default=[],
        metavar="PATH",
        help="Optional JSON list(s) of cognitive samples; rows matching cue/trigger/time_gap/relation are removed from the pool before sampling (repeat flag for multiple files).",
    )
    args = p.parse_args()

    data: List[Dict[str, Any]] = json.loads(Path(args.input).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Input must be a JSON list.")

    exclude_keys = _load_exclusion_fingerprints(args.exclude_from)
    if exclude_keys:
        before = len(data)
        data = [row for row in data if cognitive_fingerprint(row) not in exclude_keys]
        removed = before - len(data)
        print(
            f"  --exclude-from: removed {removed} rows from pool ({before} -> {len(data)}); "
            f"{len(exclude_keys)} exclusion fingerprints loaded"
        )

    if args.n <= 0 or args.n > len(data):
        raise ValueError(f"--n must be in [1, {len(data)}], got {args.n}")

    rng = random.Random(args.seed)
    subset = rng.sample(data, args.n)

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(subset, ensure_ascii=True, indent=2), encoding="utf-8")
    print(f"Wrote {len(subset)} samples to {args.output}")
    print(f"  pool={args.input} (len={len(data)}), seed={args.seed}")
    print("  sample_ids:", [s.get("sample_id") for s in subset])


if __name__ == "__main__":
    main()
