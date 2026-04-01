# LoCoMo-Plus Cognitive Benchmark: Mem0 vs Letta vs Zep

Companion repository for *The Architecture of AI Agent Memory*. **Chapter 6** of the whitepaper describes the experimental design; **Chapter 7** presents the results and analysis. This repository provides the full benchmark harness, raw data, and results so readers can inspect, verify, and reproduce every number in the paper.

To our knowledge, this is the **first three-way comparison of Letta, Mem0, and Zep on the LoCoMo-Plus 2026 cognitive benchmark**. All three systems share the same backbone (`gpt-4o-mini`), judge (`gemini-2.5-flash`), and locked hyperparameters to ensure a fair comparison.

## Key Finding

**Letta outperforms Mem0 by 34.4% on the LoCoMo-Plus cognitive benchmark, with Zep close behind.** The overall difference is statistically significant (Cochran's Q = 7.14, p = 0.028), rejecting the null hypothesis that all three architectures perform equally.

The most robust conclusion is not merely that Letta finishes first. **Self-managing memory shows a significant aggregate advantage over extraction-based memory**, while graph-based temporal memory reveals a different pattern of strengths visible in the category breakdowns.

## Overall Cognitive Performance

401 non-overlapping LoCoMo-Plus dialogues, all three systems judged on identical samples.

| System | Architecture | Correct | Wrong | Accuracy | Wilson 95% CI |
|--------|-------------|---------|-------|----------|---------------|
| **Letta** | Self-managing | 97 | 304 | 24.2% | [20.3%, 28.6%] |
| **Zep** | Graph-based | 89 | 312 | 22.2% | [18.4%, 26.5%] |
| **Mem0** | Extraction-based | 72 | 329 | 18.0% | [14.5%, 22.0%] |

Pairwise McNemar tests (Holm-adjusted):

| Comparison | p-value | Significant at 0.05? |
|------------|---------|---------------------|
| Mem0 vs Letta | 0.040 | Yes |
| Mem0 vs Zep | 0.171 | No |
| Letta vs Zep | 0.466 | No |

Zep occupies an intermediate position: architecturally distinct and descriptively competitive, but not separable from either competitor on aggregate score alone.

## Performance by Relation Type

The aggregate ranking is useful, but it is not the most interesting part of the story. Once broken down by relation type, the three architectures reveal sharply different strengths.

| Relation Type | n | Mem0 | Letta | Zep |
|---------------|---|------|-------|-----|
| **Causal** | 101 | 11.9% | 12.9% | **20.8%** |
| **Goal** | 100 | 23.0% | **30.0%** | 21.0% |
| **State** | 100 | 15.0% | **28.0%** | 22.0% |
| **Value** | 100 | 22.0% | **26.0%** | 25.0% |

- **Letta's strength -- goals and state.** Letta leads on goal reasoning (30.0%, the highest single-category score in the experiment) and state reasoning (28.0%). These are exactly the cues a self-managing memory architecture would be expected to preserve: forward-looking, identity-linked goals and situational context that appears only as passing remarks.
- **Zep's strength -- causal reasoning.** Zep leads decisively on causal reasoning at 20.8%, well ahead of both competitors. A temporal knowledge graph is naturally suited to preserving structured relationships among events across time.
- **Values -- convergence.** All three systems cluster together on value reasoning (22--26%), suggesting values may be easier to retain because they are often expressed with clarity and repetition.

## Performance by Time Gap

| Time Gap | n | Mem0 | Letta | Zep |
|----------|---|------|-------|-----|
| Short (1--2 weeks) | 91 | 15.4% | **27.5%** | **27.5%** |
| Long (3+ months) | 300 | 19.0% | **22.3%** | 20.7% |

On shorter gaps, Letta and Zep are tied at 27.5%, both far ahead of Mem0. On longer gaps (3+ months, the majority of the benchmark), the systems converge toward a narrower band. All current approaches face the same underlying challenge of memory decay over very long horizons -- Letta and Zep appear to degrade more gracefully.

## Agreement Across Systems

Of the 401 dialogues, **237 (59.1%) were answered incorrectly by all three** systems. Only **27 (6.7%) were answered correctly by all three**. None of the architectures has solved cognitive memory.

The disagreement cases reveal architectural fingerprints: Letta alone was correct in 40 cases, Zep alone in 32, Mem0 alone in 25. Letta's unique successes tend to appear where goal or state continuity matters; Zep's where causal chains matter.

Fleiss' kappa = 0.324 (fair agreement). The systems broadly agree on what is easy and what is hard, but diverge enough to suggest they are capturing genuinely different parts of the memory problem.

## The Architectural Tradeoff

The results reinforce a broader tradeoff:

- **Extraction-based** (Mem0) -- optimizes for **precision**; preserves explicit information in retrievable form; strongest on factual recall.
- **Self-managing** (Letta) -- optimizes for **abstraction**; preserves a compressed but behaviorally meaningful representation of what continues to matter; strongest on goals and state.
- **Graph-based** (Zep) -- optimizes for **structure**; preserves entities, relationships, and temporal evolution explicitly; strongest on causal linkage across time.

The results do not imply that one architecture is universally best. They imply something more useful: **different architectures are matched to different cognitive demands**.

## Protocol Lock

Every run enforces identical conditions via automated preflight checks:

| Parameter | Value |
|-----------|-------|
| Backbone model | `gpt-4o-mini` |
| Judge model | `gemini-2.5-flash` (Google) |
| Temperature | 0 (both generation and judging) |
| Max tokens | 512 |
| Query mode | Unified conversational (no task-type disclosure) |
| Labels | Binary: `correct` / `wrong` |

## Repository Structure

```
config.py                      # Environment loading, protocol lock, compliance checks
requirements.txt               # Python dependencies
.env.example                   # Template for API keys and settings

systems/
  mem0_runner.py               # Mem0 ingestion + retrieval + generation
  letta_runner.py              # Letta agent ingestion + query
  zep_runner.py                # Zep graph/vector ingestion + retrieval + generation

evaluation/
  judge.py                     # LLM-as-judge runner
  judge_prompts.py             # Locked judge prompt template
  metrics.py                   # Accuracy aggregation utilities

scripts/
  run_benchmark.py             # End-to-end benchmark orchestrator
  prepare_data.py              # Cognitive sample extraction from LoCoMo-Plus
  analyze_results.py           # Summary computation from judge results
  sample_cognitive_subset.py   # Draw reproducible random subsets
  compute_final_cognitive401_scores.py   # Wilson CIs, Cochran Q, McNemar
  build_cognitive401_final_report.py     # Generate FINAL_REPORT.md/.json

data/
  cognitive_samples_401_seed42.json      # 401-sample benchmark pool (seed=42)
  COGNITIVE_SEEDS.md                     # Seeding methodology documentation

all_three_benchmarks_cognitive_results/  # Final outputs
  FINAL_REPORT.md / .json               # Full statistical report
  FINAL_SCORES.md / .json               # Per-system scores with CIs
  judge_results.json                     # 1203 judge verdicts (401 x 3 systems)
  responses.json                         # 1203 model responses
  summary.json                           # Aggregated metrics
  run_meta.json                          # Protocol metadata

docker-compose.zep-local.yml   # Local Zep stack (Docker)
zep.local.yaml                 # Zep configuration
```

## Reproducing the Experiment

### Prerequisites

- Python 3.9+
- Docker (for Zep)
- A running [Letta](https://github.com/letta-ai/letta) server
- OpenAI API key (backbone)
- Google AI Studio API key (judge)

### 1. Install dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env:
#   OPENAI_API_KEY=sk-...
#   GOOGLE_API_KEY=AIza...
#   BENCH_SYSTEMS=mem0,letta,zep
```

### 3. Start infrastructure

```bash
# Start Letta server (see Letta docs)
# Start Zep:
docker compose -f docker-compose.zep-local.yml up -d
```

### 4. Prepare data

The pre-built pool (`data/cognitive_samples_401_seed42.json`) is included in this repo. To regenerate it from scratch:

```bash
python scripts/prepare_data.py \
  --input data/locomo_plus/data/locomo_plus.json \
  --locomo data/locomo_plus/data/locomo10.json \
  --output data/cognitive_samples_401_seed42.json \
  --sample-size 401 --seed 42
```

### 5. Run the benchmark

```bash
BENCH_SYSTEMS=mem0,letta,zep \
COGNITIVE_SAMPLES_PATH=./data/cognitive_samples_401_seed42.json \
RESULTS_DIR=./results \
python scripts/run_benchmark.py
```

### 6. Generate reports

```bash
python scripts/compute_final_cognitive401_scores.py
python scripts/build_cognitive401_final_report.py
```

## Limitations

- The three systems necessarily expose memory differently at the implementation level, even though the benchmark is matched on items, model family, and scoring protocol.
- The study relies on remote APIs for generation and judging, uses a single blinded judge in the final evaluation, and depends mainly on one benchmark family for the cognitive analysis.
- Results are best understood as strong evidence of meaningful architectural differences, not as a final universal ranking of memory systems.

## Citation

This benchmark is based on the LoCoMo-Plus dataset:

```bibtex
@article{maharana2024locomoplus,
  title={Evaluating Very Long-Term Conversational Memory of LLM Agents},
  author={Maharana, Adyasha and Lee, Dong-Ho and Tuber, Sergey and Olausson, Tristan Thrush and Palangi, Mohit and Bansal, Mohit},
  journal={arXiv preprint arXiv:2602.10715},
  year={2024}
}
```
