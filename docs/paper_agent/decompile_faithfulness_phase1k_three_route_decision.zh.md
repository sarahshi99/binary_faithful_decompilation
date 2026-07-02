# Decompilation Faithfulness Phase 1K 三路线决策

## 背景

Phase 1I/1J 已经证明继续修补 lightweight static binary motifs 不可靠：Phase 1I leave-one-case-out 为 `0.6719`，Phase 1J leave-one-case-out 为 `0.6823`。因此 Phase 1K 不再只修 static score，而是同时检查三条路线：

1. Route A：generated dynamic trace gate。
2. Route B：symbolic / concolic feasibility probe。
3. Route C：narrowed localized-bug framing audit。

## Route A：Dynamic Trace

结果文件：

- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.json`
- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.zh.md`
- `analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace/records.jsonl`

主要结果：

- Dataset：`8` cases / `56` candidates。
- Best in-sample：`trace_total_plus_min_slot_0.10`，AUC `0.8958`。
- Leave-one-case-out AUC：`0.8750`。
- Fixture collapse：`False`。
- Hard cases：`signum=0.7500`，`gcd_positive=0.5000`，`max3=1.0000`，`sum_to_n=1.0000`。
- Verdict：`borderline-dynamic-trace`。

解释：Route A 是 Phase 1K 里唯一给出明显增量信号的路线。它证明 generated dynamic traces 比当前 static motifs 更接近语义错误，但 `gcd_positive` 仍失败，所以还不能宣称一般 verifier 已经成立。

## Route A-v2：Domain-Aware Dynamic Trace

结果文件：

- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.json`
- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.zh.md`
- `analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace_v2/records.jsonl`

主要结果：

- Dataset：`8` cases / `56` candidates。
- Best in-sample：`trace_mismatch_rate`，AUC `0.9531`。
- Leave-one-case-out AUC：`0.9531`。
- Fixture collapse：`False`。
- Hard cases：`signum=0.7500`，`gcd_positive=1.0000`，`max3=1.0000`，`sum_to_n=1.0000`。
- Verdict：`pass-dynamic-trace-v2-localized-bug`。

解释：v2 修复了 v1 的关键问题。`gcd_positive` 的 source-known contract 是正整数输入，但 v1 generated inputs 包含负数和 0，导致 faithful subtraction-style gcd rewrites 被 out-of-domain behavior 错判。v2 只从 fixture 参数值推断输入域；对 `gcd_positive` 生成 strictly-positive primary inputs，不读取 candidate label，也不根据 candidate output 反向调参。结果是三个 faithful gcd rewrites 的 `trace_mismatch_rate=0.0`，hard negatives 仍保持高 mismatch，`gcd_positive` held-out AUC 从 `0.5000` 提升到 `1.0000`。

## Phase 1L：Ablation / Leakage Audit

结果文件：

- `docs/paper_agent/decompile_faithfulness_phase1l_ablation.json`
- `docs/paper_agent/decompile_faithfulness_phase1l_ablation.zh.md`

主要结果：

| Variant | AUC | gcd_positive | signum | max3 | sum_to_n |
|---|---:|---:|---:|---:|---:|
| `mixed_domain_v1_trace_mismatch` | `0.8906` | `0.5000` | `0.7500` | `1.0000` | `1.0000` |
| `domain_aware_v2_trace_mismatch` | `0.9531` | `1.0000` | `0.7500` | `1.0000` | `1.0000` |
| `fixture_only_oracle` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `static_only_min_slot` | `0.8021` | `0.6667` | `0.4583` | `1.0000` | `0.8333` |

Leakage audit：

- Domain inference source：`fixture_argument_values_only`
- Uses labels：`False`
- Uses candidate outputs：`False`
- Uses candidate ids：`False`
- V2 identical to fixture-only：`False`
- Domain-filtered cases：`count_bits8, gcd_positive`
- Verdict：`no-label-or-output-leakage-found`

解释：Phase 1L 支持 v2 的可信度。v2 明显强于 static-only `min_slot`，也不同于 fixture-only oracle；fixture-only 达到 `1.0000` 说明现有测试本身可作为上界，但 v2 没有直接退化成这个 oracle。

## Route B：Symbolic / Concolic Probe

结果文件：

- `analysis_outputs/decompile_faithfulness/phase1k_symbolic_probe/environment.json`
- `docs/paper_agent/decompile_faithfulness_phase1k_symbolic_probe.zh.md`

当前环境中 `z3`、`angr`、`claripy`、`capstone`、`unicorn` 都不可用。Phase 1K 不安装依赖、不联网，所以本轮不能运行严格 symbolic/concolic 实验。

Verdict：`needs-dependency-plan`。

解释：Route B 仍可能帮助解释 `gcd_positive` 和 `signum`，但需要单独依赖计划，不能作为本轮结果的主证据。

## Route C：Claim Matrix

结果文件：

- `docs/paper_agent/decompile_faithfulness_phase1k_claim_matrix.zh.md`

Verdict：`narrow-localized-bug-paper`。

解释：Phase 1A-1K 的证据不支持“通用 decompilation faithfulness verifier”；更可防守的边界是 source-known、小函数、可重编译、bounded generated inputs 下的 localized semantic bug auditing。

## Final Decision

`continue-to-phase2-planning-after-phase1l`

Phase 1K-v2 已经通过预设 gate：overall LOCO AUC `0.9531 >= 0.8750`，`gcd_positive=1.0000 > 0.5000`，且 `fixture_collapse=False`。Phase 1L 进一步通过 ablation / leakage audit：v2 AUC `0.9531`，比 v1 高 `0.0625`，比 static-only 高 `0.1510`，并且不是 fixture-only oracle collapse。

但最终论文边界仍应保持收窄：source-known、小函数、可重编译、fixture-domain-aware generated inputs 下的 localized semantic bug auditing。这个结果足以继续写方法和消融，不等于已经可以宣称 real-project decompilation faithfulness verifier。

下一阶段建议：

1. 写 Phase 2 candidate-generation plan：只做计划，不直接开跑 GPU。计划必须定义 candidate manifest、prompt/decompiler source、compile gate、label policy、失败归因和成功标准。
2. 保留 `min_slot` 作为辅助诊断，不再把 static binary motif 当主方法。
3. Route B symbolic 仍需单独 dependency plan，只服务 hard-case explanation。
4. GPU 2/3 现在可以被纳入一个单独的 Phase 2 candidate-generation 计划讨论，但不应直接开跑；必须先定义 candidate manifest、prompt/decompiler source、compile gate、label policy 和成功/失败判断。

## 下一条建议 prompt

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他项目目录，不要使用 subagent。
使用 superpowers:brainstorming / writing-plans 设计下一阶段，但执行时只用 superpowers:executing-plans。

基于 Phase 1K-v2 和 Phase 1L ablation 结果，继续收窄为 source-known localized semantic bug auditing。
请设计 Phase 2 candidate-generation plan，但不要直接运行 GPU 实验。

要求：
- 不启动 real-project transfer。
- 明确 candidate manifest 格式、prompt/decompiler source、compile gate、label policy、失败归因规则。
- 如果计划使用 GPU 2/3，必须写清楚 `CUDA_VISIBLE_DEVICES=2,3`、输出目录、预算和停止条件。
- 先写 spec 和 executable plan；只有计划通过后再跑。
```
