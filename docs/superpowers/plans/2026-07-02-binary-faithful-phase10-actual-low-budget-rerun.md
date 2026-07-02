# Binary-Faithful Phase 10 Actual Low-Budget Rerun Plan

> REQUIRED: Use `superpowers:executing-plans` during execution and
> `superpowers:test-driven-development` for new scripts. Do not use subagents,
> Task/Spawn, dispatching-parallel-agents, `tool_search`, or multi-agent
> workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Phase 9 used a proxy based on full-run `trace_mismatch_count / trace_input_count`.
Phase 10 turns that proxy into an actual rerun:

- generate the deterministic hard-input order;
- run only the first `max_budget` inputs once per candidate;
- compute metrics on prefixes `1, 2, 4, 8, 16`.

No GPU and no LLM candidate generation.

## Inputs

- Phase 7C2 static-hard public records.
- Phase 7E LLM public full+top-up combined records.
- Phase 6R Ghidra full records.

## Outputs

- `analysis/decompile_faithfulness/run_phase10_low_budget_rerun.py`
- `tests/test_decompile_faithfulness_phase10_low_budget.py`
- `docs/paper_agent/decompile_faithfulness_phase10_low_budget_rerun.json`
- `docs/paper_agent/decompile_faithfulness_phase10_low_budget_rerun.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase10_decision.zh.md`

## Metrics

For each dataset and budget:

- `mismatch_auc`: can the budgeted mismatch score rank wrong above faithful?
- `v3_auc`: same but using full trace-distance formula on the budget prefix.
- `wrong_detection_rate`: fraction of wrong candidates with at least one mismatch
  in the budget prefix.
- `wrong_detection_count`.
- `compile_pass_count`.
- `candidate_input_evals`: candidate count multiplied by budget.

## Gate

Pass if:

- Phase 7C2 budget-8 `mismatch_auc >= 0.98`.
- Phase 7C2 budget-8 `wrong_detection_rate >= 0.95`.
- Phase 6R Ghidra budget-8 `mismatch_auc >= 0.98`.
- Phase 6R Ghidra budget-8 `wrong_detection_rate >= 0.95`.

Verdicts:

- `pass-phase10-low-budget-rerun`
- `low-budget-rerun-partial`
- `low-budget-proxy-overestimated`

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase10_low_budget
python -m py_compile analysis/decompile_faithfulness/run_phase10_low_budget_rerun.py
python -m analysis.decompile_faithfulness.run_phase10_low_budget_rerun
python -m json.tool docs/paper_agent/decompile_faithfulness_phase10_low_budget_rerun.json
git diff --check
```
