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

- Top-1 faithful rate：`0.6667`
- Pairwise AUC：`0.8750`
- Verdict：`inconclusive`

## Mutation Buckets

| Mutation type | Candidate count | Mean distance |
|---|---:|---:|
| `constant` | 1 | 1.0000 |
| `predicate` | 2 | 2.0000 |
| `return_value` | 1 | 0.0000 |

## Kill Criterion

- 如果 `pairwise_auc >= 0.75` 且 `top1_faithful_rate >= 0.67`，继续推进。
- 如果 `pairwise_auc < 0.60` 或 `top1_faithful_rate < 0.50`，不把 recompile-guided binary feature feedback 作为核心方法。
- 其他情况标记为 inconclusive，需要加入更多 cases 和更强 negatives 后再决定。

## Interpretation

当前 controlled ranking signal 是 `inconclusive`。`pairwise_auc=0.8750` 说明特征距离对部分 plausible-wrong candidates 有明显排序信号；但 `top1_faithful_rate=0.6667` 没有越过计划中的保守阈值。

更重要的是，records 显示当前朴素 feature set 能捕捉部分 predicate 和 constant 错误，但对 `return a - b` 变成 `return b - a` 这类 return-value 语义错误给出了 `distance=0.0`。这说明当前特征还不能覆盖所有 binary-faithfulness 错误，下一步不能直接声称方法成立。

这是 controlled mutation-style audit，不是完整 decompilation 系统。它只检验 proposed binary feature distance 是否有足够信号，值得进入下一阶段实验。
