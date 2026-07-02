# Decompilation Faithfulness Phase 6R Cross-toolchain Summary

- Verdict: `pass-phase6r-cross-toolchain-ghidra-plus-radare2-importability`
- Ghidra run count: `2`
- radare2 run count: `2`
- All Ghidra main gates pass: `True`
- Min Ghidra SOTA delta vs in-project baseline: `0.1576`
- External-paper SOTA claim ready: `False`
- External-paper SOTA blocker: Needs explicit related-work baselines and at least one compile-ready second decompiler beyond Ghidra; current summary is cross-toolchain robustness, not external-paper SOTA.

## Ghidra Main Evidence

| Toolchain | Candidates | Compile pass | Paired cases | Static AUC | V3 AUC | Delta | Norm/compile fail | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `default-gcc` | `228` | `166` | `26` | `0.8207` | `1.0000` | `0.1793` | `62` | `pass-phase6r-real-decompiler-output-main-evidence` |
| `gcc-9.4.0` | `228` | `166` | `26` | `0.8424` | `1.0000` | `0.1576` | `62` | `pass-phase6r-real-decompiler-output-main-evidence` |

## radare2 Importability

| Toolchain | Binaries | Symbols | Pseudo-C-like | Compile-ready C | Verdict |
|---|---:|---:|---:|---:|---|
| `gcc-11.4.0` | `76` | `76` | `75` | `0` | `pass-phase6r-radare2-importability-smoke` |
| `gcc-9.4.0` | `76` | `76` | `75` | `0` | `pass-phase6r-radare2-importability-smoke` |

## Interpretation

This is cross-toolchain robustness evidence. It strengthens the Ghidra-based claim by checking whether the result survives different binary-producing GCC versions. radare2 is kept as real-tool importability evidence because its `pdc` output is pseudo-C, not compile-ready C.

This still does not by itself establish external-paper SOTA. For that, the project needs explicit related-work baselines, at least one second compile-ready decompiler source, and a broader benchmark table.
