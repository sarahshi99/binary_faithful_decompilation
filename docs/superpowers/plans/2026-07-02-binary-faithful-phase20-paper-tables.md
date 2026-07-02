# Binary-Faithful Phase 20 Paper Tables Plan

> REQUIRED: Use `superpowers:executing-plans` and
> `superpowers:verification-before-completion`. Do not use subagents, Task/Spawn,
> dispatching-parallel-agents, `tool_search`, or multi-agent workflows. Work only
> under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Turn Phase 18/19 final-method evidence into paper-ready table drafts.

## Outputs

- `analysis/decompile_faithfulness/run_phase20_paper_tables.py`
- `tests/test_decompile_faithfulness_phase20_paper_tables.py`
- `docs/paper_agent/decompile_faithfulness_phase20_paper_tables.md`

## Tables

1. Main result table: fixture/static baselines versus final budget-8 auditor.
2. Stability/runtime table: CI, input cost, wall-clock runtime.
3. Ablation table: fixture-neighbor old default, Phase 17 negative result, Phase 18 final policy.
4. Ghidra risk-family table: final large risk rows.

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase20_paper_tables
python -m py_compile analysis/decompile_faithfulness/run_phase20_paper_tables.py
python -m analysis.decompile_faithfulness.run_phase20_paper_tables
git diff --check
```
