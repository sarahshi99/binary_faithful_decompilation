# Decompilation Faithfulness Phase 1J CFG/Return-Binding Design

## 当前结论

这个项目已经不是 Phase 1A 初始阶段。已有结果显示：

- Phase 1A.1 controlled mutation：`pairwise_auc=1.0000`，说明 operand-sensitive binary features 在玩具 mutation 上有效。
- Phase 1B realistic negatives：raw global feature-distance 失败，`pairwise_auc=0.5000`。
- Phase 1D/1E/1F：slot-local calibration 一度恢复信号，multi-opt min slot concentration 在 3/5 cases 上到 `0.8472` / `0.8250`。
- Phase 1G：扩到 8 cases 后降到 borderline，combined AUC `0.7552`。
- Phase 1H：`instruction_bigram_l1` 和 `branch_return_immediate_pair_l1` 能暴露 `signum` reversed-return blind spot，但直接纳入 primary score 不安全。
- Phase 1I：简单 component combination 失败，best in-sample `0.7604`，leave-one-case-out `0.6719`，verdict 为 `do-not-transfer-yet`。

因此下一步不能进入 real-project transfer，也不应该只是继续扩大 cases。必须先重新设计 representation 或收窄问题边界。

## Phase 1J 研究问题

在已有 8 个 source-known cases / 56 candidates 上，能否用更结构化的 binary representation，显式建模 control-flow path 与 return value / immediate 的绑定关系，从而稳定地区分 localized semantic bug 与 behavior-preserving rewrite drift？

核心问题不是“binary feature distance 是否有一点信号”，而是：

> 能否把 Phase 1I 的 leave-one-case-out 从 `0.6719` 提升到足以继续研究的水平，同时修复 `signum`、`gcd_positive`、`max3`、`sum_to_n` 这些 held-out 弱点？

## 推荐实验：CFG/Return-Binding Audit

### 假设

当前 flat bag-of-instructions / flat slot-vote representation 漏掉了条件分支、返回值、compare immediate 和 basic-block successor 之间的绑定关系。错误 candidate 可能和 faithful rewrite 拥有相同的指令 multiset，但把 return constant 或 update value 绑定到了错误的 branch/path 上。

如果从 object code 中抽取 lightweight CFG motifs，而不是只看全局计数，应该能更稳定地捕捉这类 bug。

### 输入

复用 Phase 1H 已经生成的 per-opt artifacts，不重新生成候选：

- `analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1e`
- `analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1f`
- `analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1g`

每个 artifact root 下读取：

- `o0/o1/o2/o3/records.jsonl`
- `o0/o1/o2/o3/candidates/*__<OPT>.function.o`

### 新特征族

Phase 1J 应新增一个独立模块，例如：

- `analysis/decompile_faithfulness/structured_features.py`

建议特征族：

1. Basic-block shape
   - block count
   - block length histogram
   - terminal opcode histogram
   - fallthrough / branch / return block counts

2. CFG edge motifs
   - conditional branch edge signatures
   - back-edge / loop-like motifs
   - branch opcode plus successor terminal kind

3. Return-binding motifs
   - conditional jump -> nearby return-immediate binding
   - compare/test immediate -> conditional jump -> return-immediate binding
   - branch direction normalized return constants, e.g. negative path / positive path / zero path

4. Update-binding motifs
   - loop-carried assignment/update opcode motifs
   - modulo/subtraction/update patterns for `gcd_positive`
   - accumulator update motifs for `sum_to_n`

5. Stability controls
   - keep existing `instruction_bigram_l1` and `branch_return_immediate_pair_l1` as diagnostics
   - report faithful-rewrite drift separately from plausible-wrong drift

### Scoring

不要直接把所有新 features 加进旧 slot votes。先做并列诊断：

- `cfg_binding_l1`
- `return_binding_l1`
- `update_binding_l1`
- `structured_slot_concentration`
- `structured_plus_min_slot`

多优化级别聚合仍然保留：

- min / mean / max / range over `O0/O1/O2/O3`
- leave-one-case-out 只允许在 train cases 上选择公式，再在 held-out case 上评估

### Baseline 对照

必须同时报告：

- Phase 1G `min_slot = 0.7552`
- Phase 1I best in-sample `0.7604`
- Phase 1I leave-one-case-out `0.6719`
- Phase 1J structured features 的 in-sample 和 leave-one-case-out

## 成功门槛

Phase 1J 只有满足以下条件，才允许进入下一步：

- leave-one-case-out pairwise AUC `>= 0.80`
- `signum` held-out AUC `>= 0.667`
- `gcd_positive` held-out AUC `>= 0.667`
- `max3` held-out AUC `>= 0.667`
- `sum_to_n` held-out AUC `>= 0.667`
- 对 faithful rewrites 的 suspiciousness 不应整体高于 plausible-wrong candidates

如果只在 in-sample 提升，而 leave-one-case-out 仍低于 `0.75`，应判定为继续负结果。

## Kill Criteria

停止这条路线的条件：

- Phase 1J leave-one-case-out `< 0.75`
- hard cases 中至少两个仍低于 `0.60`
- 新 features 主要惩罚 behavior-preserving rewrites，而不是 semantic bugs
- 需要手工为每个 case 写专属规则才能提升

## 不做的事

- 不启动 real-project transfer。
- 不接入 Ghidra/RetDec/angr。
- 不用 LLM API 或 GPU。
- 不训练模型作为主方法。
- 不使用 subagent、Task/Spawn、parallel-agent 或 reviewer discovery。

## 推荐结论口径

如果 Phase 1J 成功：可以把论文方向收窄为“source-known/localized semantic bug faithfulness auditing with structured binary motifs”，再设计真实 decompiler candidate 的小规模 transfer。

如果 Phase 1J 失败：当前 binary-feature audit 方向不应作为主论文路线；可以保留为 negative result / diagnostic tooling，转向动态 trace、symbolic trace，或重新定义更窄的问题。
