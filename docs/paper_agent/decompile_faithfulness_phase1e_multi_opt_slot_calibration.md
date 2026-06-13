# Decompilation Faithfulness Phase 1E Multi-Opt Slot Calibration

## Metrics

- Cases: `3`
- Candidates: `21`
- Faithful candidates: `9`
- Plausible-wrong candidates: `12`
- Opt levels: `O0, O1, O2, O3`
- Primary score: `min_slot_concentration`
- Primary pairwise AUC: `0.8472`
- Verdict: `continue-with-multi-opt-calibration`

## Per-Opt Slot AUC

| Opt | Slot AUC | Faithful mean | Wrong mean | Verdict |
|---|---:|---:|---:|---|
| `O0` | `0.9028` | `0.5036` | `0.7481` | `continue-slot-calibration` |
| `O1` | `0.7361` | `0.3429` | `0.6606` | `weak-signal` |
| `O2` | `0.6944` | `0.3435` | `0.6589` | `weak-signal` |
| `O3` | `0.7500` | `0.3621` | `0.6483` | `continue-slot-calibration` |

## Multi-Opt AUC

| Aggregation | Pairwise AUC |
|---|---:|
| `min_slot_concentration_auc` | `0.8472` |
| `mean_slot_concentration_auc` | `0.8056` |
| `max_slot_concentration_auc` | `0.7639` |
| `range_slot_concentration_auc` | `0.4306` |

## Interpretation

Use single optimization-level scores as diagnostics and use the minimum slot concentration across optimization levels as the primary suspicion score. This makes behavior-preserving rewrites less likely to be punished when one optimization level happens to produce locally concentrated binary drift.
