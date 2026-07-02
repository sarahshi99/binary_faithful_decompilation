# Decompilation Faithfulness Phase 12 Unified Low-Budget Evaluation

- Verdict: `pass-unified-budget8-low-budget-eval`
- Strategy: `source_literal_char_interleave`
- Budgets: `[1, 2, 4, 8, 16]`

## Budget-8 Summary

| Dataset | Mismatch AUC | Wrong detection rate | Missed wrong | Avg actual inputs | AUC delta vs Phase10 | Detection delta vs Phase10 | Avg input delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `1.0000` | `1.0000` | `0` | `6.64` | `+0.0044` | `+0.0155` | `+0.03` |
| `phase7e_llm_public_full_topup` | `1.0000` | `1.0000` | `0` | `6.69` | `+0.0172` | `+0.0278` | `+0.02` |
| `phase6r_ghidra_full` | `1.0000` | `1.0000` | `0` | `6.97` | `+0.0435` | `+0.0811` | `+0.07` |

## Gate

| Gate | Passed |
|---|---:|
| `phase7c2_static_hard_public_budget8_auc_gate` | `True` |
| `phase7e_llm_public_full_topup_budget8_auc_gate` | `True` |
| `phase6r_ghidra_full_budget8_auc_gate` | `True` |
| `phase7c2_static_hard_public_budget8_detection_gate` | `True` |
| `phase7e_llm_public_full_topup_budget8_detection_gate` | `True` |
| `phase6r_ghidra_full_budget8_detection_gate` | `True` |

## Interpretation

This phase uses one input-ordering policy, `fixture_neighbor_first`, across all
current datasets. `Mismatch AUC` measures ranking quality; `Wrong detection
rate` measures how many wrong candidates are actually exposed by at least one
budgeted input. The deltas compare against Phase 10's original input order at
budget-8.
