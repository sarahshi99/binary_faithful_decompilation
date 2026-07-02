# Decompilation Faithfulness Phase 4 Paper Synthesis

## 当前可防守 claim

当前最稳的论文命题不是 general binary-only decompilation verifier，而是：

> Boundary-preserving generated dynamic traces provide a lightweight, source-known semantic auditing signal for localized bugs in decompiler/LLM-generated C candidates.

必须保留的限定词：

- `source-known`：原始 source 仍作为 oracle。
- `recompilable`：原函数和候选函数都需要可编译或可执行。
- `bounded-input`：只在明确输入域内做 trace auditing。
- `localized semantic bug auditing`：目标是发现局部语义漂移，不是证明全程序等价。

这个 claim 目前能被 Phase 1-3 支撑；如果写成 binary-only semantic equivalence 或者 SOTA decompiler generation，就会过度声称。

## 为什么不是 general verifier

Phase 1-3 的实验设置仍然依赖原始 source oracle。Dynamic Trace v3 的核心动作是比较 source function `f` 和 candidate `g` 在 generated trace inputs 上的行为差异。如果没有 source oracle，本方法当前没有独立判断语义正确性的能力。

此外，当前函数池主要是小 C 函数：

- Phase 1K：8 cases / 56 candidates。
- Phase 2：100 generations，63 compile-pass candidates。
- Phase 3：12 source-known functions，CPU manual stress 28 candidates。
- Phase 3 GPU：47 generated candidates，28 compile-pass，5 paired cases。

这些结果足以说明方法有信号，但不足以作为 CCF-A 主实验的 full-scale external validity。Phase 3 GPU combined analysis 应该被称为 smoke/top-up evidence，而不是 full benchmark。

## 负结果链条

| 阶段 | 结果 | 论文意义 |
|---|---:|---|
| Phase 1B | naive global binary distance AUC `0.5000` | static/binary distance 会惩罚 behavior-preserving rewrites，不能直接当 faithfulness verifier |
| Phase 1I | static component LOCO AUC `0.6719` | 继续拼 static motifs 提升有限 |
| Phase 1J | structural binding LOCO AUC `0.6823` | 加 CFG/return binding 后仍不够稳 |

负结果不是失败材料，而是论文动机：轻量 static/binary motifs 不足以表达 localized semantic drift。

## 正结果链条

| 阶段 | 结果 | 论文意义 |
|---|---:|---|
| Phase 1K-v2 | LOCO AUC `0.9531`，`fixture_collapse=False` | domain-aware trace 成为主方法 |
| Phase 1L | `no-label-or-output-leakage-found` | 排除明显泄漏和 fixture-only collapse |
| Phase 2-v3 | AUC `1.0000`，8/8 case AUC `1.0000` | LLM-generated candidate distribution 上保持信号 |
| Phase 3 source selection | 12 eligible functions，3289 subsets | 避免一次性小函数选择的脆弱性 |
| Phase 3 CPU | 12 cases AUC `1.0000`，fixture-passing wrong count `4` | 新 source-known 小函数池上仍能抓 fixture 漏掉的 bug |
| Phase 3 GPU | 47 generated candidates，AUC `1.0000` | generated-candidate smoke 正向，但规模不足 |

## 方法核心假设

形式化对象：

- 原始 source function：`f`
- 候选函数：`g`
- bounded domain：`D`
- fixture set：`F`
- generated trace set：`T`
- protected boundary probes：`B`
- trace score：`S(f, g, T)`

核心假设：

> 小函数 decompilation / LLM candidate 的 faithfulness bugs 经常集中在 semantic boundary：zero、sign、bit width、range endpoint、loop termination、argument order、division/modulo corner cases。保留这些 boundary probes 的 generated dynamic trace，比 static motifs 或 fixture-only 更容易暴露 localized semantic drift。

v2 到 v3 的机制变化要写成原则，而不是补丁：

- v2：从 fixture argument values 推断输入域，避免 out-of-domain false positive。
- v3：在排除 fixture overfitting 的同时保留通用 boundary probes，避免 zero/sign blind spot。

## 论文贡献草案

1. 识别并实证展示 lightweight static/binary motifs 和 fixture-only validation 在 localized semantic faithfulness auditing 中的局限。
2. 提出 boundary-preserving generated dynamic trace policy，用 source-known oracle 在 bounded input domain 内检测局部语义漂移。
3. 给出从 curated cases 到 generated candidates、再到 source-known transfer readiness 的 staged empirical audit，并明确 real-project/decompiler-output 的后续 gate。

注意：第三个贡献目前只能写成 staged audit 和 readiness，不能写成 full real-project transfer 已完成。

## 主结果表草案

| Experiment | Scale | Main Metric | Result | Claim Role |
|---|---:|---:|---:|---|
| Static binary distance | curated | AUC | `0.5000` | negative motivation |
| Static component combination | curated | LOCO AUC | `0.6719` | negative motivation |
| Structural binding | curated | LOCO AUC | `0.6823` | negative motivation |
| Dynamic Trace v2 | 8 cases / 56 candidates | LOCO AUC | `0.9531` | method discovery |
| Phase 2 generated candidates | 100 generations / 63 compile-pass | AUC | `0.9623` then v3 `1.0000` | generated distribution |
| Phase 3 source selection | 12 functions / 3289 subsets | eligible subsets | pass | selection robustness |
| Phase 3 CPU audit | 12 functions / 28 candidates | AUC | `1.0000` | source-known transfer readiness |
| Phase 3 GPU smoke/top-up | 47 candidates / 28 compile-pass | AUC | `1.0000` | positive smoke only |

这张表不能作为最终 CCF-A 主表。最终主表必须加入 Phase 5 full real-project transfer 和 Phase 6 decompiler-output feasibility。

## 失败案例和 non-oracle examples

已有 paper-facing examples：

1. `count_bits8`：生成候选通过 fixture，但统计 16 bits 而不是 8 bits。Dynamic trace 在更宽输入上发现 mismatch。
2. `safe_div_round0`：Phase 3 GPU candidate 出现 fixture-passing trace mismatch。
3. CPU manual stress 中的 `sat_add8`、`parity8`、`mod3_sum_digits`、`safe_div_round0` 都有 fixture-passing wrong examples。

这些例子适合用于第一页动机图：左边展示 fixture-only pass，右边展示 boundary trace 暴露 drift。

## Full-vs-Smoke 风险

用户提出的第一个问题是关键审稿风险：小函数池和 smoke 不足以支撑 CCF-A 主实验。

当前回答必须诚实：

- Phase 1-3 是 feasibility 和 method-discovery evidence。
- Phase 2 的 100 generations 可以称为 full gate，因为它覆盖当时定义的 8 个 curated cases。
- Phase 3 GPU 不能称为 full，它只有 47 generated candidates、5 paired cases，只能叫 smoke/top-up。
- Phase 3 source selection 的 3289 subsets 缓解了“一次性选错函数”的风险，但没有解决真实项目规模问题。

因此 Phase 5 的 gate 必须升级为 full-scale：

- 至少 `30-50` 个真实项目 source-known functions；
- 至少 `100-200` 个 compile-pass candidates；
- 至少 `20+` paired functions；
- 覆盖多个 source projects；
- 每个 risk family 都报告 case-level AUC；
- 不能只报 overall。

## SOTA 进步风险

用户提出的第二个问题也成立：现在还不能说有足够 SOTA 进步。

更准确地说，本项目不是在和 LLM4Decompile、DecompileBench、Hex-Rays/Ghidra 这类系统直接竞争“生成更好 C 代码”。本项目目前的位置是：

> semantic auditing signal for source-known decompiler/LLM-generated candidates。

因此 SOTA 对比应该分成两层：

1. Decompilation system context：说明近期工作重视 re-compilability、re-executability、semantic fidelity、real-world benchmarks。
2. Auditing-signal baselines：证明 Dynamic Trace v3 比 fixture-only、static similarity、v1/v2 trace、LLM judge 或 symbolic/fuzzing-style checks 更适合抓 localized semantic drift。

Phase 4 初步 literature anchors：

- LLM4Decompile / Decompile-Eval：强调 recompilability 和 re-executability 是 LLM decompilation 的常用指标。
- ISSTA 2024 decompiler evaluation：强调真实 decompiler 语义准确性并不理想，semantic evaluation 是核心问题。
- DecompileBench / Decompile-Bench：强调 real-world binary-source function pairs 和 semantic fidelity / functionality correctness。
- Semantic equivalence checking of decompiled binaries：说明 binary/decompiler equivalence checking 是相关但更重的方向。

已核对的来源：

- LLM4Decompile / Decompile-Eval: `https://arxiv.org/abs/2403.05286`
- ISSTA 2024, Evaluating the Effectiveness of Decompilers: `https://2024.issta.org/details/issta-2024-papers/40/Evaluating-the-Effectiveness-of-Decompilers`
- DecompileBench, ACL Findings 2025: `https://aclanthology.org/2025.findings-acl.1194/`
- Decompile-Bench, NeurIPS 2025 Datasets and Benchmarks: `https://proceedings.neurips.cc/paper_files/paper/2025/hash/079cf13ae174c31f148207d94d213bdc-Abstract-Datasets_and_Benchmarks_Track.html`

要达到 CCF-A，不能只说 AUC 高。需要证明：

- 我们解决的是一个现有 benchmark/metric 没有充分解决的 audit gap；
- 在 source-known bounded setting 内，v3 对 fixture-passing wrong candidates 有更高 recall；
- 成本低于 heavyweight symbolic equivalence；
- false positive 低于 static similarity；
- 在 real-project transfer 和 decompiler-output candidates 上仍有效。

## Baseline Matrix 草案

| Baseline family | 作用 | Phase 4 判断 |
|---|---|---|
| fixture-only / re-execution-only | 当前领域常用功能正确性信号 | 必须比较，v3 必须证明能抓 fixture-passing wrong |
| static / binary similarity | 传统轻量信号 | Phase 1 已有负结果，但 Phase 5/6 要继续作为 baseline |
| v1 mixed-domain trace | 动态 trace 消融 | 展示 domain awareness 的必要性 |
| v2 domain-aware trace | 动态 trace 消融 | 展示 boundary preservation 的必要性 |
| LLM judge | 如果使用 LLM 生成/评估候选，需要控制 judge hallucination | Phase 5/6 可选，但论文最好说明不用它做主 oracle |
| symbolic/concolic/fuzzing-style | 更重但相关的 semantic checking | 依赖允许时做 sanity baseline，否则作为 limitation |
| decompiler benchmark metrics | 连接 SOTA 语境 | Phase 6 必须纳入 |

## Phase 5/6 必须补的证据

Phase 5：

- real-project source-known transfer；
- 不是 smoke，而是 full gate；
- 至少 30 eligible functions；
- 至少 100 compile-pass candidates；
- 至少 20 paired functions；
- v3 比 best non-oracle baseline 高至少 `0.05` AUC；
- `fixture_collapse=False`；
- 报告 risk-family breakdown。

Phase 6：

- decompiler-output 或 decompiler-like candidates；
- 原始 source 仍作 oracle；
- behavior-preserving rewrites false-positive control；
- 多优化级别；
- failure taxonomy；
- 工具不可用时先写 dependency/tool feasibility。

## Phase 4 Gate

Phase 4 本身通过的条件：

- 形成 paper skeleton；
- claim boundary 明确；
- 3 个 contribution bullets 每个都能对应证据；
- Full-vs-smoke 风险写进主文档；
- SOTA/baseline gap 写进主文档；
- Phase 5/6 gate 能回答“需要跑多大才有说服力”和“如何证明有 SOTA 级贡献”。

当前 Phase 4 结论：

- 可以继续写 paper skeleton。
- 不能直接投 CCF-A。
- 下一步必须把 Phase 5 full-scale real-project transfer 作为主补强实验。
