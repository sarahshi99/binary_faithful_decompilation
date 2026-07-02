# Decompilation Faithfulness Phase 2 到 Phase 3 过渡说明

## 一句话结论

现在可以进入 Phase 3 readiness planning，但还不能直接宣称 real-project transfer 已完成。

理由是：Phase 2 v3 已经在本地 LLM 生成候选分布上通过了收窄 gate；但当前证据仍局限在 source-known、小函数、bounded generated inputs 的 localized semantic bug auditing 设置内。

## 前面实验是否成功

成功的是收窄命题，不是通用 verifier。

这也不是说一开始设想的所有路线都顺利完成了。更准确地说：

- 原始 static / binary distance 主线没有按最初乐观版本成功，Phase 1B、1I、1J 都给了负结果或 borderline 结果。
- 项目真正站住的是后来转向的 dynamic trace / source-known localized semantic bug auditing。
- Phase 2 的 GPU 生成完成了“更 realistic candidate distribution”这个目标，但它服务的是收窄后的问题定义，不是证明 arbitrary decompilation faithfulness。
- Phase 3 是在这些 gate 通过后继续做 transfer readiness，而不是宣布整个原始大问题已经解决。

| 实验 | 主要结论 | 是否支持进入下一步 |
|---|---|---|
| Phase 1K Dynamic Trace v2 | LOCO AUC `0.9531`，`gcd_positive=1.0000`，`fixture_collapse=False` | 是，支持 source-known localized 方法继续推进 |
| Phase 1L leakage / ablation | 未发现 label/output leakage；v2 明显强于 static-only | 是，排除一个关键风险 |
| Phase 2 generated candidates | 100 generations，63 compile-passed，8/8 cases 有 faithful/wrong pairs，v2 AUC `0.9623` | 是，说明方法在更 realistic candidate distribution 上仍有区分力 |
| Phase 2 result analysis | 发现 `count_bits8` fixture-passing 但 trace-mismatching 的非 oracle 例子 | 是，这是最重要的 paper-facing 正证据 |
| Phase 2 v3 scoring diagnostic | fixture-aware diagnostic 到 `1.0000`，但不应作为主方法声称 | 否，只能作为 upper-bound diagnostic |
| Phase 2 v3 boundary trace | 不使用 fixture mismatch 打分，AUC `1.0000`，8/8 case AUC `1.0000`，trace-zero blind spot 归零 | 是，支持把 v3 作为下一阶段默认 trace input policy |

## 为什么不是继续堆 GPU

GPU 生成已经完成了 Phase 2 的核心目的：让 candidate distribution 从手写 mutation 扩展到本地 LLM 生成候选。继续增加同类生成量的边际价值低于整理下一阶段边界。

当前最有价值的问题是：

1. v3 boundary trace 能否迁移到新 source-known 小函数。
2. 新函数是否仍能提供 bounded oracle 和 fixtures。
3. 是否会出现新的 fixture collapse 或边界盲点。

这些问题优先是 CPU-only preflight 和 source selection，不是 GPU 采样量问题。

## Phase 3 应该是什么

Phase 3 第一版应定义为：

> Source-known small-function transfer readiness check。

它不是 arbitrary real-project transfer。它要求每个函数都满足：

- 能从原始 source 编译并执行；
- 能精确定位单个目标函数；
- 输入域是 bounded 的；
- 有 fixtures；
- 有 oracle policy，即可以用原始 source 在 generated inputs 上得到参考输出；
- 能用 Phase 2 v3 boundary trace 评分。

## 为什么 Phase 3 不能只选一次

单次选择 5 个函数太脆弱：如果结果不好，我们无法区分是方法失败、函数选择偏了、oracle/domain 设错了，还是某个风险族本来就需要单独处理。

因此 Phase 3 现在采用：

1. 建 12 个候选小函数 source pool。
2. 先逐个编译并跑 fixtures，剔除 source/oracle 不合格项。
3. 枚举所有 5-10 函数组合。
4. 报告每个 size 的最佳组合，以及 minimal 5、balanced 7、broad 10、low-overlap backup 子集。
5. 只有多个低重叠、高覆盖子集反复失败，才考虑方法层面负结论。

当前 source selection 结果：

- Candidate functions：`12`
- Eligible functions：`12`
- Enumerated subsets：`3289`
- Verdict：`ready-for-combinatorial-phase3-cpu-audit`

## Phase 3 CPU 组合审计结果

已完成 CPU-only combinatorial audit：

- Candidate count：`28`
- Labels：`faithful=12`，`plausible_wrong=16`
- Overall pairwise AUC：`1.0000`
- 12/12 case AUC：均为 `1.0000`
- 5/5 recommended subsets AUC：均为 `1.0000`
- Fixture collapse：`False`
- Fixture-passing wrong count：`4`
- Verdict：`pass-combinatorial-phase3-cpu-audit`

这说明 v3 boundary trace 在新的 source-known 小函数池上，至少对 manual stress candidates 已经通过 transfer readiness。

## GPU 下一步

GPU generated-candidate smoke 已完成。第一次 `torch_dtype=auto` 并行跑 2/3 时模型能加载，但 generation 阶段 OOM；随后改用 `--torch-dtype float16`、`--steps 24` 后成功运行。

执行过的核心命令形态：

```bash
/home/shx/miniconda3/envs/llmxy/bin/python -m analysis.decompile_faithfulness.run_phase3_gpu_generated_smoke --device cuda:2 --torch-dtype float16 --steps 24
```

合并四个 GPU run 后：

- Candidate count：`47`
- Compile pass count：`28`
- Labels：`faithful=16`，`plausible_wrong=12`，`compile_fail=19`
- Paired case count：`5`
- Pair count：`26`
- Pairwise AUC：`1.0000`
- Fixture collapse：`False`
- Fixture-passing trace mismatch count：`1`
- Verdict：`pass-phase3-gpu-generated-combined-analysis`

这说明 Phase 3 在新 source-known 小函数池上的 LLM-generated candidate distribution 也没有击穿 v3 boundary trace。当前仍应把 claim 限定为 source-known small-function transfer readiness。

## Phase 3 暂不应该是什么

暂不应该做：

- 任意真实项目大范围抽函数；
- 无 oracle 的 binary-only verification；
- 安装 Ghidra / RetDec / angr / z3；
- GPU 批量生成候选后再补评估规则；
- 宣称完整语义等价证明。

## 推荐路线

1. 先运行 CPU-only Phase 3 readiness preflight。
2. 如果没有 source manifest，就先写 source selection manifest。
3. 选择 5-10 个 source-known 小函数，覆盖 branch、loop、arithmetic、bitwise、boundary behavior。
4. 先只用 v3 boundary trace 做 CPU audit。
5. 只有 CPU audit 证明 compile/oracle/fixture 都稳定后，再考虑 GPU 2/3 生成新候选。

## 当前判定

根据 Phase 2 v3：

- 方法 gate：通过。
- 下一阶段：允许进入 Phase 3 readiness planning。
- GPU：暂不需要。
- real-project transfer：不能直接宣称；必须先通过 source manifest 和 CPU audit。
