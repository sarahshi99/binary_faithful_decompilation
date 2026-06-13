# Decompilation Faithfulness Phase 1B Realistic Negatives Audit

## Research Question

当 candidate set 加入 realistic manual rewrites 和 hard negatives 后，recompiled binary feature distance 是否仍能把 faithful candidates 排在 plausible-but-wrong candidates 前面？

## Dataset

- Cases：`3`
- Ranking candidates：`13`
- Faithful candidates：`6`
- Plausible-wrong candidates：`7`
- External candidates：`6`
- 从 ranking 中排除的 equivalent 或 weak mutations：`4`
- 从 ranking 中排除的 compile failures：`0`
- Compiler optimization：`O0`

## Metrics

- Top-1 faithful rate：`1.0000`
- Pairwise AUC：`0.5000`
- Verdict：`kill-core-method`

## Feature Set

使用 Phase 1A.1 的 operand-sensitive `instruction_signature_l1` feature set。

## Mutation Buckets

| Mutation type | Candidate count | Mean distance |
|---|---:|---:|
| `constant` | 1 | 3.0000 |
| `manual_hard_negative` | 3 | 13.0000 |
| `predicate` | 2 | 4.0000 |
| `return_value` | 1 | 4.0000 |

## Interpretation

Phase 1B realistic-negative smoke 没有通过 naive ranking gate：`pairwise_auc=0.5000`，虽然 `top1_faithful_rate=1.0000`。

失败模式很有信息量。行为保持的 manual rewrites 可以通过 deterministic tests，但它们重新编译后的 binary feature distance 往往比局部 plausible-wrong mutations 更大。这说明当前 feature distance 更像 same-implementation proximity score，而不是通用 semantic-faithfulness score。

这是否定证据：不能把 raw binary feature distance 直接当成任意 C candidate 的全局 ranker。它不否定 posterior-sketch 方向，但说明下一步必须区分：

- behavior faithfulness；
- binary-proximity to original compiler output；
- source-level rewrite equivalence；
- slot-local feature deltas。

## Next Route

暂时不要进入 real-project transfer。应先重新设计 scoring protocol，避免把 behavior-preserving rewrite 当作 raw feature-distance ranker 的 binary-faithful positive。更有希望的下一步是 slot-local feature mismatch 和 calibration，而不是单纯 global source-candidate distance。
