# Decompilation Faithfulness Phase 17 Operator Char Policy

- Verdict: `partial-phase17-operator-char-policy`
- Strategy: `operator_char_class_first`
- Budget: `8`

## Budget-8 Dataset Comparison

| Dataset | AUC | AUC delta vs Phase12 | Wrong detection | Detection delta vs Phase12 | Missed wrong | Miss delta | Avg inputs | Avg input delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `0.9889` | `-0.0111` | `0.9612` | `-0.0388` | `10` | `+10` | `6.64` | `+0.00` |
| `phase7e_llm_public_full_topup` | `0.9914` | `-0.0086` | `0.9722` | `-0.0278` | `1` | `+1` | `6.69` | `+0.00` |
| `phase6r_ghidra_full` | `0.9565` | `-0.0326` | `0.9459` | `-0.0270` | `4` | `+2` | `6.97` | `+0.00` |

## Ghidra Risk-Family Comparison

| Risk family | Paired cases | AUC | AUC delta vs Phase16 | Detection | Detection delta vs Phase16 | Missed wrong | Miss delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| `boundary` | `7` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `branch` | `6` | `0.8333` | `-0.1667` | `0.7647` | `-0.2353` | `4` | `+4` |
| `char_boundary` | `3` | `0.6000` | `-0.3000` | `0.5556` | `-0.2222` | `4` | `+2` |
| `comparison` | `3` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `conversion` | `3` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `digits` | `4` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `division` | `4` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `loop` | `9` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `multi_arg` | `4` | `1.0000` | `+0.0714` | `1.0000` | `+0.2000` | `0` | `-2` |
| `nonnegative_domain` | `5` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `positive_domain` | `5` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `recursion` | `4` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `sign_zero` | `4` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |

## Gate

| Gate | Passed |
|---|---:|
| `phase7c2_static_hard_public_budget8_auc_no_regression` | `False` |
| `phase7e_llm_public_full_topup_budget8_auc_no_regression` | `False` |
| `phase6r_ghidra_full_budget8_auc_no_regression` | `False` |
| `phase7c2_static_hard_public_budget8_detection_no_regression` | `False` |
| `phase7e_llm_public_full_topup_budget8_detection_no_regression` | `False` |
| `phase6r_ghidra_full_budget8_detection_no_regression` | `False` |
| `phase6r_ghidra_full_budget8_auc_gate` | `False` |
| `phase6r_ghidra_full_budget8_detection_gate` | `False` |
| `phase6r_ghidra_full_large_risk_family_auc_gate` | `False` |
| `phase6r_ghidra_full_large_risk_family_detection_gate` | `False` |
| `phase6r_ghidra_full_char_boundary_detection_gate` | `False` |
| `phase6r_ghidra_full_multi_arg_detection_gate` | `True` |

## Interpretation

`Mismatch AUC` measures whether wrong candidates are ranked above faithful ones
within each case. `Wrong detection` measures whether each wrong candidate is
actually exposed by at least one budgeted input. Higher is better for both.

Phase 17 is good only if it improves the Ghidra `char_boundary` / `multi_arg`
weakness without making the public or LLM-public full evaluations worse. If it
passes, `operator_char_class_first` is a stronger default low-budget input
policy than plain `fixture_neighbor_first`. If it is partial, keep the result as
a targeted ablation and leave the Phase 16 limitation in the paper.
