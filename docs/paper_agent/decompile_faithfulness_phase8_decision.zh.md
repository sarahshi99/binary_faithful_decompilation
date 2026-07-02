# Decompilation Faithfulness Phase 8 Decision

## 结论

Phase 8 的结果是一个重要的边界修正：

- Phase 7C2 static-hard 的 `+0.0782` legacy margin 是稳定的，95% bootstrap CI 为 `[+0.0394, +0.1276]`。
- 但是当 baseline 升级为 generated-input fuzzing-style re-execution，也就是直接使用 `trace_mismatch_rate` 或 `any_trace_mismatch` 时，它和 Dynamic Trace v3 一样达到 `1.0000` AUC。
- 因此 Phase 8 verdict 是 `strong-baseline-erases-v3-extra-margin`。

这意味着当前证据支持：

> 动态重执行信号比 fixture-only / static-structured auditor 更适合 localized semantic drift auditing。

但当前证据不支持：

> Dynamic Trace v3 的 richer components，例如 absolute error、sign mismatch、zero mismatch、boundary mismatch，相比简单 generated-input mismatch baseline 已经带来额外 SOTA margin。

## 为什么这不是坏消息

这不是方法失败，而是 claim 边界变清楚了。

Phase 7 之前的问题是：我们只知道 v3 比 fixture/static 好，但不知道它是否只是因为“多跑了一批 generated inputs”。Phase 8 说明：

1. 和 fixture/static 比，动态重执行路线是稳定正向的。
2. 但在当前数据集上，简单 mismatch-rate 已经足够强，v3 的 extra scoring components 没有被当前 benchmark 区分出来。

这会影响论文叙事：

- 主贡献应写成 dynamic re-execution based faithfulness auditing，而不是复杂 v3 scoring formula。
- v3 可以保留为工程实现或 robustness variant，但不要把它包装成独立理论突破。
- CCF-A 的下一步不是继续堆同类样本，而是构造能区分 simple fuzzing mismatch 和 richer trace semantics 的 hard benchmark。

## 关键结果

| Dataset | Legacy Delta | Legacy CI95 | Strong Delta | Verdict |
|---|---:|---:|---:|---|
| Phase 7C2 static-hard public | `+0.0782` | `[+0.0394, +0.1276]` | `0.0000` | legacy stable, strong erased |
| Phase 7E LLM public full+top-up | `+0.0259` | `[0.0000, +0.0714]` | `0.0000` | weak legacy, strong erased |
| Phase 6R Ghidra full | `+0.1793` | `[+0.1087, +0.2619]` | `0.0000` | legacy stable, strong erased |
| Phase 6R Ghidra gcc9 full | `+0.1576` | `[+0.0870, +0.2381]` | `0.0000` | legacy stable, strong erased |

## 对 CCF-A 目标的影响

当前还不达标外部 SOTA。

可以作为论文雏形的部分：

1. 问题定义：source-known localized semantic drift auditing。
2. 核心机制：generated-input dynamic re-execution catches errors that fixture/static miss。
3. 实验证据：Ghidra full、cross-toolchain、CodeFuse public static-hard full-scale rows。

仍缺 CCF-A 级别支撑：

1. 能区分 simple mismatch baseline 和 richer semantic trace scoring 的 hard benchmark。
2. 第二个 compile-ready decompiler，或更强的 public decompiler-output benchmark。
3. 对 fuzzing-style baseline 的成本、公平性、输入预算敏感性分析。
4. 外部相关工作的直接指标对齐，而不是只和 in-project baselines 比。

## 下一阶段建议

Phase 9 应该变成 `input-budget and hard-semantic benchmark`，目标是回答：

> 如果 fuzzing-style re-execution 也很强，那么我们的研究贡献到底在哪里？

推荐三条路线，优先顺序如下：

1. Input-budget curve。
   - 比较 fixture-only、random 4/8/16/32/64/128 inputs、boundary-only、current hard generated inputs、v3 total。
   - 如果 v3 只在 128 inputs 时和 fuzzing 持平，那么贡献可能是 input generation，不是 score formula。
   - 如果少量 targeted boundary inputs 能接近 v3，则论文可以转向低成本 targeted execution auditor。
2. Hard semantic families。
   - 专门构造 mismatch-rate 不够、但 richer trace semantics 有用的 cases，例如 sign-only drift、magnitude drift、zero-boundary drift、termination/timeout drift。
   - 成功 gate：v3 beats fuzzing mismatch by `>= 0.03` on at least one hard family，并且 overall 不明显下降。
3. Cost-normalized comparison。
   - 比较每种 baseline 的 input count、compile/run time、false positive rate。
   - 如果 v3 不超过 fuzzing AUC，但能以更少 inputs 或更低 FP 达成同等效果，也仍可能是论文贡献。

## 建议 prompt

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他项目目录，不要使用 subagent。
使用 superpowers:brainstorming / writing-plans / executing-plans / test-driven-development。

基于 Phase 8 结果继续 Phase 9。
目标：不要再只和 fixture/static 比，而是设计 input-budget curve 和 hard-semantic benchmark，检验 simple fuzzing mismatch baseline 为什么这么强，以及 Dynamic Trace v3 是否仍有可发表的额外价值。

要求：
- CPU-only，除非后续明确需要 LLM judge。
- 先写 Phase 9 plan/spec。
- TDD 实现 input-budget baseline analyzer。
- 输入：Phase 7C2 static-hard、Phase 7E LLM public、Phase 6R Ghidra full records。
- 第一阶段只做已有 records 上的 cost/input-budget proxy；如果必须重跑 trace inputs，再单独写执行计划。
- 成功 gate：发现至少一个 defensible claim：
  1. v3 在 hard semantic family 上超过 fuzzing mismatch >= 0.03；
  2. 或 targeted dynamic execution 用更少 inputs 达到 fuzzing/v3 的效果；
  3. 或证明当前方法只能 claim dynamic re-execution, not v3 scoring, 并据此重写论文路线。
```
