# Decompilation Faithfulness Phase 7D Second Decompiler Decision

- Verdict: `blocked-awaiting-second-decompiler-approval`
- Ready second-decompiler tool count: `0`
- Available tool count: `2`
- Ghidra first decompiler ready: `True`
- radare2 importability-only: `True`
- Recommended next action: No second compile-ready decompiler is available locally. Keep Ghidra as the main real-decompiler evidence, keep radare2 as importability-only, and proceed to Phase 7E LLM-generated/LLM-judge public benchmark baselines on GPU 2/3 unless the user approves installing RetDec, rev.ng, Binary Ninja, or Hex-Rays.

## Tool Matrix

| Tool | Available | Compile-ready C candidate | Evidence kind | Path/module | Reason |
|---|---:|---:|---|---|---|
| `Ghidra` | `True` | `False` | `first_compile_ready_decompiler` | `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/ghidra_12.1.2_PUBLIC/support/analyzeHeadless` | Already used as Phase 6R main decompiler; not counted as the second decompiler. |
| `radare2/r2 pdc` | `True` | `False` | `real_tool_importability_only` | `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_tools/apt_radare2/root/usr/bin/radare2` | Project Phase 6R shows pdc pseudo-C/importability, but not compile-ready C function candidates. |
| `RetDec` | `False` | `False` | `candidate_second_decompiler` | `` | Could be a second compile-ready C decompiler if installed and its output normalizes/compiles. |
| `rev.ng` | `False` | `False` | `candidate_second_decompiler` | `` | Could provide decompiled C/IR if installed; not available in this environment. |
| `angr AIL` | `False` | `False` | `candidate_evaluable_ir` | `angr:not found; ailment:not found; claripy:not found; capstone:not found` | Even if available, this would likely be evaluable IR rather than compile-ready C; current modules are absent. |
| `Binary Ninja` | `False` | `False` | `candidate_second_decompiler_or_mlil` | `binaryninja:not found` | License/tool not detected; MLIL/HLIL may be useful, but compile-ready C is not assumed. |
| `Hex-Rays / IDA` | `False` | `False` | `candidate_second_decompiler` | `` | Could be strong second decompiler evidence if licensed and headless export is available. |

## Interpretation

Phase 7D does not currently provide a second compile-ready decompiler. Ghidra remains the first real-decompiler main evidence; radare2 remains real-tool importability evidence because its `pdc` output is pseudo-C rather than compile-ready C.

For the CCF-A/SOTA path, the next practical step is Phase 7E: run LLM-generated candidates or an LLM judge baseline on the public CodeFuse subset using GPU 2/3, unless a new decompiler dependency is approved.
