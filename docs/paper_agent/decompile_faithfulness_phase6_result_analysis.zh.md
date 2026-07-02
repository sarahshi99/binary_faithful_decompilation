# Decompilation Faithfulness Phase 6 Result Analysis

- Verdict: `pass-phase6-decompiler-like-ccfa-proxy`
- Tool probe verdict: `ready-for-assembly-context-decompiler-like-generation`
- Real decompiler output available: `False`
- Source functions: `38`
- Candidates: `430`
- Compile pass count: `430`
- Paired case count: `38`
- Label counts: `{'faithful': 152, 'plausible_wrong': 278}`
- Fixture-passing wrong count: `278`
- Fixture-only AUC: `0.5000`
- Static structured proxy AUC: `0.9487`
- Dynamic Trace v3 AUC: `1.0000`
- SOTA delta vs best non-oracle baseline: `0.0513`
- V3 behavior-preserving rewrite FP rate: `0.0000`
- Static behavior-preserving rewrite FP rate: `1.0000`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6_decompiler_like/records.jsonl`

## Gate Check

| Gate | Passed |
|---|---:|
| `source_function_scale_gate` | `True` |
| `compile_pass_scale_gate` | `True` |
| `paired_function_gate` | `True` |
| `v3_beats_fixture_gate` | `True` |
| `v3_beats_static_gate` | `True` |
| `behavior_preserving_fp_gate` | `True` |

## By Optimization Level

| Opt | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
| `O0` | `215` | `38` | `0.5000` | `1.0000` | `1.0000` |
| `O2` | `215` | `38` | `0.5000` | `0.9460` | `1.0000` |

## By Candidate Source

| Source | Candidates | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|
| `assembly_context_decompiler_like_control` | `76` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `assembly_context_decompiler_like_fixture_ifchain` | `278` | `0` | `0.0000` | `0.0000` | `0.0000` |
| `assembly_context_decompiler_like_rewrite` | `76` | `0` | `0.0000` | `0.0000` | `0.0000` |

## Failure Taxonomy

| Category | Count |
|---|---:|
| `decompiler_tool_unavailable` | `1` |
| `decompiler_syntax_failure` | `0` |
| `candidate_compile_failure` | `0` |
| `undefined_behavior_mismatch` | `0` |
| `oracle_domain_mismatch` | `0` |
| `trace_domain_miss` | `0` |
| `fixture_passing_semantic_drift` | `278` |
| `behavior_preserving_rewrite_false_positive` | `0` |
| `baseline_stronger_than_v3` | `0` |

## Interpretation

这是 full-scale Phase 6 proxy：覆盖 Phase 5 的全部 `38` 个 source-known 函数，并按 `O0/O2` 生成 objdump assembly context。候选是 `assembly_context_decompiler_like`，不是 Ghidra/RetDec/r2 的真实 decompiler output。

本轮正向点是：在 fixture-only 被 fixture-ifchain 候选压成弱 baseline 的情况下，Dynamic Trace v3 仍能抓住 fixture-passing semantic drift；同时 behavior-preserving noop-guard rewrite 的 v3 false positive 需要保持低。CCF-A 主张仍不能写成“真实反编译器输出已验证”，下一步需要真实 decompiler 依赖计划来补这条证据链。
