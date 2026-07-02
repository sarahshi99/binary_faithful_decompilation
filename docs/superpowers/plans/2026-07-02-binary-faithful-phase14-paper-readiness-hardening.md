# Binary-Faithful Phase 14 Paper Readiness Hardening Plan

> REQUIRED: Use `superpowers:executing-plans` during execution and
> `superpowers:test-driven-development` for new scripts. Do not use subagents,
> Task/Spawn, dispatching-parallel-agents, `tool_search`, or multi-agent
> workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Turn Phase 12/13 from a strong method table into paper-ready evidence:

1. bootstrap confidence intervals for Phase 12;
2. runtime/cost summary;
3. remaining miss taxonomy;
4. experiment-section draft text.

## Inputs

- `docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.json`
- `analysis_outputs/decompile_faithfulness/phase12_unified_low_budget/*/records_budgeted.jsonl`
- Phase 10 and Phase 13 summary documents.

## Outputs

- `analysis/decompile_faithfulness/run_phase14_paper_readiness.py`
- `tests/test_decompile_faithfulness_phase14_paper_readiness.py`
- `docs/paper_agent/decompile_faithfulness_phase14_paper_readiness.json`
- `docs/paper_agent/decompile_faithfulness_phase14_paper_readiness.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase14_experiment_section_draft.md`

## Metrics

- Case-level bootstrap CI for budget-8 AUC.
- Case-level bootstrap CI for wrong-detection rate.
- Missed wrong candidates by dataset/case/candidate type.
- Average actual inputs per candidate.
- Approximate candidate input evaluations.

## Gate

Phase 14 is paper-hardening, not method discovery.

Pass if:

- all Phase 12 budget-8 AUC CI lower bounds are `>= 0.95`;
- all Phase 12 budget-8 detection CI lower bounds are `>= 0.90`;
- remaining misses are enumerated and explained;
- draft experiment text states the claim boundary clearly.

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase14_paper_readiness
python -m py_compile analysis/decompile_faithfulness/run_phase14_paper_readiness.py
python -m analysis.decompile_faithfulness.run_phase14_paper_readiness
python -m json.tool docs/paper_agent/decompile_faithfulness_phase14_paper_readiness.json
git diff --check
```
