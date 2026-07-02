# Binary-Faithful Phase 11 Ghidra Input Ordering Plan

> REQUIRED: Use `superpowers:executing-plans` during execution and
> `superpowers:test-driven-development` for new scripts. Do not use subagents,
> Task/Spawn, dispatching-parallel-agents, `tool_search`, or multi-agent
> workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Phase 10 showed that actual low-budget reruns are strong on public static-hard
and LLM-public candidates, but Ghidra budget-8 fails:

- budget-8 `Mismatch AUC = 0.9565`
- budget-8 `Wrong detection rate = 0.9189`

The misses are concentrated in three Ghidra fixture-overfit candidates. Phase 11
tests whether deterministic input ordering can expose those errors earlier
without generating new candidates or using GPU.

## Inputs

- Ghidra full records:
  `analysis_outputs/decompile_faithfulness/phase6r_ghidra_full/records.jsonl`
- Function manifest:
  `docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json`
- Phase 10 low-budget implementation for metrics and rerun structure.

## Output Files

- `analysis/decompile_faithfulness/run_phase11_input_ordering.py`
- `tests/test_decompile_faithfulness_phase11_input_ordering.py`
- `docs/paper_agent/decompile_faithfulness_phase11_input_ordering.json`
- `docs/paper_agent/decompile_faithfulness_phase11_input_ordering.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase11_decision.zh.md`

## Strategies

Compare these deterministic input orders on the same candidate set:

1. `phase5b_original`: current Phase 10 order.
2. `fixture_neighbor_first`: put one-step neighborhoods around fixture inputs
   before the broad cross-product tail.
3. `boundary_first`: put domain boundary values, equal pairs, zeros, and
   char/range boundaries before the tail.
4. `mixed_boundary_neighbor`: interleave fixture-neighborhood and boundary
   inputs, then append the original tail.

No candidate source changes are allowed.

## Metrics

For budgets `[1, 2, 4, 8, 16]`:

- `mismatch_auc`: whether wrong candidates rank above faithful candidates.
- `wrong_detection_rate`: fraction of wrong candidates with at least one
  mismatch in the budget prefix.
- `missed_wrong_count`: wrong candidates still undetected.
- `avg_actual_inputs_per_candidate`: real execution cost.

## Gate

Primary pass:

- best strategy at budget-8 has `mismatch_auc >= 0.98`
- best strategy at budget-8 has `wrong_detection_rate >= 0.95`

Adaptive pass:

- best strategy at budget-16 has `mismatch_auc >= 0.98`
- best strategy at budget-16 has `wrong_detection_rate >= 0.97`

Verdicts:

- `pass-ghidra-budget8-input-ordering`
- `pass-ghidra-adaptive-budget16`
- `input-ordering-still-insufficient`

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase11_input_ordering
python -m py_compile analysis/decompile_faithfulness/run_phase11_input_ordering.py
python -m analysis.decompile_faithfulness.run_phase11_input_ordering
python -m json.tool docs/paper_agent/decompile_faithfulness_phase11_input_ordering.json
git diff --check
```
