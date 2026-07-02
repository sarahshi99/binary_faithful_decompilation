# Decompilation Faithfulness Phase 1 总览与下一步

## 一句话结论

Phase 1 已经从一个“recompiled binary feature distance 是否有信号”的小型 sanity check，推进成了 8 个 source-known cases / 56 个 candidates 的连续 kill-gate。当前结论是：

- 静态 binary feature 确实能提供一些诊断信号。
- raw global distance 已经被 realistic rewrites 击穿。
- multi-opt slot concentration 一度有效，但扩到更难 cases 后只剩 borderline。
- order-sensitive、component-combination、CFG/return-binding 三轮修补都没有通过 leave-one-case-out gate。
- Phase 1K 三路线 scout 已完成：dynamic trace 明显强于 static motifs，LOCO AUC 达到 `0.8750`，且没有退化成 fixture oracle；但 `gcd_positive=0.5000` 仍未解决。
- Phase 1K-v2 已完成：domain-aware dynamic trace 把 LOCO AUC 提升到 `0.9531`，`gcd_positive` 从 `0.5000` 提升到 `1.0000`，且 `fixture_collapse=False`。
- Phase 1L 已完成：ablation / leakage audit 显示 v2 不是 fixture-only oracle，也没有 label / candidate-output leakage；v2 AUC `0.9531`，static-only `min_slot` 只有 `0.8021`。
- symbolic/concolic route 当前缺少 `z3/angr/claripy/capstone/unicorn`，需要单独依赖计划，不能作为本轮主证据。
- 因此现在仍不应直接进入 real-project transfer；最终决策更新为 `continue-to-phase2-planning-after-phase1l`，把问题收窄为 source-known / localized semantic bug auditing，并先设计 Phase 2 candidate generation，而不是直接跑 GPU。

## Phase 1 每个实验在做什么

| Phase | 核心问题 | 做法 | 结果 | 用处 / 结论 |
|---|---|---|---|---|
| 1A initial | 在玩具 controlled mutations 上，binary distance 能不能把 faithful 排在 wrong 前面？ | 3 个 source-known C 函数；原始函数为 faithful，规则 mutation 为 wrong；用 objdump/nm features 做全局距离排序。 | 初始 `pairwise_auc=0.875`，`top1=0.6667`，发现 operand-order blind spot。 | 说明方向有信号，但特征太粗，`return a-b` vs `return b-a` 这类错误会漏掉。 |
| 1A.1 | 修补 operand-order blind spot 后，controlled gate 是否通过？ | 加 `instruction_signature_l1`，让 opcode+operand 归一化签名参与距离。 | `pairwise_auc=1.0000`，`top1=1.0000`，`verdict=continue`。 | 证明在玩具 mutation 上，operand-sensitive binary features 可用；但这还不是 decompiler 现实场景。 |
| 1B | realistic faithful rewrites 会不会击穿 raw global distance？ | 加 manual faithful rewrites 和 manual hard negatives；同样用全局 binary distance 排序。 | `pairwise_auc=0.5000`，`top1=1.0000`，`verdict=kill-core-method`。 | raw global distance 失败：行为保持 rewrite 也会产生很大 binary drift，不能直接当“不忠实”信号。 |
| 1C | binary feature delta 能不能定位到错误 source slot？ | controlled mutations 上，把 feature components 映射到 `branch_predicate`、`constant`、`return_value` 等 slot votes。 | `hit_at_1=1.0000`，`hit_at_2=1.0000`，`hit_at_3=1.0000`。 | controlled localization 有效，提示“局部错误浓度”比全局距离更有希望。 |
| 1D | slot-local concentration 能不能区分 realistic rewrites 和 localized semantic bugs？ | 在 Phase 1B candidates 上，不看总距离，改看 slot votes 是否集中。 | O0：`pairwise_slot_auc=1.0000`；O2：`0.6667`。 | O0 很强，但优化级别一变就弱，说明必须做 optimization-aware calibration。 |
| 1E | multi-opt 是否能稳定 slot-local signal？ | 扩到 21 candidates，扫 `O0/O1/O2/O3`，用 min/mean/max slot concentration 聚合。 | single-opt slot AUC `0.9028/0.7361/0.6944/0.7500`；multi-opt min `0.8472`。 | multi-opt conservative score 有效：取多优化级别中的最小 suspiciousness，可减少单一编译设置的偶然漂移。 |
| 1F | 新增 cases 后 signal 是否还稳？ | 加 `max3`、`sum_to_n`，合并 5 cases / 35 candidates。 | new cases alone `0.7917`；combined multi-opt min `0.8250`。 | 仍过 continue gate，但安全边际下降；需要继续扩大难例。 |
| 1G | 更难的 branch/return/bit/loop cases 会怎样？ | 加 `signum`、`is_power_of_two`、`gcd_positive`，合并 8 cases / 56 candidates。 | new cases alone `0.6389`；combined multi-opt min `0.7552`，borderline。 | 暴露核心问题：当前 representation 会漏掉符号方向、返回常量绑定、循环语义等错误。 |
| 1H | order-sensitive diagnostics 能不能解释 blind spot？ | 加 `instruction_bigram_l1`、`branch_return_immediate_pair_l1` 作为诊断组件。 | `signum/manual_signum_reversed_signs` 的旧 components 全 0，新 components 能抓到 `4.0/4.0`；但 primary score 不变。 | 新组件能解释问题，但不能直接作为主分数，因为 faithful rewrites 也会改变 instruction order。 |
| 1I | 简单组合旧 score + 新 diagnostics，能不能稳健提升？ | 在 8 cases 上做 formula search，并用 leave-one-case-out 防止 in-sample 过拟合。 | best in-sample `0.7604`，LOCO `0.6719`，`verdict=do-not-transfer-yet`。 | 小公式组合失败；不能靠手调权重解决 representation mismatch。 |
| 1J | CFG/return-binding 结构特征能不能修复 1G/1H 盲点？ | 抽取 basic blocks、CFG edge motifs、branch->return binding、compare->branch->return binding，再做 LOCO。 | best in-sample 仍是 `min_slot=0.7552`；LOCO `0.6823`；hard cases：`signum=0.5000`、`gcd_positive=0.5833`、`max3=0.6667`、`sum_to_n=0.5833`。 | 结构化静态 motifs 仍失败，应记录为负结果。当前 lightweight static binary motif 路线不适合作为主方法继续加码。 |
| 1K | dynamic trace、symbolic/concolic feasibility、narrowed framing 三路线 scout。 | Route A 运行 generated dynamic trace；Route B 探测 symbolic 依赖；Route C 写 claim matrix。 | Route A LOCO `0.8750`，fixture collapse `False`，verdict `borderline-dynamic-trace`；Route B `needs-dependency-plan`；Route C `narrow-localized-bug-paper`。 | dynamic trace 是目前唯一有明显增量的信号，但 `gcd_positive=0.5000` 说明仍不能做通用 verifier；下一步应收窄论文边界并做 Dynamic Trace v2。 |
| 1K-v2 | fixture-domain-aware generated inputs 能不能修复 `gcd_positive`，同时不退化成 fixture oracle？ | 从 fixture 参数值推断输入域；对 `gcd_positive` 只生成 strictly-positive primary inputs；复用 v1 trace score 和 LOCO。 | LOCO `0.9531`；`gcd_positive=1.0000`；`signum=0.7500`；`max3=1.0000`；`sum_to_n=1.0000`；fixture collapse `False`；verdict `pass-dynamic-trace-v2-localized-bug`。 | v2 通过 gate，说明 source-known localized semantic bug auditing 是可继续写的方法路线；但还需要 Phase 1L ablation / leakage audit 后再进入更真实 candidate generation。 |
| 1L | v2 的提升是不是 fixture oracle、label leakage 或 static-only signal？ | 只读比较 v1 mixed-domain、v2 domain-aware、fixture-only oracle、static-only `min_slot`；记录 leakage audit。 | v2 AUC `0.9531`，v1 `0.8906`，fixture-only `1.0000`，static-only `0.8021`；v2 != fixture-only；leakage verdict `no-label-or-output-leakage-found`。 | v2 可信度通过消融验证。下一步可以设计 Phase 2 candidate generation，但仍需先写计划，不直接跑 GPU。 |

## 这些实验之间的区别

1. 1A/1A.1 是“全局 binary distance 是否有基本信号”。
   - faithful candidate 通常就是原始函数。
   - wrong candidate 是规则 mutation。
   - 它回答的是最小 sanity check，不代表现实 decompilation。

2. 1B 是“现实 rewrite drift 会不会让全局距离失效”。
   - 加了 manual faithful rewrites。
   - 结果说明全局距离不能直接用。

3. 1C/1D 是从“全局距离”转向“slot-localized suspiciousness”。
   - 不再问 drift 大不大，而是问 drift 是否集中在某类语义 slot 上。
   - 这是 Phase 1 里第一次真正接近论文方法的部分。

4. 1E/1F/1G 是扩大覆盖面和优化级别。
   - 1E 证明 multi-opt conservative aggregation 有用。
   - 1F 说明加新例子后还可用。
   - 1G 说明继续加难例后开始不稳，尤其是 branch/path/return/loop 相关错误。

5. 1H/1I/1J 是三轮修补。
   - 1H 是诊断，不改主 score。
   - 1I 是公式组合，失败。
   - 1J 是结构化静态 CFG/return-binding，仍失败。

## 当前不应直接使用 GPU 2/3 的原因

GPU 2/3 当前空闲，但现有 Phase 1 pipeline 的核心是：

- `gcc`
- `objdump`
- `nm`
- Python 标准库
- source-known C candidates

这些都是 CPU-only。更重要的是，Phase 1J 的 gate 没过，原计划中的 real-project transfer / realistic LLM-decompiler candidate generation 还没有方法学资格开始。现在直接用 GPU 跑 LLM candidate generation，风险是生成一批更贵、更真实但评价信号仍不可靠的数据，最后只会放大当前 representation mismatch。

GPU 2/3 应在以下任一条件满足后使用：

1. Phase 1K-v2 已证明 dynamic trace 能把 hard cases 拉上来，但仍需要先写单独 Phase 2 candidate-generation 计划。
2. 明确要做一个独立的 “LLM/decompiler candidate collection” 数据工程任务，而不是验证当前 static score。
3. 已经选定本地模型、prompt、candidate manifest 格式、compile gate、失败归因规则，并接受这一步是数据采集，不是 method validation。

## 原定后续 phase 是什么

原计划里的 Task 8 是 real-project transfer design gate：选小型真实 C 项目，控制 `O0/O2`，比较 same-source recompile noise、behavior-changing mutations、behavior-preserving rewrites，然后再写真实项目抽取计划。

这一步原本应该在 Phase 1A/1B/1C 初步通过后进行。但后续结果改变了判断：

- 1B 已经 kill 了 raw global distance。
- 1G 让 multi-opt slot concentration 变成 borderline。
- 1I 和 1J 都没有通过 leave-one-case-out。

所以 Task 8 现在不能按原计划启动。它不是永远取消，而是推迟到下一轮 representation gate 通过之后。

## 下一步应该怎么办

推荐进入 Phase 2 candidate-generation planning，而不是直接 real-project transfer 或直接开 GPU。

具体下一步：

1. 写 Phase 2 candidate-generation spec
   - 明确 candidate manifest 格式。
   - 明确 prompt 或 decompiler source。
   - 明确 compile gate、label policy、失败归因规则。
   - 明确 GPU 2/3 的使用命令、预算和停止条件。

2. 保持 source-known/localized-bug 边界
   - 继续使用 generated inputs，不把 fixture tests 当主分数。
   - 不把结果解释成通用 real-project decompilation verifier。

3. symbolic route 仍需单独计划
   - 当前环境缺少 `z3/angr/claripy/capstone/unicorn`。
   - 如果要继续 Route B，应另开 dependency plan，并把它限定为 hard-case explanation。

4. GPU 2/3 只进入计划讨论，不直接开跑
   - v2 已经让 Phase 2 candidate generation 变得可以讨论。
   - 但开跑前必须先定义 candidate manifest、prompt/decompiler source、compile gate、label policy、失败归因规则。

## 推荐下一条 prompt

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他项目目录，不要使用 subagent。

基于 Phase 1K-v2 和 Phase 1L ablation 结果，继续收窄为 source-known localized semantic bug auditing。请设计 Phase 2 candidate-generation plan，但不要直接运行 GPU 实验。

要求：
- 不启动 real-project transfer。
- 明确 candidate manifest 格式、prompt/decompiler source、compile gate、label policy、失败归因规则。
- 如果计划使用 GPU 2/3，必须写清楚 `CUDA_VISIBLE_DEVICES=2,3`、输出目录、预算和停止条件。
- 先写 spec 和 executable plan；只有计划通过后再跑。
```
