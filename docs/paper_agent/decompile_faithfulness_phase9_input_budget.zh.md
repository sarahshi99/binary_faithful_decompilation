# Decompilation Faithfulness Phase 9 Input Budget

- Verdict: `low-budget-dynamic-execution-claim`
- Interpretation: Current records support a low-budget generated-input dynamic execution claim: simple mismatch saturates ranking, and a small input budget catches most wrong candidates.

## Dataset Summary

| Dataset | Paired cases | Budget-8 AUC | Budget-8 wrong mean | Budget-8 wrong p10 | Budget-8 wrong min | V3 AUC | Fuzz mismatch AUC |
|---|---:|---:|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `50` | `1.0000` | `0.9935` | `1.0000` | `0.6404` | `1.0000` | `1.0000` |
| `phase7e_llm_public_full_topup` | `24` | `1.0000` | `1.0000` | `1.0000` | `0.9998` | `1.0000` | `1.0000` |
| `phase6r_ghidra_full` | `26` | `1.0000` | `0.9800` | `0.9952` | `0.3591` | `1.0000` | `1.0000` |
| `phase6r_ghidra_gcc9_full` | `26` | `1.0000` | `0.9800` | `0.9952` | `0.3591` | `1.0000` | `1.0000` |

## Phase 7C2 Budget Curve

| Budget | AUC | Wrong detect mean | Wrong detect p10 | Wrong detect min |
|---|---:|---:|---:|---:|
| `1` | `1.0000` | `0.8026` | `0.3333` | `0.1081` |
| `2` | `1.0000` | `0.8925` | `0.6000` | `0.2072` |
| `4` | `1.0000` | `0.9664` | `0.9333` | `0.3804` |
| `8` | `1.0000` | `0.9935` | `1.0000` | `0.6404` |
| `16` | `1.0000` | `0.9985` | `1.0000` | `0.8981` |
| `32` | `1.0000` | `0.9999` | `1.0000` | `0.9929` |
| `64` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `128` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |

## Phase 7C2 Top V3 Family Deltas

| Group | Paired cases | Fuzz mismatch AUC | V3 AUC | Delta |
|---|---:|---:|---:|---:|
| `risk:public_benchmark` | `50` | `1.0000` | `1.0000` | `0.0000` |
| `risk:operator_boundary` | `34` | `1.0000` | `1.0000` | `0.0000` |
| `risk:branch` | `18` | `1.0000` | `1.0000` | `0.0000` |
| `risk:multi_arg` | `18` | `1.0000` | `1.0000` | `0.0000` |
| `risk:loop` | `11` | `1.0000` | `1.0000` | `0.0000` |
| `mutation:phase7_static_hard_predicate_strictness` | `5` | `1.0000` | `1.0000` | `0.0000` |
| `mutation:phase7_static_hard_arithmetic_operator` | `4` | `1.0000` | `1.0000` | `0.0000` |
| `mutation:phase7_static_hard_bitshift_direction` | `0` | `0.0000` | `0.0000` | `0.0000` |

## Gate

| Gate | Passed |
|---|---:|
| `budget8_low_cost_gate` | `True` |
| `v3_hard_family_delta_gate` | `False` |

## Interpretation

Phase 9 shows whether the current evidence supports a low-budget dynamic
execution claim or a v3-specific scoring claim. AUC can saturate even at
budget 1 because faithful candidates often have zero mismatch while wrong
candidates have nonzero mismatch. The wrong-candidate detection statistics
therefore matter more for cost-sensitive claims.
