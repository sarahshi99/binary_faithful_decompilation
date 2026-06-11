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

- Top-1 faithful rate: `0.6667`
- Pairwise AUC: `0.8750`
- Verdict: `inconclusive`

## Mutation Buckets

| Mutation type | Candidate count | Mean distance |
|---|---:|---:|
| `constant` | 1 | 1.0000 |
| `predicate` | 2 | 2.0000 |
| `return_value` | 1 | 0.0000 |

## Kill Criterion

- Continue if `pairwise_auc >= 0.75` and `top1_faithful_rate >= 0.67`.
- Kill core method if `pairwise_auc < 0.60` or `top1_faithful_rate < 0.50`.
- Otherwise mark the signal inconclusive and add stronger candidates before method claims.

## Interpretation

The controlled ranking signal is inconclusive. Add more cases and harder negatives before deciding whether to keep or kill the method.

## Observed Blind Spots

The current feature set assigns zero mean distance to these wrong-candidate buckets: `return_value`. This means opcode/immediate/count features miss at least one semantic error family and should not be treated as a complete binary-faithfulness metric.

This is a controlled mutation-style audit, not a full decompilation system. It only tests whether the proposed binary feature distance contains enough faithfulness signal to justify the next experiment.
