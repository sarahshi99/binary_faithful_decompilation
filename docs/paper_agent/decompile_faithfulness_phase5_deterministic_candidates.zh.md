# Decompilation Faithfulness Phase 5 Deterministic Candidates

- Verdict: `pass-phase5-deterministic-candidate-layer`
- Source functions: `38`
- Candidates: `190`
- Compile pass count: `190`
- Behavior labels: `{'faithful': 38, 'plausible_wrong': 152}`
- Paired case count: `38`
- Fixture-passing wrong count: `0`
- Trace pairwise AUC: `1.0000`
- Fixture collapse: `True`
- Candidate manifest verdict: `pass-phase5-full-candidate-generation`

## 解释

这是 Phase 5 的 deterministic candidate layer：每个真实项目函数包含一个 behavior-preserving original 和多个 manual stress constants。它用于保证 source-known auditing 方法有 full-scale compile-pass paired data，不替代 LLM/decompiler candidate layer，也不能单独作为 SOTA 生成质量证据。
