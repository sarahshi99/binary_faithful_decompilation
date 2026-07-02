# Binary-Faithful Phase 9 Input-Budget Plan

> REQUIRED: Use `superpowers:executing-plans` during execution and
> `superpowers:test-driven-development` for new scripts. Do not use subagents,
> Task/Spawn, dispatching-parallel-agents, `tool_search`, or multi-agent
> workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Phase 8 showed that a generated-input fuzzing-style mismatch baseline reaches
the same AUC as Dynamic Trace v3 on current full records. Phase 9 asks a sharper
question:

If simple generated-input mismatch is enough for ranking, how many inputs are
needed, and is there any current hard family where v3's richer trace components
beat simple mismatch?

## Task 1: Input-budget Proxy Analyzer

Create:

- `analysis/decompile_faithfulness/run_phase9_input_budget.py`
- `tests/test_decompile_faithfulness_phase9_input_budget.py`
- `docs/paper_agent/decompile_faithfulness_phase9_input_budget.json`
- `docs/paper_agent/decompile_faithfulness_phase9_input_budget.zh.md`

Use existing records only. Do not rerun trace inputs in this task.

For each wrong candidate with `N = trace_input_count` and
`M = trace_mismatch_count`, estimate the probability that a budget of `k`
uniformly sampled generated inputs catches at least one mismatch:

`1 - C(N-M, k) / C(N, k)`

Compute for budgets:

- `1, 2, 4, 8, 16, 32, 64, 128`

Report:

- case-level AUC using budget-hit probability as score;
- wrong-candidate mean detection probability;
- wrong-candidate minimum detection probability;
- wrong-candidate p10 detection probability.

## Task 2: Hard-family Delta Scan

For each dataset, scan groups by:

- mutation type;
- risk family when present.

Report group AUC for:

- `fuzzing_mismatch_rate`;
- `fuzzing_any_mismatch`;
- `trace_abs_error_mean`;
- `trace_boundary_mismatch_rate`;
- `trace_sign_mismatch_rate`;
- `trace_zero_mismatch_rate`;
- `v3_trace_total`.

Gate:

- `v3_hard_family_delta_gate` passes if any group has
  `v3_trace_total - fuzzing_mismatch_rate >= 0.03`.

## Task 3: Decision

Create:

- `docs/paper_agent/decompile_faithfulness_phase9_decision.zh.md`

Possible claims:

- `low-budget-dynamic-execution-claim`: budget `k=8` reaches high expected
  wrong detection while v3 does not beat fuzzing mismatch by family.
- `v3-hard-family-claim`: at least one family shows v3-only margin.
- `needs-new-hard-semantic-benchmark`: no current family separates v3 from
  simple mismatch and budget curve is already saturated.

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase9_input_budget
python -m py_compile analysis/decompile_faithfulness/run_phase9_input_budget.py
python -m analysis.decompile_faithfulness.run_phase9_input_budget
python -m json.tool docs/paper_agent/decompile_faithfulness_phase9_input_budget.json
git diff --check
```
