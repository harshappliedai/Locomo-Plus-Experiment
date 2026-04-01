# Cognitive 401 — final report (Mem0, Letta, Zep)

**Generated (UTC):** 2026-03-22T17:44:18.427796+00:00  

**Dialogues:** 401 | **Judgments:** 1203 | **Pool:** `cognitive_samples_401_seed42.json`


## 1. Executive summary

| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |
|--------|---------|-------|---|----------|----------------|
| **mem0** | 72 | 329 | 401 | 0.1796 | [0.1451, 0.2201] |
| **letta** | 97 | 304 | 401 | 0.2419 | [0.2026, 0.2861] |
| **zep** | 89 | 312 | 401 | 0.2219 | [0.1840, 0.2651] |

## 2. Statistical tests (paired on the same 401 dialogues)

### Cochran's Q

- **Q** = 7.138686, **df** = 2, **p** = 0.028174

- *Interpretation:* reject H₀ (equal accuracy across systems) if p < α (e.g. 0.05).


### Pairwise McNemar (binary correct/wrong)

*Holm-adjusted p-values across the three tests.*


#### `mem0_vs_letta`

- Contingency (rows=mem0, cols=letta): both wrong **269**, mem0 only **35**, 
letta only **60**, both correct **37**

- McNemar **p** = 0.013379 | Holm-adjusted **p** = 0.040136 
| reject α=0.05: **True**


#### `mem0_vs_zep`

- Contingency (rows=mem0, cols=zep): both wrong **277**, mem0 only **35**, 
zep only **52**, both correct **37**

- McNemar **p** = 0.085689 | Holm-adjusted **p** = 0.171378 
| reject α=0.05: **False**


#### `letta_vs_zep`

- Contingency (rows=letta, cols=zep): both wrong **262**, letta only **50**, 
zep only **42**, both correct **47**

- McNemar **p** = 0.465707 | Holm-adjusted **p** = 0.465707 
| reject α=0.05: **False**


### Inter-rater agreement on judge labels (wrong=0, correct=1)

- **Fleiss' κ** (3 raters): **0.3240**


| Pair | Cohen's κ | p-value (H₀: κ=0) |
|------|-----------|-------------------|
| mem0_vs_letta | 0.2919 | — |
| mem0_vs_zep | 0.3258 | — |
| letta_vs_zep | 0.3564 | — |

| Pair | % identical label |
|------|-------------------|
| mem0_vs_letta | 76.31% |
| mem0_vs_zep | 78.30% |
| letta_vs_zep | 77.06% |

## 3. Agreement across systems (per dialogue)

- **exactly_0_correct:** 237

- **exactly_1_correct:** 97

- **exactly_2_correct:** 40

- **exactly_3_correct:** 27

- **All three correct** (`n=27`): see `FINAL_REPORT.json` → `sample_ids_all_three_correct`

- **All three wrong** (`n=237`): see `FINAL_REPORT.json` → `sample_ids_all_three_wrong`


### Pattern counts `(mem0, letta, zep)` as 0/1

- (0, 0, 0): **237**

- (0, 1, 0): **40**

- (0, 0, 1): **32**

- (1, 1, 1): **27**

- (1, 0, 0): **25**

- (0, 1, 1): **20**

- (1, 1, 0): **10**

- (1, 0, 1): **10**


## 4. Pool distribution (ground-truth design)

### `relation_type` counts in pool

- **causal:** 101

- **goal:** 100

- **state:** 100

- **value:** 100


### `time_gap` bucket counts (from pool text via `evaluation.metrics._bucket_time_gap`)

- **long_3_plus_months:** 300

- **short_1_to_2_weeks:** 91

- **unknown:** 10


## 5. Category-wise results (canonical labels from **pool** JSON)

*Each system has the same **n** per category (401 split by pool metadata).*


### By `relation_type`


#### `causal`

| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |
|--------|---------|-------|---|----------|----------------|
| **mem0** | 12 | 89 | 101 | 0.1188 | [0.0693, 0.1963] |
| **letta** | 13 | 88 | 101 | 0.1287 | [0.0768, 0.2078] |
| **zep** | 21 | 80 | 101 | 0.2079 | [0.1402, 0.2970] |

#### `goal`

| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |
|--------|---------|-------|---|----------|----------------|
| **mem0** | 23 | 77 | 100 | 0.2300 | [0.1584, 0.3215] |
| **letta** | 30 | 70 | 100 | 0.3000 | [0.2189, 0.3958] |
| **zep** | 21 | 79 | 100 | 0.2100 | [0.1417, 0.2998] |

#### `state`

| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |
|--------|---------|-------|---|----------|----------------|
| **mem0** | 15 | 85 | 100 | 0.1500 | [0.0931, 0.2328] |
| **letta** | 28 | 72 | 100 | 0.2800 | [0.2014, 0.3749] |
| **zep** | 22 | 78 | 100 | 0.2200 | [0.1500, 0.3107] |

#### `value`

| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |
|--------|---------|-------|---|----------|----------------|
| **mem0** | 22 | 78 | 100 | 0.2200 | [0.1500, 0.3107] |
| **letta** | 26 | 74 | 100 | 0.2600 | [0.1840, 0.3537] |
| **zep** | 25 | 75 | 100 | 0.2500 | [0.1755, 0.3430] |

### By time-gap bucket


#### `long_3_plus_months`

| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |
|--------|---------|-------|---|----------|----------------|
| **mem0** | 57 | 243 | 300 | 0.1900 | [0.1496, 0.2382] |
| **letta** | 67 | 233 | 300 | 0.2233 | [0.1799, 0.2738] |
| **zep** | 62 | 238 | 300 | 0.2067 | [0.1647, 0.2561] |

#### `short_1_to_2_weeks`

| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |
|--------|---------|-------|---|----------|----------------|
| **mem0** | 14 | 77 | 91 | 0.1538 | [0.0939, 0.2418] |
| **letta** | 25 | 66 | 91 | 0.2747 | [0.1936, 0.3741] |
| **zep** | 25 | 66 | 91 | 0.2747 | [0.1936, 0.3741] |

#### `unknown`

| System | Correct | Wrong | n | Accuracy | Wilson 95% CI |
|--------|---------|-------|---|----------|----------------|
| **mem0** | 1 | 9 | 10 | 0.1000 | [0.0179, 0.4042] |
| **letta** | 5 | 5 | 10 | 0.5000 | [0.2366, 0.7634] |
| **zep** | 2 | 8 | 10 | 0.2000 | [0.0567, 0.5098] |

## 6. Files in this folder

- `FINAL_REPORT.json` — machine-readable duplicate of this report

- `FINAL_SCORES.json` / `FINAL_SCORES.md` — scores + category detail (judge-row metadata)

- `judge_results.json`, `responses.json`, `summary.json`, `errors.json`, `run_meta.json`


## 7. Regenerate

```bash
python scripts/compute_final_cognitive401_scores.py
python scripts/build_cognitive401_final_report.py
```
