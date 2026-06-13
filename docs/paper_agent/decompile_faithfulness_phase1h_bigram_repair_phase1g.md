# Decompilation Faithfulness Phase 1E Multi-Opt Slot Calibration

## Metrics

- Cases: `3`
- Candidates: `21`
- Faithful candidates: `9`
- Plausible-wrong candidates: `12`
- Opt levels: `O0, O1, O2, O3`
- Primary score: `min_slot_concentration`
- Primary pairwise AUC: `0.6389`
- Verdict: `weak-multi-opt-signal`

## Per-Opt Slot AUC

| Opt | Slot AUC | Faithful mean | Wrong mean | Verdict |
|---|---:|---:|---:|---|
| `O0` | `0.6250` | `0.5296` | `0.6513` | `weak-signal` |
| `O1` | `0.7639` | `0.3523` | `0.6525` | `continue-slot-calibration` |
| `O2` | `0.6250` | `0.3935` | `0.5695` | `weak-signal` |
| `O3` | `0.6250` | `0.3958` | `0.5695` | `weak-signal` |

## Multi-Opt AUC

| Aggregation | Pairwise AUC |
|---|---:|
| `min_slot_concentration_auc` | `0.6389` |
| `mean_slot_concentration_auc` | `0.7222` |
| `max_slot_concentration_auc` | `0.7083` |
| `range_slot_concentration_auc` | `0.4306` |

## Interpretation

Use single optimization-level scores as diagnostics and use the minimum slot concentration across optimization levels as the primary suspicion score. This makes behavior-preserving rewrites less likely to be punished when one optimization level happens to produce locally concentrated binary drift.
