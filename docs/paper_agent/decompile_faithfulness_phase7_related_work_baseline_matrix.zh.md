# Decompilation Faithfulness Phase 7 Related-work Baseline Matrix

## 结论

Baseline gate：`ready-baseline-implementation-after-benchmark-source`

Phase 7A 本地预检显示当前项目目录没有公开 benchmark checkout，因此不能直接进入 public benchmark main evaluation。但 baseline 定义本身已经清楚：一旦用户批准下载或提供本地 benchmark 路径，就可以按本矩阵实现。

## Claim 分层

本项目必须区分三类 claim：

1. **Decompiler generation quality**：谁生成的 C 更可读、更可编译、更能通过测试。
2. **Decompiler output validation**：给定一个反编译输出，如何判断它是否可信。
3. **Source-known semantic drift auditing**：给定原始 source oracle 和候选 C，如何发现 fixture 漏掉的局部语义漂移。

Dynamic Trace v3 当前最适合第 3 类。若写成第 1 类，会和 LLM4Decompile / DecompileBench 等工作错位竞争。

## Baseline Matrix

| Baseline / Related Work | Literature role | Metric to align | Direct reproduction? | Phase 7 proxy if not direct | Needs GPU/API/dependency | Decision |
|---|---|---|---|---|---|---|
| LLM4Decompile / Decompile-Eval | LLM decompilation generation | recompilability, re-executability | Not yet; dataset/model not local | Use public benchmark functions and compare fixture-only vs v3 on generated/perturbed candidates | GPU/API if generating candidates | `proxy-first` |
| DecompileBench | Real-world decompilation benchmark | runtime-aware validation, functionality correctness, semantic fidelity | Not yet; benchmark not local | Import source-known subset after approval; preserve benchmark IDs | network/download likely | `needs-benchmark-source` |
| Decompile-Bench | Large binary-source function pairs | large-scale source/binary alignment | Not yet; benchmark not local | Start with approved subset, not full million-scale | network/storage likely | `subset-first` |
| CodeFuse-DeBench | Benchmark stages for decompiled code | readability, recompilation, functionality | Not yet; repo/data not local | Use recompilation/functionality stages as comparison columns | network/download likely | `needs-benchmark-source` |
| fixture-only / re-execution-only | Common correctness gate | pass/fail on provided tests | Yes | Existing fixture mismatch / fixture pass signal | no | `implement-now` |
| static structured similarity | Lightweight non-oracle baseline | AUC / ranking score | Yes | Existing static structured proxy | no | `implement-now` |
| Dynamic Trace v1/v2/v3 | Method ablation | AUC, recall at fixed FP, FP rate | Yes | Existing dynamic trace modules, add public split adapter | no | `implement-now` |
| LLM judge | Popular semantic proxy, but hallucination-prone | pairwise correctness / wrongness judgment | No local baseline yet | Optional baseline after benchmark import; prompt fixed and output audited | GPU/API | `approval-needed` |
| fuzzing-style baseline | Heavier dynamic validation | generated input mismatch rate | Partially; v3 already resembles bounded generated traces | Add random/coverage-light baseline without boundary policy | no initially | `implement-after-import` |
| symbolic/concolic baseline | Strong semantic checking reference | satisfiability / counterexample found | No; z3/angr unavailable earlier | Dependency plan only for hard-case sanity | z3/angr | `dependency-plan-needed` |
| second compile-ready decompiler | Cross-decompiler robustness | v3 delta across tool sources | Only Ghidra compile-ready today | RetDec / rev.ng / angr AIL feasibility route | dependency/license | `phase7c-needed` |

## Main Table Target

Phase 7 main table should not be a decompiler-generation leaderboard. It should be:

| Setting | Candidate source | Benchmark | Baseline | Metric | Result |
|---|---|---|---|---|---|
| Source-known public functions | Ghidra / LLM / perturbation | public subset | fixture-only | AUC / recall | TBD |
| Source-known public functions | same | public subset | static structured | AUC / recall | TBD |
| Source-known public functions | same | public subset | v1/v2/v3 | AUC / recall / FP | TBD |
| Optional | same | public subset | LLM judge | agreement / AUC | TBD |
| Optional | second decompiler | public subset | v3 | cross-tool delta | TBD |

## Required Metrics

Minimum metrics for SOTA alignment:

- compile-pass / recompilability rate;
- fixture pass / re-executability rate;
- fixture-passing wrong count;
- AUC for faithful vs plausible-wrong ranking;
- recall at fixed behavior-preserving false positive rate;
- behavior-preserving rewrite false positive rate;
- per-risk-family breakdown;
- runtime/cost per candidate.

## Current Blockers

1. `blocked-needs-benchmark-download-approval`：本项目下没有 public benchmark checkout。
2. No second compile-ready decompiler beyond Ghidra.
3. No LLM judge / LLM generation baseline approval yet.
4. No public benchmark function manifest.

## Immediate Recommendation

下一步不是启动 GPU，而是先选择一个 benchmark acquisition route：

1. 用户提供本地 benchmark checkout 路径；或
2. 批准下载 CodeFuse-DeBench / DecompileBench / Decompile-Eval 中的一个；或
3. 如果短期不能下载公开 benchmark，先做 Phase 7C second decompiler dependency plan，把 Ghidra-only 风险降下来。

推荐优先级：

1. `CodeFuse-DeBench`：工程化 benchmark 框架更容易对齐 recompilation/functionality stages。
2. `DecompileBench`：论文语境强，但可能需要额外数据处理。
3. `Decompile-Eval / HumanEval-style`：规模较小，适合先做 adapter smoke。

## Gate

`ready-baseline-implementation-after-benchmark-source`

Baseline 定义已经足够执行；缺的是公开 benchmark 数据源或用户批准下载。
