# Cognitive benchmark seeds

## Pool size (Locomo-Plus)

`data/locomo_plus/data/locomo_plus.json` has **401** cognitive rows. Use `--sample-size 401` (or less) in `prepare_data.py`.

## Two-stage seeding

1. **Build the pool** -- `scripts/prepare_data.py`  
   - `--seed` controls which Locomo-Plus rows are sampled **and** which LoCoMo conversation is stitched per row.  
   - Default: `42`.  
   - Example (full pool):

   ```bash
   python scripts/prepare_data.py \
     --input data/locomo_plus/data/locomo_plus.json \
     --locomo data/locomo_plus/data/locomo10.json \
     --output data/cognitive_samples_401_seed42.json \
     --sample-size 401 \
     --seed 42
   ```

2. **Pick a benchmark subset** (optional) -- `scripts/sample_cognitive_subset.py`  
   - `--seed` here is **only** for choosing which rows from the pool file to run (does not re-stitch).  
   - Use a **different** seed than step 1 for a random subset from the same pool.

   ```bash
   python scripts/sample_cognitive_subset.py \
     --input data/cognitive_samples_401_seed42.json \
     --output data/cognitive_subset_50_seed99.json \
     --n 50 \
     --seed 99
   ```

## Running the benchmark

```bash
BENCH_SYSTEMS=mem0,letta,zep \
COGNITIVE_SAMPLES_PATH=./data/cognitive_samples_401_seed42.json \
RESULTS_DIR=./results \
python scripts/run_benchmark.py
```

## Generating reports

```bash
python scripts/compute_final_cognitive401_scores.py
python scripts/build_cognitive401_final_report.py
```
