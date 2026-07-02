# Decompilation Faithfulness Phase 3 Readiness Preflight

- Verdict: `ready-for-combinatorial-phase3-cpu-audit`
- Method gate passed: `True`
- Phase 2 v3 verdict: `pass-v3-boundary-trace`
- Phase 2 v3 pairwise AUC: `1.0`
- Phase 2 v3 fixture collapse: `False`
- Phase 2 v3 trace-zero blind spots: `0`
- Repository source candidate count: `12`
- Phase 3 manifest exists: `False`
- Phase 3 source pool exists: `True`
- Phase 3 source pool function count: `12`
- Phase 3 source selection verdict: `ready-for-combinatorial-phase3-cpu-audit`
- Phase 3 source selection eligible count: `12`
- Phase 3 source selection subset count: `3289`
- Selected function count: `0`
- Fixture-ready count: `0`

## Interpretation

Phase 2 v3 的方法 gate 已经足够支持设计 Phase 3 readiness check。现在 Phase 3 不再依赖一次性固定 5 个函数，而是使用 source pool + combinatorial subset selection。

因此当前还不应该直接启动 GPU candidate generation，也不应该宣称 arbitrary real-project transfer 已经完成。下一步应先在多个推荐子集上跑 CPU-only v3 boundary trace audit。

## Repository Source Candidates

Excluded dirs: `.git, __pycache__, analysis_outputs, docs, tests`

| Path | Kind |
|---|---|
| `analysis_inputs/decompile_faithfulness/phase3_sources/bounded_abs100.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/clamp_then_square.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/days_before_month.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/gcd_nonnegative.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/high_nibble.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/mod3_sum_digits.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/parity8.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/popcount_nibble_diff.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/safe_div_round0.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/sat_add8.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/triangle_wave10.c` | `c_source` |
| `analysis_inputs/decompile_faithfulness/phase3_sources/within_range_inclusive.c` | `c_source` |

## Recommended Next Steps

1. Run the combinatorial Phase 3 CPU audit using v3 boundary trace across the recommended subsets.
2. Treat one subset failure as local evidence; only repeated failures across diverse subsets should count against the method.
3. Only consider GPU candidate generation after CPU audit confirms compile/oracle coverage and no fixture collapse.
