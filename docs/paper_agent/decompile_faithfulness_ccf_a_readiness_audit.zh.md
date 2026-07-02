# Decompilation Faithfulness CCF-A Readiness Audit

## 总体判定

当前项目还没有达到 CCF-A 投稿完成态，但已经从“探索性实验”推进到“有明确论文种子的 strong positive state”。

更准确的判断：

- 已具备一个可发表方向的核心：`source-known / bounded-input / localized semantic bug auditing`。
- 已经证明原始 static/binary motif 路线不可靠，这是重要负结果。
- Dynamic Trace v3 在 controlled、manual stress、LLM-generated candidates、新 source-known 小函数池上都给出正向结果。
- 但还缺 CCF-A 级别需要的外部基线、真实工具/项目覆盖、系统消融、复杂度/鲁棒性分析、正式论文叙事和图表。

当前成熟度估计：`5.5 / 10`。

可以进入 Phase 4 paper synthesis，但还不应认为已经可以投 CCF-A。

## 按“四步速通 CCF-A”自查

### 1. 精准定义问题

当前状态：`部分达标，约 7 / 10`。

已经有的证据：

- Phase 1B 证明 naive global binary feature distance 会被 behavior-preserving rewrites 击穿，AUC `0.5000`。
- Phase 1I/1J 证明继续修 lightweight static binary motifs 不稳，LOCO 分别为 `0.6719` / `0.6823`。
- Phase 2 证明 fixture-only 不够：`count_bits8` 出现 fixture-passing 但 trace-mismatching 的 generated candidate。
- Phase 3 证明新函数池上仍有 fixture-passing trace mismatch：GPU generated combined analysis 中出现 `safe_div_round0` 的 non-oracle 例子。

当前问题定义可以写成：

> Existing lightweight binary-similarity or fixture-only validation signals are insufficient for localized semantic faithfulness auditing of decompiler/LLM-generated C candidates: they either punish behavior-preserving rewrites or miss boundary-localized semantic drift. We study a source-known, recompilable, bounded-input setting where the original source can act as a trace oracle and ask whether generated dynamic traces can expose semantic drift beyond fixtures.

还缺的东西：

- 需要系统化 literature matrix，说明前人主要依赖哪些信号：static similarity、compiler equivalence、test suites、symbolic execution、LLM judge、decompiler benchmark 等。
- 需要更直接的 motivating examples，最好来自真实 decompiler/LLM 输出，而不仅是本项目生成 candidates。
- 需要把“不是 general equivalence”提前讲清楚，避免审稿人认为问题被过度缩小。

### 2. 启发性解法

当前状态：`有核心洞察，但理论表达还不够，约 6.5 / 10`。

已有方法核心：

- Dynamic Trace v2：从 fixture domain 推断 bounded input region，避免在 `gcd_positive` 这类 domain-sensitive case 上生成不合语义域的 trace inputs。
- Dynamic Trace v3：保留 generic boundary probes，即使这些 boundary probes 与 fixture args 重合，也不从 primary generated trace 中删除。
- 主分数不使用 `fixture_mismatch_rate`，因此不是直接复读 fixture label。

可以提炼成论文假设：

> Faithfulness bugs in small decompiled functions are often localized around semantic boundaries: sign, zero, loop termination, bit width, range endpoints, and argument order. A boundary-preserving generated trace policy is a low-complexity way to expose these bugs while avoiding the brittleness of static binary motifs and the overfitting of fixture-only validation.

还缺的东西：

- 形式化定义：
  - source function `f`;
  - candidate `g`;
  - bounded domain `D`;
  - fixture set `F`;
  - generated trace set `T`;
  - protected boundary subset `B`;
  - score `S(f,g,T)`。
- 需要写清 v2 -> v3 的机制改进为什么不是 heuristic patch，而是 “boundary preservation under fixture exclusion”。
- 需要和 symbolic execution / fuzzing / test generation 的关系讲清楚：本方法不是替代所有 verifier，而是 lightweight semantic auditing signal。

### 3. 无懈可击的实验支撑

当前状态：`内部证据强，外部广度不足，约 5 / 10`。

已有强证据：

| Evidence | Result |
|---|---:|
| Phase 1K-v2 LOCO AUC | `0.9531` |
| Phase 1L leakage verdict | `no-label-or-output-leakage-found` |
| Phase 2 generated candidates | `100` generations, `63` compile-pass |
| Phase 2 v2 AUC | `0.9623` |
| Phase 2 v3 AUC | `1.0000` |
| Phase 3 source pool | `12` functions, `3289` subsets |
| Phase 3 CPU manual stress AUC | `1.0000` |
| Phase 3 GPU generated candidates | `47` generated, `28` compile-pass |
| Phase 3 GPU combined AUC | `1.0000` |
| Fixture collapse in final main experiments | `False` |

主要短板：

- 数据规模仍小：8 built-in + 12 Phase3 source-known functions。
- Phase 3 GPU generated paired cases 只有 `5` 个。
- 尚未覆盖真实 C 项目函数抽取。
- 尚未接入真实 decompiler outputs。
- 尚未与近期 representative baselines 系统对比。
- 尚未做 compute cost / runtime overhead / trace input count scaling。
- 尚未做 robustness：
  - 不同 compiler opt level；
  - 不同 trace budget；
  - 不同 boundary policy；
  - 不同 LLM generation prompt/model；
  - noisy / equivalent rewrites；
  - timeout / nontermination handling。

CCF-A 级别实验还需要：

1. Baseline matrix。
2. Larger source-known benchmark。
3. Real-project source-known transfer。
4. Decompiler-output or decompiler-like candidates。
5. Full ablation table。
6. Failure taxonomy。
7. Complexity and runtime analysis。

### 4. 写作与视觉呈现

当前状态：`还没开始论文级打磨，约 3 / 10`。

已有材料：

- Phase 1-3 实验文档完整。
- 负结果链条清楚。
- 正向主表已经能抽出来。
- non-oracle examples 已经有：
  - Phase 2 `count_bits8`；
  - Phase 3 `safe_div_round0`；
  - manual stress 中多个 fixture-passing wrong examples。

还缺：

- 论文标题、abstract、intro narrative。
- 第一页 motivating figure。
- 方法总图。
- 主结果总表。
- 失败案例图。
- Appendix 结构。
- Threats to validity。
- Reproducibility checklist。

## 是否达标

当前不达 CCF-A 完成态。

但已经达到了：

- 可以写完整 workshop / arXiv paper draft；
- 可以进入 CCF-A paper shaping；
- 可以立刻启动 Phase 4 synthesis；
- 可以设计 Phase 5/6 作为补强实验，而不是继续盲目探索。

最危险的地方不是当前方法没有信号，而是 claim 过大。只要写成 “general binary-only decompilation verifier”，就会被审稿人击穿。当前最稳的 claim 是：

> Source-known, recompilable, bounded-input localized semantic bug auditing for decompiler/LLM-generated C candidates.

## 推荐新阶段定义

### Phase 4：Paper Synthesis And Claim Shaping

目标：把 Phase 1-3 整理成论文骨架。

任务：

1. 写 problem statement。
2. 写 method formalization。
3. 整理主结果表。
4. 整理 negative result table。
5. 整理 non-oracle examples。
6. 写 claim boundary。
7. 写 Phase 5/6 实验需求。

成功 gate：

- 形成 6-8 页 paper skeleton。
- 明确 3 个 contribution bullets。
- 每个 contribution 都能对应实验表。

### Phase 5：Real-Project Source-Known Transfer

目标：从小型真实 C 项目中抽取 source-known 小函数，保持 oracle 可执行。

范围：

- 不是 arbitrary binary-only。
- 不是大型项目全函数。
- 先选 2-3 个小项目，每个项目 10-30 个函数候选。
- 只选 integer / bounded / deterministic / no I/O / no heap 的函数。

成功 gate：

- 至少 `30-50` 个真实项目 source-known functions。
- 至少 `100-200` 个 generated or decompiler-like candidates。
- 至少 `20+` paired cases。
- AUC 明显高于 baselines。
- fixture collapse 为 false。

### Phase 6：Decompiler-Output / Binary-Oriented Feasibility

目标：检查方法能否进入更接近真实 decompilation 的 setting。

谨慎范围：

- 先 source-known + decompiler output。
- 原始 source 仍作为 oracle。
- 不直接声称 binary-only semantic equivalence。

候选工具/来源：

- real decompiler outputs；
- LLM decompiler-style generated outputs；
- different compiler optimization levels；
- behavior-preserving rewrites。

成功 gate：

- Dynamic Trace v3 对 real/decompiler-like candidates 仍有 signal。
- 对 behavior-preserving rewrites false positive 可控。
- 对 localized bugs recall 明显优于 fixture-only baseline。

## 三个月执行建议

### 第 1-2 周：Phase 4

- 写完整 paper skeleton。
- 做 literature matrix。
- 生成主表、负结果表、方法图。
- 明确最终 claim。

### 第 3-6 周：Phase 5

- 选择真实小 C 项目。
- 写 extraction/filter pipeline。
- 跑 source-known real-project transfer。
- 做 baseline 对比和消融。

### 第 7-9 周：Phase 6

- 接入 decompiler-output 或 decompiler-like candidates。
- 做 robustness / optimization-level / trace-budget 实验。
- 写 failure taxonomy。

### 第 10-12 周：Paper

- 写 full draft。
- 补 appendix。
- 做图表 polish。
- 内部 review。
- 最后只补必要实验，不再发散。

## 下一步立即行动

现在应该启动 Phase 4，不应该继续直接堆 GPU。

建议下一条具体任务：

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他项目目录，不使用 subagent。

基于 Phase 1-3 的所有结果，启动 Phase 4 paper synthesis。
请写：
1. paper problem statement；
2. method formalization；
3. contribution bullets；
4. main result table；
5. negative result table；
6. Phase 5/6 experiment plan。

目标是判断如何把当前项目推进到 CCF-A 论文标准。
```
