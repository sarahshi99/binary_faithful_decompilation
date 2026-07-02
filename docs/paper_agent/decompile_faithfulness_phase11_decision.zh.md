# Decompilation Faithfulness Phase 11 Decision

## Verdict

`pass-ghidra-budget8-input-ordering`

## Result Meaning

Best budget-8 strategy: `fixture_neighbor_first` with `Mismatch AUC = 0.9891` and `Wrong detection rate = 0.9730`.

Best budget-16 strategy: `fixture_neighbor_first` with `Mismatch AUC = 1.0000` and `Wrong detection rate = 1.0000`.

`Mismatch AUC` measures whether wrong candidates are ranked above faithful ones.
`Wrong detection rate` measures how many wrong candidates are actually exposed by
at least one input in the budget prefix.

## Decision

Phase 11 fixes the Phase 10 Ghidra low-budget weakness. The paper can claim budget-8 dynamic re-execution across public static-hard, LLM-public, and Ghidra settings, with input ordering as a necessary component.

## Next Step

If Phase 11 passes budget-8, update the paper method to include input ordering
and move to broader SOTA comparison tables. If only budget-16 passes, frame the
method as adaptive-budget dynamic re-execution. If neither passes, design a
stronger generated-input policy before making CCF-A-level claims.
