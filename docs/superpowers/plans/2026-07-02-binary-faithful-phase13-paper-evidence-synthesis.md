# Binary-Faithful Phase 13 Paper Evidence Synthesis Plan

> REQUIRED: Use `superpowers:executing-plans` during execution and
> `superpowers:test-driven-development` for new scripts. Do not use subagents,
> Task/Spawn, dispatching-parallel-agents, `tool_search`, or multi-agent
> workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Convert Phase 8/10/12 results into a paper-facing evidence package:

- what the main method is now;
- which claims are supported;
- which claims are not supported;
- what table should appear in the paper;
- what remains before a CCF-A submission.

## Inputs

- Phase 8 SOTA hardening JSON.
- Phase 10 actual low-budget rerun JSON.
- Phase 12 unified low-budget evaluation JSON.

## Outputs

- `analysis/decompile_faithfulness/run_phase13_paper_evidence_synthesis.py`
- `tests/test_decompile_faithfulness_phase13_paper_evidence.py`
- `docs/paper_agent/decompile_faithfulness_phase13_paper_evidence.json`
- `docs/paper_agent/decompile_faithfulness_phase13_paper_evidence.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase13_decision.zh.md`

## Claim Rules

Supported if Phase 12 passes:

- low-budget targeted dynamic re-execution;
- source-known localized semantic drift auditing;
- superiority over fixture/static legacy baselines;
- budget-8 effectiveness across current public static-hard, LLM-public, and
  Ghidra datasets.

Not supported:

- v3 scoring components beat strong fuzzing-style mismatch baseline;
- decompiler generation SOTA;
- universal external benchmark SOTA;
- cross-decompiler robustness beyond current Ghidra-centered evidence.

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase13_paper_evidence
python -m py_compile analysis/decompile_faithfulness/run_phase13_paper_evidence_synthesis.py
python -m analysis.decompile_faithfulness.run_phase13_paper_evidence_synthesis
python -m json.tool docs/paper_agent/decompile_faithfulness_phase13_paper_evidence.json
git diff --check
```
