# Decompilation Faithfulness Phase 1K Dynamic Trace Audit

## Dataset

- Cases: `8`
- Candidates: `56`
- Faithful candidates: `24`
- Plausible-wrong candidates: `32`

## Leave-One-Case-Out

- Pairwise AUC: `0.8750`
- Fixture collapse: `False`
- Verdict: `borderline-dynamic-trace`

| Held-out case | Selected formula | Train AUC | Held-out AUC |
|---|---|---:|---:|
| `absdiff` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |
| `clamp8` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |
| `count_bits8` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |
| `gcd_positive` | `trace_mismatch_rate` | `0.9464` | `0.5000` |
| `is_power_of_two` | `trace_total_plus_min_slot_0.10` | `0.9167` | `0.7500` |
| `max3` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |
| `signum` | `trace_total_plus_min_slot_0.10` | `0.9167` | `0.7500` |
| `sum_to_n` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |

## Hard Cases

| Case | Held-out AUC |
|---|---:|
| `signum` | `0.7500` |
| `gcd_positive` | `0.5000` |
| `max3` | `1.0000` |
| `sum_to_n` | `1.0000` |

## Formula Scores

| Formula | Pairwise AUC |
|---|---:|
| `trace_total_plus_min_slot_0.10` | `0.8958` |
| `trace_total_plus_min_slot_0.25` | `0.8958` |
| `trace_mismatch_rate` | `0.8906` |
| `trace_total` | `0.8906` |
| `min_slot` | `0.8021` |

## Interpretation

This is Route A of the Phase 1K three-route scout. The primary score uses generated trace inputs, while fixture-test behavior is reported separately to detect oracle-like collapse.
