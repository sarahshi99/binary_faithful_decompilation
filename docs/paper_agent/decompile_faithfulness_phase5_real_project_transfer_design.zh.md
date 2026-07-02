# Decompilation Faithfulness Phase 5 Real-Project Source-Known Transfer

## 为什么 Phase 5 不是 binary-only

Phase 5 仍然保留 source-known oracle：原始 C source 是标准答案，candidate 只是被审计对象。

这样做不是退缩，而是为了把问题定义稳住。当前方法需要比较 source function 和 candidate function 在 generated trace inputs 上的行为。如果没有 source oracle，就会变成另一个问题：binary-only semantic equivalence checking。那个方向更重，不能由 Phase 1-3 的证据直接支撑。

## 为什么不能再是 smoke

用户提出的担心是正确的：小函数池和 smoke 结果不能支撑 CCF-A 主实验。

Phase 5 必须是 full-scale gate：

- 至少 `30` 个真实项目 source-known functions；
- 目标范围 `30-50` 个 functions；
- 至少 `2` 个 source projects；
- 至少 `100` 个 compile-pass candidates；
- 目标范围 `100-200` 个 compile-pass candidates；
- 至少 `20` 个有 faithful/wrong pairs 的 functions；
- 每个主要 risk family 尽量至少 `3` 个 paired functions。

如果达不到这个规模，只能写成 pilot，不允许写成主实验。

## 项目和函数选择标准

第一轮只选小型真实 C 项目里的可控函数。

函数必须满足：

- deterministic；
- integer-only 参数和返回值；
- bounded input domain 可明确写出；
- no I/O；
- no heap allocation；
- no external mutable state；
- no callback；
- bounded domain 内无 undefined behavior；
- 原始 source 可编译为 oracle；
- fixture 覆盖普通行为和边界行为。

排除函数也要记录原因，因为这会成为论文威胁分析的一部分。

## Candidate 来源

候选来源分层：

1. behavior-preserving rewrites：用于 false-positive control。
2. manual stress candidates：覆盖已知 bug family。
3. LLM-generated `strict_rewrite` / `strict_bug` candidates：贴近 Phase 2/3 的 candidate distribution。
4. decompiler-like candidates：如果已有，不安装新工具也可纳入；否则留给 Phase 6。

结果表必须按 candidate source 分开报，不能只报 overall。

## Baseline Matrix

必须比较：

| Baseline | 用途 |
|---|---|
| fixture-only mismatch | 检查 v3 是否真的抓住 fixture 漏掉的 bug |
| static-only min-slot / structural score | 连接 Phase 1 负结果 |
| Dynamic Trace v1 mixed-domain | 证明 domain awareness 必要 |
| Dynamic Trace v2 domain-aware | 证明 boundary preservation 必要 |
| Dynamic Trace v3 boundary-preserving | 主方法 |

可选比较：

- LLM judge：只作为辅助，不作为 oracle。
- symbolic/concolic：只有依赖已存在或另写 dependency plan 才做。
- fuzzing-style random input baseline：需要固定 seed 和同等 input budget。

## SOTA 进步应如何定义

Phase 5 不应该声称“生成质量超过 SOTA decompiler”。更合理的 SOTA 贡献是：

> 在 source-known bounded auditing setting 内，Dynamic Trace v3 比已有轻量评估信号更能发现 localized semantic drift，尤其是 fixture-passing wrong candidates。

近期相关工作表明，decompilation 领域已经越来越重视 recompilability、re-executability、semantic fidelity、runtime validation 和 real-world functions。因此我们必须把 Phase 5 做成真实项目 full-scale transfer，而不是继续只在 curated cases 上报高 AUC。

已核对的来源：

- LLM4Decompile / Decompile-Eval: `https://arxiv.org/abs/2403.05286`
- ISSTA 2024, Evaluating the Effectiveness of Decompilers: `https://2024.issta.org/details/issta-2024-papers/40/Evaluating-the-Effectiveness-of-Decompilers`
- DecompileBench, ACL Findings 2025: `https://aclanthology.org/2025.findings-acl.1194/`
- Decompile-Bench, NeurIPS 2025 Datasets and Benchmarks: `https://proceedings.neurips.cc/paper_files/paper/2025/hash/079cf13ae174c31f148207d94d213bdc-Abstract-Datasets_and_Benchmarks_Track.html`

## 成功 Gate

Phase 5 pass 条件：

- Dynamic Trace v3 pairwise AUC `>= 0.85`；
- v3 比最佳 non-oracle baseline 高至少 `0.05` AUC；
- `fixture_collapse=False`；
- 至少 `5` 个 fixture-passing wrong candidates，或者解释为什么候选来源没有产生这类样本；
- 没有未解释的 risk-family AUC `< 0.60`；
- behavior-preserving rewrites false-positive rate `<= 10%`，或者每个 false positive 都有 trace-domain 解释。

## 失败归因规则

失败前必须先归因：

- source extraction failure；
- oracle compile failure；
- fixture design failure；
- bounded-domain design failure；
- candidate generation failure；
- paired data 不足；
- baseline 强于 v3；
- v3 trace-domain miss；
- v3 对 behavior-preserving rewrite 误报。

只有数据规模足够、归因排除实验设置问题、且 v3 仍输给 baseline，才算方法层面的负结果。

## 预计产物

- `docs/paper_agent/decompile_faithfulness_phase5_project_candidates.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json`
- `docs/paper_agent/decompile_faithfulness_phase5_preflight.json`
- `docs/paper_agent/decompile_faithfulness_phase5_candidate_manifest.json`
- `docs/paper_agent/decompile_faithfulness_phase5_result_analysis.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase5_gate_decision.zh.md`
