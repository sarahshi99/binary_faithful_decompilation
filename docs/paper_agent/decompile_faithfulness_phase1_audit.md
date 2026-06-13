# Decompilation Faithfulness Phase 1A Audit

## Research Question

Can recompiled binary feature distance rank faithful C candidates above plausible-but-wrong C candidates in a controlled source-known benchmark?

## Dataset

- Cases: `3`
- Ranking candidates: `7`
- Faithful candidates: `3`
- Plausible-wrong candidates: `4`
- Equivalent or weak mutations excluded from ranking: `4`
- Compile failures excluded from ranking: `0`
- Compiler optimization: `O0`

## Metrics

- Top-1 faithful rate: `1.0000`
- Pairwise AUC: `1.0000`
- Verdict: `continue`

## Feature Set

Phase 1A.1 includes an operand-sensitive `instruction_signature_l1` component. This was added after the opcode/immediate/count-only metric missed the `return a - b` -> `return b - a` behavior-changing counterfactual.

## Mutation Buckets

| Mutation type | Candidate count | Mean distance |
|---|---:|---:|
| `constant` | 1 | 3.0000 |
| `predicate` | 2 | 4.0000 |
| `return_value` | 1 | 4.0000 |

## Kill Criterion

- Continue if `pairwise_auc >= 0.75` and `top1_faithful_rate >= 0.67`.
- Kill core method if `pairwise_auc < 0.60` or `top1_faithful_rate < 0.50`.
- Otherwise mark the signal inconclusive and add stronger candidates before method claims.

## Interpretation

The controlled ranking signal passes the first gate. The next step is to add realistic LLM/decompiler negatives before making paper-level claims.

This is a controlled mutation-style audit, not a full decompilation system. It only tests whether the proposed binary feature distance contains enough faithfulness signal to justify the next experiment.

## Next Route

Phase 1B realistic negatives show that the naive global feature-distance ranker fails on behavior-preserving rewrites. Phase 1D slot calibration recovers signal at O0 but weakens at O2. Phase 1E expands to 21 realistic candidates across `O0/O1/O2/O3`: single-opt slot AUCs are `0.9028/0.7361/0.6944/0.7500`, while raw global-distance AUCs are `0.1111/0.5000/0.5000/0.5833`. A multi-opt conservative score using the minimum slot concentration reaches `0.8472`. Phase 1F adds `max3` and `sum_to_n`; combined across 5 cases and 35 candidates, multi-opt min slot concentration reaches `0.8250`. Continue with multi-opt slot-local calibration, but broaden source-known coverage before real-project transfer.
