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

First close the uncommitted Phase 1A.1 follow-up with fresh verification, local diff review fallback, and a focused commit. Then proceed serially to Phase 1B realistic negatives input support. Phase 1C slot localization and real-project transfer should wait until realistic negatives confirm that the signal survives beyond controlled mutations.
