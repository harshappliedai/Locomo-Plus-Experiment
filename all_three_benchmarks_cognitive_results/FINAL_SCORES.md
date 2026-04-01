# Final scores — cognitive 401 (mem0, Letta, Zep)
**Samples:** 401 | **Judgments:** 1203

## Overall accuracy & Wilson 95% CI
| System | Correct | Accuracy | Wilson 95% CI |
|--------|---------|----------|----------------|
| **mem0** | 72/401 | 0.1796 | [0.1451, 0.2201] |
| **letta** | 97/401 | 0.2419 | [0.2026, 0.2861] |
| **zep** | 89/401 | 0.2219 | [0.1840, 0.2651] |

## Cochran's Q (identical accuracy across three systems?)
- **Q** = 7.1387, **df** = 2, **p** = 0.028174

## Pairwise McNemar (paired per dialogue)
### `mem0_vs_letta`
- Both wrong: 269, mem0 only: 35, letta only: 60, both correct: 37
- **p** = 0.013379 (Holm-adjusted **p** = 0.040136)
### `mem0_vs_zep`
- Both wrong: 277, mem0 only: 35, zep only: 52, both correct: 37
- **p** = 0.085689 (Holm-adjusted **p** = 0.171378)
### `letta_vs_zep`
- Both wrong: 262, letta only: 50, zep only: 42, both correct: 47
- **p** = 0.465707 (Holm-adjusted **p** = 0.465707)

## By relation type (n, accuracy, Wilson 95% CI)
*`n` can differ slightly per system if `relation_type` metadata varies for the same `sample_id` (rare; 24/401 in this pool).*
### `causal`
| System | Correct | n | Accuracy | Wilson 95% CI |
|--------|---------|---|----------|----------------|
| **mem0** | 11 | 98 | 0.1122 | [0.0638, 0.1899] |
| **letta** | 13 | 100 | 0.1300 | [0.0776, 0.2098] |
| **zep** | 21 | 101 | 0.2079 | [0.1402, 0.2970] |

### `goal`
| System | Correct | n | Accuracy | Wilson 95% CI |
|--------|---------|---|----------|----------------|
| **mem0** | 24 | 105 | 0.2286 | [0.1587, 0.3176] |
| **letta** | 30 | 103 | 0.2913 | [0.2123, 0.3852] |
| **zep** | 21 | 100 | 0.2100 | [0.1417, 0.2998] |

### `state`
| System | Correct | n | Accuracy | Wilson 95% CI |
|--------|---------|---|----------|----------------|
| **mem0** | 13 | 95 | 0.1368 | [0.0817, 0.2202] |
| **letta** | 28 | 96 | 0.2917 | [0.2102, 0.3892] |
| **zep** | 22 | 100 | 0.2200 | [0.1500, 0.3107] |

### `value`
| System | Correct | n | Accuracy | Wilson 95% CI |
|--------|---------|---|----------|----------------|
| **mem0** | 24 | 103 | 0.2330 | [0.1619, 0.3233] |
| **letta** | 26 | 102 | 0.2549 | [0.1803, 0.3473] |
| **zep** | 25 | 100 | 0.2500 | [0.1755, 0.3430] |


## By time-gap bucket (n, accuracy, Wilson 95% CI)
*Buckets match `evaluation.metrics._bucket_time_gap` (short = week; long = month wording; etc.).*
### `long_3_plus_months`
| System | Correct | n | Accuracy | Wilson 95% CI |
|--------|---------|---|----------|----------------|
| **mem0** | 57 | 299 | 0.1906 | [0.1501, 0.2390] |
| **letta** | 66 | 298 | 0.2215 | [0.1780, 0.2720] |
| **zep** | 62 | 300 | 0.2067 | [0.1647, 0.2561] |

### `short_1_to_2_weeks`
| System | Correct | n | Accuracy | Wilson 95% CI |
|--------|---------|---|----------|----------------|
| **mem0** | 15 | 91 | 0.1648 | [0.1025, 0.2543] |
| **letta** | 26 | 92 | 0.2826 | [0.2008, 0.3819] |
| **zep** | 25 | 91 | 0.2747 | [0.1936, 0.3741] |

### `unknown`
| System | Correct | n | Accuracy | Wilson 95% CI |
|--------|---------|---|----------|----------------|
| **mem0** | 0 | 11 | 0.0000 | [0.0000, 0.2588] |
| **letta** | 5 | 11 | 0.4545 | [0.2127, 0.7199] |
| **zep** | 2 | 10 | 0.2000 | [0.0567, 0.5098] |

