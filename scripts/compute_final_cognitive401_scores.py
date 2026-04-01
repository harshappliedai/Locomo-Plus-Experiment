#!/usr/bin/env python3
"""
Compute final scores from 401×3 cognitive judgments.

Reads:  all_three_benchmarks_cognitive_results/judge_results.json
Writes: all_three_benchmarks_cognitive_results/FINAL_SCORES.json
        all_three_benchmarks_cognitive_results/FINAL_SCORES.md
Updates: all_three_benchmarks_cognitive_results/summary.json (same as compute_metrics)
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.metrics import _bucket_time_gap, compute_metrics  # noqa: E402

try:
    from statsmodels.stats.contingency_tables import cochrans_q, mcnemar
    from statsmodels.stats.multitest import multipletests
    from statsmodels.stats.proportion import proportion_confint
except ImportError as e:
    raise SystemExit(f"statsmodels required: {e}") from e


SYSTEMS = ("mem0", "letta", "zep")


def _wilson(count: int, n: int, alpha: float = 0.05) -> Tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    lo, hi = proportion_confint(count, n, alpha=alpha, method="wilson")
    return (float(lo), float(hi))


def _build_matrix(judgments: List[dict]) -> Tuple[np.ndarray, List[str]]:
    """N×3 binary matrix (correct=1) in SYSTEMS column order; aligned sample_ids."""
    by_sid: Dict[str, Dict[str, int]] = defaultdict(dict)
    for row in judgments:
        sid = str(row.get("sample_id", ""))
        sys = str(row.get("system", "")).lower()
        if sys not in SYSTEMS:
            continue
        lab = str(row.get("label", "wrong")).lower()
        by_sid[sid][sys] = 1 if lab == "correct" else 0

    missing = [sid for sid, d in by_sid.items() if set(d.keys()) != set(SYSTEMS)]
    if missing:
        raise ValueError(f"Incomplete triples: {len(missing)} samples, e.g. {missing[:5]}")

    sids = sorted(by_sid.keys(), key=lambda x: int(x.split("_")[1]))
    mat = np.array([[by_sid[s][sys] for sys in SYSTEMS] for s in sids], dtype=np.float64)
    return mat, sids


def _stratified_stats(
    judgments: List[dict],
    key_fn,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    """For each system and category: n, correct, accuracy, wilson_95_ci."""
    cells: Dict[str, Dict[str, List[dict]]] = defaultdict(lambda: defaultdict(list))
    for row in judgments:
        sys = str(row.get("system", "")).lower()
        if sys not in SYSTEMS:
            continue
        cat = key_fn(row)
        cells[sys][cat].append(row)

    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for sys in SYSTEMS:
        out[sys] = {}
        for cat, rows in sorted(cells[sys].items()):
            correct = sum(1 for r in rows if str(r.get("label", "")).lower() == "correct")
            n = len(rows)
            lo, hi = _wilson(correct, n)
            out[sys][cat] = {
                "n": n,
                "correct": correct,
                "accuracy": float(correct / n) if n else 0.0,
                "wilson_95_ci": [lo, hi],
            }
    return out


def _mcnemar_pair(col_a: np.ndarray, col_b: np.ndarray) -> Dict[str, Any]:
    """col_a, col_b are 0/1 vectors length N."""
    both_fail = int(np.sum((col_a == 0) & (col_b == 0)))
    a_ok_b_fail = int(np.sum((col_a == 1) & (col_b == 0)))
    a_fail_b_ok = int(np.sum((col_a == 0) & (col_b == 1)))
    both_ok = int(np.sum((col_a == 1) & (col_b == 1)))
    table = [[both_fail, a_fail_b_ok], [a_ok_b_fail, both_ok]]
    res = mcnemar(table, exact=True)
    return {
        "n_both_fail": both_fail,
        "n_first_ok_second_fail": a_ok_b_fail,
        "n_first_fail_second_ok": a_fail_b_ok,
        "n_both_ok": both_ok,
        "p_value": float(res.pvalue),
        "statistic": float(res.statistic) if hasattr(res.statistic, "__float__") else res.statistic,
    }


def main() -> None:
    bundle = ROOT / "all_three_benchmarks_cognitive_results"
    jr_path = bundle / "judge_results.json"
    if not jr_path.exists():
        raise SystemExit(f"Missing {jr_path}; run the benchmark first.")

    judgments: List[dict] = json.loads(jr_path.read_text(encoding="utf-8"))
    n_expect = len(judgments)
    if n_expect != 401 * 3:
        print(f"Warning: expected 1203 judgments, got {n_expect}", file=sys.stderr)

    summary = compute_metrics(judgments)
    (bundle / "summary.json").write_text(json.dumps(summary, ensure_ascii=True, indent=2), encoding="utf-8")

    mat, _ = _build_matrix(judgments)
    n = mat.shape[0]

    cq = cochrans_q(mat, return_object=True)

    systems_block = {}
    for j, sys in enumerate(SYSTEMS):
        col = mat[:, j]
        correct = int(col.sum())
        systems_block[sys] = {
            "correct": correct,
            "n": n,
            "accuracy": float(correct / n) if n else 0.0,
            "wilson_95_ci": list(_wilson(correct, n)),
        }

    pairs = [
        ("mem0", "letta", 0, 1),
        ("mem0", "zep", 0, 2),
        ("letta", "zep", 1, 2),
    ]
    mcnemar_raw: Dict[str, Any] = {}
    pvals = []
    keys = []
    for name_a, name_b, ia, ib in pairs:
        key = f"{name_a}_vs_{name_b}"
        d = _mcnemar_pair(mat[:, ia], mat[:, ib])
        d["contrast"] = f"{name_a} (first) vs {name_b} (second) in contingency labels"
        mcnemar_raw[key] = d
        pvals.append(d["p_value"])
        keys.append(key)

    reject, p_corr, _, _ = multipletests(pvals, method="holm")
    for i, key in enumerate(keys):
        mcnemar_raw[key]["holm_adjusted_p"] = float(p_corr[i])
        mcnemar_raw[key]["holm_reject_005"] = bool(reject[i])

    by_relation_detail = _stratified_stats(
        judgments, lambda r: str(r.get("relation_type", "unknown"))
    )
    by_gap_detail = _stratified_stats(
        judgments, lambda r: _bucket_time_gap(str(r.get("time_gap", "")))
    )

    out: Dict[str, Any] = {
        "title": "Final scores \u2014 cognitive 401 pool, all three systems",
        "source": str(jr_path.relative_to(ROOT)),
        "n_samples": n,
        "n_judgments": len(judgments),
        "systems": systems_block,
        "overall_accuracy_from_summary": {s: summary[s]["overall_accuracy"] for s in SYSTEMS},
        "by_relation_type": {s: summary[s]["by_relation_type"] for s in SYSTEMS},
        "by_time_gap_bucket": {s: summary[s]["by_time_gap_bucket"] for s in SYSTEMS},
        "by_relation_type_detail": by_relation_detail,
        "by_time_gap_bucket_detail": by_gap_detail,
        "cochran_q": {
            "description": "Same 401 dialogues; test equality of marginal correct rates across mem0/letta/zep",
            "statistic": float(cq.statistic),
            "df": int(cq.df),
            "p_value": float(cq.pvalue),
        },
        "mcnemar_pairwise": mcnemar_raw,
        "multiple_comparison": {
            "method": "Holm-Bonferroni",
            "family": "three pairwise McNemar tests",
        },
    }

    (bundle / "FINAL_SCORES.json").write_text(json.dumps(out, ensure_ascii=True, indent=2), encoding="utf-8")

    # Markdown report
    md = []
    md.append("# Final scores — cognitive 401 (mem0, Letta, Zep)\n")
    md.append(f"**Samples:** {n} | **Judgments:** {len(judgments)}\n")
    md.append("\n## Overall accuracy & Wilson 95% CI\n")
    md.append("| System | Correct | Accuracy | Wilson 95% CI |")
    md.append("|--------|---------|----------|----------------|")
    for sys in SYSTEMS:
        b = systems_block[sys]
        lo, hi = b["wilson_95_ci"]
        md.append(
            f"| **{sys}** | {b['correct']}/{b['n']} | {b['accuracy']:.4f} | [{lo:.4f}, {hi:.4f}] |"
        )
    md.append("\n## Cochran's Q (identical accuracy across three systems?)\n")
    md.append(
        f"- **Q** = {cq.statistic:.4f}, **df** = {cq.df}, **p** = {cq.pvalue:.6f}\n"
    )
    md.append("\n## Pairwise McNemar (paired per dialogue)\n")
    for key in keys:
        d = mcnemar_raw[key]
        md.append(f"### `{key}`\n")
        md.append(
            f"- Both wrong: {d['n_both_fail']}, {key.split('_vs_')[0]} only: {d['n_first_ok_second_fail']}, "
            f"{key.split('_vs_')[1]} only: {d['n_first_fail_second_ok']}, both correct: {d['n_both_ok']}\n"
        )
        md.append(
            f"- **p** = {d['p_value']:.6f} (Holm-adjusted **p** = {d['holm_adjusted_p']:.6f})\n"
        )
    # Category keys union across systems
    rel_cats = sorted(
        set(c for s in SYSTEMS for c in by_relation_detail[s].keys())
    )
    gap_cats = sorted(
        set(c for s in SYSTEMS for c in by_gap_detail[s].keys())
    )

    md.append("\n## By relation type (n, accuracy, Wilson 95% CI)\n")
    md.append(
        "*`n` can differ slightly per system if `relation_type` metadata varies for the same `sample_id` (rare; 24/401 in this pool).*\n"
    )
    for rel in rel_cats:
        md.append(f"### `{rel}`\n")
        md.append("| System | Correct | n | Accuracy | Wilson 95% CI |")
        md.append("|--------|---------|---|----------|----------------|")
        for sys in SYSTEMS:
            d = by_relation_detail[sys].get(rel)
            if not d:
                md.append(f"| **{sys}** | — | 0 | — | — |")
                continue
            lo, hi = d["wilson_95_ci"]
            md.append(
                f"| **{sys}** | {d['correct']} | {d['n']} | {d['accuracy']:.4f} | [{lo:.4f}, {hi:.4f}] |"
            )
        md.append("\n")

    md.append("\n## By time-gap bucket (n, accuracy, Wilson 95% CI)\n")
    md.append(
        "*Buckets match `evaluation.metrics._bucket_time_gap` (short = week; long = month wording; etc.).*\n"
    )
    for gap in gap_cats:
        md.append(f"### `{gap}`\n")
        md.append("| System | Correct | n | Accuracy | Wilson 95% CI |")
        md.append("|--------|---------|---|----------|----------------|")
        for sys in SYSTEMS:
            d = by_gap_detail[sys].get(gap)
            if not d:
                md.append(f"| **{sys}** | — | 0 | — | — |")
                continue
            lo, hi = d["wilson_95_ci"]
            md.append(
                f"| **{sys}** | {d['correct']} | {d['n']} | {d['accuracy']:.4f} | [{lo:.4f}, {hi:.4f}] |"
            )
        md.append("\n")

    md_text = "".join(s if s.endswith("\n") else s + "\n" for s in md)
    (bundle / "FINAL_SCORES.md").write_text(md_text, encoding="utf-8")
    print(f"Wrote {bundle / 'FINAL_SCORES.json'} and FINAL_SCORES.md")
    print(json.dumps(systems_block, indent=2))
    print("Cochran Q p =", cq.pvalue)


if __name__ == "__main__":
    main()
