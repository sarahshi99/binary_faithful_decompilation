# Decompilation Faithfulness Phase 1K Dynamic Trace v2 Audit

## Dataset

- Cases: `8`
- Candidates: `56`
- Faithful candidates: `24`
- Plausible-wrong candidates: `32`

## Leave-One-Case-Out

- Pairwise AUC: `0.9531`
- Fixture collapse: `False`
- Verdict: `pass-dynamic-trace-v2-localized-bug`

| Held-out case | Selected formula | Train AUC | Held-out AUC |
|---|---|---:|---:|
| `absdiff` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `clamp8` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `count_bits8` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `gcd_positive` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `is_power_of_two` | `trace_mismatch_rate` | `0.9643` | `0.8750` |
| `max3` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `signum` | `trace_mismatch_rate` | `0.9821` | `0.7500` |
| `sum_to_n` | `trace_mismatch_rate` | `0.9464` | `1.0000` |

## Hard Cases

| Case | Held-out AUC |
|---|---:|
| `signum` | `0.7500` |
| `gcd_positive` | `1.0000` |
| `max3` | `1.0000` |
| `sum_to_n` | `1.0000` |

## Formula Scores

| Formula | Pairwise AUC |
|---|---:|
| `trace_mismatch_rate` | `0.9531` |
| `trace_total` | `0.9531` |
| `trace_total_plus_min_slot_0.10` | `0.9375` |
| `trace_total_plus_min_slot_0.25` | `0.9375` |
| `min_slot` | `0.8021` |

## Interpretation

Dynamic Trace v2 uses fixture-domain-aware generated inputs. It does not use candidate labels or candidate outputs to choose the input domain.
