# Decompilation Faithfulness Phase 2 V3 Scoring Diagnostic

- Verdict: `needs-boundary-input-regeneration`
- Baseline AUC: `0.9623`
- Best non-fixture formula: `trace_total_v2` AUC `0.9623`
- Best fixture-aware diagnostic: `trace_total_plus_fixture_0.25` AUC `1.0000`
- Trace-zero blind spot candidates: `2`

## Formula Table

| Formula | Risk | AUC | Misordered/Tied | Zero-scored Wrong | Remaining Trace-zero Blind Spots | Weak Cases |
|---|---|---:|---:|---:|---:|---|
| `trace_total_v2` | `method_candidate` | 0.9623 | 8 / 106 | 2 | 2 | `{'signum': 0.9, 'is_power_of_two': 0.9285714285714286}` |
| `trace_total_plus_boundary_0.25` | `method_candidate` | 0.9623 | 8 / 106 | 2 | 2 | `{'signum': 0.9, 'is_power_of_two': 0.9285714285714286}` |
| `trace_total_plus_boundary_1.00` | `method_candidate` | 0.9623 | 8 / 106 | 2 | 2 | `{'signum': 0.9, 'is_power_of_two': 0.9285714285714286}` |
| `trace_total_plus_zero_1.00` | `method_candidate` | 0.9623 | 8 / 106 | 2 | 2 | `{'signum': 0.9, 'is_power_of_two': 0.9285714285714286}` |
| `trace_total_plus_fixture_0.25` | `diagnostic_fixture_aware` | 1.0000 | 0 / 106 | 0 | 0 | `{}` |
| `trace_total_plus_fixture_1.00` | `diagnostic_fixture_aware` | 1.0000 | 0 / 106 | 0 | 0 | `{}` |
| `max_trace_fixture` | `diagnostic_fixture_aware` | 1.0000 | 0 / 106 | 0 | 0 | `{}` |

## Trace-zero Blind Spots

- `signum` `strict_bug` `full_v1__phase2_gpu_signum_strict_bug_02`: fixture_mismatch `0.2000`, boundary_mismatch `0.0000`, zero_mismatch `0.0000`
- `is_power_of_two` `strict_bug` `topup_v1__phase2_gpu_is_power_of_two_strict_bug_03`: fixture_mismatch `0.1429`, boundary_mismatch `0.0000`, zero_mismatch `0.0000`

## Interpretation

这个诊断只复用 Phase 2 combined records，不重新生成候选，也不重跑 trace。

如果 boundary/zero-only formula 没有优于 v2，而 fixture-aware diagnostic 能消除 blind spot，则说明问题不只是 scoring weight，而是 primary generated trace inputs 缺少必要 boundary cases。此时 v3 应优先重新生成 boundary-aware trace inputs，而不是把 fixture_mismatch 直接加入主方法。

Fixture-aware warning: fixture-aware formulas are diagnostic upper bounds because fixture_mismatch is adjacent to the behavior gate used for labels; they should not be claimed as the final method.
