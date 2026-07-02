# Decompilation Faithfulness Phase 3 Source Selection

- Verdict: `ready-for-combinatorial-phase3-cpu-audit`
- Candidate functions: `12`
- Eligible functions: `12`
- Enumerated subsets: `3289`
- Subset size range: `5` - `10`

## Key Point

Phase 3 不采用一次性固定 5 个函数的脆弱设计，而是先建立候选池，再枚举多个 5-10 函数子集。单个子集失败只能触发局部归因：可能是该函数、该风险族、该 oracle/domain 定义或 candidate distribution 有问题。只有多个低重叠、高覆盖子集反复失败，才应升级为方法层面的负结论。

Negative conclusion policy: Do not reject the method from one failed subset. Require repeated failures across diverse high-coverage subsets before treating Phase 3 as a method-level failure.

## Source Validation

| Case | Compiled | Fixture Passed | Tags |
|---|---:|---:|---|
| `bounded_abs100` | `True` | `True` | `branch, boundary, sign_zero, unary` |
| `sat_add8` | `True` | `True` | `arithmetic, branch, boundary, multi_arg` |
| `within_range_inclusive` | `True` | `True` | `branch, comparison, multi_arg, boundary` |
| `parity8` | `True` | `True` | `bitwise, loop, boundary, unary` |
| `high_nibble` | `True` | `True` | `bitwise, boundary, unary` |
| `gcd_nonnegative` | `True` | `True` | `loop, modulo, multi_arg, sign_zero` |
| `mod3_sum_digits` | `True` | `True` | `loop, division, modulo, sign_zero, unary` |
| `days_before_month` | `True` | `True` | `branch, loop, boundary, calendar_like, unary` |
| `triangle_wave10` | `True` | `True` | `branch, modulo, sign_zero, boundary, unary` |
| `safe_div_round0` | `True` | `True` | `branch, division, multi_arg, sign_zero` |
| `clamp_then_square` | `True` | `True` | `arithmetic, branch, boundary, unary` |
| `popcount_nibble_diff` | `True` | `True` | `bitwise, loop, multi_arg, sign_zero` |

## Top Subsets

| Rank | Score | Size | Cases | Critical Tags |
|---:|---:|---:|---|---|
| 1 | `1159` | `10` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 2 | `1155` | `10` | `sat_add8, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square, popcount_nibble_diff` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 3 | `1140` | `9` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 4 | `1140` | `9` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 5 | `1140` | `9` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 6 | `1140` | `9` | `sat_add8, within_range_inclusive, parity8, high_nibble, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 7 | `1140` | `9` | `sat_add8, within_range_inclusive, parity8, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 8 | `1140` | `9` | `sat_add8, within_range_inclusive, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 9 | `1140` | `9` | `within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 10 | `1139` | `10` | `bounded_abs100, sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 11 | `1139` | `10` | `bounded_abs100, sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| 12 | `1139` | `10` | `bounded_abs100, sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |

## Top Subset By Size

| Size | Score | Cases | Critical Tags |
|---:|---:|---|---|
| `5` | `1048` | `sat_add8, within_range_inclusive, parity8, gcd_nonnegative, safe_div_round0` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| `6` | `1077` | `sat_add8, within_range_inclusive, parity8, gcd_nonnegative, days_before_month, safe_div_round0` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| `7` | `1102` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, days_before_month, safe_div_round0` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| `8` | `1121` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, safe_div_round0` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| `9` | `1140` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |
| `10` | `1159` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` | `arithmetic, bitwise, boundary, branch, division, loop, multi_arg, sign_zero` |

## Recommended Diverse Subsets

| Rank | Score | Size | Cases |
|---:|---:|---:|---|
| 1 | `1048` | `5` | `sat_add8, within_range_inclusive, parity8, gcd_nonnegative, safe_div_round0` |
| 2 | `1102` | `7` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, days_before_month, safe_div_round0` |
| 3 | `1159` | `10` | `sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, clamp_then_square` |
| 4 | `1135` | `10` | `bounded_abs100, sat_add8, parity8, high_nibble, gcd_nonnegative, mod3_sum_digits, days_before_month, triangle_wave10, safe_div_round0, popcount_nibble_diff` |
| 5 | `1119` | `10` | `bounded_abs100, sat_add8, within_range_inclusive, parity8, high_nibble, gcd_nonnegative, days_before_month, safe_div_round0, clamp_then_square, popcount_nibble_diff` |

## How To Interpret Future Failures

1. 如果单个函数原始 source 编译或 fixture 失败，先修 source manifest，不记录为方法失败。
2. 如果一个子集失败但其他低重叠子集通过，记录为 subset-specific failure。
3. 如果同一风险族反复失败，进入 targeted hard-case analysis。
4. 只有多个低重叠、高覆盖子集都无法维持 no-fixture-collapse 和合理 AUC，才考虑 Phase 3 方法 gate 失败。
