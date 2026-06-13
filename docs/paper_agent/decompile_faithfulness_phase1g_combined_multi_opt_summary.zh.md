# Decompilation Faithfulness Phase 1G Combined Multi-Opt Summary

## Dataset

- Cases：`8`
- Candidates：`56`
- Faithful candidates：`24`
- Plausible-wrong candidates：`32`
- Sources：Phase 1E expanded candidates、Phase 1F new cases，以及 Phase 1G 的 `signum` / `is_power_of_two` / `gcd_positive`

## Single-Opt Results

| Opt | Slot-concentration AUC | Raw global-distance AUC |
|---|---:|---:|
| `O0` | `0.8021` | `0.1615` |
| `O1` | `0.6979` | `0.5260` |
| `O2` | `0.6354` | `0.5365` |
| `O3` | `0.5885` | `0.5938` |

## Multi-Opt Results

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.7552` |
| mean slot concentration | `0.7500` |
| max slot concentration | `0.6979` |
| range slot concentration | `0.4271` |

## Interpretation

合并 8 cases 后，multi-opt min slot concentration 仍然勉强超过 continue threshold，但安全边际很小。Phase 1G 说明当前 feature mapping 会漏掉一部分返回常量和符号方向错误。

Raw global distance 仍然不能作为主 ranker：它在 `O0` 下严重失败，在优化级别下也没有稳定变强。

## Verdict

不要开始 real-project transfer。下一步应做 Phase 1H feature-blind-spot repair，重点补强 operand/constant-sensitive signatures，然后再继续扩大迁移复杂度。
