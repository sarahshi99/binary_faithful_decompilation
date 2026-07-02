# Decompilation Faithfulness Phase 7 Benchmark Feasibility

- Verdict: `ready-public-benchmark-import`
- Benchmark count: `5`
- Available count: `1`
- Format identified count: `1`
- Network used: `False`
- Dependency install used: `False`

## Availability Matrix

| Benchmark | Available | Format identified | Source-known possible | Compile harness needed | Recommended next action |
|---|---:|---:|---:|---:|---|
| `Decompile-Eval / HumanEval-style` | `False` | `False` | `True` | `True` | request approval to download or point Codex to a local benchmark checkout |
| `ExeBench-style` | `False` | `False` | `True` | `True` | request approval to download or point Codex to a local benchmark checkout |
| `DecompileBench` | `False` | `False` | `True` | `True` | request approval to download or point Codex to a local benchmark checkout |
| `CodeFuse-DeBench` | `True` | `True` | `True` | `True` | import local benchmark with a dedicated adapter |
| `Decompile-Bench` | `False` | `False` | `True` | `True` | request approval to download or point Codex to a local benchmark checkout |

## Interpretation

This preflight only scans local project paths. It does not download benchmarks, install dependencies, or use GPU.

If the verdict is `blocked-needs-benchmark-download-approval`, Phase 7 cannot yet claim public benchmark alignment. The next step is to approve one benchmark acquisition route or provide a local checkout path.
