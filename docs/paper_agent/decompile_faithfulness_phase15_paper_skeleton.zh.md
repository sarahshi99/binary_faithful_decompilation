# Phase 15 论文骨架说明

## 这版骨架解决什么问题

旧的 Phase 4 paper outline 还是以 `boundary-preserving Dynamic Trace v3` 为中心。Phase 8-19 后，证据已经发生了变化：

- Phase 8 证明 v3 richer scoring components 不能作为独立 SOTA margin。
- Phase 10 证明 input-budget proxy 对 Ghidra 太乐观。
- Phase 11/12 证明 `fixture_neighbor_first` 输入排序能把低预算路线修成统一方法。
- Phase 14 给出 case-level bootstrap CI 和 miss taxonomy。
- Phase 17 证明粗暴 `operator_char_class_first` 会伤害 public/char-boundary 覆盖，不能作为最终策略。
- Phase 18/19 证明 `source_literal_char_interleave` 能在不增加平均输入数的情况下修复 Ghidra 剩余 miss，并刷新 bootstrap/runtime/risk 证据。

因此 Phase 15 新骨架把论文主线改成：

`source-literal-aware fixture-neighbor low-budget dynamic re-execution`

而不是：

`Dynamic Trace v3 scoring formula`

## 当前论文标题建议

`Source-Literal-Aware Dynamic Re-Execution for Source-Known Decompilation Faithfulness Auditing`

这个标题有三个好处：

1. `Source-Literal-Aware` 点出最终方法，而不是泛泛说 dynamic trace。
2. `Source-Known` 主动收窄，避免被 binary-only verifier 预期击穿。
3. `Auditing` 说明是验证/评估方向，不是 decompiler generation leaderboard。

## 当前论文 claim

可以 claim：

- 在 source-known、recompilable、bounded-input 设定下，低预算 targeted dynamic re-execution 能发现 fixture/static 容易漏掉的 localized semantic drift。
- 统一 `source_literal_char_interleave` 策略在三条 full 主证据上通过 budget-8 gate。
- 三条主证据的 AUC 和 wrong-detection 都达到 `1.0000`，case-level bootstrap CI95 都为 `[1.0000, 1.0000]`。
- Ghidra `char_boundary` / `multi_arg` 风险族已从 Phase 16 的 partial gate 修到 `1.0000`。

不能 claim：

- 通用 binary-only verifier。
- 超过 LLM4Decompile / DecompileBench 等 generation SOTA。
- v3 scoring components 相比 strong generated-input mismatch 有额外 SOTA margin。
- 跨 decompiler 泛化已经充分。

## 论文结构

新骨架文件：

`docs/paper_agent/decompile_faithfulness_phase15_paper_skeleton.md`

结构如下：

1. Abstract
2. Introduction
3. Problem Definition
4. Method
5. Experimental Setup
6. Main Results
7. Ablations and Negative Results
8. Related Work Positioning
9. Threats to Validity
10. Conclusion
11. Appendix checklist

## 还缺什么才能变成投稿稿

优先级最高：

1. 把 skeleton 扩写成 6-8 页正文。
2. 把 Phase 19 wall-clock runtime 表写入论文主表/附表。
3. 补 method figure 和 motivating example figure。
4. 把 Phase 19 per-risk-family breakdown 写成 ablation/risk 表。
5. 写完整 related work，不要只列名字。
6. 明确处理第二 compile-ready decompiler 缺口：要么补实验，要么写进 scope/limitation。

## 现在距离 CCF-A 的写作状态

当前是：

`final-method-table-ready + runtime/risk-ready + paper-skeleton-ready`

还不是：

`submission-ready`

粗略估计：

- 写成完整 arXiv/workshop draft：已经可以开始，约 `1` 周内可成稿。
- 冲 CCF-A：还需要 `2-4` 周补 figures、related work、LaTeX 主文、review polish。
- 如果必须补第二 compile-ready decompiler：取决于工具可用性，可能额外 `1-4` 周。
