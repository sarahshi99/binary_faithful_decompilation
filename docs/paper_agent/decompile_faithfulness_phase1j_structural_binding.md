# Decompilation Faithfulness Phase 1J Structural Binding Audit

## Dataset

- Cases: `8`
- Candidates: `56`
- Faithful candidates: `24`
- Plausible-wrong candidates: `32`

## Baselines

- Phase 1G multi-opt min slot AUC: `0.7552`
- Phase 1I best in-sample AUC: `0.7604`
- Phase 1I leave-one-case-out AUC: `0.6719`

## Best In-Sample Formula

- Formula: `min_slot`
- Pairwise AUC: `0.7552`

## Leave-One-Case-Out

- Pairwise AUC: `0.6823`
- Verdict: `do-not-transfer-yet`

| Held-out case | Selected formula | Train AUC | Held-out AUC |
|---|---|---:|---:|
| `absdiff` | `mean_slot` | `0.7500` | `0.7500` |
| `clamp8` | `mean_slot` | `0.7619` | `0.6667` |
| `count_bits8` | `min_slot` | `0.7381` | `0.8750` |
| `gcd_positive` | `min_slot` | `0.7798` | `0.5833` |
| `is_power_of_two` | `min_slot` | `0.7440` | `0.8333` |
| `max3` | `mean_slot` | `0.7619` | `0.6667` |
| `signum` | `min_slot` | `0.7917` | `0.5000` |
| `sum_to_n` | `min_slot` | `0.7798` | `0.5833` |

## Hard Cases

| Case | Held-out AUC |
|---|---:|
| `signum` | `0.5000` |
| `gcd_positive` | `0.5833` |
| `max3` | `0.6667` |
| `sum_to_n` | `0.5833` |

## Formula Scores

| Formula | Pairwise AUC |
|---|---:|
| `min_slot` | `0.7552` |
| `mean_slot` | `0.7500` |
| `min_slot_plus_branch_return_0.10` | `0.7500` |
| `mean_slot_plus_structured_0.10` | `0.7396` |
| `min_slot_plus_cfg_edge_0.10` | `0.7188` |
| `mean_slot_plus_structured_0.25` | `0.7083` |
| `structured_only` | `0.1562` |
| `structured_binding_total` | `0.1562` |

## Interpretation

This is a CPU-only source-known kill-gate. Labels are used for offline evaluation and formula selection only; structured feature extraction reads object-code paths without using candidate labels.

## Next Route

The structured binding gate did not pass. Record Phase 1J as negative evidence for lightweight static binary motifs and pivot before real-project transfer: dynamic traces, symbolic traces, or a narrower localized-bug problem framing are better next candidates.
