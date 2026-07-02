# Decompilation Faithfulness Phase 3 Combinatorial CPU Audit

- Verdict: `pass-combinatorial-phase3-cpu-audit`
- Case count: `12`
- Candidate count: `28`
- Label counts: `{'faithful': 12, 'plausible_wrong': 16}`
- Overall pairwise AUC: `1.0000`
- Fixture collapse: `False`
- Fixture-passing wrong count: `4`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase3_combinatorial_cpu_audit/records.jsonl`

## Interpretation

这是 Phase 3 的 CPU-only 组合审计，不使用 GPU。它不再依赖单次选择 5 个函数，而是在 source selection 推荐的 minimal / balanced / broad / low-overlap 子集上同时检查 v3 boundary trace。

本轮候选是 source-known manual stress candidates，标签来自人工语义标注，不是 fixture pass/fail。这样可以显式检查 fixture-passing wrong candidates 是否仍能被 wider v3 trace 抓住。

## Case AUC

| Case | Pairwise AUC |
|---|---:|
| `bounded_abs100` | `1.0000` |
| `clamp_then_square` | `1.0000` |
| `days_before_month` | `1.0000` |
| `gcd_nonnegative` | `1.0000` |
| `high_nibble` | `1.0000` |
| `mod3_sum_digits` | `1.0000` |
| `parity8` | `1.0000` |
| `popcount_nibble_diff` | `1.0000` |
| `safe_div_round0` | `1.0000` |
| `sat_add8` | `1.0000` |
| `triangle_wave10` | `1.0000` |
| `within_range_inclusive` | `1.0000` |

## Recommended Subset Metrics

| Rank | Size | AUC | Fixture Collapse | Fixture-passing Wrong | Cases |
|---:|---:|---:|---:|---:|---|
| 1 | `5` | `1.0000` | `False` | `3` | `sat_add8, within_range_inclusive, parity8, gcd_nonnegative, safe_div_round0` |
| 2 | `7` | `1.0000` | `False` | `3` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, days_before_month, safe_div_round0` |
| 3 | `10` | `1.0000` | `False` | `4` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` |
| 4 | `10` | `1.0000` | `False` | `4` | `bounded_abs100, sat_add8, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, popcount_nibble_diff` |
| 5 | `10` | `1.0000` | `False` | `3` | `bounded_abs100, sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, days_before_month, safe_div_round0, clamp_then_square, popcount_nibble_diff` |

## Fixture-passing Wrong Examples

| Case | Candidate | Trace Total | Trace Mismatch Rate |
|---|---|---:|---:|
| `sat_add8` | `sat_add8_upper_bound_256_hidden` | `0.0185` | `0.0115` |
| `parity8` | `parity8_counts_16_bits_hidden` | `0.2531` | `0.1053` |
| `mod3_sum_digits` | `mod3_sum_digits_ignores_negative_hidden` | `0.3859` | `0.1786` |
| `safe_div_round0` | `safe_div_round0_b_one_hidden` | `0.1277` | `0.0765` |

## Claim Boundary

这个结果如果通过，只支持 source-known small-function transfer readiness。它仍不等于 arbitrary real-project transfer，也不等于 binary-only semantic equivalence。GPU 2/3 只有在需要生成新 LLM candidates 时才进入下一步。
