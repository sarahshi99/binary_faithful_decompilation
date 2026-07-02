# Phase 5 Project Candidates

## Candidate Source Trees

- `analysis_inputs/decompile_faithfulness/phase5_external_sources/thealgorithms_c`
- `analysis_inputs/decompile_faithfulness/phase5_external_sources/c_algorithms`

## Exclusion Rules

只保留 deterministic、bounded-domain、integer-trace-compatible 的 C functions。带 I/O、heap-only API、数组/结构体主接口、外部状态、callback 或无法稳定生成边界 oracle 的函数不进入本轮 gate。

## Selected Projects

- `thealgorithms_c`: 以原始小型算法/LeetCode/转换/游戏 helper 为主。
- `c_algorithms`: 原项目多为 pointer/container API；本轮只保留少量明确标注的 scalar adapters，用于测试第二真实项目来源，不把它们夸大为原生 scalar API。

## Function Pool

| Case | Project | Kind | Signature | Risks |
|---|---|---|---|---|
| `ta_gcd_GCD` | `thealgorithms_c` | `direct_function` | `int GCD(int x, int y)` | `loop, modulo, positive_domain` |
| `ta_lcm_gcd` | `thealgorithms_c` | `direct_function` | `int gcd(int a, int b)` | `loop, modulo, positive_domain` |
| `ta_lcm_lcm` | `thealgorithms_c` | `direct_function` | `int lcm(int a, int b)` | `arithmetic, division, positive_domain` |
| `ta_armstrong_power` | `thealgorithms_c` | `direct_function` | `int power(int x, unsigned int y)` | `recursion, boundary, nonnegative_domain` |
| `ta_armstrong_order` | `thealgorithms_c` | `direct_function` | `int order(int x)` | `loop, digits, nonnegative_domain` |
| `ta_armstrong_isArmstrong` | `thealgorithms_c` | `direct_function` | `int isArmstrong(int x)` | `digits, helper_dependency, boundary` |
| `ta_decimal_to_binary` | `thealgorithms_c` | `direct_function` | `int decimal_to_binary(unsigned int number)` | `conversion, recursion, nonnegative_domain` |
| `ta_decimal_to_octal` | `thealgorithms_c` | `direct_function` | `int decimal_to_octal(int decimal)` | `conversion, recursion, boundary` |
| `ta_binary_to_octal_three_digits` | `thealgorithms_c` | `direct_function` | `int three_digits(int n)` | `conversion, digits, loop` |
| `ta_affine_mod_inverse` | `thealgorithms_c` | `direct_function` | `int modular_multiplicative_inverse(unsigned int a, unsigned int m)` | `modulo, loop, zero_boundary` |
| `ta_euler_is_palindromic` | `thealgorithms_c` | `direct_function` | `int is_palindromic(unsigned int n)` | `digits, loop, boundary` |
| `ta_leetcode_tribonacci` | `thealgorithms_c` | `direct_function` | `int tribonacci(int n)` | `dynamic_programming, loop, boundary` |
| `ta_leetcode_fib` | `thealgorithms_c` | `direct_function` | `int fib(int N)` | `recursion, boundary, nonnegative_domain` |
| `ta_leetcode_divide` | `thealgorithms_c` | `direct_function` | `int divide(int dividend, int divisor)` | `division, loop, positive_domain` |
| `ta_leetcode_reverse` | `thealgorithms_c` | `direct_function` | `int reverse(int x)` | `digits, sign_zero, overflow_guard` |
| `ta_leetcode_range_bitwise_and` | `thealgorithms_c` | `direct_function` | `int rangeBitwiseAnd(int m, int n)` | `bitwise, loop, boundary` |
| `ta_leetcode_find_complement` | `thealgorithms_c` | `direct_function` | `int findComplement(int num)` | `bitwise, loop, positive_domain` |
| `ta_leetcode_hamming_distance` | `thealgorithms_c` | `direct_function` | `int hammingDistance(int x, int y)` | `bitwise, loop, zero_boundary` |
| `ta_leetcode_unique_paths` | `thealgorithms_c` | `direct_function` | `int uniquePaths(int m, int n)` | `dynamic_programming, multi_arg, positive_domain` |
| `ta_leetcode_max` | `thealgorithms_c` | `direct_function` | `int max(int a, int b)` | `branch, comparison, sign_zero` |
| `ta_leetcode_get_point_key` | `thealgorithms_c` | `direct_function` | `int getPointKey(int i, int j, int boardSize, int boardColSize)` | `arithmetic, multi_arg, boundary` |
| `ta_leetcode_get_triplet_id` | `thealgorithms_c` | `direct_function` | `int getTripletId(int i, int j)` | `division, grid_boundary, multi_arg` |
| `ta_leetcode_intersection_size` | `thealgorithms_c` | `direct_function` | `int intersectionSize(int p11, int p12, int p21, int p22)` | `geometry, branch, boundary` |
| `ta_leetcode_compute_area` | `thealgorithms_c` | `direct_function` | `int computeArea(int ax1, int ay1, int ax2, int ay2, int bx1, int by1, int bx2, int by2)` | `geometry, helper_dependency, multi_arg` |
| `ta_leetcode_my_sqrt` | `thealgorithms_c` | `direct_function` | `int mySqrt(int x)` | `binary_search, boundary, nonnegative_domain` |
| `ta_bucket_get_bucket_index` | `thealgorithms_c` | `direct_function` | `int getBucketIndex(int value)` | `division, bucket_boundary, nonnegative_domain` |
| `ta_naval_valid_entry_line_column` | `thealgorithms_c` | `direct_function` | `int validEntryLineColumn(int line, char column)` | `range_check, char_boundary, branch` |
| `ta_shunting_get_precedence` | `thealgorithms_c` | `direct_function` | `int getPrecedence(char operator)` | `char_boundary, branch, operator_precedence` |
| `ta_shunting_get_associativity` | `thealgorithms_c` | `direct_function` | `int getAssociativity(char operator)` | `char_boundary, branch, operator_associativity` |
| `ta_infix_is_operand` | `thealgorithms_c` | `direct_function` | `int isOprnd(char ch)` | `char_boundary, range_check, branch` |
| `ta_infix_precedence_two` | `thealgorithms_c` | `direct_function` | `int getPrecedence (char op1, char op2)` | `char_boundary, operator_precedence, multi_arg` |
| `ta_leetcode_min` | `thealgorithms_c` | `direct_function` | `int min(int a, int b)` | `branch, comparison, sign_zero` |
| `ta_leetcode_maxval` | `thealgorithms_c` | `direct_function` | `int maxval(int a, int b)` | `branch, comparison, sign_zero` |
| `ca_int_hash_value` | `c_algorithms` | `scalar_adapter` | `int ca_int_hash_value(int value)` | `adapter, hash, sign_zero` |
| `ca_int_equal_values` | `c_algorithms` | `scalar_adapter` | `int ca_int_equal_values(int left, int right)` | `adapter, comparison, sign_zero` |
| `ca_int_compare_values` | `c_algorithms` | `scalar_adapter` | `int ca_int_compare_values(int left, int right)` | `adapter, comparison, sign_zero` |
| `ca_string_hash_selector` | `c_algorithms` | `scalar_adapter` | `int ca_string_hash_selector(int selector)` | `adapter, hash, branch` |
| `ca_string_nocase_hash_selector` | `c_algorithms` | `scalar_adapter` | `int ca_string_nocase_hash_selector(int selector)` | `adapter, hash, case_boundary` |

## Scale Risk

- Source projects: `2` / required `2`
- Eligible real-project functions: `38` / required `30`
- Source gate verdict: `pass-phase5-source-gate`
- Preflight verdict: `pass-phase5-preflight`

这一步专门回应“小函数池/smoke 不跑 full 是否有说服力”：Phase 5 不再使用 Phase 3 的 12 个 curated functions 作为主证据，而是把真实项目函数池扩展到 `30+` 后才允许进入 GPU candidate generation。

## Next Gate

只有当 `decompile_faithfulness_phase5_preflight.json` 为 `pass-phase5-preflight` 时，才启动 GPU 2/3 生成 100-200 个 compile-pass candidates。
