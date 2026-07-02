# Binary-Faithful Phase 17 Operator Char Policy Plan

> REQUIRED: Use `superpowers:writing-plans`,
> `superpowers:test-driven-development`, and `superpowers:executing-plans`.
> Do not use subagents, Task/Spawn, dispatching-parallel-agents,
> `tool_search`, or multi-agent workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Phase 16 found a focused Ghidra weakness: budget-8
`fixture_neighbor_first` misses two wrong `ta_infix_precedence_two`
`fixture_ifchain` candidates. The missed case is a `char` operator-precedence
function whose fixtures include `$`, `*`, and `+`, but not equivalent operator
classes such as `/`, `%`, and `-`.

Phase 17 tests a generic fix:

`operator_char_class_first`

This is not a case-specific patch. It prioritizes common ASCII operator
characters for `char` parameters, then falls back to fixture-neighbor inputs and
the existing generated-input tail.

## Success Gate

Run a full CPU evaluation across all three current datasets:

1. `phase7c2_static_hard_public`
2. `phase7e_llm_public_full_topup`
3. `phase6r_ghidra_full`

Pass if:

- budget-8 AUC and wrong-detection do not regress versus Phase 12 on every
  dataset;
- Ghidra budget-8 AUC remains at least `0.98`;
- Ghidra budget-8 wrong-detection remains at least `0.95`;
- Ghidra large risk-family AUC remains at least `0.90`;
- Ghidra large risk-family wrong-detection reaches at least `0.90`;
- specifically, Ghidra `char_boundary` and `multi_arg` wrong-detection reach at
  least `0.90`.

## Outputs

- `analysis/decompile_faithfulness/run_phase17_operator_char_policy.py`
- `tests/test_decompile_faithfulness_phase17_operator_char_policy.py`
- `analysis_outputs/decompile_faithfulness/phase17_operator_char_policy/`
- `docs/paper_agent/decompile_faithfulness_phase17_operator_char_policy.json`
- `docs/paper_agent/decompile_faithfulness_phase17_operator_char_policy.zh.md`

## Implementation Steps

1. Keep the Phase 11 `operator_char_class_first` input policy surgical.
   Verify the focused precedence test passes.
2. Add a Phase 17 runner that:
   - invokes Phase 12 with `--strategy-id operator_char_class_first` into a
     Phase 17 output directory;
   - compares budget-8 results against the existing Phase 12 baseline;
   - computes Phase 16-style risk-family rows from the Phase 17 records;
   - compares those rows against existing Phase 16 risk rows;
   - writes one paper-facing JSON and Chinese markdown summary.
3. Add unit tests for verdict logic, metric deltas, and risk-row lookup.
4. Run full CPU evaluation.
5. Interpret whether this becomes the new default method or stays as an
   ablation/limitation note.

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase11_input_ordering
python -m unittest tests.test_decompile_faithfulness_phase17_operator_char_policy
python -m py_compile analysis/decompile_faithfulness/run_phase11_input_ordering.py
python -m py_compile analysis/decompile_faithfulness/run_phase17_operator_char_policy.py
python -m analysis.decompile_faithfulness.run_phase17_operator_char_policy
python -m json.tool docs/paper_agent/decompile_faithfulness_phase17_operator_char_policy.json
git diff --check
```
