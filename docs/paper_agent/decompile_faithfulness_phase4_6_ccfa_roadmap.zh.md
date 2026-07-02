# Decompilation Faithfulness Phase 4/5/6 CCF-A Roadmap

## Superpowers 使用说明

本轮重新按 Superpowers 流程审查了 Phase 4/5/6：

- 读取本机 Superpowers 插件缓存中的 `brainstorming`、`using-git-worktrees`、`writing-plans` 文档；
- 按 brainstorming 做路线比较；
- 按 using-git-worktrees 检查当前是否需要隔离工作区；
- 按 writing-plans 写成可执行计划；
- 遵守本项目覆盖规则：不使用 subagent，只允许后续用 `superpowers:executing-plans` 串行执行。

当前 Codex 会话没有把 `superpowers:*` 暴露为一等 skills，但插件文件已经在本机缓存中可读。因此本轮是按本地插件文档执行，而不是调用 subagent 或外部工具。

## 当前总判断

Phase 1-3 没有证明一个 general binary-only decompilation verifier。它们证明的是一个更窄但更稳的方向：

> source-known、可重编译、bounded-input、小函数 localized semantic bug auditing。

这个方向已经有 paper seed，但还没达到 CCF-A 完成态。

最重要的结论是：

- static / binary motif 主线不是主贡献，更多是负结果；
- Dynamic Trace v3 是当前主方法；
- Phase 2/3 的正结果支持继续扩展，但不能直接跳到 binary-only 或大规模真实项目 claim；
- 下一步必须先做 Phase 4 paper synthesis，否则 Phase 5/6 很容易变成无边界实验。

## 为什么可以进入 Phase 4

可以进入 Phase 4，不是因为所有原始设想都成功了，而是因为项目已经收敛出可防守命题。

已通过的关键 gate：

| 阶段 | 结果 | 意义 |
|---|---:|---|
| Phase 1K-v2 | LOCO AUC `0.9531`，`fixture_collapse=False` | dynamic trace 主方法成立 |
| Phase 1L | `no-label-or-output-leakage-found` | 排除明显泄漏风险 |
| Phase 2-v3 | AUC `1.0000`，8/8 case AUC `1.0000` | generated candidates 上保持信号 |
| Phase 3 CPU | 12 functions，AUC `1.0000` | 新 source-known 小函数池上通过 |
| Phase 3 GPU | 47 generated candidates，AUC `1.0000` | 新函数池的 generated candidate smoke 通过 |

没完成的 CCF-A 要求：

- 真实小 C 项目 transfer；
- decompiler-output 或 decompiler-like candidates；
- 系统 baseline matrix；
- 论文级方法形式化；
- failure taxonomy；
- runtime / robustness / ablation 完整表。

## Phase 4：Paper Synthesis And Claim Shaping

Phase 4 的目标不是跑更多实验，而是把已有证据变成论文骨架。

必须产出：

- 可防守 problem statement；
- 方法形式化；
- 3 个 contribution bullets；
- 主结果表；
- 负结果表；
- non-oracle motivating examples；
- literature / baseline matrix；
- Phase 5/6 的精确 gate。

Phase 4 成功后，应该能回答：

1. 论文到底解决什么问题？
2. 为什么不是 general verifier？
3. Dynamic Trace v3 的科学假设是什么？
4. 当前证据支持哪三个贡献？
5. 还缺哪些实验才能冲 CCF-A？

## Phase 5：Real-Project Source-Known Transfer

Phase 5 是真正补外部有效性的阶段。

它不是 binary-only。它仍然保留 source-known oracle，只是函数来源从项目内 curated cases 扩展到小型真实 C 项目。

建议 gate：

- 至少 `30` 个真实项目 source-known functions；
- 至少 `2` 个 source projects；
- 至少 `100` 个 compile-pass candidates；
- 至少 `20` 个有 faithful/wrong pairs 的 functions；
- Dynamic Trace v3 AUC `>= 0.85`；
- v3 比最佳 non-oracle baseline 高至少 `0.05`；
- `fixture_collapse=False`；
- 没有未解释的 risk-family AUC `< 0.60`。

如果 Phase 5 失败，先不要立刻否定方法。要区分：

- 函数选择失败；
- oracle/domain 设计失败；
- candidate 生成失败；
- 某个风险族需要新 boundary policy；
- v3 主方法真的不迁移。

## Phase 6：Decompiler-Output / Binary-Oriented Feasibility

Phase 6 才开始靠近真实 decompilation，但仍然不能直接改成 binary-only。

正确边界是：

- 原始 source 仍作为 oracle；
- candidate 可以来自真实 decompiler output 或 decompiler-like LLM generation；
- 检查 behavior-preserving rewrites 的 false positive；
- 做 failure taxonomy；
- 不安装 heavyweight dependency，除非另写 dependency plan。

建议 gate：

- 至少 `20` 个 source-known functions 有 decompiler-output 或 decompiler-like candidates；
- 至少 `50` 个 compile-pass candidates；
- 至少 `10` 个 paired functions；
- v3 超过 fixture-only 和 static-only baseline；
- behavior-preserving rewrite false-positive rate `<= 10%`，或者每个 false positive 都有明确 trace-domain 原因。

如果本地没有 Ghidra / RetDec / radare2 等工具，Phase 6 可以先拆成：

- Phase 6A：dependency / tool feasibility；
- Phase 6B：candidate evaluation。

## Worktree 决策

按 `using-git-worktrees` 检查后，当前仓库是普通 checkout：

- `.git` 等于 common git dir；
- 当前分支是 `phase1a-audit`；
- 不是 submodule；
- 不是 linked worktree。

本轮只是新增设计和计划文档，而且当前工作区包含大量 Phase 1-3 未提交实验结果。为了保留上下文，本轮不新建 worktree。

以后如果开始大规模实现 Phase 5/6 脚本，建议先把当前结果提交或保存 checkpoint，然后再考虑 worktree。

## 下一步执行顺序

1. 先执行 Phase 4 paper synthesis。
2. Phase 4 gate 过了以后，再写并执行 Phase 5 real-project transfer。
3. Phase 5 有明确正结果或明确 blocker 后，再进入 Phase 6。
4. 每一步都用 `superpowers:executing-plans` 串行执行，不使用 subagent。

## 下一条建议 prompt

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他项目目录，不要使用 subagent。
按 docs/superpowers/plans/2026-06-30-binary-faithful-phase4-6-ccfa-roadmap.md 执行，只使用 superpowers:executing-plans。

先执行 Phase 4，不要启动 Phase 5/6 实验。
目标是生成：
- docs/paper_agent/decompile_faithfulness_phase4_evidence_index.json
- docs/paper_agent/decompile_faithfulness_phase4_paper_synthesis.zh.md
- docs/paper_agent/decompile_faithfulness_phase4_paper_outline.md

执行后做 json 校验和 git diff --check。
```
