# Binary-Faithful Phase 6 Decompiler-Output Feasibility Design

> **Superpowers mode:** Use `superpowers:executing-plans` only for execution. Do not use subagents, dispatching-parallel-agents, Task/Spawn, reviewer subagents, `tool_search`, or multi-agent workflows. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Evaluate source-known dynamic trace auditing on real decompiler-output or decompiler-like candidates.

## Scope Boundary

Original source remains the oracle. Phase 6 does not claim binary-only equivalence. It only tests whether candidates that are closer to real decompiler output can still be audited by Dynamic Trace v3.

## Why Phase 6 Exists

Phase 5 tests real-project source-known transfer. Phase 6 tests candidate realism.

The key reviewer question is:

> Does the signal survive when candidates come from real decompilers or realistic decompiler-style generation, rather than manual or prompt-designed bugs?

## Candidate Sources

Preferred order:

1. Real decompiler output from tools already installed locally.
2. Decompiler-like LLM candidates generated from binary/assembly/decompiler context.
3. Existing Phase 5 candidates compiled at multiple optimization levels and rewritten into decompiler-like style.

No heavyweight dependency installation should happen in Phase 6 without a separate dependency plan.

## Tool Feasibility

Probe only:

```bash
command -v ghidraRun
command -v retdec-decompiler
command -v r2
command -v objdump
```

If no decompiler is available, Phase 6 can produce `needs-decompiler-dependency-plan` and stop. `objdump` alone is enough for binary/assembly context generation, but not enough to claim real decompiler-output evaluation.

## Success Gate

Phase 6 passes if:

- at least `20` source-known functions have decompiler-output or decompiler-like candidates;
- at least `50` compile-pass candidates are evaluated;
- at least `10` functions have faithful/wrong pairs;
- Dynamic Trace v3 beats fixture-only and static-only baselines;
- behavior-preserving rewrite false-positive rate is `<= 10%`, or every false positive has a documented trace-domain cause;
- results are reported by optimization level when binaries are generated locally.

## Failure Taxonomy

Every candidate failure must be assigned to one of:

- decompiler tool unavailable;
- decompiler syntax failure;
- candidate compile failure;
- undefined-behavior mismatch;
- oracle/domain mismatch;
- trace-domain miss;
- fixture-passing semantic drift;
- behavior-preserving rewrite false positive;
- baseline stronger than v3.

## CCF-A Interpretation

Phase 6 is necessary for CCF-A credibility because it connects the audit signal to decompiler-output realism. It is not sufficient by itself unless Phase 5 has already established full-scale source-known transfer.

## Output

Expected outputs:

- `docs/paper_agent/decompile_faithfulness_phase6_tool_feasibility.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase6_candidate_manifest.json`
- `docs/paper_agent/decompile_faithfulness_phase6_result_analysis.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase6_gate_decision.zh.md`

## Design Self-Review

Scope check: Phase 6 remains source-known and bounded.

Dependency check: tool installation is explicitly outside this plan.

SOTA check: Phase 6 compares auditing signal quality against baselines on realistic candidates; it does not claim to beat SOTA decompiler generation systems.
