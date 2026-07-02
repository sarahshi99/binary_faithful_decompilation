# Decompilation Faithfulness Phase 11 Ghidra Input Ordering

- Verdict: `pass-ghidra-budget8-input-ordering`
- Dataset: `phase6r_ghidra_full`
- Budgets: `[1, 2, 4, 8, 16]`

## Budget-8 Strategy Comparison

| Strategy | Complete eval | Mismatch AUC | Wrong detection rate | Missed wrong | Avg actual inputs |
|---|---:|---:|---:|---:|---:|
| `phase5b_original` | `True` | `0.9565` | `0.9189` | `6` | `6.90` |
| `fixture_neighbor_first` | `True` | `0.9891` | `0.9730` | `2` | `6.97` |
| `boundary_first` | `False` | `1.0000` | `0.9722` | `2` | `8.00` |
| `mixed_boundary_neighbor` | `False` | `1.0000` | `0.9722` | `2` | `8.00` |

## Budget-16 Strategy Comparison

| Strategy | Complete eval | Mismatch AUC | Wrong detection rate | Missed wrong | Avg actual inputs |
|---|---:|---:|---:|---:|---:|
| `phase5b_original` | `True` | `0.9783` | `0.9730` | `2` | `11.43` |
| `fixture_neighbor_first` | `True` | `1.0000` | `1.0000` | `0` | `11.86` |
| `boundary_first` | `False` | `1.0000` | `0.9722` | `2` | `16.00` |
| `mixed_boundary_neighbor` | `False` | `1.0000` | `1.0000` | `0` | `16.00` |

## Best Strategies

- Budget-8: `fixture_neighbor_first` with AUC `0.9891` and detection `0.9730`.
- Budget-16: `fixture_neighbor_first` with AUC `1.0000` and detection `1.0000`.

## Gate

| Gate | Passed |
|---|---:|
| `budget8_auc_gate` | `True` |
| `budget8_detection_gate` | `True` |
| `budget16_auc_gate` | `True` |
| `budget16_detection_gate` | `True` |

## Interpretation

This phase keeps candidates fixed and changes only the generated-input order.
The best-strategy selector prioritizes complete evaluations before AUC, so an
ordering that times out original/candidate executions is not allowed to win by
dropping hard cases. It tests whether Phase 10's Ghidra misses were caused by
late coverage of fixture-neighborhood and boundary cases.
