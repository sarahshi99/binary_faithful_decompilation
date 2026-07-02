# Decompilation Faithfulness Phase 6 Gate Decision

- Decision: `needs-decompiler-dependency-plan`
- Phase 6 verdict: `pass-phase6-decompiler-like-ccfa-proxy`
- Real decompiler output available: `False`
- Dynamic Trace v3 AUC: `1.0000`
- Best non-oracle baseline AUC: `0.9487`
- SOTA delta: `0.0513`

## Gate

| Gate | Passed |
|---|---:|
| `source_function_scale_gate` | `True` |
| `compile_pass_scale_gate` | `True` |
| `paired_function_gate` | `True` |
| `v3_beats_fixture_gate` | `True` |
| `v3_beats_static_gate` | `True` |
| `behavior_preserving_fp_gate` | `True` |

## Claim Boundary

This run passes the assembly-context decompiler-like proxy gate, but real decompiler-output transfer still requires Ghidra/RetDec/r2 or equivalent.

## Next Step

如果目标是 CCF-A 主实验，下一步不是继续堆更多 synthetic if-chain，而是写 Phase 6R dependency plan：安装/固定至少一个真实 decompiler，导入真实 decompiler output，再复用本轮同一套 source-known oracle、v3/baseline、false-positive gate。
