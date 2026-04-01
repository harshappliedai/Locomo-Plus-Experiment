from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Tuple

try:
    from statsmodels.stats.contingency_tables import mcnemar
    from statsmodels.stats.proportion import proportion_confint
except ImportError:
    mcnemar = None  # type: ignore[assignment]
    proportion_confint = None  # type: ignore[assignment]


def _bucket_time_gap(time_gap: str) -> str:
    t = (time_gap or "").lower()
    if "week" in t:
        return "short_1_to_2_weeks"
    if "month" in t and ("1" in t or "2" in t or "3" in t):
        return "medium_1_to_3_months"
    if "month" in t or "+" in t:
        return "long_3_plus_months"
    return "unknown"


def _acc(rows: List[Dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return sum(1 for r in rows if r.get("label") == "correct") / len(rows)


def compute_metrics(judgments: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_system: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in judgments:
        by_system[row["system"]].append(row)

    output: Dict[str, Any] = {}
    for system_name, rows in by_system.items():
        by_relation: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_gap: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_relation[row.get("relation_type", "unknown")].append(row)
            by_gap[_bucket_time_gap(row.get("time_gap", ""))].append(row)

        output[system_name] = {
            "overall_accuracy": _acc(rows),
            "total_samples": len(rows),
            "by_relation_type": {k: _acc(v) for k, v in by_relation.items()},
            "by_time_gap_bucket": {k: _acc(v) for k, v in by_gap.items()},
        }

    return output


def _pair_key(row: Dict[str, Any]) -> str:
    """Unique key for a sample: (run, sample_id) when run present, else sample_id."""
    run = row.get("run")
    sid = str(row.get("sample_id", ""))
    return f"{run}::{sid}" if run else sid


def _validate_paired(judgments: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    """Group by (run, sample_id), keep only samples with both mem0 and letta."""
    by_sample: Dict[str, Dict[str, str]] = defaultdict(dict)
    for row in judgments:
        key = _pair_key(row)
        sys = str(row.get("system", "")).lower()
        label = str(row.get("label", "wrong")).lower()
        if label not in ("correct", "wrong"):
            label = "wrong"
        if sys in ("mem0", "letta"):
            by_sample[key][sys] = label
    return {k: v for k, v in by_sample.items() if set(v.keys()) == {"mem0", "letta"}}


def _build_mcnemar_table(by_sample: Dict[str, Dict[str, str]]) -> List[List[int]]:
    """2x2 contingency for McNemar. Rows=Letta, Cols=Mem0."""
    a = b = c = d = 0
    for labels in by_sample.values():
        letta_ok = labels.get("letta") == "correct"
        mem0_ok = labels.get("mem0") == "correct"
        if letta_ok and mem0_ok:
            a += 1
        elif letta_ok and not mem0_ok:
            b += 1
        elif not letta_ok and mem0_ok:
            c += 1
        else:
            d += 1
    return [[d, c], [b, a]]


def _wilson_ci(count: int, nobs: int, alpha: float = 0.05) -> Tuple[float, float]:
    if nobs == 0 or proportion_confint is None:
        return (0.0, 0.0)
    low, high = proportion_confint(count, nobs, alpha=alpha, method="wilson")
    return (float(low), float(high))


def compute_stats_with_ci(judgments: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Same as compute_metrics plus Wilson 95% CIs and McNemar test for Letta vs Mem0.
    Requires paired design (each sample has both mem0 and letta). Requires statsmodels.
    """
    base = compute_metrics(judgments)
    if mcnemar is None or proportion_confint is None:
        base["_ci_95"] = None
        base["_mcnemar"] = None
        base["_stats_note"] = "statsmodels not installed; CIs and McNemar unavailable"
        return base

    by_sample = _validate_paired(judgments)
    n = len(by_sample)
    if n == 0:
        base["_ci_95"] = None
        base["_mcnemar"] = None
        base["_stats_note"] = "No valid paired samples"
        return base

    mem0_correct = sum(1 for labels in by_sample.values() if labels.get("mem0") == "correct")
    letta_correct = sum(1 for labels in by_sample.values() if labels.get("letta") == "correct")

    base["_ci_95"] = {
        "mem0": {"accuracy": mem0_correct / n, "ci_95": list(_wilson_ci(mem0_correct, n)), "n": n},
        "letta": {"accuracy": letta_correct / n, "ci_95": list(_wilson_ci(letta_correct, n)), "n": n},
    }

    table = _build_mcnemar_table(by_sample)
    result = mcnemar(table, exact=True)
    stat = result.statistic
    base["_mcnemar"] = {
        "p_value": float(result.pvalue),
        "statistic": float(stat) if hasattr(stat, "__float__") else stat,
    }
    return base
