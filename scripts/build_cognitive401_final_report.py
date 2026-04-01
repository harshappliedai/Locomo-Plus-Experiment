#!/usr/bin/env python3
"""
Build comprehensive FINAL_REPORT.md + FINAL_REPORT.json in
all_three_benchmarks_cognitive_results/.

Includes: correct/wrong totals, pool-canonical categories, Wilson CIs, Cochran Q,
McNemar (Holm), Fleiss & Cohen kappa, agreement patterns, sample ID lists.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from evaluation.metrics import _bucket_time_gap, compute_metrics  # noqa: E402

try:
    from statsmodels.stats.contingency_tables import cochrans_q, mcnemar
    from statsmodels.stats.inter_rater import aggregate_raters, cohens_kappa, fleiss_kappa
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


def _labels_matrix(judgments: List[dict]) -> Tuple[np.ndarray, List[str]]:
    by_sid: Dict[str, Dict[str, int]] = defaultdict(dict)
    for row in judgments:
        sid = str(row.get("sample_id", ""))
        sys = str(row.get("system", "")).lower()
        if sys not in SYSTEMS:
            continue
        lab = str(row.get("label", "wrong")).lower()
        by_sid[sid][sys] = 1 if lab == "correct" else 0
    missing = [s for s, d in by_sid.items() if set(d.keys()) != set(SYSTEMS)]
    if missing:
        raise ValueError(f"Incomplete triples: {len(missing)}")
    sids = sorted(by_sid.keys(), key=lambda x: int(x.split("_")[1]))
    mat = np.array([[by_sid[s][sys] for sys in SYSTEMS] for s in sids], dtype=np.float64)
    return mat, sids


def _mcnemar_pair(col_a: np.ndarray, col_b: np.ndarray) -> Dict[str, Any]:
    both_fail = int(np.sum((col_a == 0) & (col_b == 0)))
    a_ok_b_fail = int(np.sum((col_a == 1) & (col_b == 0)))
    a_fail_b_ok = int(np.sum((col_a == 0) & (col_b == 1)))
    both_ok = int(np.sum((col_a == 1) & (col_b == 1)))
    table = [[both_fail, a_fail_b_ok], [a_ok_b_fail, both_ok]]
    res = mcnemar(table, exact=True)
    return {
        "contingency_table": {
            "rows_first_rater_second_rater": ["[both_wrong, first_wrong_second_ok]", "[first_ok_second_wrong, both_ok]"],
            "counts": table,
        },
        "n_both_fail": both_fail,
        "n_first_ok_second_fail": a_ok_b_fail,
        "n_first_fail_second_ok": a_fail_b_ok,
        "n_both_ok": both_ok,
        "p_value": float(res.pvalue),
        "statistic": float(res.statistic) if hasattr(res.statistic, "__float__") else res.statistic,
    }


def _cohen_table(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    t = np.zeros((2, 2), dtype=float)
    for i in range(len(a)):
        t[int(a[i]), int(b[i])] += 1
    return t


def main() -> None:
    bundle = ROOT / "all_three_benchmarks_cognitive_results"
    jr_path = bundle / "judge_results.json"
    pool_path = bundle / "cognitive_samples_401_seed42.json"
    if not jr_path.exists() or not pool_path.exists():
        raise SystemExit("Need judge_results.json and cognitive_samples_401_seed42.json in bundle.")

    judgments: List[dict] = json.loads(jr_path.read_text(encoding="utf-8"))
    pool: List[dict] = json.loads(pool_path.read_text(encoding="utf-8"))
    pool_by_id = {r["sample_id"]: r for r in pool}

    mat, sids = _labels_matrix(judgments)
    n = mat.shape[0]

    # --- Overall correct / wrong ---
    overall_rw: Dict[str, Dict[str, int]] = {}
    for j, sys in enumerate(SYSTEMS):
        col = mat[:, j]
        c = int(col.sum())
        overall_rw[sys] = {"correct": c, "wrong": n - c, "n": n}

    # --- Cochran Q ---
    cq = cochrans_q(mat, return_object=True)

    # --- McNemar x3 + Holm ---
    pairs = [("mem0", "letta", 0, 1), ("mem0", "zep", 0, 2), ("letta", "zep", 1, 2)]
    mcnemar_out: Dict[str, Any] = {}
    pvals: List[float] = []
    keys: List[str] = []
    for name_a, name_b, ia, ib in pairs:
        key = f"{name_a}_vs_{name_b}"
        d = _mcnemar_pair(mat[:, ia], mat[:, ib])
        d["contrast"] = f"{name_a} (rows) vs {name_b} (cols) in 2x2 McNemar setup"
        mcnemar_out[key] = d
        pvals.append(d["p_value"])
        keys.append(key)
    reject, p_corr, _, _ = multipletests(pvals, method="holm")
    for i, key in enumerate(keys):
        mcnemar_out[key]["holm_adjusted_p"] = float(p_corr[i])
        mcnemar_out[key]["holm_reject_alpha_0.05"] = bool(reject[i])

    # --- Fleiss kappa (wrong=0, correct=1) ---
    agg_table, _cats = aggregate_raters(mat.astype(int), n_cat=2)
    fleiss = float(fleiss_kappa(agg_table))

    # --- Cohen kappa pairwise (judge labels as nominal) ---
    cohen_pairwise: Dict[str, Any] = {}
    for name_a, name_b, ia, ib in pairs:
        key = f"{name_a}_vs_{name_b}"
        tab = _cohen_table(mat[:, ia], mat[:, ib])
        kr = cohens_kappa(tab, return_results=True)
        cohen_pairwise[key] = {
            "confusion_counts_rows_{}_cols_{}".format(name_a, name_b): tab.tolist(),
            "kappa": float(kr.kappa),
            "std_kappa": float(kr.std_kappa) if kr.std_kappa is not None else None,
            "z_stat": float(kr.z_stat) if hasattr(kr, "z_stat") and kr.z_stat is not None else None,
            "pvalue": float(kr.pvalue) if hasattr(kr, "pvalue") and kr.pvalue is not None else None,
        }

    # --- How many systems correct per item ---
    k_correct = mat.sum(axis=1).astype(int)
    agreement_k: Dict[str, int] = {
        "exactly_0_correct": int(np.sum(k_correct == 0)),
        "exactly_1_correct": int(np.sum(k_correct == 1)),
        "exactly_2_correct": int(np.sum(k_correct == 2)),
        "exactly_3_correct": int(np.sum(k_correct == 3)),
    }
    all_three_correct_ids = [sids[i] for i in range(n) if k_correct[i] == 3]
    all_three_wrong_ids = [sids[i] for i in range(n) if k_correct[i] == 0]

    # Pattern (mem0,letta,zep) as string
    pattern_counts: Dict[str, int] = {}
    for i in range(n):
        pat = tuple(int(mat[i, j]) for j in range(3))
        pattern_counts[str(pat)] = pattern_counts.get(str(pat), 0) + 1

    # Pairwise raw agreement rate
    pairwise_agree: Dict[str, float] = {}
    for name_a, name_b, ia, ib in pairs:
        key = f"{name_a}_vs_{name_b}"
        pairwise_agree[key] = float(np.mean(mat[:, ia] == mat[:, ib]))

    # --- Pool-canonical relation + gap stratification ---
    by_rel: Dict[str, Dict[str, Dict[str, Any]]] = {s: {} for s in SYSTEMS}
    by_gap: Dict[str, Dict[str, Dict[str, Any]]] = {s: {} for s in SYSTEMS}

    rel_cells: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))
    gap_cells: Dict[str, Dict[str, List[int]]] = defaultdict(lambda: defaultdict(list))

    for i, sid in enumerate(sids):
        pr = pool_by_id.get(sid)
        if not pr:
            continue
        rel = str(pr.get("relation_type", "unknown"))
        gap = _bucket_time_gap(str(pr.get("time_gap", "")))
        for j, sys in enumerate(SYSTEMS):
            bit = int(mat[i, j])
            rel_cells[rel][sys].append(bit)
            gap_cells[gap][sys].append(bit)

    def finalize_strata(cells: Dict[str, Dict[str, List[int]]]) -> Dict[str, Dict[str, Dict[str, Any]]]:
        out: Dict[str, Dict[str, Dict[str, Any]]] = {s: {} for s in SYSTEMS}
        for cat, sysmap in sorted(cells.items()):
            for sys in SYSTEMS:
                bits = sysmap.get(sys, [])
                nc = len(bits)
                corr = sum(bits)
                wr = nc - corr
                lo, hi = _wilson(corr, nc) if nc else (0.0, 0.0)
                out[sys][cat] = {
                    "n": nc,
                    "correct": corr,
                    "wrong": wr,
                    "accuracy": float(corr / nc) if nc else 0.0,
                    "wilson_95_ci": [lo, hi],
                }
        return out

    rel_detail = finalize_strata(rel_cells)
    gap_detail = finalize_strata(gap_cells)

    # Pool distribution
    rel_dist = Counter(str(r.get("relation_type", "unknown")) for r in pool)
    gap_dist = Counter(_bucket_time_gap(str(r.get("time_gap", ""))) for r in pool)

    summary_metrics = compute_metrics(judgments)

    report_json: Dict[str, Any] = {
        "title": "Cognitive 401 — final report (mem0, Letta, Zep)",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "judge_results": str(jr_path.relative_to(ROOT)),
            "pool": str(pool_path.relative_to(ROOT)),
        },
        "n_dialogues": n,
        "n_judgments": len(judgments),
        "overall_correct_wrong": overall_rw,
        "wilson_95_ci_overall": {
            sys: list(_wilson(overall_rw[sys]["correct"], overall_rw[sys]["n"]))
            for sys in SYSTEMS
        },
        "summary_metrics_compute_metrics": summary_metrics,
        "pool_distribution_relation_type": dict(sorted(rel_dist.items())),
        "pool_distribution_time_gap_bucket": dict(sorted(gap_dist.items())),
        "by_relation_type_canonical_from_pool": rel_detail,
        "by_time_gap_bucket_canonical_from_pool": gap_detail,
        "cochran_q": {
            "description": "H0: equal probability of 'correct' across the three systems (same 401 items)",
            "statistic": float(cq.statistic),
            "df": int(cq.df),
            "p_value": float(cq.pvalue),
        },
        "mcnemar_pairwise": mcnemar_out,
        "multiple_comparison": {"method": "Holm-Bonferroni", "family": "three pairwise McNemar tests"},
        "fleiss_kappa_binary": {
            "description": "Fleiss κ on 3 'raters' (systems), categories wrong(0)/correct(1)",
            "kappa": fleiss,
        },
        "cohens_kappa_pairwise": cohen_pairwise,
        "pairwise_label_agreement_rate": pairwise_agree,
        "agreement_number_correct_systems": agreement_k,
        "pattern_counts_mem0_letta_zep_binary": pattern_counts,
        "sample_ids_all_three_correct": all_three_correct_ids,
        "sample_ids_all_three_wrong": all_three_wrong_ids,
    }

    out_json = bundle / "FINAL_REPORT.json"
    out_md = bundle / "FINAL_REPORT.md"
    out_json.write_text(json.dumps(report_json, ensure_ascii=True, indent=2), encoding="utf-8")

    lines: List[str] = []
    L = lines.append

    L("# Cognitive 401 — final report (Mem0, Letta, Zep)\n")
    L(f"**Generated (UTC):** {report_json['generated_at_utc']}  \n")
    L(f"**Dialogues:** {n} | **Judgments:** {len(judgments)} | **Pool:** `cognitive_samples_401_seed42.json`\n")

    L("\n## 1. Executive summary\n")
    L("| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |")
    L("|--------|---------|-------|---|----------|----------------|")
    for sys in SYSTEMS:
        o = overall_rw[sys]
        lo, hi = report_json["wilson_95_ci_overall"][sys]
        acc = o["correct"] / o["n"]
        L(f"| **{sys}** | {o['correct']} | {o['wrong']} | {o['n']} | {acc:.4f} | [{lo:.4f}, {hi:.4f}] |")

    L("\n## 2. Statistical tests (paired on the same 401 dialogues)\n")
    L("### Cochran's Q\n")
    L(f"- **Q** = {cq.statistic:.6f}, **df** = {cq.df}, **p** = {cq.pvalue:.6f}\n")
    L("- *Interpretation:* reject H₀ (equal accuracy across systems) if p < α (e.g. 0.05).\n")

    L("\n### Pairwise McNemar (binary correct/wrong)\n")
    L("*Holm-adjusted p-values across the three tests.*\n")
    for key in keys:
        d = mcnemar_out[key]
        a, b = key.split("_vs_")
        L(f"\n#### `{key}`\n")
        L(f"- Contingency (rows={a}, cols={b}): both wrong **{d['n_both_fail']}**, {a} only **{d['n_first_ok_second_fail']}**, ")
        L(f"{b} only **{d['n_first_fail_second_ok']}**, both correct **{d['n_both_ok']}**\n")
        L(f"- McNemar **p** = {d['p_value']:.6f} | Holm-adjusted **p** = {d['holm_adjusted_p']:.6f} ")
        L(f"| reject α=0.05: **{d['holm_reject_alpha_0.05']}**\n")

    L("\n### Inter-rater agreement on judge labels (wrong=0, correct=1)\n")
    L(f"- **Fleiss' κ** (3 raters): **{fleiss:.4f}**\n")
    L("\n| Pair | Cohen's κ | p-value (H₀: κ=0) |")
    L("|------|-----------|-------------------|")
    for key in keys:
        ck = cohen_pairwise[key]
        pv = ck.get("pvalue")
        pv_s = f"{pv:.6f}" if pv is not None else "—"
        L(f"| {key} | {ck['kappa']:.4f} | {pv_s} |")

    L("\n| Pair | % identical label |")
    L("|------|-------------------|")
    for k, v in pairwise_agree.items():
        L(f"| {k} | {100 * v:.2f}% |")

    L("\n## 3. Agreement across systems (per dialogue)\n")
    for k, v in agreement_k.items():
        L(f"- **{k}:** {v}\n")
    L(f"- **All three correct** (`n={len(all_three_correct_ids)}`): see `FINAL_REPORT.json` → `sample_ids_all_three_correct`\n")
    L(f"- **All three wrong** (`n={len(all_three_wrong_ids)}`): see `FINAL_REPORT.json` → `sample_ids_all_three_wrong`\n")
    L("\n### Pattern counts `(mem0, letta, zep)` as 0/1\n")
    for pat, cnt in sorted(pattern_counts.items(), key=lambda x: -x[1]):
        L(f"- {pat}: **{cnt}**\n")

    L("\n## 4. Pool distribution (ground-truth design)\n")
    L("### `relation_type` counts in pool\n")
    for k, v in sorted(rel_dist.items()):
        L(f"- **{k}:** {v}\n")
    L("\n### `time_gap` bucket counts (from pool text via `evaluation.metrics._bucket_time_gap`)\n")
    for k, v in sorted(gap_dist.items()):
        L(f"- **{k}:** {v}\n")

    L("\n## 5. Category-wise results (canonical labels from **pool** JSON)\n")
    L("*Each system has the same **n** per category (401 split by pool metadata).*\n")

    rel_cats = sorted(rel_dist.keys())
    L("\n### By `relation_type`\n")
    for rel in rel_cats:
        L(f"\n#### `{rel}`\n")
        L("| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |")
        L("|--------|---------|-------|---|----------|----------------|")
        for sys in SYSTEMS:
            cell = rel_detail[sys].get(rel, {"n": 0, "correct": 0, "wrong": 0, "accuracy": 0.0, "wilson_95_ci": [0.0, 0.0]})
            lo, hi = cell["wilson_95_ci"]
            L(
                f"| **{sys}** | {cell['correct']} | {cell['wrong']} | {cell['n']} | "
                f"{cell['accuracy']:.4f} | [{lo:.4f}, {hi:.4f}] |"
            )

    gap_cats = sorted(gap_dist.keys())
    L("\n### By time-gap bucket\n")
    for gap in gap_cats:
        L(f"\n#### `{gap}`\n")
        L("| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |")
        L("|--------|---------|-------|---|----------|----------------|")
        for sys in SYSTEMS:
            cell = gap_detail[sys].get(
                gap, {"n": 0, "correct": 0, "wrong": 0, "accuracy": 0.0, "wilson_95_ci": [0.0, 0.0]}
            )
            lo, hi = cell["wilson_95_ci"]
            L(
                f"| **{sys}** | {cell['correct']} | {cell['wrong']} | {cell['n']} | "
                f"{cell['accuracy']:.4f} | [{lo:.4f}, {hi:.4f}] |"
            )

    L("\n## 6. Files in this folder\n")
    L("- `FINAL_REPORT.json` — machine-readable duplicate of this report\n")
    L("- `FINAL_SCORES.json` / `FINAL_SCORES.md` — scores + category detail (judge-row metadata)\n")
    L("- `judge_results.json`, `responses.json`, `summary.json`, `errors.json`, `run_meta.json`\n")

    L("\n## 7. Regenerate\n")
    L("```bash\n")
    L("python scripts/compute_final_cognitive401_scores.py\n")
    L("python scripts/build_cognitive401_final_report.py\n")
    L("```\n")

    out_md.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_md} and {out_json}")


if __name__ == "__main__":
    main()
