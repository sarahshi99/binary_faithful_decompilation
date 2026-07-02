# Decompilation Faithfulness Phase 7 Public Benchmark Result

- Verdict: `method-negative-public-benchmark`
- Benchmark: `CodeFuse-DeBench`
- Source functions: `56`
- Candidates: `600`
- Compile pass count: `600`
- Paired case count: `53`
- Label counts: `{'faithful': 242, 'plausible_wrong': 358}`
- Fixture-passing wrong count: `358`
- Fixture-only AUC: `0.5000`
- Static structured proxy AUC: `0.9693`
- Dynamic Trace v3 AUC: `1.0000`
- Delta vs best non-oracle baseline: `0.0307`
- V3 behavior-preserving FP rate: `0.0000`
- External-paper SOTA claim ready: `False`
- External-paper SOTA blocker: This run is a public benchmark alignment row, not yet a direct reproduction of LLM4Decompile/DecompileBench generation metrics or a second compile-ready decompiler.
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase7_public_benchmark_eval/records.jsonl`

## Gate Check

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

## Risk-family Breakdown

| Risk | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
| `branch` | `200` | `19` | `0.5000` | `0.9536` | `1.0000` |
| `loop` | `116` | `11` | `0.5000` | `0.9839` | `1.0000` |
| `multi_arg` | `214` | `19` | `0.5000` | `1.0000` | `1.0000` |
| `operator_boundary` | `412` | `37` | `0.5000` | `0.9554` | `1.0000` |
| `public_benchmark` | `600` | `53` | `0.5000` | `0.9693` | `1.0000` |

## Mutation Breakdown

| Mutation | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
| `phase7_behavior_preserving_noop_guard` | `112` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `phase7_fixture_ifchain_semantic_drift` | `376` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `phase7_original_control` | `112` | `0` | `0.0000` | `0.0000` | `0.0000` |

## Failure Taxonomy

| Category | Count |
|---|---:|
| `candidate_compile_failure` | `0` |
| `fixture_passing_semantic_drift` | `358` |
| `trace_domain_miss` | `18` |
| `behavior_preserving_rewrite_false_positive` | `0` |

## Interpretation

这是 Phase 7C 的 full public benchmark row：输入来自 CodeFuse-DeBench 的保守 source-known scalar C 主集，候选为 CPU-only deterministic/decompiler-like controls 和 fixture-overfit semantic drift variants，覆盖 `O0/O2`。这一步回答的是“Dynamic Trace v3 能否在公开 benchmark 对齐行上超过 fixture/static auditor”，不是“生成模型是否超过相关工作”。
