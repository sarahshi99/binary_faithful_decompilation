# Decompilation Faithfulness Phase 7 SOTA Alignment Plan

## 当前状态

Phase 6 可以收口，结论是：

- Phase 6 proxy：完成。
- Phase 6R Ghidra real decompiler output：完成并通过。
- Phase 6R cross-toolchain：完成并通过。
- radare2：完成 importability smoke，但不是 compile-ready C 主证据。

因此 Phase 6 的合理状态是：

`complete-for-ghidra-cross-toolchain`

但外部论文 SOTA 状态仍然是：

`not-ready-for-external-paper-sota-claim`

## 为什么还不能直接说超过相关文献 SOTA

当前 Phase 6R 的强结论是：

> 在 Phase 5 的 `38` 个 source-known 函数、`O0/O2`、真实 Ghidra 输出和两个 GCC toolchain 下，Dynamic Trace v3 都明显超过项目内 fixture/static baseline。

这不是同一件事：

> 在公开 decompilation benchmark 上超过 LLM4Decompile / DecompileBench / CodeFuse-DeBench 等相关工作。

差距主要有三点：

1. 没有公开 benchmark row。
2. 没有明确复现或代理相关文献 baseline。
3. 没有第二个 compile-ready decompiler 主证据；radare2 当前只是 pseudo-C importability。

## Phase 7 的目标

Phase 7 不是继续堆 Phase 6 实验，而是做 SOTA alignment：

1. 找到或导入公开 / SOTA-aligned benchmark。
2. 把项目的 source-known semantic drift auditing 指标和相关文献常用指标对齐。
3. 建立外部 baseline matrix。
4. 决定是否可以宣称 external-paper SOTA；如果不行，明确收窄 claim。

## 我们真正要 PK 的对象

本项目不是直接和 LLM4Decompile 竞争“谁生成的 C 更好”。更准确的 PK 方向是：

> 在 source-known bounded setting 下，Dynamic Trace v3 是否比 fixture-only、static similarity、LLM judge、轻量 fuzz/symbolic proxy 更能发现 decompiler/LLM-generated candidates 中的 localized semantic drift。

因此主表应包含：

- fixture-only / re-execution-only baseline；
- static structured baseline；
- Dynamic Trace v1/v2/v3 ablation；
- LLM judge baseline，如果可用；
- symbolic/fuzzing-style baseline，如果依赖可用；
- Ghidra / second decompiler candidate source；
- public benchmark split。

## 推荐执行顺序

### Phase 7A：Public Benchmark Feasibility

先检查本地有没有可用公开 benchmark 或能否导入：

- Decompile-Eval / HumanEval-style；
- ExeBench-style；
- DecompileBench；
- Decompile-Bench；
- CodeFuse-DeBench。

不下载、不联网，除非用户明确批准。

成功 gate：

- 至少一个公开或 SOTA-aligned benchmark 可用；
- 至少 `50` 个函数可导入或可表示为 source-known functions；
- 至少 `30` 个函数能在本地 harness 编译/运行；
- 至少 `2` 个 optimization/toolchain 变体可行。

### Phase 7B：External Baseline Matrix

把相关文献指标变成可执行 baseline matrix：

- 哪些能直接复现；
- 哪些只能做代理；
- 哪些需要 GPU/API；
- 哪些需要额外依赖。

### Phase 7C：Public Benchmark Main Evaluation

只有 Phase 7A/7B 通过后才跑。

成功 gate：

- 至少 `100` 个 compile-pass candidates；
- 至少 `30` 个 paired faithful/wrong functions；
- v3 超过 fixture-only 和 static structured；
- v3 over best non-oracle baseline delta `>= 0.05`；
- behavior-preserving false-positive rate `<= 10%`；
- 有 risk-family breakdown 和 failure taxonomy。

### Phase 7D：Second Compile-ready Decompiler

优先评估 RetDec / rev.ng / angr AIL / Binary Ninja / Hex-Rays 是否可用。

如果没有第二个 compile-ready decompiler，论文可以继续写 Ghidra-based source-known auditor，但不能把 cross-decompiler robustness 说得太满。

### Phase 7E：GPU 0/1 LLM Baseline

GPU 0/1 只用于：

- LLM candidate generation；
- LLM repair/refinement baseline；
- local LLM judge baseline。

在 public benchmark preflight 通过前，不启动 GPU。

## 当前建议

下一步执行：

1. Phase 7A public benchmark feasibility preflight。
2. Phase 7B related-work baseline matrix。
3. 再根据 preflight 结果决定是否下载 benchmark、是否安装第二 decompiler、是否启动 GPU 0/1。

## 对 CCF-A 的影响

如果 Phase 7 通过：

- 论文可以从“项目内 positive evidence”升级到“public/SOTA-aligned benchmark evidence”。
- 可以更有力地回应 full-vs-smoke 和 SOTA improvement 两个审稿风险。

如果 Phase 7 不通过：

- 论文仍然可以保留 source-known bounded semantic auditor 方向；
- 但不能宣称 external-paper SOTA；
- 需要把贡献收窄为 Ghidra/source-known semantic drift auditing，并把 public benchmark 作为 limitation / future work。

## 下一条建议 prompt

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他目录，不要使用 subagent。
按 docs/superpowers/plans/2026-07-01-binary-faithful-phase7-sota-alignment.md 执行。

先执行 Task 1-3：
- 冻结 Phase 6 状态；
- 做 Phase 7 public benchmark feasibility preflight；
- 写 related-work baseline matrix。

不要下载 benchmark，不要安装新依赖，不要启动 GPU，除非 preflight 后我明确批准。
```
