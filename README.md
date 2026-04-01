# LoCoMo-Plus Cognitive Benchmark (Letta vs Mem0 vs Zep)

Local-first benchmark harness comparing **Letta**, **Mem0 OSS**, and **Zep** on LoCoMo-Plus cognitive samples, using **`gpt-4o-mini`** as the shared backbone.

## What Is Locked (Paper Alignment)

- Unified conversational query mode (no task-type disclosure)
- Cognitive judge labels are binary: `correct` / `wrong`
- Judge prompt template matches the paper's cognitive-awareness template
- Backbone model: `gpt-4o-mini`
- `temperature=0` and `max_tokens=512` for generation and judging
- Preflight protocol checks fail fast on drift

## Project Layout

- `config.py`: env loading, protocol lock, compliance checks
- `systems/mem0_runner.py`: Mem0 ingestion/retrieval/generation path
- `systems/letta_runner.py`: Letta local agent ingestion/query path
- `systems/zep_runner.py`: Zep graph/vector ingestion/retrieval/generation path
- `evaluation/judge.py`: LLM-as-judge runner
- `evaluation/judge_prompts.py`: locked judge prompt
- `evaluation/metrics.py`: aggregation utilities
- `scripts/prepare_data.py`: cognitive sample extraction
- `scripts/run_benchmark.py`: end-to-end orchestrator
- `scripts/analyze_results.py`: summary computation

## Setup

1. Create virtual env and install deps:
   - `python3 -m venv .venv`
   - `source .venv/bin/activate`
   - `pip install -r requirements.txt`

2. Configure env:
   - Copy `.env.example` to `.env` (already created)
   - Fill `OPENAI_API_KEY` (for backbone)
   - Fill `GOOGLE_API_KEY` (for paper-default judge `gemini-2.5-flash`)
   - Ensure Letta local server is running at `LETTA_BASE_URL`
  - Choose systems with `BENCH_SYSTEMS` (default: `mem0,letta`)
  - If you do not want Zep, keep `zep` out of `BENCH_SYSTEMS`

### Local Zep (Graph + Vector) Quickstart

This repo includes a local stack template:

- `docker-compose.zep-local.yml`
- `zep.local.yaml`

Bring Zep up:

- `docker compose -f docker-compose.zep-local.yml up -d`

Set `.env` values for benchmark integration:

- `ZEP_BASE_URL=http://localhost:8000`
- `ZEP_API_KEY=local-dev-token` (only if `BENCH_SYSTEMS` includes `zep`)
- `MEM0_TELEMETRY=false` to disable Mem0 PostHog telemetry in local runs

3. Prepare data:
   - `python scripts/prepare_data.py --input /path/to/locomo_plus.json --output ./data/cognitive_samples.json`

4. Run benchmark:
   - `python scripts/run_benchmark.py`

5. Analyze:
   - `python scripts/analyze_results.py`

## Output Files

- `results/responses.json`
- `results/judge_results.json`
- `results/summary.json`
- `results/paper_alignment_report.json`
- `results/run_meta.json`

## Notes

- Mem0, Letta, and Zep are local infrastructure paths.
- Backbone is OpenAI (`gpt-4o-mini`), judge defaults to Google Gemini (`gemini-2.5-flash`) to match the paper.
- If Letta SDK response shapes differ by version, adjust the extractor in `systems/letta_runner.py`.
- If your local Zep image expects different config keys, update `zep.local.yaml` accordingly.
