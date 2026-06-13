# Decompilation Faithfulness Phase 1B Realistic Negatives Audit

## Research Question

Can recompiled binary feature distance still rank faithful candidates above plausible-but-wrong candidates when the candidate set includes realistic manual rewrites and hard negatives?

## Dataset

- Cases: `3`
- Ranking candidates: `13`
- Faithful candidates: `6`
- Plausible-wrong candidates: `7`
- Equivalent or weak mutations excluded from ranking: `4`
- Compile failures excluded from ranking: `0`
- Compiler optimization: `O0`

## Metrics

- Top-1 faithful rate: `1.0000`
- Pairwise AUC: `0.5000`
- Verdict: `kill-core-method`

## Feature Set

Phase 1A.1 includes an operand-sensitive `instruction_signature_l1` component. This was added after the opcode/immediate/count-only metric missed the `return a - b` -> `return b - a` behavior-changing counterfactual.

## Mutation Buckets

| Mutation type | Candidate count | Mean distance |
|---|---:|---:|
| `constant` | 1 | 3.0000 |
| `manual_hard_negative` | 3 | 13.0000 |
| `predicate` | 2 | 4.0000 |
| `return_value` | 1 | 4.0000 |

## Kill Criterion

- Continue if `pairwise_auc >= 0.75` and `top1_faithful_rate >= 0.67`.
- Kill core method if `pairwise_auc < 0.60` or `top1_faithful_rate < 0.50`.
- Otherwise mark the signal inconclusive and add stronger candidates before method claims.

## Interpretation

The Phase 1B realistic-negative smoke fails the naive ranking gate: `pairwise_auc=0.5000`, even though `top1_faithful_rate=1.0000`.

The failure mode is informative. Behavior-preserving manual rewrites compile and pass the deterministic tests, but their recompiled binary feature distance is often larger than the distance of local plausible-wrong mutations. This means the current feature distance is closer to a same-implementation proximity score than a general semantic-faithfulness score.

This is negative evidence against using raw binary feature distance as a direct ranker over arbitrary C candidates. It does not kill the broader posterior-sketch idea, but it does mean the next method must separate:

- behavior faithfulness;
- binary-proximity to the original compiler output;
- source-level rewrite equivalence;
- slot-local feature deltas.

## Next Route

Do not start real-project transfer yet. First redesign the scoring protocol so realistic behavior-preserving rewrites are not treated as binary-faithful positives for a raw feature-distance ranker. The promising next direction is slot-local feature mismatch and calibration, not global source-candidate distance alone.
