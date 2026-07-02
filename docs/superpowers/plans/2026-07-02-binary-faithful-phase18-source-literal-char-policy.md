# Binary-Faithful Phase 18 Source Literal Char Policy Plan

> REQUIRED: Use `superpowers:writing-plans`,
> `superpowers:test-driven-development`, and `superpowers:executing-plans`.
> Do not use subagents, Task/Spawn, dispatching-parallel-agents,
> `tool_search`, or multi-agent workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Phase 17 showed a negative result: blindly putting common operator characters
first fixes `ta_infix_precedence_two`, but regresses broader char/boundary
coverage by pushing useful fixture-neighbor probes out of budget 8.

Phase 18 tests a more defensible source-known policy:

`source_literal_char_interleave`

For `char` parameters, extract character literals from the original source and
interleave those probes with fixture-neighbor probes. This keeps the original
localized-boundary behavior while adding source-semantic coverage for operators
that appeared in code but were absent from fixtures.

## Success Gate

Pass if, on the same three full datasets:

- budget-8 AUC and wrong-detection do not regress versus Phase 12;
- Ghidra budget-8 AUC remains at least `0.98`;
- Ghidra budget-8 wrong-detection remains at least `0.95`;
- Ghidra large risk-family AUC remains at least `0.90`;
- Ghidra large risk-family wrong-detection reaches at least `0.90`;
- Ghidra `char_boundary` and `multi_arg` wrong-detection reach at least `0.90`.

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase11_input_ordering
python -m unittest tests.test_decompile_faithfulness_phase18_source_literal_char_policy
python -m py_compile analysis/decompile_faithfulness/run_phase11_input_ordering.py
python -m py_compile analysis/decompile_faithfulness/run_phase18_source_literal_char_policy.py
python -m analysis.decompile_faithfulness.run_phase18_source_literal_char_policy
python -m json.tool docs/paper_agent/decompile_faithfulness_phase18_source_literal_char_policy.json
git diff --check
```
