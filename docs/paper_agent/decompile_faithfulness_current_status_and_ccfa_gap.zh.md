# Decompilation Faithfulness 当前状态与 CCF-A Gap

## 总体判断

当前项目已经从“探索性实验”推进到“主方法和主表基本成型，可以进入论文写作与外部补强”的阶段。

如果用 CCF-A 完成度粗略评分：

- Phase 13 后：约 `7.0 / 10` 到 `7.5 / 10`。
- Phase 19 后：约 `8.0 / 10` 到 `8.3 / 10`。

这个分数的含义是：核心问题、方法机制、三套 full 主结果、case-level bootstrap、runtime/risk-family 表、负结果边界都已经比较完整。现在最大的缺口不是“主方法有没有效果”，而是“论文包装、外部相关工作 PK、第二 compile-ready decompiler 或明确 Ghidra-centered scope”。

当前最稳的论文方法名：

`source-literal-aware fixture-neighbor low-budget dynamic re-execution`

当前最稳的论文 scope：

`source-known localized semantic drift auditing`

不要写成：

- general binary-only decompilation verifier；
- decompiler generation SOTA；
- v3 scoring components beat all strong fuzzing baselines；
- cross-decompiler robustness 已充分证明。

## 当前主结果是否好

好。Phase 18/19 后，最终方法在三套 full 数据上 budget-8 全过，而且不再有 Phase 16 的 Ghidra char-boundary/multi-arg 缺口。

最终方法：

`source_literal_char_interleave`

机制解释：

1. 先保留 fixture-neighbor probes，用于抓 fixture-overfit 和边界附近语义漂移。
2. 对 `char` 参数，从原始 source 中抽取真实出现过的 char literals，并与 fixture-neighbor probes 交错。
3. 不使用 Phase 17 那种粗暴 operator-first 列表，因为 full 结果证明它会挤掉有用的字母/边界 probe。

Phase 18 full budget-8 结果：

| Dataset | Budget-8 AUC | Wrong detection | Missed wrong | Avg inputs |
|---|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `1.0000` | `1.0000` | `0` | `6.64` |
| `phase7e_llm_public_full_topup` | `1.0000` | `1.0000` | `0` | `6.69` |
| `phase6r_ghidra_full` | `1.0000` | `1.0000` | `0` | `6.97` |

Phase 19 bootstrap：

| Dataset | AUC CI95 | Detection CI95 | Missed wrong |
|---|---:|---:|---:|
| `phase7c2_static_hard_public` | `[1.0000, 1.0000]` | `[1.0000, 1.0000]` | `0` |
| `phase7e_llm_public_full_topup` | `[1.0000, 1.0000]` | `[1.0000, 1.0000]` | `0` |
| `phase6r_ghidra_full` | `[1.0000, 1.0000]` | `[1.0000, 1.0000]` | `0` |

Phase 19 runtime：

| Dataset | Candidates | Total seconds | Mean sec/candidate | P95 sec/candidate | Input evals/sec |
|---|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `478` | `85.60` | `0.1782` | `0.0923` | `37.05` |
| `phase7e_llm_public_full_topup` | `136` | `7.94` | `0.0573` | `0.0874` | `114.65` |
| `phase6r_ghidra_full` | `166` | `11.21` | `0.0660` | `0.1031` | `103.25` |

解释：

- AUC = wrong candidates 是否能排在 faithful candidates 前面。
- Wrong detection = wrong candidates 是否至少被一个 budgeted input 暴露。
- Avg inputs 约 `7`，说明方法仍是低预算。
- Runtime 是当前 Python trace harness 下的 compile/run 实测，已经可以进论文成本表。

## 实验方案是否完成

结论：主线实验已经完成，并且经过 Phase 17 负结果和 Phase 18 修正后，最终方法比 Phase 12 更稳。

| 阶段 | 原目标 | 当前状态 | 结果性质 | 是否支撑当前主 claim |
|---|---|---|---|---|
| Phase 1A-1J | binary/static feature route | 已完成 | 多数负向；raw/global/static motif 不稳 | 支撑问题动机和负结果 |
| Phase 1K-v2 | dynamic trace route | 已完成 | 正向，修复早期 hard case | 是 |
| Phase 1L | leakage / ablation | 已完成 | 正向，无明显 label/output leakage | 是 |
| Phase 2 | generated candidate full run | 已完成 | 正向，v3 boundary trace pass | 是 |
| Phase 3 | 新小函数池和组合选择 | 已完成 | 正向，CPU/GPU combined 通过 | 是，但不是最终主证据 |
| Phase 4 | paper synthesis / claim shaping | 已完成初版 | 收窄为 source-known localized auditing | 是 |
| Phase 5/5B | source-known transfer + hard candidates | 已完成主要路线 | hard candidate route 正向；一般 GPU generation 不作为主 claim | 是 |
| Phase 6/6R | decompiler-like + Ghidra real output | 已完成 | Ghidra full/gcc9 full 通过 | 是，真实工具主证据 |
| Phase 6R radare2 | second tool smoke | 已完成 smoke | radare2 没有 compile-ready C | limitation |
| Phase 7 | public benchmark / LLM-public alignment | 已完成主要 rows | public static-hard + LLM-public full 正向 | 是 |
| Phase 8 | SOTA hardening | 已完成 | strong generated-input mismatch 抹平 v3 extra margin | 支撑 claim 修正 |
| Phase 9/10 | low-budget proxy 与 actual rerun | 已完成 | proxy 偏乐观；actual rerun 暴露 Ghidra 弱点 | 引出 Phase 11 |
| Phase 11/12 | fixture-neighbor unified eval | 已完成 | 正向，但 Ghidra 剩 2 个 miss | 旧主方法 |
| Phase 13/14 | evidence synthesis + bootstrap | 已完成 | 旧方法 paper-ready，但仍有 miss | 被 Phase 18/19 更新 |
| Phase 15/16 | paper skeleton + runtime/risk | 已完成 | runtime 表生成，发现 Ghidra char-boundary/multi-arg 缺口 | 引出 Phase 17/18 |
| Phase 17 | operator-first char policy | 已完成 | 负结果：修 multi_arg 但伤 char_boundary/public | 作为 ablation |
| Phase 18 | source-literal char interleave | 已完成 full | 强正向：三套 full budget-8 全 `1.0`，miss `0` | 当前最终主方法 |
| Phase 19 | final evidence refresh | 已完成 | bootstrap/runtime/risk 全过 | 当前论文证据包 |

## 距离 CCF-A 还有多远

现在不是“实验主线没站住”，而是“论文和外部说服力还要补齐”。

最关键剩余项：

1. **第二 compile-ready decompiler 或 scope 处理**：如果能补 RetDec / rev.ng / Binary Ninja / Hex-Rays 任一 compile-ready row，会显著增强；如果不能，论文必须明确 Ghidra-centered real-decompiler evidence。
2. **相关工作和 SOTA 定位**：不能声称 generation SOTA；要和 decompiler evaluation、semantic auditing、fuzzing/symbolic checking、LLM decompilation benchmark 清晰对位。
3. **论文写作与图表**：需要 method figure、motivating example、main table、ablation table、runtime/risk table、threats to validity。
4. **外部复现包**：整理 manifests、records、scripts、seed、budget、candidate filtering rules。
5. **额外鲁棒性可选项**：如果时间允许，补一个 held-out 函数集合或第二 toolchain，会让满分可信度更高。

粗略时间判断：

- 写成完整 arXiv/workshop draft：现在可以开始，约 `1` 周内可成稿。
- 冲 CCF-A：还需要约 `2-4` 周集中写作、补图、补 related work、做审稿式自查。
- 如果强行要求第二 compile-ready decompiler：取决于工具可用性，可能额外 `1-4` 周。

## 下一步

进入论文成稿阶段：

1. 更新 Phase 15 skeleton 到 Phase 18/19 final method。
2. 生成主表、ablation 表、runtime/risk 表的 LaTeX 草稿。
3. 写 motivating example：Phase 17 负结果与 Phase 18 修复可作为很好的方法动机。
4. 做 related-work/SOTA matrix。
5. 决定是否继续尝试第二 compile-ready decompiler；如果不做，就把 scope 写硬。
