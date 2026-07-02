# Decompilation Faithfulness Phase 7 Static-hard Result

- Verdict: `pass-phase7-static-hard-sota-delta`
- Benchmark: `CodeFuse-DeBench`
- Source functions: `56`
- Candidates: `524`
- Compile pass count: `503`
- Paired case count: `50`
- Label counts: `{'faithful': 236, 'plausible_wrong': 267, 'compile_fail': 21}`
- Fixture-passing wrong count: `18`
- Fixture-only AUC: `0.9218`
- Static structured proxy AUC: `0.6831`
- Dynamic Trace v3 AUC: `1.0000`
- Delta vs best non-oracle baseline: `0.0782`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase7_static_hard/records.jsonl`

## Gate Check

| Gate | Passed |
|---|---:|
| `source_function_scale_gate` | `True` |
| `compile_pass_scale_gate` | `True` |
| `paired_function_gate` | `True` |
| `v3_beats_fixture_gate` | `True` |
| `v3_beats_static_gate` | `True` |
| `sota_delta_gate` | `True` |
| `fixture_collapse_gate` | `True` |

## Mutation Breakdown

| Mutation | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
| `phase7_static_hard_arithmetic_operator` | `122` | `4` | `0.3333` | `0.5417` | `1.0000` |
| `phase7_static_hard_bitshift_direction` | `2` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `phase7_static_hard_bitwise_operator` | `2` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `phase7_static_hard_compound_assignment` | `14` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `phase7_static_hard_constant` | `60` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `phase7_static_hard_original_control` | `112` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `phase7_static_hard_predicate_equality` | `24` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `phase7_static_hard_predicate_strictness` | `65` | `5` | `0.8571` | `0.8929` | `1.0000` |
| `phase7_static_hard_return_expression` | `102` | `0` | `0.0000` | `0.0000` | `0.0000` |

## Interpretation

Phase 7C2 专门补 `static-hard` 候选：每个候选只做一次局部源码微扰，尽量保留原函数控制结构和编译形态，用来检查 Phase 7C 中 static baseline 过强是否只是因为 fixture-ifchain 候选结构太明显。
