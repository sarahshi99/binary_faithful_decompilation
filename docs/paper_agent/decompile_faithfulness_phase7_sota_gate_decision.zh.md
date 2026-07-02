# Decompilation Faithfulness Phase 7 SOTA Gate Decision

- Decision: `revise-method-before-sota-claim`
- Phase 7 verdict: `method-negative-public-benchmark`
- Dynamic Trace v3 AUC: `1.0000`
- Best non-oracle baseline AUC: `0.9693`
- Delta: `0.0307`
- External-paper SOTA ready: `False`

## Gate

| Gate | Passed |
|---|---:|
| `source_function_scale_gate` | `True` |
| `compile_pass_scale_gate` | `True` |
| `paired_function_gate` | `True` |
| `v3_beats_fixture_gate` | `True` |
| `v3_beats_static_gate` | `True` |
| `sota_delta_gate` | `False` |
| `behavior_preserving_fp_gate` | `True` |
| `fixture_collapse_gate` | `True` |
| `risk_breakdown_gate` | `True` |

## Claim Boundary

Phase7C reaches public benchmark scale and v3 beats fixture/static, but the delta against the best static baseline is below the CCF-A/SOTA gate. This row is useful as public alignment evidence, not sufficient as the main SOTA claim.

## Next Step

先补 static-hard 或 LLM-generated public benchmark candidates，检查 v3 是否在更接近真实生成错误的候选上拉开 delta；同时继续 Phase 7D 的第二 decompiler feasibility。
