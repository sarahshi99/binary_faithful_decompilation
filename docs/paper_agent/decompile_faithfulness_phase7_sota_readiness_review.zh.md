# Decompilation Faithfulness Phase 7 SOTA Readiness Review

## 结论

Phase 7 已经补上了 full public benchmark 证据，但还不能宣称超过外部 decompilation 文献 SOTA。

当前最稳的论文 claim 是：

> 在 source-known、可重编译、小 C 函数、bounded generated inputs 的 localized semantic drift auditing 设定下，Dynamic Trace v3 在公开 CodeFuse-DeBench scalar C 子集和 Ghidra real-decompiler 输出上，能比 fixture-only / static-structured auditor 更稳健地识别语义错误；其中 static-hard public row 已达到 `+0.0782` 的方法 margin。

不能写成：

> 我们已经超过 LLM4Decompile / DecompileBench / CodeFuse-DeBench 的生成质量 SOTA，或已经构建通用 decompiler faithfulness verifier。

## 已完成证据

| Row | Scale | Best baseline | Dynamic Trace v3 | Delta | Verdict |
|---|---:|---:|---:|---:|---|
| Phase 7C ordinary public | 600 candidates / 53 paired cases | Static `0.9693` | `1.0000` | `+0.0307` | `method-negative-public-benchmark` |
| Phase 7C2 static-hard public | 503 compile-pass / 50 paired cases | Fixture `0.9218` | `1.0000` | `+0.0782` | `pass-phase7-static-hard-sota-delta` |
| Phase 7E LLM public full+top-up | 143 compile-pass / 24 paired cases | Fixture `0.9741` | `1.0000` | `+0.0259` | `method-negative-phase7-llm-public` |
| Phase 7D second decompiler | local probe | none ready | n/a | n/a | `blocked-awaiting-second-decompiler-approval` |

## 对两个核心担忧的回答

### 1. Full 而不是 smoke

Phase 7C、7C2、7E 都已经不是 smoke：

- Phase 7C 覆盖 CodeFuse-DeBench 保守 scalar C 主集：`56` source functions，`600` candidates。
- Phase 7C2 覆盖同一 public source pool 的 static-hard 局部语义漂移：`524` candidates，`503` compile-pass。
- Phase 7E 用 GPU 2/3 做了第一轮 full shard 加第二轮 full top-up：`224` generations，`143` compile-pass。

因此现在的问题不再是“样本太小没有说服力”，而是“哪一种候选分布能支持什么 claim”。

### 2. 距离 CCF-A / SOTA 的进步

正向结果存在，但还不够泛化为外部 SOTA：

- 强正向：static-hard public row 的 `+0.0782` 超过预设 `>=0.05` gate，说明方法不是只在 toy/smoke 上成立。
- 稳定正向：ordinary public 和 LLM public row 中 v3 都达到 `1.0000`，且强于 static structured。
- SOTA blocker：ordinary public 的 static baseline 已经 `0.9693`，LLM public 的 fixture baseline 已经 `0.9741`，所以 delta 分别只有 `+0.0307` 和 `+0.0259`。

这说明 Dynamic Trace v3 的上限很好，但在某些 public/LLM candidate 分布中，baseline 也很强。论文必须把主表放在“static-hard/local semantic drift”和“real decompiler semantic auditing”，而不是把普通 candidate pool 当 SOTA 主证据。

## 主表建议

主表应该分三块，避免混淆任务定义：

1. Public source-known semantic auditing。
   - ordinary public row 作为规模/对齐证据。
   - static-hard public row 作为主要方法 margin 证据。
2. Real decompiler output auditing。
   - Phase 6R Ghidra full + cross-toolchain 作为真实工具证据。
   - radare2 只放 importability/limitation，不放 compile-ready 主表。
3. LLM-generated candidates。
   - Phase 7E 作为强 baseline stress test。
   - 结论写为 v3 perfect detection but not enough delta over fixture baseline。

## 缺口

1. 还缺第二个 compile-ready real decompiler。RetDec / rev.ng / Binary Ninja / Hex-Rays 任一可用后，才能把 cross-decompiler claim 写硬。
2. 还缺直接外部指标对齐。当前不是复现 LLM4Decompile/DecompileBench 的 Pass@k 或 decompilation generation quality 指标。
3. 还缺更强 baseline。需要 LLM judge、symbolic/fuzzing-style、或 real decompiler native verifier baseline，否则审稿人会问 static/fixture 是否太弱或任务太窄。
4. 还缺 confidence interval / bootstrap。现在 AUC 是点估计，CCF-A 论文需要不确定性和按 family 的稳定性。

## 下一步计划

Phase 8 应该做 SOTA hardening，而不是继续无目标增加样本：

1. Bootstrap significance。
   - 对 Phase 7C2、7E、Phase 6R 做 case-level bootstrap CI。
   - 输出主表置信区间，验证 `+0.0782` 是否统计稳定。
2. Strong-baseline audit。
   - CPU-only 先实现 fuzzing-style baseline：random/boundary generated inputs + fixture-only expansion。
   - 如果仍无法覆盖 static-hard errors，再把 Dynamic Trace v3 的价值写得更清楚。
3. Second decompiler dependency decision。
   - 若用户批准安装/使用 RetDec 或 rev.ng，优先跑一个 compile-ready second-decompiler row。
   - 若不批准，论文 claim 收窄为 Ghidra-backed real decompiler evidence。
4. Paper framing。
   - 题目和摘要避免“general decompilation SOTA”。
   - 主贡献写成 localized semantic drift auditing problem + dynamic trace verifier。
   - 把 ordinary public 和 LLM public negative-delta row 主动放入 limitations/robustness，不隐藏。

## 下一条建议 prompt

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他项目目录，不要使用 subagent。
使用 superpowers:writing-plans / executing-plans / test-driven-development。

继续 Phase 8 SOTA hardening。
目标不是盲目增加样本，而是验证 Phase 7C2 的 `+0.0782` margin 是否足够稳定，并补强 baseline。

请先做 CPU-only bootstrap significance 和 fuzzing-style baseline plan：
- 对 Phase 7C2 static-hard、Phase 7E LLM public、Phase 6R Ghidra full 做 case-level bootstrap CI。
- 实现一个 fixture-expansion/fuzzing-style baseline，与 Dynamic Trace v3 比较。
- 不使用 GPU，除非后续需要 LLM judge。
- 成功 gate：Phase 7C2 v3 delta 的 95% bootstrap CI lower bound > 0，且 fuzzing-style baseline 不能完全抹平 v3 margin。
```
