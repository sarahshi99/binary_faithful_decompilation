# Decompilation Faithfulness Phase 9 Decision

## 结论

Phase 9 verdict：`low-budget-dynamic-execution-claim`。

Phase 8 发现 simple generated-input mismatch baseline 已经抹平 v3 extra scoring margin。Phase 9 进一步说明：这不是因为必须跑满 `128` 个 inputs 才有效；在当前 full records 上，预算 `k=8` 的 generated-input dynamic execution 已经非常强。

## 指标怎么读

这几个指标回答的是不同问题：

- `AUC`：排序指标。它问的是“wrong candidate 的分数是否高于同一 case 里的 faithful candidate”。`1.0000` 表示在可配对样本中全部排对。它不等于“每次运行都必抓错”。
- `wrong detection mean`：预算为 `k` 个 inputs 时，一个 wrong candidate 至少被一个 input 抓到 mismatch 的平均概率。越接近 `1` 越好。
- `wrong detection p10`：所有 wrong candidates 中较难的底部 10% 的抓错概率。这个比 mean 更能说明长尾风险。
- `wrong detection min`：最难 wrong candidate 的抓错概率。它通常会比 mean 低很多，用来提醒低预算下是否还有极难样本。
- `Budget-k`：只允许使用 `k` 个 generated inputs。Phase 9 里这是根据 full run 的 `trace_mismatch_count / trace_input_count` 做 without-replacement proxy，还不是 actual rerun。

因此，Phase 9 的好消息不是简单的 “AUC=1 很漂亮”，而是：

> 在 `k=8` 时，多个 full rows 的 wrong detection mean 和 p10 已经非常高，说明低预算动态执行这条路线值得转成真实实验。

同时，Phase 9 的风险是：

> 这还是 proxy，不是实际截断 inputs 后重新执行；所以必须做 Phase 10 actual low-budget rerun。

关键结果：

- Phase 7C2 static-hard public：Budget-8 AUC `1.0000`，wrong detection mean `0.9935`，p10 `1.0000`，min `0.6404`。
- Phase 7E LLM public full+top-up：Budget-8 AUC `1.0000`，wrong detection mean `1.0000`，p10 `1.0000`。
- Phase 6R Ghidra full：Budget-8 AUC `1.0000`，wrong detection mean `0.9800`，p10 `0.9952`。
- Phase 6R Ghidra gcc9 full：Budget-8 AUC `1.0000`，wrong detection mean `0.9800`，p10 `0.9952`。

同时，hard-family scan 没有发现当前数据中 `v3_trace_total` 相比 `fuzzing_mismatch_rate` 有 `>= 0.03` 的 family-level margin。

## 论文路线修正

当前最防守的贡献不再是：

> 复杂 Dynamic Trace v3 scoring formula 超过所有 baseline。

而应改成：

> 对 source-known localized semantic drift auditing，少量 generated inputs 的 dynamic re-execution 就能稳定击穿 fixture/static auditor；在 CodeFuse public static-hard、LLM-generated public candidates、Ghidra real-decompiler output 上，预算约 `8` 个 generated inputs 已经接近饱和。

这条路线更简单，也更容易解释：

1. 前人/常见 baseline 依赖 fixture 或 static structure，容易被 fixture-overfit 或 static-hard local semantic drift 绕过。
2. 我们发现真正关键的不是复杂模型，而是低预算、targeted generated-input re-execution。
3. 这给 decompiler faithfulness auditing 一个更实用的 tradeoff：少量动态执行换来明显更可靠的语义错误发现。

## 对 CCF-A 的意义

正向：

- 有 full-scale public rows，不是 smoke。
- 有真实 Ghidra decompiler-output rows，不只是 synthetic variants。
- 有 bootstrap CI 和 strong baseline 自查，避免过度 claim。
- 低预算 claim 比 v3 scoring claim 更清晰，也更可能被审稿人接受。

仍缺：

1. 输入预算需要真实重跑确认。Phase 9 当前是基于已有 `trace_mismatch_count / trace_input_count` 的 without-replacement proxy，不是实际重采样执行。
2. 需要解释 generated inputs 如何产生、为什么公平、是否依赖 source-known oracle。
3. 需要和 fuzzing/symbolic/re-execution 相关工作更直接对齐。
4. 还缺第二个 compile-ready decompiler，或者至少一个更强 public decompiler-output benchmark。

## 下一步

Phase 10 应该做 `actual low-budget rerun`，把 Phase 9 的 proxy 变成真实实验：

1. 对 Phase 7C2、Phase 7E、Phase 6R 选定 budgets：`1, 2, 4, 8, 16`。
2. 固定 deterministic generated-input ordering 或多个 random seeds。
3. 实际只用前 `k` 个 inputs 重新计算 mismatch score，而不是从 full trace count 推概率。
4. 报告 AUC、wrong detection recall、runtime/compile overhead。
5. 成功 gate：
   - Budget-8 在 Phase 7C2 和 Phase 6R 上 AUC `>= 0.98`。
   - Budget-8 wrong detection mean `>= 0.95`。
   - 与 full 128-input result 的差距可解释。

如果 Phase 10 通过，论文主贡献可以改为：

> Low-budget generated-input dynamic re-execution for source-known decompilation faithfulness auditing。

如果 Phase 10 不通过，说明 Phase 9 proxy 过乐观，需要回到 hard-semantic benchmark 或 input generation 方法本身。

## 建议 prompt

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他项目目录，不要使用 subagent。
使用 superpowers:brainstorming / writing-plans / executing-plans / test-driven-development。

基于 Phase 9 结果继续 Phase 10。
目标：把 input-budget proxy 变成 actual low-budget rerun。

要求：
- CPU-only，除非明确需要 LLM judge。
- 不重新生成 LLM candidates。
- 对 Phase 7C2 static-hard、Phase 6R Ghidra full、Phase 7E LLM public full+top-up 做 budget rerun。
- budgets: 1, 2, 4, 8, 16。
- 优先复用已有 candidate source 和 trace input generation 逻辑。
- 输出 AUC、wrong detection recall、runtime proxy、与 full 128-input 的差距。
- 成功 gate：Budget-8 在 Phase 7C2 和 Phase 6R 上 AUC >= 0.98，wrong detection mean >= 0.95。
```
