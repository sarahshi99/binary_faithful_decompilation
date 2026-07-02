# Decompilation Faithfulness Phase 5 Gate Decision

- Decision: `pass-phase5b-hard-candidate-sota-delta`
- Source gate: `pass-phase5-source-gate`
- Preflight: `pass-phase5-preflight`
- Phase 5A regular candidates: `scale-positive-sota-delta-not-established`
- Phase 5B hard candidates: `pass-phase5b-hard-candidate-sota-delta`
- Eligible functions: `38`
- Source projects: `2`
- Oracle ready: `38` / `38`

## Phase 5A Regular Candidate Distribution

- Candidates: `450`
- Compile-pass candidates: `303`
- Paired functions: `38`
- Fixture-passing wrong candidates: `0`
- Fixture-only AUC: `1.0000`
- Dynamic Trace v3 AUC: `1.0000`
- SOTA delta vs fixture-only: `0.0000`
- Verdict: `scale-positive-sota-delta-not-established`

解释：Phase 5A 解决了 full-scale / smoke 风险，但候选太容易，fixture-only 已经能区分 wrong candidates。因此它证明 pipeline 可规模化，但不能单独证明 v3 的 SOTA 增益。

## Phase 5B Fixture-Passing Hard Candidate Distribution

- Candidates: `177`
- Compile-pass candidates: `177`
- Paired functions: `38`
- Fixture-passing wrong candidates: `139`
- Fixture-only AUC: `0.5000`
- Dynamic Trace v3 AUC: `1.0000`
- SOTA delta vs fixture-only: `0.5000`
- Fixture collapse: `False`
- Verdict: `pass-phase5b-hard-candidate-sota-delta`

解释：Phase 5B 专门构造通过原始 fixtures、但在独立 hard probes 上与 source oracle 不一致的候选。这个设置正好测试 fixture-only 的盲区；v3 在这里给出 `+0.5000` AUC 增量，说明方法贡献在 hard candidate distribution 上成立。

## Final Phase 5 Decision

Phase 5 当前结论是：

`pass-phase5b-hard-candidate-sota-delta`

这意味着：

1. 小函数池 / smoke 风险已经显著缓解：真实项目 `38` 函数、`2` 项目来源、full-scale candidate count 已达标。
2. SOTA 增益风险在 hard candidate distribution 上得到正面证据：v3 明显优于 fixture-only。
3. 还不能直接声称 binary-only verifier 或真实 decompiler-output transfer 已完成。

## Next

可以进入 Phase 6，但 Phase 6 的目标必须明确：

1. 不再验证“v3 是否能赢 fixture-only hard candidates”，这个 Phase 5B 已经过。
2. Phase 6 要验证 decompiler-output / LLM-decompiler-output 分布中是否也存在 fixture-passing semantic drift。
3. 如果真实 decompiler-output 不足以产生 hard negatives，需要报告 candidate-generation limitation，而不是否定 v3 方法本身。
