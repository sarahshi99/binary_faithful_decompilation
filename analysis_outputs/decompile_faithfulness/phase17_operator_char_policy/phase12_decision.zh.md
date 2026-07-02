# Decompilation Faithfulness Phase 12 Decision

## Verdict

`partial-unified-low-budget-eval`

## Decision

Phase 12 is promising but not enough for a single universal budget-8 claim. The paper should either use dataset-specific/adaptive input ordering or add another input policy.

## Next Step

If Phase 12 passes, update the method description and SOTA comparison tables to
use `fixture_neighbor_first` as the default low-budget input policy. If it is
partial or failed, inspect the failing datasets before writing the paper claim.
