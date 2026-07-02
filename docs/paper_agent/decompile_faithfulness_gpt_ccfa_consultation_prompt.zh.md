# 给 GPT 的 CCF-A 咨询 Prompt

## 使用方式

建议先把“主 prompt”完整发给 GPT。等它输出第一轮审查后，再按下面的 follow-up prompts 逐个追问。目标不是让 GPT 夸结果，而是让它像强审稿人和论文合作者一样，把当前工作补到 CCF-A 可投状态。

## 主 Prompt

```text
我在做一个 binary/decompilation faithfulness 方向的研究项目，目标是冲 CCF-A 论文。请你扮演三个角色联合审查：

1. 顶会系统安全/程序分析审稿人：严格挑 claim、实验、baseline、scope 的漏洞。
2. 论文导师：帮我把问题定义、核心洞察、方法叙事、贡献边界写成可投稿论文。
3. 实验设计合作者：给出最小但足够强的补实验清单，避免无意义堆实验。

项目当前最稳的 scope 是：

source-known localized semantic drift auditing

不要把它理解成：

- general binary-only decompilation verifier
- decompiler generation SOTA
- arbitrary real-project decompilation correctness proof
- cross-decompiler robustness 已充分证明

当前最终方法是：

source_literal_char_interleave

方法思想：

对 source-known C 函数的 decompiler/decompiler-like candidate，不只用原始 fixture，也不只用静态 binary/code motif，而是做低预算 dynamic re-execution。具体地：

1. 保留 fixture-neighbor probes，用于暴露 fixture-overfit 和边界附近语义漂移。
2. 对 char 参数，从原始 source 中提取真实出现过的 char literals。
3. 将 source-literal char probes 与 fixture-neighbor probes 交错，而不是使用通用 operator-first char list。
4. 每个 candidate 使用 budget 8 左右的输入，目标是低成本暴露 localized semantic drift。

主结果：

Budget = 8。

| Dataset | Candidates | Paired cases | Fixture AUC | Static AUC | Final AUC | Wrong detection | Avg inputs | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Public static-hard | 478 | 50 | 0.9211 | 0.6806 | 1.0000 | 1.0000 | 6.64 | 0 |
| LLM-public | 136 | 24 | 0.9741 | 0.7759 | 1.0000 | 1.0000 | 6.69 | 0 |
| Ghidra | 166 | 26 | 0.5000 | 0.8207 | 1.0000 | 1.0000 | 6.97 | 0 |

Stability/runtime：

- 三套 full 数据的 case-level bootstrap AUC CI95 都是 [1.0000, 1.0000]。
- Detection CI95 都是 [1.0000, 1.0000]。
- Missed wrong 都是 0。
- Runtime:
  - Public static-hard: 478 candidates, total 85.60s, p95 0.0923s/candidate, 37.05 input evals/sec。
  - LLM-public: 136 candidates, total 7.94s, p95 0.0874s/candidate, 114.65 input evals/sec。
  - Ghidra: 166 candidates, total 11.21s, p95 0.1031s/candidate, 103.25 input evals/sec。

Ablation：

| Method | Public static-hard | LLM-public | Ghidra |
|---|---:|---:|---:|
| Fixture-neighbor | 1.0000 / 1.0000 / 0 | 1.0000 / 1.0000 / 0 | 0.9891 / 0.9730 / 2 |
| Operator-char-first | 0.9889 / 0.9612 / 10 | 0.9914 / 0.9722 / 1 | 0.9565 / 0.9459 / 4 |
| Source-literal interleave | 1.0000 / 1.0000 / 0 | 1.0000 / 1.0000 / 0 | 1.0000 / 1.0000 / 0 |

关键历史：

- 早期 static/binary motif route 效果不稳，支持“纯静态 motif 不足以做 faithfulness auditing”的问题动机。
- Dynamic trace route 后来成为主线。
- Phase 17 的 operator-char-first 是负结果：修了 Ghidra multi_arg，但伤害 public/LLM 和 char-boundary。
- Phase 18 的 source-literal interleave 修复 Ghidra char_boundary/multi_arg，且三套 full 不退化。
- Phase 19/20 已有 final readiness、runtime/risk、paper tables。

我现在担心的 CCF-A 缺口：

1. 外部 SOTA 定位不够硬：不能声称 decompiler generation SOTA，那到底和谁 PK，贡献怎么写？
2. 真实工具覆盖偏 Ghidra：第二个 compile-ready decompiler 证据弱。应该补哪个工具，还是把 Ghidra-centered scope 写硬？
3. 数据集代表性：虽然是 full，但 reviewers 会质疑小函数池、source-known、candidate construction 是否偏向我们方法。
4. 论文叙事：如何把 source-literal-aware fixture-neighbor low-budget dynamic re-execution 讲成机制洞察，而不是 heuristic patch？
5. CCF-A gate：到底还缺哪些必要实验、图表、对比、威胁分析和写作材料？

请你输出：

1. 一句话论文 thesis：最适合 CCF-A 的核心立论。
2. 最合适的论文题目候选 5 个。
3. Contribution 列表：哪些能写，哪些不能写。
4. Related work / SOTA matrix：至少列出应对比的研究类别、代表工作类型、我们和它们的关系、不能比较的原因。
5. Reviewer attack matrix：强审稿人最可能攻击的 10 个点，以及每个点的补救方式。
6. 必做补实验清单：按“必须做 / 强烈建议 / 可选”排序，每个实验说明目的、预期结果、失败时如何修改 claim。
7. 最小 CCF-A 成稿计划：按一周粒度安排，目标是尽快形成可投 draft。
8. 论文结构：Abstract、Introduction、Motivation、Method、Evaluation、Threats、Related Work 每节应写什么。
9. 是否应该补第二 decompiler：给出明确 yes/no/conditional，并说明推荐工具和失败备选。
10. 最终 verdict：当前离 CCF-A 是 6/10、7/10、8/10 还是 9/10？为什么？

要求：

- 不要泛泛鼓励，要像审稿人一样严格。
- 如果你认为结果不够 CCF-A，请明确缺口和最近可行路线。
- 不要建议无限扩大 scope。
- 不要把当前工作包装成 general verifier。
- 所有建议都要服务于 CCF-A 论文可接受性。
```

## Follow-up Prompt 1：确定论文 Claim

```text
基于上一轮审查，请你只做 claim engineering。

请输出：

1. 最强但不过度的 paper claim。
2. 更保守的 paper claim。
3. 更激进但可能被拒的 paper claim。
4. 推荐使用哪个版本，为什么。
5. Abstract 第一版，控制在 180-220 词。
6. Introduction 的前 4 段，每段说明要证明什么。
7. 明确列出论文中禁止出现或必须弱化的表述。
```

## Follow-up Prompt 2：SOTA 和 Related Work

```text
请你专门帮我解决 SOTA/related work 问题。

我的方法不是 decompiler generation，不是 binary-only verifier，而是 source-known localized semantic drift auditing。

请输出：

1. 应该比较的 baseline 类别。
2. 不应该硬比的类别，以及为什么。
3. related work taxonomy。
4. 每个 taxonomy 下应该怎么写“我们的区别”。
5. 如果 reviewer 问“你没有超过 decompiler generation SOTA”，应该如何回应。
6. 如果 reviewer 问“这只是 fuzzing/symbolic execution”，应该如何回应。
7. 如果 reviewer 问“source-known 设置太弱”，应该如何回应。
```

## Follow-up Prompt 3：补实验设计

```text
请你只做补实验设计，目标是把当前工作从 8/10 推到 CCF-A 更稳。

当前主结果已经是三套 full：

- Public static-hard
- LLM-public
- Ghidra

最终方法在三套 full 上 AUC/detection 都是 1.0，missed wrong = 0。

请设计最小补实验集合：

1. 必做实验，最多 3 个。
2. 强烈建议实验，最多 5 个。
3. 可选实验，最多 5 个。

每个实验必须包含：

- 要回答的 reviewer question。
- 具体实验 protocol。
- 成功 gate。
- 失败后如何修改 claim。
- 是否需要 GPU。
- 预计写进论文的表/图位置。

特别关注：

- 第二 decompiler 是否值得补。
- 数据集代表性。
- source-known 是否合理。
- budget sensitivity。
- failure case / negative result 如何转化为论文资产。
```

## Follow-up Prompt 4：强审稿人预演

```text
请你扮演 CCF-A 强审稿人，对这篇论文做拒稿式审查。

请输出：

1. Reject review 版本，至少 8 条主要批评。
2. 每条批评对应的 rebuttal 方案。
3. 哪些批评必须通过补实验解决，哪些可以通过写作解决。
4. 如果只能再做 2 个实验，应该做哪两个。
5. 如果只能再写 3 张图/表，应该是哪三张。
6. 最终你是否会 borderline accept？需要满足什么条件？
```

## Follow-up Prompt 5：论文写作任务拆解

```text
现在请你把这篇论文拆成可执行写作任务。

输出：

1. Paper outline，精确到 subsection。
2. 每个 subsection 的核心论点。
3. 每个 subsection 需要引用哪些实验表/图。
4. 每个 subsection 的风险点。
5. 先写哪 5 个部分，为什么。
6. 两周内完成 submission-quality draft 的日程。
```

## 给 GPT 的材料优先级

如果 GPT 需要更多材料，优先粘贴这些文件内容：

1. `README.md`
2. `docs/paper_agent/decompile_faithfulness_current_status_and_ccfa_gap.zh.md`
3. `docs/paper_agent/decompile_faithfulness_phase20_paper_tables.md`
4. `docs/paper_agent/decompile_faithfulness_phase18_source_literal_char_policy.zh.md`
5. `docs/paper_agent/decompile_faithfulness_phase19_final_method_readiness.zh.md`
6. `docs/paper_agent/decompile_faithfulness_phase19_final_runtime_risk.zh.md`
7. `docs/paper_agent/decompile_faithfulness_phase15_paper_skeleton.md`

## 我们要从 GPT 那里拿到的最终产物

最理想的 GPT 输出不是“建议继续努力”，而是下面这些可执行产物：

1. 论文最终 claim。
2. Introduction 逻辑链。
3. Related work taxonomy。
4. Reviewer attack/rebuttal matrix。
5. 只剩 2-3 个必须补的实验。
6. 论文图表清单。
7. CCF-A submission checklist。
8. 如果不够 CCF-A，明确降级路线：比如 Security workshop、ASE/TOSEM、ICSE-SEIP、或 artifact paper。
