# Decompilation Faithfulness Phase 12 Unified Low-Budget Evaluation

- Verdict: `partial-unified-low-budget-eval`
- Strategy: `operator_char_class_first`
- Budgets: `[1, 2, 4, 8, 16]`

## Budget-8 Summary

| Dataset | Mismatch AUC | Wrong detection rate | Missed wrong | Avg actual inputs | AUC delta vs Phase10 | Detection delta vs Phase10 | Avg input delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `0.9889` | `0.9612` | `10` | `6.64` | `-0.0067` | `-0.0233` | `+0.03` |
| `phase7e_llm_public_full_topup` | `0.9914` | `0.9722` | `1` | `6.69` | `+0.0086` | `+0.0000` | `+0.02` |
| `phase6r_ghidra_full` | `0.9565` | `0.9459` | `4` | `6.97` | `+0.0000` | `+0.0270` | `+0.07` |

## Gate

| Gate | Passed |
|---|---:|
| `phase7c2_static_hard_public_budget8_auc_gate` | `True` |
| `phase7e_llm_public_full_topup_budget8_auc_gate` | `True` |
| `phase6r_ghidra_full_budget8_auc_gate` | `False` |
| `phase7c2_static_hard_public_budget8_detection_gate` | `True` |
| `phase7e_llm_public_full_topup_budget8_detection_gate` | `True` |
| `phase6r_ghidra_full_budget8_detection_gate` | `False` |

## Interpretation

This phase uses one input-ordering policy, `fixture_neighbor_first`, across all
current datasets. `Mismatch AUC` measures ranking quality; `Wrong detection
rate` measures how many wrong candidates are actually exposed by at least one
budgeted input. The deltas compare against Phase 10's original input order at
budget-8.
