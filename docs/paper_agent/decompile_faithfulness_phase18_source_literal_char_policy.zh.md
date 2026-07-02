# Decompilation Faithfulness Phase 18 Source Literal Char Policy

- Verdict: `pass-phase18-source-literal-char-policy`
- Strategy: `source_literal_char_interleave`
- Budget: `8`

## Budget-8 Dataset Comparison

| Dataset | AUC | AUC delta vs Phase12 | Wrong detection | Detection delta vs Phase12 | Missed wrong | Miss delta |
|---|---:|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `phase7e_llm_public_full_topup` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `phase6r_ghidra_full` | `1.0000` | `+0.0109` | `1.0000` | `+0.0270` | `0` | `-2` |

## Ghidra Risk-Family Comparison

| Risk family | Paired cases | AUC | AUC delta vs Phase16 | Detection | Detection delta vs Phase16 | Missed wrong | Miss delta |
|---|---:|---:|---:|---:|---:|---:|---:|
| `boundary` | `7` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `branch` | `6` | `1.0000` | `+0.0000` | `1.0000` | `+0.0000` | `0` | `+0` |
| `char_boundary` | `3` | `1.0000` | `+0.1000` | `1.0000` | `+0.2222` | `0` | `-2` |
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
| `phase7c2_static_hard_public_budget8_auc_no_regression` | `True` |
| `phase7e_llm_public_full_topup_budget8_auc_no_regression` | `True` |
| `phase6r_ghidra_full_budget8_auc_no_regression` | `True` |
| `phase7c2_static_hard_public_budget8_detection_no_regression` | `True` |
| `phase7e_llm_public_full_topup_budget8_detection_no_regression` | `True` |
| `phase6r_ghidra_full_budget8_detection_no_regression` | `True` |
| `phase6r_ghidra_full_budget8_auc_gate` | `True` |
| `phase6r_ghidra_full_budget8_detection_gate` | `True` |
| `phase6r_ghidra_full_large_risk_family_auc_gate` | `True` |
| `phase6r_ghidra_full_large_risk_family_detection_gate` | `True` |
| `phase6r_ghidra_full_char_boundary_detection_gate` | `True` |
| `phase6r_ghidra_full_multi_arg_detection_gate` | `True` |

## Interpretation

This phase tests a conservative source-known input policy. It extracts
character literals from the original source and interleaves them with
fixture-neighbor probes, instead of front-loading a generic operator list. A
passing result would support adding source-literal char probes to the final
low-budget auditor. A partial or failed result means Phase 16's char-boundary
miss should remain a limitation rather than be patched into the main claim.
