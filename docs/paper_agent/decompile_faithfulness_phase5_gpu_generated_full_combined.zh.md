# Decompilation Faithfulness Phase 5 GPU Generated Combined

- Verdict: `needs-more-phase5-gpu-generated-samples`
- Source functions: `38`
- Source projects: `['c_algorithms', 'thealgorithms_c']`
- Generations: `452`
- Parsed candidates: `260`
- Evaluated candidates: `260`
- Compile pass count: `113`
- Behavior labels: `{'faithful': 71, 'compile_fail': 147, 'plausible_wrong': 42}`
- Paired case count: `17`
- Fixture-passing wrong count: `0`
- Trace pairwise AUC: `1.0000`
- Fixture collapse: `True`
- Candidate manifest verdict: `needs-full-candidate-generation`

## By Project

| Project | Label Counts |
|---|---|
| `c_algorithms` | `{'faithful': 10, 'compile_fail': 14, 'plausible_wrong': 2}` |
| `thealgorithms_c` | `{'compile_fail': 133, 'plausible_wrong': 40, 'faithful': 61}` |

## CCF-A 风险自查

1. Full-scale 风险：只有当 compile-pass candidates `>=100` 且 paired functions `>=20` 时，本 combined report 才会给出 `pass-phase5-full-candidate-generation`。
2. SOTA 进步风险：本文件只说明 candidate generation 和 bounded trace audit 是否达到规模。最终是否达到 CCF-A/SOTA 贡献，还必须继续跑 Phase 5 result analysis，对比 fixture-only、static/binary motif、Dynamic Trace v1/v2/v3，并检查 `v3 - best non-oracle baseline >= 0.05`。
