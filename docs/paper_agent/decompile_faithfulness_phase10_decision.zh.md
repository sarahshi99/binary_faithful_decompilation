# Decompilation Faithfulness Phase 10 Decision

## Verdict

`low-budget-proxy-overestimated`

## 指标怎么读

Phase 10 评估的是“少量 generated inputs 真实重跑时，能不能尽早发现候选反编译代码不忠实”。这里最重要的三个指标是：

- `Mismatch AUC`：排序指标。对同一个 case，错误候选的 mismatch 分数是否高于 faithful 候选。`1.0` 是完美排序，`0.5` 接近随机。它回答“能不能把错的排在更危险的位置”，但不等价于“每个错都被抓住”。
- `Wrong detection rate`：召回指标。所有 `plausible_wrong` 候选里，有多少在当前预算内至少出现一次输出不一致。它更接近“实际抓错率”。
- `Avg actual inputs`：真实成本。因为有些函数可生成输入少于请求预算，所以 budget-8 不一定真的平均跑 8 个输入。这个数越低，说明同样效果越便宜。

`V3 AUC` 在 Phase 10 中基本等于 `Mismatch AUC`，因为低预算前缀下核心信号仍是“是否输出不一致”。这也说明：Phase 8 以后，论文主张应从“复杂 v3 打败强 fuzz baseline”修正为“低预算 generated-input dynamic re-execution 很强且可解释”。

## 结果好还是不好

结论是“主线好，泛化边界还不够好”。

好的部分：

- `phase7c2_static_hard_public` 在 budget-8 上 `Mismatch AUC = 0.9956`，`Wrong detection rate = 0.9845`，两个门槛都过了。这是当前最强的正向结果：公开 static-hard 数据里，平均 `6.61` 个实际输入就能抓住绝大多数错误。
- `phase7e_llm_public_full_topup` 在 budget-8 上 `Mismatch AUC = 0.9828`，`Wrong detection rate = 0.9722`，也很强。它不是主 gate，但说明 LLM-public 候选上同样有低预算证据。

不够好的部分：

- `phase6r_ghidra_full` 在 budget-8 上 `Mismatch AUC = 0.9565`，`Wrong detection rate = 0.9189`，没有达到 `AUC >= 0.98` 和 `detection >= 0.95`。
- `phase6r_ghidra_full` 到 budget-16 时，`Wrong detection rate = 0.9730` 已经过线，但 `Mismatch AUC = 0.9783` 仍略低于 `0.98`。这说明 Ghidra 并不是完全失败，而是 budget-8 的输入顺序/覆盖不够稳。

所以，Phase 10 不是坏结果，但它推翻了 Phase 9 里“budget-8 到处都够”的乐观 proxy。现在可以防守的说法是：低预算动态重执行在 public static-hard 和 LLM-public 上非常强；对真实 Ghidra 输出，需要更好的输入排序或自适应预算，不能直接宣称 universal budget-8。

## Decision

继续走低预算 dynamic re-execution 方向，但把论文 claim 收窄为：

> We show that generated-input dynamic re-execution can expose semantic infidelity missed by fixture/static checks at low cost; budget-8 is sufficient for the public static-hard and LLM-public settings, while real-decompiler outputs require input-ordering hardening or an adaptive budget.

Phase 10 漏检并不分散：Ghidra budget-8 只漏掉 `6` 个 wrong，来自 `3` 个 case，全部是 `fixture_ifchain_00`；budget-16 只剩 `ta_leetcode_get_point_key` 的 `2` 个 wrong。这是一个可以继续修的明确问题。

## Next Step

进入 Phase 11：Ghidra input-ordering hardening。

目标不是增加新候选或使用 GPU，而是在同一批真实 Ghidra records 上比较多种 deterministic input ordering：

- 原始 `phase5b_hard_probe` 顺序。
- fixture-neighborhood-first。
- boundary/domain-first。
- coverage-proxy mixed order。

成功 gate：

- 首选：`phase6r_ghidra_full` budget-8 `Mismatch AUC >= 0.98` 且 `Wrong detection rate >= 0.95`。
- 次选：budget-16 `Mismatch AUC >= 0.98` 且 `Wrong detection rate >= 0.97`，形成 `adaptive budget <= 16` 的防守性 claim。
