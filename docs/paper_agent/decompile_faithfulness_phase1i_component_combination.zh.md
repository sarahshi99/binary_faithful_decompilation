# Decompilation Faithfulness Phase 1I Component Combination Audit

## Question

在 8 个 source-known cases / 56 个 candidates 上，能否通过简单的 component-combination rule，把 Phase 1G/1H 的 borderline signal 稳定提升到可迁移水平？

## Dataset

- Cases：`8`
- Candidates：`56`
- Faithful candidates：`24`
- Plausible-wrong candidates：`32`
- Inputs：Phase 1H 的 `phase1e`、`phase1f`、`phase1g` per-opt records

## In-Sample Formula Scores

| Formula | Pairwise AUC |
|---|---:|
| `mean_slot_plus_range_0.10` | `0.7604` |
| `min_slot` | `0.7552` |
| `mean_slot` | `0.7500` |
| `mean_slot_plus_bigram_0.10` | `0.7500` |
| `mean_slot_plus_global_0.10` | `0.7500` |
| `mean_slot_plus_global_0.25` | `0.7500` |
| `mean_slot_plus_bigram_0.25` | `0.7396` |
| `mean_slot_plus_branch_return_0.10` | `0.7396` |
| `mean_slot_plus_range_0.25` | `0.7083` |
| `max_slot` | `0.6979` |
| `mean_slot_plus_branch_return_0.25` | `0.6979` |

## Leave-One-Case-Out

- Pairwise AUC：`0.6719`
- Verdict：`do-not-transfer-yet`

| Held-out case | Selected formula | Train AUC | Held-out AUC |
|---|---|---:|---:|
| `absdiff` | `mean_slot_plus_range_0.10` | `0.7619` | `0.7500` |
| `clamp8` | `mean_slot_plus_range_0.10` | `0.7738` | `0.6667` |
| `count_bits8` | `min_slot` | `0.7381` | `0.8750` |
| `gcd_positive` | `min_slot` | `0.7798` | `0.5833` |
| `is_power_of_two` | `mean_slot_plus_range_0.10` | `0.7500` | `0.8333` |
| `max3` | `mean_slot_plus_range_0.10` | `0.7857` | `0.5833` |
| `signum` | `min_slot` | `0.7917` | `0.5000` |
| `sum_to_n` | `min_slot` | `0.7798` | `0.5833` |

## Interpretation

这个结果是明确负结果。即使在 in-sample 情况下，最好的简单 formula 也只有 `0.7604`，只比 `min_slot=0.7552` 略高；一旦做 leave-one-case-out，AUC 掉到 `0.6719`。

这说明当前 representation / slot mapping 的问题不能靠小权重组合解决。`signum`、`gcd_positive`、`max3`、`sum_to_n` 的 held-out 表现都很弱，代表不同程序结构下的 failure mode 不一致。

## Verdict

不要进入 real-project transfer。下一步应重新设计 representation 或问题边界，例如：

- 把控制流路径和 return value 的绑定显式建模，而不是只看 flat binary feature bags。
- 把 behavior-preserving rewrite drift 和 localized semantic bug drift 分成两个阶段检测。
- 引入更强的 source-known oracle / symbolic trace / lightweight dynamic trace，再决定是否保留这个 paper direction。
