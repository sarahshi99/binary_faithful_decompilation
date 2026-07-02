# Decompilation Faithfulness Phase 10 Actual Low-Budget Rerun

- Verdict: `low-budget-proxy-overestimated`
- Budgets: `[1, 2, 4, 8, 16]`

## Budget-8 Summary

| Dataset | Rerun candidates | Mismatch AUC | V3 AUC | Wrong detection rate | Wrong detected | Avg actual inputs | Actual input evals |
|---|---:|---:|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `478` | `0.9956` | `0.9956` | `0.9845` | `254` | `6.61` | `3160` |
| `phase7e_llm_public_full_topup` | `136` | `0.9828` | `0.9828` | `0.9722` | `35` | `6.67` | `907` |
| `phase6r_ghidra_full` | `166` | `0.9565` | `0.9565` | `0.9189` | `68` | `6.90` | `1145` |

## Phase 7C2 Budget Curve

| Requested budget | Mismatch AUC | V3 AUC | Wrong detection rate | Wrong detected | Avg actual inputs | Actual input evals |
|---|---:|---:|---:|---:|---:|---:|
| `1` | `0.8456` | `0.8456` | `0.7519` | `194` | `1.00` | `478` |
| `2` | `0.8567` | `0.8567` | `0.7597` | `196` | `2.00` | `956` |
| `4` | `0.9556` | `0.9556` | `0.9070` | `234` | `4.00` | `1912` |
| `8` | `0.9956` | `0.9956` | `0.9845` | `254` | `6.61` | `3160` |
| `16` | `0.9956` | `0.9956` | `0.9845` | `254` | `8.95` | `4280` |

## Gate

| Gate | Passed |
|---|---:|
| `phase7c2_budget8_auc_gate` | `True` |
| `phase7c2_budget8_detection_gate` | `True` |
| `phase6r_budget8_auc_gate` | `False` |
| `phase6r_budget8_detection_gate` | `False` |

## Interpretation

This is an actual low-budget rerun over deterministic generated-input prefixes.
Unlike Phase 9, it does not infer budget behavior from the full 128-input
mismatch count. Each candidate is re-executed on the first `max_budget` inputs,
and each budget is computed from that output prefix.
