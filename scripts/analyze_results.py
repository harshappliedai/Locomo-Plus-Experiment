from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from evaluation.metrics import compute_metrics


def analyze(judge_results_path: str, output_path: str) -> None:
    with open(judge_results_path, "r", encoding="utf-8") as f:
        judgments = json.load(f)
    if not isinstance(judgments, list):
        raise ValueError("judge_results.json must be a list")

    summary: Dict[str, Any] = compute_metrics(judgments)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=True, indent=2)
    print(json.dumps(summary, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze benchmark outputs.")
    parser.add_argument("--judge-results", default="./results/judge_results.json")
    parser.add_argument("--output", default="./results/summary.json")
    args = parser.parse_args()
    analyze(args.judge_results, args.output)


if __name__ == "__main__":
    main()
