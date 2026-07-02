# Decompilation Faithfulness Phase 6R Dependency Decision

## 当前结论

Decision：`blocked-awaiting-user-approval`

Phase 6 proxy 已经通过，但不能替代真实 decompiler-output 实验。

当前 Phase 6 proxy 结果：

- Source-known functions：`38`
- Candidates：`430`
- Compile pass：`430`
- Paired cases：`38`
- Fixture-only AUC：`0.5000`
- Static structured proxy AUC：`0.9487`
- Dynamic Trace v3 AUC：`1.0000`
- v3 vs best non-oracle baseline delta：`+0.0513`
- V3 behavior-preserving rewrite false-positive rate：`0.0000`
- Real decompiler output available：`False`

解释：结果是正向的，而且是 full proxy，不是 smoke。但它仍是 `assembly_context_decompiler_like`，不是 Ghidra / RetDec / radare2 真实输出。CCF-A 主 claim 不能只靠这条证据。

## 本机工具状态

已确认可用：

- `/usr/bin/gcc`
- `/usr/bin/objdump`
- `/usr/bin/unzip`
- `/usr/bin/tar`
- `/usr/bin/docker`
- `/home/shx/miniconda3/bin/conda`
- `/home/shx/miniconda3/bin/mamba`

未找到：

- `ghidraRun`
- `ghidra-analyzeHeadless`
- `analyzeHeadless`
- `retdec-decompiler`
- `r2`
- `radare2`

Docker 本地镜像中也没有 Ghidra / RetDec / radare2 相关镜像。

APT 中存在 `radare2` candidate：`4.2.1+dfsg-2`，但尚未安装。

## 推荐路线

推荐分两步：

1. `install-radare2-smoke-first`
2. `install-ghidra-main-evidence`

原因：

- `radare2` 可能最快验证真实工具链入口，但 focal 的 r2 版本和 pseudo-C 能力未必足够论文主证据。
- Ghidra 的 headless decompiler 更适合作为 CCF-A 主实验，因为它是审稿人熟悉且可复现的真实 decompiler source。
- RetDec 可作为第二工具 robustness，但不建议作为第一步。

## 为什么不现在直接安装

安装会改变系统或用户环境，并且可能需要网络 / apt / 下载 release 包。按照项目协议，这一步需要用户明确批准后再执行。

## 通过标准

Phase 6R 成功 gate：

- 至少 `20` 个函数有真实 decompiler-output candidates。
- 至少 `50` 个 normalized candidates compile-pass。
- 至少 `10` 个 paired functions。
- Dynamic Trace v3 同时超过 fixture-only 和 static structured baseline。
- v3 over best non-oracle baseline delta `>= 0.05`。
- behavior-preserving false-positive rate `<= 10%`。
- 每个失败样本都有 failure taxonomy。

## 对 CCF-A 的影响

如果 Phase 6R 通过：

- Phase 5B 证明 source-known hard fixture-overfit semantic drift 上有明显 SOTA/baseline delta。
- Phase 6 proxy 证明 assembly-context decompiler-like full scale 上仍有 delta。
- Phase 6R 证明真实 decompiler output 上信号仍成立。
- 这三者合起来才更接近 CCF-A 主实验所需的“真实性 + full scale + baseline improvement”。

如果 Phase 6R 失败：

- 项目仍可写成 source-known localized semantic bug auditing，但不能把 decompiler-output realism 作为主贡献。
- 需要把 Phase 6R 失败拆成：decompiler output normalization 失败、candidate compile 失败、oracle/domain mismatch、或 v3 signal 不迁移。

## 下一条建议 prompt

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他目录，不要使用 subagent。
我批准执行 Phase 6R dependency plan。

先走 install-radare2-smoke-first 路线：
- 安装或启用 radare2；
- 只做真实工具 importability check；
- 不把 smoke 当 CCF-A 主结果；
- 通过后再讨论 Ghidra main evidence。
```

或者，如果你希望直接做主证据：

```text
项目目录：/home/shx/projects/binary_faithful_decompilation。
严格不要进入其他目录，不要使用 subagent。
我批准执行 Phase 6R dependency plan。

直接走 install-ghidra-main-evidence 路线：
- 安装或启用 Ghidra headless；
- 对 Phase 5 的 38 个函数跑 O0/O2 真实 decompiler-output full experiment；
- 复用 Phase 6 的 source-known oracle、baseline 和 v3 gate；
- 不启动 GPU。
```
