# Decompilation Faithfulness Phase 3 GPU Generated Combined Analysis

- Verdict: `pass-phase3-gpu-generated-combined-analysis`
- Candidate count: `47`
- Compile pass count: `28`
- Label counts: `{'compile_fail': 19, 'faithful': 16, 'plausible_wrong': 12}`
- Paired case count: `5`
- Pair count: `26`
- Pairwise AUC: `1.0000`
- Fixture collapse: `False`
- Fixture-passing trace mismatch count: `1`

## Interpretation

四个 Phase 3 GPU generated smoke/top-up run 合并后，已经形成可解释的 generated-candidate distribution。单个小 run 可能 paired cases 不足或 fixture-collapse 统计不可解读；合并后有 5 个 case 出现 faithful/wrong 配对，overall pairwise AUC 为 `1.0000`，并且出现 fixture-passing 但 trace-mismatching 的 generated candidate。

这支持的仍是 source-known small-function transfer readiness，不是 arbitrary real-project transfer 或 binary-only semantic equivalence。

## Run Metrics

| Run | Candidates | Compile Pass | Labels | Pairs | AUC | Fixture Collapse |
|---|---:|---:|---|---:|---:|---:|
| `cuda2_base` | `10` | `7` | `{'compile_fail': 3, 'faithful': 6, 'plausible_wrong': 1}` | `0` | `0.0000` | `True` |
| `cuda2_bugtopup` | `10` | `4` | `{'compile_fail': 6, 'faithful': 1, 'plausible_wrong': 3}` | `0` | `0.0000` | `True` |
| `cuda3_base` | `12` | `7` | `{'compile_fail': 5, 'faithful': 4, 'plausible_wrong': 3}` | `1` | `1.0000` | `True` |
| `cuda3_bugtopup` | `15` | `10` | `{'compile_fail': 5, 'faithful': 5, 'plausible_wrong': 5}` | `6` | `1.0000` | `False` |

## Case Metrics

| Case | Candidates | Compile Pass | Labels | Pairs | AUC | Fixture Collapse |
|---|---:|---:|---|---:|---:|---:|
| `days_before_month` | `2` | `1` | `{'compile_fail': 1, 'plausible_wrong': 1}` | `0` | `0.0000` | `True` |
| `gcd_nonnegative` | `6` | `2` | `{'compile_fail': 4, 'plausible_wrong': 2}` | `0` | `0.0000` | `True` |
| `high_nibble` | `5` | `5` | `{'faithful': 3, 'plausible_wrong': 2}` | `6` | `1.0000` | `True` |
| `parity8` | `10` | `5` | `{'compile_fail': 5, 'faithful': 4, 'plausible_wrong': 1}` | `4` | `1.0000` | `True` |
| `safe_div_round0` | `9` | `6` | `{'compile_fail': 3, 'faithful': 5, 'plausible_wrong': 1}` | `5` | `1.0000` | `False` |
| `sat_add8` | `8` | `6` | `{'compile_fail': 2, 'faithful': 3, 'plausible_wrong': 3}` | `9` | `1.0000` | `True` |
| `within_range_inclusive` | `7` | `3` | `{'compile_fail': 4, 'faithful': 1, 'plausible_wrong': 2}` | `2` | `1.0000` | `True` |

## Fixture-passing Trace Mismatch Examples

| Run | Case | Candidate | Trace Total | Trace Mismatch Rate |
|---|---|---|---:|---:|
| `cuda3_bugtopup` | `safe_div_round0` | `cuda3_bugtopup__phase3_gpu_safe_div_round0_strict_bug_02` | `0.2980` | `0.0706` |
