# Decompilation Faithfulness Phase 14 Paper Readiness

- Verdict: `pass-phase14-paper-readiness-hardening`
- Budget: `8`
- Bootstrap iterations: `2000`
- Seed: `20260702`

## Budget-8 Stability And Cost

| Dataset | AUC | AUC CI95 | Wrong detection | Detection CI95 | Avg inputs | Input evals | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|---:|
| `phase6r_ghidra_full` | `1.0000` | `[1.0000, 1.0000]` | `1.0000` | `[1.0000, 1.0000]` | `6.97` | `1157` | `0` |
| `phase7c2_static_hard_public` | `1.0000` | `[1.0000, 1.0000]` | `1.0000` | `[1.0000, 1.0000]` | `6.64` | `3172` | `0` |
| `phase7e_llm_public_full_topup` | `1.0000` | `[1.0000, 1.0000]` | `1.0000` | `[1.0000, 1.0000]` | `6.69` | `910` | `0` |

## Miss Taxonomy

| Dataset | Missed wrong | By case | By candidate family |
|---|---:|---|---|
| `phase6r_ghidra_full` | `0` | `{}` | `{}` |
| `phase7c2_static_hard_public` | `0` | `{}` | `{}` |
| `phase7e_llm_public_full_topup` | `0` | `{}` | `{}` |

## Gate

| Gate | Passed |
|---|---:|
| `phase6r_ghidra_full_auc_ci_lower_gate` | `True` |
| `phase7c2_static_hard_public_auc_ci_lower_gate` | `True` |
| `phase7e_llm_public_full_topup_auc_ci_lower_gate` | `True` |
| `phase6r_ghidra_full_detection_ci_lower_gate` | `True` |
| `phase7c2_static_hard_public_detection_ci_lower_gate` | `True` |
| `phase7e_llm_public_full_topup_detection_ci_lower_gate` | `True` |

## Interpretation

The confidence intervals are case-level bootstrap intervals over the budget-8
records. Cost is reported as an input-evaluation proxy because prior trace files
do not preserve full wall-clock compile/run timing. Phase 19 final runtime is
reported separately in `decompile_faithfulness_phase19_final_runtime_risk.zh.md`.
The final miss taxonomy has zero missed wrong candidates on the current full
datasets.
