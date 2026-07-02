# Binary-Faithful Phase 16 Runtime And Risk Breakdown Plan

> REQUIRED: Use `superpowers:executing-plans` and
> `superpowers:test-driven-development`. Do not use subagents, Task/Spawn,
> dispatching-parallel-agents, `tool_search`, or multi-agent workflows. Work only
> under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Fill two paper-table gaps from Phase 15:

1. wall-clock runtime / compile-run cost;
2. per-risk-family breakdown.

## Inputs

- Phase 12 records:
  `analysis_outputs/decompile_faithfulness/phase12_unified_low_budget/*/records_budgeted.jsonl`
- Function manifests:
  - `docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json`
  - `docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json`
- Phase 10 dataset specs and records.
- Phase 11 fixture-neighbor input ordering.

## Outputs

- `analysis/decompile_faithfulness/run_phase16_runtime_risk_breakdown.py`
- `tests/test_decompile_faithfulness_phase16_runtime_risk.py`
- `docs/paper_agent/decompile_faithfulness_phase16_runtime_risk.json`
- `docs/paper_agent/decompile_faithfulness_phase16_runtime_risk.zh.md`

## Runtime Method

Rerun budget-8 `fixture_neighbor_first` for each current dataset. Measure:

- total wall seconds per dataset;
- mean and p95 seconds per candidate;
- candidate count;
- actual input evals;
- input evals per second.

This timing includes C harness compile and execution because `dynamic_trace.run_trace`
compiles and runs each candidate trace harness.

## Risk Breakdown

Using budget-8 Phase 12 records, group paired cases by manifest `risk_families`.
For each family, compute:

- case count;
- candidate count;
- paired case count;
- AUC;
- wrong-detection rate;
- missed wrong count.

## Gate

Pass if:

- runtime table is generated for all three current datasets;
- every dataset has measured candidate count > 0;
- every dataset has at least one risk-family row;
- no risk family with at least 3 paired cases has AUC < 0.90 or detection < 0.90.

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase16_runtime_risk
python -m py_compile analysis/decompile_faithfulness/run_phase16_runtime_risk_breakdown.py
python -m analysis.decompile_faithfulness.run_phase16_runtime_risk_breakdown
python -m json.tool docs/paper_agent/decompile_faithfulness_phase16_runtime_risk.json
git diff --check
```
