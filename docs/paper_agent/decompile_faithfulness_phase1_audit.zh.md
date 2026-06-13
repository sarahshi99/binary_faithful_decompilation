# Decompilation Faithfulness Phase 1A Audit

## Research Question

在 source-known controlled benchmark 上，recompiled binary feature distance 能否把 faithful C candidate 排在 plausible-but-wrong C candidate 前面？

## Dataset

- Cases：`3`
- Ranking candidates：`7`
- Faithful candidates：`3`
- Plausible-wrong candidates：`4`
- 从 ranking 中排除的 equivalent 或 weak mutations：`4`
- 从 ranking 中排除的 compile failures：`0`
- Compiler optimization：`O0`

## Metrics

- Top-1 faithful rate：`1.0000`
- Pairwise AUC：`1.0000`
- Verdict：`continue`

## Feature Set

Phase 1A.1 加入了 operand-sensitive 的 `instruction_signature_l1` component。加入原因是初始 opcode/immediate/count-only metric 漏掉了 `return a - b` -> `return b - a` 这个 behavior-changing counterfactual。

## Mutation Buckets

| Mutation type | Candidate count | Mean distance |
|---|---:|---:|
| `constant` | 1 | 3.0000 |
| `predicate` | 2 | 4.0000 |
| `return_value` | 1 | 4.0000 |

## Kill Criterion

- 如果 `pairwise_auc >= 0.75` 且 `top1_faithful_rate >= 0.67`，继续推进。
- 如果 `pairwise_auc < 0.60` 或 `top1_faithful_rate < 0.50`，不把 recompile-guided binary feature feedback 作为核心方法。
- 其他情况标记为 inconclusive，需要加入更多 cases 和更强 negatives 后再决定。

## Interpretation

当前 controlled ranking signal 通过第一道 gate：`pairwise_auc=1.0000`，`top1_faithful_rate=1.0000`，verdict 为 `continue`。这说明在当前 source-known controlled mutations 上，recompiled binary feature distance 能把 faithful C candidate 排在 plausible-wrong candidate 前面。

需要保守解释：这个结果依赖 Phase 1A.1 新增的 `instruction_signature_l1`。它修复了初始特征对 return-value operand-order 错误的盲点，但这仍然只是 controlled mutation-style audit，不是完整 decompilation evidence。

下一步应加入 realistic LLM/decompiler negatives，检查这个信号是否仍然成立，再决定是否推进 slot-level localization 或真实项目迁移。

## Next Route

先收尾当前未提交的 Phase 1A.1 follow-up：重新跑 fresh verification，执行 local diff review fallback，然后做 focused commit。之后按串行方式进入 Phase 1B realistic negatives input support。Phase 1C slot localization 和真实项目迁移应等待 realistic negatives 证明该信号不只在 controlled mutations 上成立。
