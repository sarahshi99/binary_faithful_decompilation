# Decompilation Faithfulness Phase 2 V3 Boundary Trace

- Verdict: `pass-v3-boundary-trace`
- Candidate count: `63`
- Label counts: `{'faithful': 34, 'plausible_wrong': 29}`
- Pairwise AUC: `1.0000`
- Case pairwise AUC: `{'absdiff': 1.0, 'clamp8': 1.0, 'count_bits8': 1.0, 'gcd_positive': 1.0, 'is_power_of_two': 1.0, 'max3': 1.0, 'signum': 1.0, 'sum_to_n': 1.0}`
- Fixture collapse: `False`
- Trace-zero blind spot wrong count: `0`
- Fixture-passing trace mismatch count: `1`
- Input counts: `{'absdiff': 169, 'clamp8': 26, 'count_bits8': 21, 'max3': 256, 'sum_to_n': 27, 'signum': 28, 'is_power_of_two': 27, 'gcd_positive': 251}`

## Interpretation

V3 boundary trace 不使用 `fixture_mismatch_rate` 作为主分数，而是在 primary generated trace inputs 中强制保留通用 boundary probes，例如 `0`, `-1`, `1`。这避免了 v2 因为排除 fixture args 而同时排除通用边界值的问题。

成功 gate：overall AUC 至少保持 v2 combined 的 `0.9623`，`signum` 和 `is_power_of_two` case AUC 提升到 `1.0000`，`fixture_collapse=False`，且 trace-zero blind spot wrong count 归零。
