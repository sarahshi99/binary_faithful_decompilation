# Decompilation Faithfulness Phase 1F New-Cases Multi-Opt Slot Calibration

## Question

在新增 `max3` 和 `sum_to_n` 两类 source-known C 结构后，multi-opt slot-local calibration 是否仍然成立？

## Dataset

- Cases：`2`
- Candidates：`14`
- Faithful candidates：`6`
- Plausible-wrong candidates：`8`
- Optimization levels：`O0`、`O1`、`O2`、`O3`

## Results

| Opt | Slot-concentration AUC | Raw global-distance AUC | Faithful mean | Wrong mean | Verdict |
|---|---:|---:|---:|---:|---|
| `O0` | `0.9167` | `0.2708` | `0.4440` | `0.7999` | `continue-slot-calibration` |
| `O1` | `0.5417` | `0.7292` | `0.5957` | `0.7448` | `inconclusive-or-redesign` |
| `O2` | `0.5625` | `0.6458` | `0.5813` | `0.7056` | `inconclusive-or-redesign` |
| `O3` | `0.2917` | `0.7292` | `0.6035` | `0.6710` | `inconclusive-or-redesign` |

## Multi-Opt Aggregation

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.7917` |
| mean slot concentration | `0.7083` |
| max slot concentration | `0.5833` |
| range slot concentration | `0.4167` |

## Interpretation

新增 cases 暴露了更强的 optimization sensitivity：单独看 `O3` 时 slot concentration 甚至反向，但 multi-opt conservative score 仍能恢复到 `0.7917`，勉强通过继续推进 gate。

这个结果支持当前路线，但也提醒我们不能只把 slot concentration 当成固定特征。下一步应把 multi-opt min score 作为主 suspiciousness，并继续扩大 source-known cases；同时记录 raw global distance，因为它在新增 cases 的优化级别下偶尔有补充信号，但在 Phase 1E 的 `O0` 下明显失败。
