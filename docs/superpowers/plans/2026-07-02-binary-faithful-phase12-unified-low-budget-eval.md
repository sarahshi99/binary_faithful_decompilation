# Binary-Faithful Phase 12 Unified Low-Budget Evaluation Plan

> REQUIRED: Use `superpowers:executing-plans` during execution and
> `superpowers:test-driven-development` for new scripts. Do not use subagents,
> Task/Spawn, dispatching-parallel-agents, `tool_search`, or multi-agent
> workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Phase 11 fixed the Phase 10 Ghidra budget-8 weakness by using
`fixture_neighbor_first` input ordering. Phase 12 checks whether that can be
presented as a unified final method across all current datasets, instead of
mixing different input orders per dataset.

No GPU, no LLM generation, no new candidates.

## Inputs

- Phase 7C2 static-hard public records.
- Phase 7E LLM public full+top-up records.
- Phase 6R Ghidra full records.
- Phase 10 original low-budget result JSON for baseline deltas.
- Phase 11 input-ordering implementation.

## Outputs

- `analysis/decompile_faithfulness/run_phase12_unified_low_budget_eval.py`
- `tests/test_decompile_faithfulness_phase12_unified_low_budget.py`
- `docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.json`
- `docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase12_decision.zh.md`

## Method

Run the same strategy, `fixture_neighbor_first`, on all three datasets and
compute budget curves for `[1, 2, 4, 8, 16]`.

Report deltas against Phase 10's original input order at budget-8:

- AUC delta.
- Wrong-detection-rate delta.
- Actual input cost delta.

## Gate

For each dataset at budget-8:

- `mismatch_auc >= 0.98`
- `wrong_detection_rate >= 0.95`

Verdicts:

- `pass-unified-budget8-low-budget-eval`
- `partial-unified-low-budget-eval`
- `fail-unified-low-budget-eval`

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase12_unified_low_budget
python -m py_compile analysis/decompile_faithfulness/run_phase12_unified_low_budget_eval.py
python -m analysis.decompile_faithfulness.run_phase12_unified_low_budget_eval
python -m json.tool docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.json
git diff --check
```
