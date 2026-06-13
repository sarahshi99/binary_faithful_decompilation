# Decompilation Faithfulness Phase 1F Combined Multi-Opt Summary

## Dataset

- Cases：`5`
- Candidates：`35`
- Faithful candidates：`15`
- Plausible-wrong candidates：`20`
- Sources：Phase 1E expanded realistic candidates，加上 Phase 1F 新增的 `max3` 和 `sum_to_n` candidates

## Single-Opt Results

| Opt | Slot-concentration AUC | Raw global-distance AUC |
|---|---:|---:|
| `O0` | `0.9083` | `0.1750` |
| `O1` | `0.6583` | `0.5917` |
| `O2` | `0.6417` | `0.5583` |
| `O3` | `0.5667` | `0.6417` |

## Multi-Opt Results

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.8250` |
| mean slot concentration | `0.7667` |
| max slot concentration | `0.6917` |
| range slot concentration | `0.4250` |

## Interpretation

合并 5 个 source-known cases 后，没有任何单一 optimization level 足够稳定。`O0` 下 slot concentration 很强，但 raw global distance 严重失败；优化级别升高后，slot concentration 变弱，而 raw global distance 在部分新增 cases 上反而有补充信号。

最稳定的主信号仍然是 multi-opt conservative slot concentration：取 `O0/O1/O2/O3` 的最小 slot concentration 后，AUC 为 `0.8250`，超过 continue gate。下一轮实验应把它作为默认 suspiciousness score。

## Verdict

继续推进 multi-opt slot-local calibration，但在 real-project transfer 前继续扩大 source-known coverage。
