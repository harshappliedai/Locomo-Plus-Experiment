# Cognitive benchmark results — Mem0, Letta, Zep (401 pool)

Benchmark outputs for all three memory systems evaluated on every row in `cognitive_samples_401_seed42.json`.

## Files

| File | Description |
|------|-------------|
| `cognitive_samples_401_seed42.json` | Copy of the benchmark input pool |
| `judge_results.json` | **1203** judge verdict rows (401 samples x 3 systems) |
| `responses.json` | **1203** model response rows |
| `summary.json` | Aggregated accuracy metrics via `compute_metrics()` |
| `run_meta.json` | Protocol lock and experiment metadata |
| `paper_alignment_report.json` | Protocol compliance verification |
| `FINAL_REPORT.md` / `FINAL_REPORT.json` | Full statistical report (Cochran Q, McNemar, kappa, category breakdowns) |
| `FINAL_SCORES.md` / `FINAL_SCORES.json` | Per-system scores with Wilson 95% CIs |

## Regenerate reports

```bash
python scripts/compute_final_cognitive401_scores.py
python scripts/build_cognitive401_final_report.py
```
