# Decompilation Faithfulness Phase 1J 结构绑定审计

## 数据集

- Cases: `8`
- Candidates: `56`
- Faithful candidates: `24`
- Plausible-wrong candidates: `32`

## 基线

- Phase 1G multi-opt min slot AUC: `0.7552`
- Phase 1I best in-sample AUC: `0.7604`
- Phase 1I leave-one-case-out AUC: `0.6719`

## Leave-One-Case-Out

- Pairwise AUC: `0.6823`
- Verdict: `do-not-transfer-yet`

| Held-out case | Selected formula | Train AUC | Held-out AUC |
|---|---|---:|---:|
| `absdiff` | `mean_slot` | `0.7500` | `0.7500` |
| `clamp8` | `mean_slot` | `0.7619` | `0.6667` |
| `count_bits8` | `min_slot` | `0.7381` | `0.8750` |
| `gcd_positive` | `min_slot` | `0.7798` | `0.5833` |
| `is_power_of_two` | `min_slot` | `0.7440` | `0.8333` |
| `max3` | `mean_slot` | `0.7619` | `0.6667` |
| `signum` | `min_slot` | `0.7917` | `0.5000` |
| `sum_to_n` | `min_slot` | `0.7798` | `0.5833` |

## Hard Cases

| Case | Held-out AUC |
|---|---:|
| `signum` | `0.5000` |
| `gcd_positive` | `0.5833` |
| `max3` | `0.6667` |
| `sum_to_n` | `0.5833` |

## 解释

这是 source-known kill-gate，不是 real-project transfer。标签只用于离线评估和 LOCO 公式选择；结构特征抽取只读取 object 文件路径。

## 后续路线

结构绑定 gate 未通过。Phase 1J 应记录为 lightweight static binary motifs 的负结果；在 real-project transfer 前应先转向 dynamic trace、symbolic trace，或重新收窄为更明确的 localized-bug 问题。
