# Decompilation Faithfulness Phase 5B Hard Candidates

- Verdict: `pass-phase5b-hard-candidate-sota-delta`
- Source functions: `38`
- Source projects: `['c_algorithms', 'thealgorithms_c']`
- Candidates: `177`
- Compile pass count: `177`
- Behavior labels: `{'faithful': 38, 'plausible_wrong': 139}`
- Paired case count: `38`
- Fixture-passing wrong count: `139`
- Fixture-only AUC: `0.5000`
- V3 hard trace AUC: `1.0000`
- SOTA delta vs fixture-only: `0.5000`
- Fixture collapse: `False`
- Candidate manifest verdict: `pass-phase5b-full-hard-candidate-generation`

## Gate Check

| Gate | Passed |
|---|---:|
| `scale_gate` | `True` |
| `fixture_passing_wrong_gate` | `True` |
| `v3_auc_gate` | `True` |
| `sota_delta_gate` | `True` |
| `fixture_collapse_gate` | `True` |

## Interpretation

Phase 5B 专门测试 fixture-only 的盲区：candidate 先被构造成通过原始 fixtures，再用独立 hard probes 由 source-known oracle 判定是否存在语义漂移。

如果本结果通过，它说明 Dynamic Trace v3 在 fixture-passing wrong candidates 上确实提供了超出 fixture-only 的审计信号。它仍不是 decompiler-output transfer；Phase 6 还需要真实 decompiler/LLM-decompiler 输出。
