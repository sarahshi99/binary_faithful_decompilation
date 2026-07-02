# Decompilation Faithfulness Phase 5B -> Phase 6 Transition

## Current Status

Phase 5A regular candidate distribution 已证明 full-scale pipeline 能跑通，但没有证明 v3 相比 fixture-only 的增益：

- `450` candidates
- `303` compile-pass
- `38` paired functions
- fixture-only AUC `1.0000`
- v3 AUC `1.0000`
- delta `0.0000`

Phase 5B hard candidate distribution 建立了关键方法增益：

- `38` real-project source-known functions
- `177` candidates
- `177` compile-pass
- `38` paired functions
- `139` fixture-passing wrong candidates
- fixture-only AUC `0.5000`
- v3 AUC `1.0000`
- delta `0.5000`
- verdict `pass-phase5b-hard-candidate-sota-delta`

## Interpretation

现在可以说：在 source-known bounded auditing setting 中，Dynamic Trace v3 对 fixture-passing semantic drift 有明显增量。

仍不能说：

- 已解决 binary-only semantic equivalence；
- 已证明真实 decompiler-output transfer；
- 已证明 LLM/decompiler 生成质量优于 SOTA。

## Phase 6 Objective

Phase 6 应验证真实或 decompiler-like output 分布中是否也存在 Phase 5B 类型的 hard candidates：

1. source-known oracle 保持不变；
2. candidate 来源改为 decompiler-output / LLM-decompiler-output / decompiler-like transforms；
3. 仍要求 fixture-only vs v3 baseline matrix；
4. 成功 gate 继续要求 `v3 - best non-oracle baseline >= 0.05`；
5. 若候选生成无法产生 fixture-passing wrong，应记录为 candidate-distribution limitation。

## Suggested Prompt

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
不要进入其他项目目录，不要使用 subagent。
使用 superpowers:brainstorming / writing-plans 设计 Phase 6，但执行时只用 superpowers:executing-plans。

基于 Phase 5B 已通过的 hard-candidate full run，设计 Phase 6 decompiler-output / decompiler-like transfer。
要求保持 full-scale 思路，不回退到 smoke：
- source-known oracle；
- 至少 30 real-project functions；
- 目标 100+ compile-pass candidates；
- 至少 20 paired functions；
- 报 fixture-only、static/binary motifs、v1/v2/v3；
- 成功 gate：v3 AUC >= 0.85，且 v3 - best non-oracle baseline >= 0.05；
- 如果需要 GPU，只用 GPU 2。
```
