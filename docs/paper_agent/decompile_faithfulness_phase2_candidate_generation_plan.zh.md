# Decompilation Faithfulness Phase 2 Candidate Generation Plan

## 先回答：为什么现在可以进入 Phase 2 planning？

这里的“进入 Phase 2”不是说已经可以直接跑 GPU、直接做 real-project transfer，也不是说整个 decompilation faithfulness 问题已经解决。

准确说法是：

> Phase 1K-v2 和 Phase 1L 已经让 source-known localized semantic bug auditing 这个收窄问题通过了方法 gate，因此可以开始设计下一阶段 candidate generation；但还不能直接宣称 general decompiler faithfulness verifier，也不能跳过计划直接跑 GPU。

前面实验的状态：

| 部分 | 结论 |
|---|---|
| Raw global binary distance | 失败。Phase 1B realistic rewrites 后 AUC `0.5000`。 |
| Static binary motifs / slot concentration | 只能做辅助诊断。Phase 1I/1J LOCO 分别是 `0.6719` / `0.6823`。 |
| Dynamic Trace v1 | 部分成功。LOCO `0.8750`，但 `gcd_positive=0.5000`。 |
| Dynamic Trace v2 | 成功通过收窄 gate。LOCO `0.9531`，`gcd_positive=1.0000`，`fixture_collapse=False`。 |
| Phase 1L ablation / leakage | 成功。v2 AUC `0.9531`，static-only `0.8021`，v2 不等于 fixture-only oracle，leakage verdict `no-label-or-output-leakage-found`。 |
| Real-project transfer | 尚未证明，不能启动。 |

所以现在允许的是：

- 写 Phase 2 candidate-generation plan；
- 设计如何生成更 realistic 的 source-known candidates；
- 明确 manifest、prompt、compile gate、label policy、失败归因；
- 如果以后要用 GPU 2/3，先写清楚命令、预算、输出和停止条件。

现在不允许的是：

- 直接跑 GPU；
- 直接进入真实项目；
- 直接声称通用 decompiler faithfulness verifier。

## Phase 2 研究问题

在已有 8 个 source-known C cases 上，能否通过 LLM 或 decompiler-like source 生成更真实的 candidate distribution，并用 Dynamic Trace v2 对这些 candidates 做 localized semantic bug auditing？

换句话说，Phase 2 不是验证新 metric 本身，而是扩大 candidate 来源，让评估对象更接近真实生成/反编译输出。

## 实验范围

In scope：

- 只使用已有 8 个 source-known cases。
- 生成 candidates，不新增 source cases。
- 生成 candidate 初始 label 统一为 `unknown`。
- compile / behavior gate 自动把 unknown 分成：
  - `faithful`
  - `plausible_wrong`
  - `compile_fail`
- Dynamic Trace v2 是主评估信号。
- GPU 2/3 只在计划通过后才可用于本地 LLM candidate generation。

Out of scope：

- real-project transfer；
- 新 benchmark；
- 网络下载；
- 安装 Ghidra / RetDec / angr / z3；
- 训练或微调模型；
- subagent / parallel agent。

## Candidate Manifest

复用现有格式：

```json
[
  {
    "case_id": "gcd_positive",
    "candidates": [
      {
        "candidate_id": "llm_gcd_positive_0001",
        "label": "unknown",
        "mutation_type": "llm_generated",
        "function_source": "int gcd_positive(int a, int b) { ... }"
      }
    ]
  }
]
```

Phase 2 可增加 optional metadata，但不改变 evaluator 语义：

```json
{
  "source_kind": "local_llm",
  "source_name": "model-or-tool-name",
  "prompt_id": "phase2_v1_signature_only",
  "raw_output_path": "analysis_outputs/decompile_faithfulness/phase2_candidate_generation/raw/...",
  "cleaning_status": "parsed_function",
  "generation_index": 0,
  "sampling": {
    "temperature": 0.6,
    "top_p": 0.95,
    "max_new_tokens": 512
  }
}
```

如果现有 loader 不保留 optional metadata，就用 sidecar：

- `analysis_outputs/decompile_faithfulness/phase2_candidate_generation/metadata.jsonl`

## Prompt Families

Phase 2 至少比较三类 prompt，避免 candidate distribution 太单一。

### Prompt 1：Signature + Natural Spec

输入：

- 函数签名；
- 简短行为描述；
- fixture-domain 约束。

不给原始实现。

目的：

- 模拟“根据 specification 写实现”；
- 产生 faithful implementations 和自然 bug。

### Prompt 2：Source Rewrite

输入：

- 原始函数源码；
- 要求等价改写，结构不同。

目的：

- 生成 behavior-preserving rewrites；
- 检查 v2 是否不会误伤 faithful rewrites。

### Prompt 3：Bug-Seeding

输入：

- 原始函数源码；
- 要求生成 plausible but subtly wrong implementation。

目的：

- 生成 hard negatives；
- 但初始 label 仍应设为 `unknown`，由 behavior gate 自动标注，除非人工明确 curated。

## Candidate Cleaning Rules

清洗规则必须 deterministic：

- 只接受一个 C function；
- function name 必须等于 case 的目标函数名；
- 不允许 `main`；
- 不允许 `#include` / preprocessor；
- 不允许额外 helper function，除非先扩展 evaluator；
- raw output 必须保存；
- cleaned function_source 才写入 manifest。

## Evaluation Pipeline

Phase 2 generated candidates 的评估流程：

1. Manifest validation。
2. `/usr/bin/gcc` compile gate。
3. Fixture behavior gate：
   - pass -> `faithful`
   - fail -> `plausible_wrong`
   - compile fail -> `compile_fail`
4. Dynamic Trace v2 audit。
5. 汇总：
   - case；
   - prompt family；
   - source kind；
   - compile pass rate；
   - behavior label distribution；
   - v2 score distribution。

## GPU 2/3 使用策略

原始计划阶段不使用 GPU；CPU smoke 通过后，2026-06-18 已获准启动 GPU smoke。

当前实际可用策略：

```bash
/home/shx/miniconda3/envs/llmxy/bin/python -m analysis.decompile_faithfulness.run_phase2_gpu_smoke --device cuda:2
```

注意：在 `llmxy` 环境中，设置 `CUDA_VISIBLE_DEVICES=2` 或 `CUDA_VISIBLE_DEVICES=2,3` 会导致 CUDA probing 不可用；因此本项目当前不设置 `CUDA_VISIBLE_DEVICES`，而是在脚本内部显式 `torch.cuda.set_device(cuda:2)` 并把模型/输入移动到该 device。启动前必须检查 `nvidia-smi`，不 kill、不暂停、不改动他人进程。

GPU run 必须提前写清：

- model path / model id；
- Python environment；
- script path；
- output manifest path；
- raw output directory；
- candidates per case；
- prompt family；
- runtime budget；
- stop condition。

## 推荐执行顺序

1. CPU-only manifest smoke
   - 用极少量手写/fixture-derived candidates 验证 manifest -> compile gate -> behavior label -> v2 evaluator 贯通。

2. Local model availability probe
   - 不联网；
   - 只检查本地模型路径；
   - 如果没有可用本地模型，不进入 GPU run。

3. GPU smoke, later only after approval
   - 每个 case 每个 prompt family 生成 1-2 个 candidates；
   - 检查 compile rate 和 label distribution。

4. GPU full, later only after smoke
   - 目标至少 8 cases 全覆盖；
   - 每个 case 至少 5 个 compiling generated candidates；
   - 至少 5 个 cases 同时出现 faithful 和 plausible_wrong。

## 成功标准

Smoke gate：

- manifest validates；
- 至少每个 case 2 个 candidates compile；
- 总体至少有 1 个 faithful 和 1 个 plausible_wrong；
- Dynamic Trace v2 evaluator 可以运行；
- 没有 fixture oracle collapse。

Full gate：

- 8 cases 全覆盖；
- 每 case 至少 5 个 compiling generated candidates；
- 至少 5 cases 同时有 faithful / plausible_wrong；
- v2 score distribution 能区分 faithful 和 plausible_wrong；
- compile failures 和 cleaning failures 有明确归因。

Stop conditions：

- 大多数 candidate compile fail；
- candidates 都是 trivial faithful rewrites；
- candidates 都是明显测试失败 bug；
- 评估退化成 fixture-only oracle；
- GPU run 超预算或输出不可复现。

## 2026-06-18 GPU Smoke 执行更新

当前已经执行了 CPU-only Phase 2 smoke harness，结果通过：

- Smoke gate passed: `True`
- Candidates: `17`
- Compile pass count: `17`
- Behavior labels: `faithful=9`, `plausible_wrong=8`, `compile_fail=0`
- Fixture collapse: `False`
- Non-oracle probe count: `1`
- Trace pairwise AUC: `0.9444`

已新增 GPU smoke runner：

- `analysis/decompile_faithfulness/run_phase2_gpu_smoke.py`
- `tests/test_decompile_faithfulness_phase2_gpu_smoke.py`

第一轮默认 smoke：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_gpu_smoke.zh.md`
- 4 generations，1 parsed，1 compiled。
- label：`faithful=0`，`plausible_wrong=1`，`compile_fail=0`。
- 结论：链路打通，但 label diversity 未通过。

第二轮 `strict_signature` smoke：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_gpu_smoke_strict_signature.zh.md`
- 8 generations，6 parsed，2 compiled。
- label：`faithful=1`，`plausible_wrong=1`，`compile_fail=4`。
- 结论：GPU smoke 和 label diversity 通过；但同一 case 内还没有 faithful/wrong 配对，所以 `trace_pairwise_auc` 和 `fixture_collapse` 还不能解读为 Dynamic Trace v2 成败。

## 下一步

已完成 paired pilot、full_v1 和 targeted top-up。当前不需要继续启动新的 GPU 生成实验。

Paired pilot：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_gpu_paired_pilot.zh.md`
- 16 generations，15 parsed，10 compiled。
- label：`faithful=6`，`plausible_wrong=4`，`compile_fail=5`。
- paired cases：`2`。
- 结论：通过进入 full generation 的前置 gate。

Full v1：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_gpu_full_v1.zh.md`
- 80 generations，60 parsed，50 compiled。
- label：`faithful=27`，`plausible_wrong=23`，`compile_fail=10`。
- paired cases：`8`。
- `fixture_collapse=False`。
- `trace_pairwise_auc=0.9733`。
- 小缺口：`is_power_of_two` 只有 3 个 compiling candidates，未满足每 case >= 5 的 full gate。

Targeted top-up：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_gpu_topup_v1.zh.md`
- 20 generations，18 parsed，13 compiled。
- 目标 case：`is_power_of_two` 和 `max3`。

Combined full result：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_gpu_full_v1_plus_topup.zh.md`
- 100 generations，78 parsed，63 compiled。
- label：`faithful=34`，`plausible_wrong=29`，`compile_fail=15`。
- 每 case 编译通过候选数均 >= 5。
- 8/8 cases 同时包含 `faithful` 和 `plausible_wrong`。
- `fixture_collapse=False`。
- `trace_pairwise_auc=0.9623`。
- 结论：`pass-phase2-full-candidate-generation`。

Result analysis：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_result_analysis.zh.md`
- 结论：`pass-phase2-result-analysis`。
- 关键发现：
  - 8/8 cases 都有 faithful/wrong 配对。
  - 每 case 编译通过候选数均 >= 5。
  - `strict_rewrite` 主要产生 faithful：`faithful=25`，`plausible_wrong=3`。
  - `strict_bug` 主要产生 wrong：`faithful=9`，`plausible_wrong=26`。
  - 出现 1 个 fixture-passing 但 trace-mismatching 的 non-oracle 例子：`count_bits8` 生成了 count 16 bits 而非 8 bits 的实现。
  - 主要 blind spot 是 zero-boundary：`signum` / `is_power_of_two` 的部分 zero bug 被 fixture gate 捕获，但 primary trace score 为 0，说明 v3 应强制 boundary coverage 或把 fixture/boundary mismatch 纳入主分数。

Paper-facing table / claim text：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_paper_table_and_claims.zh.md`
- 可防守 claim：Dynamic Trace v2 在 source-known localized semantic bug auditing 的 generated candidate distribution 上保持强区分度。
- 必须保留 caveat：这不是 general verifier，也不是 real-project transfer。

V3 scoring diagnostic：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_v3_scoring_diagnostic.zh.md`
- 结论：`needs-boundary-input-regeneration`。
- `trace_total_v2`：AUC `0.9623`，weak cases 为 `signum=0.9000` 和 `is_power_of_two=0.9286`。
- 现有 `boundary` / `zero` feature 加权没有改善 AUC，也没有消除 2 个 trace-zero blind spots。
- fixture-aware diagnostic 可到 AUC `1.0000`，但这是 label-adjacent diagnostic upper bound，不应作为主方法。
- 下一步 v3 应重做 boundary-aware generated trace inputs，而不是只调 scoring 权重。

V3 boundary trace：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_v3_boundary_trace.zh.md`
- 结论：`pass-v3-boundary-trace`。
- 方法：不把 `fixture_mismatch_rate` 加入主分数，只在 primary trace inputs 中强制保留通用 boundary probes。
- Candidate count：`63`。
- Overall pairwise AUC：`1.0000`。
- 8/8 case pairwise AUC 均为 `1.0000`。
- `fixture_collapse=False`。
- trace-zero blind spot wrong count：`0`。
- 解释：v2 的 zero-boundary blind spot 主要来自 input regeneration policy，而不是 scoring 权重不足。

下一步应该转向 result analysis，而不是继续堆 GPU 生成量：

1. 按 case 分析 Dynamic Trace v2 的成功/失败模式。
2. 按 prompt family 分析 `strict_rewrite` 和 `strict_bug` 的分布差异。
3. 对 cleaning / compile failures 做归因。
4. 准备 Phase 2 paper-facing result table，并更新论文边界为 source-known localized semantic bug auditing。

Result analysis 已完成后，下一步应改为：

1. 写 Phase 2 paper-facing result table 和 claim text。
2. 设计 Dynamic Trace v3 的 boundary/fixture-aware scoring 小实验。
3. 只在 v3 小实验通过后，再考虑 Phase 3 real-project-transfer readiness check。

当前第 1-2 步已完成。新的下一步：

1. 将 v3 boundary trace refinement 提炼成方法描述和消融表。
2. 写 Phase 2/3 transition：当前已经可以讨论一个小型 real-project-transfer readiness check。
3. 真实项目前仍需保持边界：source-known / recompilable / bounded input；不要直接宣称 arbitrary binary decompilation verifier。
