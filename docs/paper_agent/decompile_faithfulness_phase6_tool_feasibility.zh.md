# Phase 6 Tool Feasibility

## Tool Probe

| Tool | Path |
|---|---|
| `ghidraRun` | `not found` |
| `retdec-decompiler` | `not found` |
| `r2` | `not found` |
| `radare2` | `not found` |
| `objdump` | `/usr/bin/objdump` |
| `gcc` | `/usr/bin/gcc` |

## Available Candidate Sources

本机没有发现 Ghidra、RetDec、radare2/r2 等真实 decompiler 工具；`objdump` 和 `gcc` 可用。因此本轮可以做 full-scale `assembly_context_decompiler_like` 候选，但不能声称已经评估真实 decompiler output。

## Dependency Decision

Phase 6 不安装新依赖。真实 decompiler-output import 需要单独 dependency plan，至少安装并固定 Ghidra/RetDec/r2 之一，然后重新跑真实输出版本。

## Verdict

`ready-for-assembly-context-decompiler-like-generation`
