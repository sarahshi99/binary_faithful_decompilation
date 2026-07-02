# Decompilation Faithfulness Phase 6R radare2 Smoke

- Verdict: `pass-phase6r-radare2-importability-smoke`
- Tool: `radare2`
- Tool path: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_tools/apt_radare2/root/usr/bin/radare2`
- Tool version: `radare2 4.2.1 0 @ linux-x86-64 git.4.2.1
commit: unknown build:`
- Toolchain label: `gcc-11.4.0`
- Binary compiler: `/usr/bin/gcc`
- Optimization levels: `['O0', 'O2']`
- Binaries: `76`
- Compile pass: `76`
- Symbol found: `76`
- Disassembly output count: `76`
- Pseudo-C output count: `76`
- Pseudo-C-like output count: `75`
- Compile-ready decompiler C count: `0`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_radare2_gcc11_smoke/records.jsonl`

## Failure Counts

| Category | Count |
|---|---:|
| `pseudo_c_not_compile_ready` | `1` |

## Interpretation

这是 Phase 6R 的真实工具链 importability smoke。`radare2` 已经能在用户态运行，并能对 Phase 5 的 source-known 函数二进制做符号定位、反汇编和 `pdc` pseudo-C 输出。

但是 `pdc` 输出是 pseudo-C，不是可直接编译的 C function candidate。因此这个结果只能证明真实工具入口可用，不能替代 Ghidra/RetDec 真实 decompiler-output full experiment，也不能作为 CCF-A 主结果。

下一步建议直接走 Ghidra main evidence：安装或启用 headless Ghidra，导出真实 decompiler C，再复用 Phase 6 的 source-known oracle、baseline 和 Dynamic Trace v3 gate。
