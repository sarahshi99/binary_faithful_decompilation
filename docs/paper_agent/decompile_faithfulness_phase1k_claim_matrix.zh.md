# Decompilation Faithfulness Phase 1K Claim Matrix

## 目的

这个 claim matrix 用来决定 Phase 1 之后论文叙事是否还能维持“通用 decompilation faithfulness verifier”，还是应该收窄成 source-known / localized semantic bug auditing。

## Claim Matrix

| Claim | Phase 1A-1J 后状态 | 证据 | Phase 1K A/B 还能改变什么 | 论文措辞建议 |
|---|---|---|---|---|
| raw global binary distance can rank decompilation faithfulness | 不成立 | Phase 1B realistic rewrites 后 `pairwise_auc=0.5000`；Phase 1E raw global-distance 在多优化级别也很弱。 | Route A 已经转向行为 trace，不再拯救 raw global distance；Route B 也不会让 global binary distance 成为主方法。 | 不要作为主贡献。可以作为被系统性排除的 baseline / negative result。 |
| multi-opt slot concentration is a robust verifier | 边界不足 | Phase 1E `0.8472`、Phase 1F `0.8250`，但 Phase 1G 降到 `0.7552`；Phase 1I LOCO `0.6719`，Phase 1J LOCO `0.6823`。 | Route A 说明 dynamic trace + 少量 min-slot 有更强信号，但 slot concentration 本身不能单独承担 verifier。 | 只能说是 useful diagnostic / auxiliary signal，不能说 robust verifier。 |
| static binary motifs are useful diagnostics | 局部成立 | Phase 1H 能解释 `signum` blind spot；Phase 1J 的 CFG/return-binding 没通过 gate，但能提供失败归因。 | Route A 可以把 static motifs 退到辅助特征或 case analysis；Route B 若成功，可与 symbolic explanation 对照。 | 可以作为 diagnostic evidence，不要作为 ranking method 的核心。 |
| source-known dynamic traces can identify localized semantic bugs | 初步成立但未完全通过 hard-case gate | Phase 1K Route A LOCO `0.8750`，不是 fixture collapse；`max3`、`sum_to_n` 达到 `1.0000`，`signum=0.7500`，但 `gcd_positive=0.5000`。 | Route A 后续可加入 loop-aware / termination-aware trace features，专门处理 `gcd_positive`；这条路线目前最有增量。 | 可以作为下一阶段主线，但必须限定为 source-known、bounded generated inputs、localized semantic bug auditing。 |
| symbolic/concolic summaries may explain hard cases | 有潜力但本轮不可执行 | Phase 1K Route B 发现 `z3/angr/claripy/capstone/unicorn` 当前都不可用；没有依赖时只能做有限枚举，和 Route A 重叠。 | 单独依赖计划可能改变 `gcd_positive`、`signum` 的解释能力；本轮不能证明。 | 写成 future method extension 或 planned follow-up，不要当作当前实验贡献。 |
| real-project transfer is justified now | 不成立 | Phase 1I/1J 都是 `do-not-transfer-yet`；Phase 1K Route A 仍是 `borderline-dynamic-trace`，且 hard case `gcd_positive=0.5000`。 | 只有 Route A 后续修复 hard cases，或 Route B 依赖计划给出可复现实验后，才可重开 transfer gate。 | 明确推迟。不要现在启动真实项目迁移。 |
| GPU LLM/decompiler candidate generation is justified now | 不成立 | 当前 Phase 1K 是 CPU/gcc/source-known audit；评价信号还没有稳定到足以消费 GPU 生成大批 candidates。 | 如果先定义 candidate manifest、prompt、compile gate、失败归因规则，可以作为独立数据采集任务，不应混入 Phase 1K gate。 | 现在不启动。若后续需要 GPU 2/3，应另开 Phase 2 data-collection plan。 |

## Route C Verdict

`narrow-localized-bug-paper`

当前最可防守的论文边界不是“通用反编译忠实性验证”，而是：

> 在 source-known、小函数、可重编译的设置下，结合 generated dynamic traces 和辅助 binary diagnostics，识别 localized semantic bugs，并系统性展示哪些 static binary similarity 信号会失败。

这个收窄不会否定 Phase 1 的价值；相反，它把负结果变成边界证据，把 Route A 的正结果变成下一阶段可继续投入的主线。
