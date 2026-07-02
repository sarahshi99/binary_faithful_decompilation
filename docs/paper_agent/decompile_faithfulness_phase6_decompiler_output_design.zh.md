# Decompilation Faithfulness Phase 6 Decompiler-Output Feasibility

## 为什么仍然保留 source-known oracle

Phase 6 的目标是让 candidate 更接近真实 decompiler output，而不是把整个问题切换成 binary-only equivalence。

原始 source 仍然作为 oracle。这样可以把变量隔离清楚：

- Phase 5 测真实项目函数；
- Phase 6 测真实或近真实 decompiler-style candidates；
- 但 semantic judgment 仍然来自 source oracle。

如果同时去掉 source oracle，就会把工具可用性、binary lifting、equivalence checking、candidate parsing 和方法信号混成一个不可归因的大问题。

## 候选来源

优先顺序：

1. 本地已经安装的真实 decompiler output。
2. 使用 assembly / binary context 生成的 decompiler-like LLM candidates。
3. Phase 5 candidates 的多优化级别、decompiler-style rewrite 版本。

Phase 6 不自动安装 Ghidra、RetDec、radare2、angr、z3。需要安装时另写 dependency plan。

## 工具依赖策略

只做探测：

```bash
command -v ghidraRun
command -v retdec-decompiler
command -v r2
command -v objdump
```

解释：

- 有 Ghidra / RetDec / r2：可以进入真实 decompiler-output candidate import。
- 只有 `objdump`：可以做 assembly-context decompiler-like generation，但不能声称真实 decompiler-output。
- 都没有：输出 `needs-decompiler-dependency-plan`。

## False Positive Control

必须纳入 behavior-preserving rewrites。否则 v3 可能只是对代码形态变化敏感，而不是对语义错误敏感。

通过条件：

- behavior-preserving rewrite false-positive rate `<= 10%`；
- 或者每个 false positive 都能归因到 trace-domain 设计问题。

## Failure Taxonomy

每个失败候选都要归类：

- decompiler tool unavailable；
- decompiler syntax failure；
- candidate compile failure；
- undefined-behavior mismatch；
- oracle/domain mismatch；
- trace-domain miss；
- fixture-passing semantic drift；
- behavior-preserving rewrite false positive；
- baseline stronger than v3。

## 成功 Gate

Phase 6 pass 条件：

- 至少 `20` 个 source-known functions 有 decompiler-output 或 decompiler-like candidates；
- 至少 `50` 个 compile-pass candidates；
- 至少 `10` 个 paired functions；
- v3 超过 fixture-only 和 static-only baseline；
- behavior-preserving rewrite false-positive rate `<= 10%`，或误报均有具体原因；
- 如果本地生成 binary，结果按 optimization level 报告。

## 何时可以写进 CCF-A 主实验

只有在以下条件满足时，Phase 6 才能成为 CCF-A 主实验：

1. Phase 5 full-scale real-project transfer 已通过；
2. Phase 6 不只是 decompiler tool probe，而是真正有 compile-pass candidates；
3. v3 在 realistic candidates 上仍比 baseline 强；
4. failure taxonomy 能解释失败而不是只报 overall。

如果 Phase 6 只完成了工具探测或少量候选，它只能作为 feasibility，不够支撑主 claim。
