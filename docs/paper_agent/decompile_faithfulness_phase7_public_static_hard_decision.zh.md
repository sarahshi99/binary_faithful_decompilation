# Decompilation Faithfulness Phase 7 Public Benchmark Decision

## 结论

Phase 7C 和 Phase 7C2 的结论不同，但不矛盾：

- Phase 7C ordinary public row：`method-negative-public-benchmark`。
- Phase 7C2 static-hard row：`pass-phase7-static-hard-sota-delta`。

因此当前可以说：

> 在 CodeFuse-DeBench source-known scalar C 子集上，Dynamic Trace v3 已经有 public benchmark 对齐证据；当候选错误更接近局部语义漂移、且结构与原函数接近时，v3 相比 fixture/static baseline 有足够 margin。

但还不能说：

> 已经超过外部 decompilation 文献 SOTA。

## Phase 7C：ordinary public row

结果文件：

- `docs/paper_agent/decompile_faithfulness_phase7_public_benchmark_result.json`
- `docs/paper_agent/decompile_faithfulness_phase7_public_benchmark_result.zh.md`
- `analysis_outputs/decompile_faithfulness/phase7_public_benchmark_eval/records.jsonl`

主要结果：

- Source functions：`56`
- Candidates：`600`
- Compile pass：`600`
- Paired cases：`53`
- Fixture-only AUC：`0.5000`
- Static structured proxy AUC：`0.9693`
- Dynamic Trace v3 AUC：`1.0000`
- Delta vs best baseline：`+0.0307`
- Verdict：`method-negative-public-benchmark`

解释：v3 是满分，但 static baseline 也接近满分。原因是 Phase 7C 的主要 wrong candidates 是 fixture-ifchain，结构变化很明显，static structured baseline 也能抓到。因此这行证明了 full/public scale 和 v3 正向，但不能作为 SOTA margin 主证据。

## Phase 7C2：static-hard public row

结果文件：

- `docs/paper_agent/decompile_faithfulness_phase7_static_hard_result.json`
- `docs/paper_agent/decompile_faithfulness_phase7_static_hard_result.zh.md`
- `analysis_outputs/decompile_faithfulness/phase7_static_hard/records.jsonl`

主要结果：

- Source functions：`56`
- Candidates：`524`
- Compile pass：`503`
- Paired cases：`50`
- Fixture-only AUC：`0.9218`
- Static structured proxy AUC：`0.6831`
- Dynamic Trace v3 AUC：`1.0000`
- Delta vs best baseline：`+0.0782`
- Verdict：`pass-phase7-static-hard-sota-delta`

解释：C2 的 wrong candidates 是一次性局部微扰，例如 predicate strictness、arithmetic operator、return expression、constant perturbation。它们比 fixture-ifchain 更接近局部语义错，结构变化也更小，因此 static baseline 明显变弱，v3 拉开了超过 `0.05` 的 margin。

## 对 CCF-A / SOTA 的影响

正向点：

1. 用户担心的 full-vs-smoke 问题，这里已经是 full public row，不是 smoke。
2. 用户担心的 SOTA improvement 问题，C2 在 static-hard public candidates 上给出了 `+0.0782` 的 method margin。
3. v3 false-positive 风险较低：C7 ordinary row 中 behavior-preserving rewrite FP 为 `0`。

仍缺的点：

1. 还没有直接复现 LLM4Decompile / DecompileBench / CodeFuse-DeBench 的生成质量指标。
2. 还没有第二个 compile-ready decompiler 主证据。
3. 还没有 LLM judge / LLM-generated public candidate baseline。

## 下一步

推荐继续 Phase 7D / 7E：

1. Phase 7D：second compile-ready decompiler feasibility，优先 RetDec / rev.ng / angr AIL / Binary Ninja / Hex-Rays。
2. Phase 7E：在 GPU 2/3 上跑 CodeFuse public subset 的 LLM-generated candidates 或 LLM judge baseline。
3. 最终 SOTA readiness review：把 Phase 6R、Phase 7C、Phase 7C2、7D/7E 统一成主表和 limitations。
