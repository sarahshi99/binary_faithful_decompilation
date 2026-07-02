# Decompilation Faithfulness Phase 5 GPU Generated Combined

- Verdict: `needs-more-phase5-gpu-generated-samples`
- Source functions: `38`
- Source projects: `['c_algorithms', 'thealgorithms_c']`
- Generations: `228`
- Parsed candidates: `103`
- Evaluated candidates: `103`
- Compile pass count: `56`
- Behavior labels: `{'faithful': 36, 'compile_fail': 47, 'plausible_wrong': 20}`
- Paired case count: `10`
- Fixture-passing wrong count: `0`
- Trace pairwise AUC: `1.0000`
- Fixture collapse: `True`
- Candidate manifest verdict: `needs-full-candidate-generation`

## By Project

| Project | Label Counts |
|---|---|
| `c_algorithms` | `{'faithful': 5}` |
| `thealgorithms_c` | `{'compile_fail': 47, 'plausible_wrong': 20, 'faithful': 31}` |

## CCF-A 风险自查

1. Full-scale 风险：只有当 compile-pass candidates `>=100` 且 paired functions `>=20` 时，本 combined report 才会给出 `pass-phase5-full-candidate-generation`。
2. SOTA 进步风险：本文件只说明 candidate generation 和 bounded trace audit 是否达到规模。最终是否达到 CCF-A/SOTA 贡献，还必须继续跑 Phase 5 result analysis，对比 fixture-only、static/binary motif、Dynamic Trace v1/v2/v3，并检查 `v3 - best non-oracle baseline >= 0.05`。
