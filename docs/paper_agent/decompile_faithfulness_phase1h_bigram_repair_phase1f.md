# Decompilation Faithfulness Phase 1E Multi-Opt Slot Calibration

## Metrics

- Cases: `2`
- Candidates: `14`
- Faithful candidates: `6`
- Plausible-wrong candidates: `8`
- Opt levels: `O0, O1, O2, O3`
- Primary score: `min_slot_concentration`
- Primary pairwise AUC: `0.7917`
- Verdict: `continue-with-multi-opt-calibration`

## Per-Opt Slot AUC

| Opt | Slot AUC | Faithful mean | Wrong mean | Verdict |
|---|---:|---:|---:|---|
| `O0` | `0.9167` | `0.4440` | `0.7999` | `continue-slot-calibration` |
| `O1` | `0.5417` | `0.5957` | `0.7448` | `inconclusive-or-redesign` |
| `O2` | `0.5625` | `0.5813` | `0.7056` | `inconclusive-or-redesign` |
| `O3` | `0.2917` | `0.6035` | `0.6710` | `inconclusive-or-redesign` |

## Multi-Opt AUC

| Aggregation | Pairwise AUC |
|---|---:|
| `min_slot_concentration_auc` | `0.7917` |
| `mean_slot_concentration_auc` | `0.7083` |
| `max_slot_concentration_auc` | `0.5833` |
| `range_slot_concentration_auc` | `0.4167` |

## Interpretation

Use single optimization-level scores as diagnostics and use the minimum slot concentration across optimization levels as the primary suspicion score. This makes behavior-preserving rewrites less likely to be punished when one optimization level happens to produce locally concentrated binary drift.
