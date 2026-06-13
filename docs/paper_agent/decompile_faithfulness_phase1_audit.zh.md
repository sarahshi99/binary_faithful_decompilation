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

Phase 1B realistic negatives 已经补跑：加入 manual faithful rewrites 和 manual hard negatives 后，`pairwise_auc=0.5000`，naive global feature-distance ranker 失败。Phase 1C controlled slot localization 显示 `hit_at_1=1.0000`。Phase 1D slot-calibration audit 在同一 realistic candidates 上于 `O0` 恢复信号，但 `O2` follow-up 降到 `0.6667`。Phase 1E 进一步扩大到 21 个 realistic candidates 并扫 `O0/O1/O2/O3`：single-opt slot AUC 为 `0.9028/0.7361/0.6944/0.7500`，raw global-distance AUC 为 `0.1111/0.5000/0.5000/0.5833`。使用 multi-opt conservative score，也就是取 `O0/O1/O2/O3` 的最小 slot concentration，AUC 达到 `0.8472`。因此下一步应把 multi-opt slot-local calibration 实现为主 suspiciousness score，再考虑 real-project transfer。
