# Decompilation Faithfulness Phase 2 Result Analysis

- Verdict: `pass-phase2-result-analysis`
- Generations: `100`
- Parsed candidates: `78`
- Evaluated candidates: `78`
- Compile pass count: `63`
- Label counts: `{'faithful': 34, 'plausible_wrong': 29, 'compile_fail': 15}`
- Paired cases: `8` / `8`
- Fixture collapse: `False`
- Fixture-passing trace mismatches: `1`
- Trace pairwise AUC: `0.9623`

## Full Gate

- Passed: `True`
- Checks: `{'all_8_cases_represented': True, 'min_5_compile_pass_per_case': True, 'at_least_5_paired_cases': True, 'all_cases_paired': True, 'trace_auc_at_least_0_9': True}`
- Compile pass by case: `{'absdiff': 7, 'clamp8': 6, 'count_bits8': 5, 'gcd_positive': 7, 'is_power_of_two': 11, 'max3': 12, 'signum': 9, 'sum_to_n': 6}`

## Case Table

| Case | Gen | Parsed | Compiled | Labels | Hidden | AUC | Misordered/Tied | Margin |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| `absdiff` | 10 | 8 | 7 | `{'faithful': 4, 'plausible_wrong': 3, 'compile_fail': 1}` | 0 | 1.0000 | 0 / 12 | 0.7402 |
| `clamp8` | 10 | 7 | 6 | `{'faithful': 2, 'compile_fail': 1, 'plausible_wrong': 4}` | 0 | 1.0000 | 0 / 8 | 0.0774 |
| `count_bits8` | 10 | 8 | 5 | `{'faithful': 3, 'compile_fail': 3, 'plausible_wrong': 2}` | 1 | 1.0000 | 0 / 6 | 1.0961 |
| `gcd_positive` | 10 | 8 | 7 | `{'plausible_wrong': 4, 'faithful': 3, 'compile_fail': 1}` | 0 | 1.0000 | 0 / 12 | 1.2021 |
| `is_power_of_two` | 20 | 13 | 11 | `{'faithful': 4, 'compile_fail': 2, 'plausible_wrong': 7}` | 0 | 0.9286 | 4 / 28 | 0.0000 |
| `max3` | 20 | 17 | 12 | `{'faithful': 11, 'plausible_wrong': 1, 'compile_fail': 5}` | 0 | 1.0000 | 0 / 11 | 1.8435 |
| `signum` | 10 | 10 | 9 | `{'compile_fail': 1, 'faithful': 4, 'plausible_wrong': 5}` | 0 | 0.9000 | 4 / 20 | 0.0000 |
| `sum_to_n` | 10 | 7 | 6 | `{'faithful': 3, 'compile_fail': 1, 'plausible_wrong': 3}` | 0 | 1.0000 | 0 / 9 | 1.2208 |

## Prompt Table

| Prompt | Gen | Parsed | Compiled | Labels | Hidden | Parsed Rate | Compile Rate | Faithful Rate | Wrong Rate |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| `strict_bug` | 50 | 43 | 35 | `{'faithful': 9, 'plausible_wrong': 26, 'compile_fail': 8}` | 1 | 0.8600 | 0.8140 | 0.2571 | 0.7429 |
| `strict_rewrite` | 50 | 35 | 28 | `{'faithful': 25, 'compile_fail': 7, 'plausible_wrong': 3}` | 0 | 0.7000 | 0.8000 | 0.8929 | 0.1071 |

## Failure Analysis

- Cleaning status counts: `{'parsed_function': 78, 'parse_failed': 22}`
- Cleaning reason counts: `{'tried statuses: unbalanced_braces, unbalanced_braces': 5, 'tried statuses: unbalanced_braces': 5, 'tried statuses: missing_expected_function, missing_expected_function': 4, 'tried statuses: multiple_functions, multiple_functions': 2, 'tried statuses: rejected_library_call, rejected_library_call': 1, 'tried statuses: multiple_expected_functions, multiple_expected_functions': 1, 'tried statuses: rejected_ellipsis': 1, 'tried statuses: unbalanced_braces, missing_expected_function, missing_expected_function, rejected_preprocessor': 1, 'tried statuses: missing_expected_function': 1, 'tried statuses: rejected_preprocessor, rejected_preprocessor': 1}`
- Compile failure categories: `{'undeclared_or_forbidden_call': 4, 'syntax_or_compile_error': 11}`
- Runtime timeout count: `2`

## Hard Examples

Lowest-scored plausible wrong candidates:

- `signum` `strict_bug` `full_v1__phase2_gpu_signum_strict_bug_02`: trace_total `0.0000`, trace_mismatch `0.0000`, fixture_mismatch `0.2000`
- `is_power_of_two` `strict_bug` `topup_v1__phase2_gpu_is_power_of_two_strict_bug_03`: trace_total `0.0000`, trace_mismatch `0.0000`, fixture_mismatch `0.1429`
- `clamp8` `strict_bug` `full_v1__phase2_gpu_clamp8_strict_bug_01`: trace_total `0.0774`, trace_mismatch `0.0400`, fixture_mismatch `0.2000`
- `is_power_of_two` `strict_bug` `full_v1__phase2_gpu_is_power_of_two_strict_bug_01`: trace_total `0.3578`, trace_mismatch `0.1600`, fixture_mismatch `0.2857`
- `is_power_of_two` `strict_bug` `topup_v1__phase2_gpu_is_power_of_two_strict_bug_00`: trace_total `0.3578`, trace_mismatch `0.1600`, fixture_mismatch `0.2857`
- `clamp8` `strict_bug` `full_v1__phase2_gpu_clamp8_strict_bug_00`: trace_total `0.6963`, trace_mismatch `0.2400`, fixture_mismatch `0.4000`
- `absdiff` `strict_bug` `full_v1__phase2_gpu_absdiff_strict_bug_04`: trace_total `0.7402`, trace_mismatch `0.4142`, fixture_mismatch `0.2500`
- `absdiff` `strict_bug` `full_v1__phase2_gpu_absdiff_strict_bug_01`: trace_total `0.9401`, trace_mismatch `0.4615`, fixture_mismatch `0.5000`

Highest-scored faithful candidates:

- `count_bits8` `strict_bug` `full_v1__phase2_gpu_count_bits8_strict_bug_01`: trace_total `0.2387`, trace_mismatch `0.1053`, fixture_mismatch `0.0000`
- `absdiff` `strict_rewrite` `full_v1__phase2_gpu_absdiff_strict_rewrite_00`: trace_total `0.0000`, trace_mismatch `0.0000`, fixture_mismatch `0.0000`
- `absdiff` `strict_rewrite` `full_v1__phase2_gpu_absdiff_strict_rewrite_03`: trace_total `0.0000`, trace_mismatch `0.0000`, fixture_mismatch `0.0000`
- `absdiff` `strict_rewrite` `full_v1__phase2_gpu_absdiff_strict_rewrite_04`: trace_total `0.0000`, trace_mismatch `0.0000`, fixture_mismatch `0.0000`
- `absdiff` `strict_bug` `full_v1__phase2_gpu_absdiff_strict_bug_00`: trace_total `0.0000`, trace_mismatch `0.0000`, fixture_mismatch `0.0000`
- `clamp8` `strict_rewrite` `full_v1__phase2_gpu_clamp8_strict_rewrite_02`: trace_total `0.0000`, trace_mismatch `0.0000`, fixture_mismatch `0.0000`
- `clamp8` `strict_bug` `full_v1__phase2_gpu_clamp8_strict_bug_02`: trace_total `0.0000`, trace_mismatch `0.0000`, fixture_mismatch `0.0000`
- `count_bits8` `strict_rewrite` `full_v1__phase2_gpu_count_bits8_strict_rewrite_01`: trace_total `0.0000`, trace_mismatch `0.0000`, fixture_mismatch `0.0000`

Fixture-passing but trace-mismatching candidates:

- `count_bits8` `strict_bug` `full_v1__phase2_gpu_count_bits8_strict_bug_01`: trace_total `0.2387`, trace_mismatch `0.1053`, fixture_mismatch `0.0000`

```c
int count_bits8(int x) {
    int total = 0;
    for (int i = 0; i < 16; i++) {
        if ((x & (1 << i)) != 0) {
            total++;
        }
    }
    return total;
}
```


## Qualitative Findings

- Positive non-oracle example: `count_bits8` generated a fixture-passing implementation that counts 16 low bits instead of 8. The original fixture did not expose this because its tested values stay within the low-byte regime; Dynamic Trace v2 exposed the semantic drift on broader generated inputs.
- Boundary blind spot: the lowest-scored wrong examples include `signum` and `is_power_of_two` bugs around zero. These were caught by the fixture behavior gate but received trace_total `0.0000`, which means the primary generated trace set did not sufficiently cover those exact boundary inputs. A future v3 should fold fixture/boundary mismatch into the primary score or force zero-boundary coverage per domain.

## Interpretation

Phase 2 结果支持一个收窄但可防守的结论：在 source-known、小函数、bounded generated inputs 的 localized semantic bug auditing 设置下，Dynamic Trace v2 对本地 LLM 生成候选仍保持强区分度。

`faithful` 在这批实验中表示 fixture behavior gate 通过，不等于完整语义真值。报告中的 `Fixture-passing trace mismatches` 是最重要的 non-oracle 证据：这些候选通过了原 fixture，但在更宽的 generated trace inputs 上和源函数不一致。

这不支持 general decompilation faithfulness verifier，也不支持 real-project transfer。当前证据更适合写成：generated candidates 让 candidate distribution 更 realistic，而 Dynamic Trace v2 在这个分布上没有退化成 fixture-only oracle。

下一步不应继续堆 GPU 生成量。更有价值的是写 Phase 2 result table、case-level qualitative analysis、failure attribution，并设计一个小的 Phase 3 real-project-transfer readiness check。
