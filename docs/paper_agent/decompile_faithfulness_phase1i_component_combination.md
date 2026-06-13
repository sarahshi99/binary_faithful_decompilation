# Decompilation Faithfulness Phase 1I Component Combination Audit

## Dataset

- Cases: `8`
- Candidates: `56`
- Faithful candidates: `24`
- Plausible-wrong candidates: `32`

## Best In-Sample Formula

- Formula: `mean_slot_plus_range_0.10`
- Pairwise AUC: `0.7604`

## Leave-One-Case-Out

- Pairwise AUC: `0.6719`
- Verdict: `do-not-transfer-yet`

| Held-out case | Selected formula | Train AUC | Held-out AUC |
|---|---|---:|---:|
| `absdiff` | `mean_slot_plus_range_0.10` | `0.7619` | `0.7500` |
| `clamp8` | `mean_slot_plus_range_0.10` | `0.7738` | `0.6667` |
| `count_bits8` | `min_slot` | `0.7381` | `0.8750` |
| `gcd_positive` | `min_slot` | `0.7798` | `0.5833` |
| `is_power_of_two` | `mean_slot_plus_range_0.10` | `0.7500` | `0.8333` |
| `max3` | `mean_slot_plus_range_0.10` | `0.7857` | `0.5833` |
| `signum` | `min_slot` | `0.7917` | `0.5000` |
| `sum_to_n` | `min_slot` | `0.7798` | `0.5833` |

## Formula Scores

| Formula | Pairwise AUC |
|---|---:|
| `mean_slot_plus_range_0.10` | `0.7604` |
| `min_slot` | `0.7552` |
| `mean_slot` | `0.7500` |
| `mean_slot_plus_bigram_0.10` | `0.7500` |
| `mean_slot_plus_global_0.10` | `0.7500` |
| `mean_slot_plus_global_0.25` | `0.7500` |
| `mean_slot_plus_bigram_0.25` | `0.7396` |
| `mean_slot_plus_branch_return_0.10` | `0.7396` |
| `mean_slot_plus_range_0.25` | `0.7083` |
| `max_slot` | `0.6979` |
| `mean_slot_plus_branch_return_0.25` | `0.6979` |

## Interpretation

This is a calibration audit over source-known cases, not a training claim. The leave-one-case-out result is the main guard against selecting a formula that only wins in-sample.
