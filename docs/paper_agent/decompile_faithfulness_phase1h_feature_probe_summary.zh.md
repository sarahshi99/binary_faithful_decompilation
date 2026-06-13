# Decompilation Faithfulness Phase 1H Feature Probe Summary

## Question

operand/order-sensitive binary features 能不能修复 Phase 1G 暴露的 blind spot，同时不误伤 behavior-preserving rewrites？

## Change

新增两个诊断 feature component：

- `instruction_bigram_l1`：相邻 normalized instruction signature 的顺序距离。
- `branch_return_immediate_pair_l1`：conditional jump 到附近 return-immediate 的配对距离。

这两个 component 会记录在 `FeatureDistance.components` 里，但当前不进入 primary slot-vote concentration score。

## Diagnostic Result

新 feature 能检测到最明确的 Phase 1G 盲点。对 `signum/manual_signum_reversed_signs` 的 `O0` 结果，旧的 bag-style components 全是 0：

| Component | Value |
|---|---:|
| `opcode_l1` | `0.0` |
| `instruction_signature_l1` | `0.0` |
| `immediate_symmetric_diff` | `0.0` |
| `instruction_bigram_l1` | `4.0` |
| `branch_return_immediate_pair_l1` | `4.0` |

## Combined Primary Score

因为新 components 只是 diagnostic-only，8-case primary score 保持 Phase 1G baseline：

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.7552` |
| mean slot concentration | `0.7500` |
| max slot concentration | `0.6979` |
| range slot concentration | `0.4271` |

## Interpretation

这个 probe 确认了 root cause：部分 semantic bugs 对 bag-of-instruction features 不可见，因为相同的 instruction signatures 出现在不同的控制流/顺序上下文里。

但把 order-sensitive components 直接手写进 slot-vote concentration 并不够安全，因为 behavior-preserving rewrites 也可能改变 instruction order。下一步应该做 source-known cases 上的 calibrated component-combination experiment，而不是继续手搓单一 vote 权重。

## Verdict

保留新 components 作为诊断证据；不要声称 Phase 1H 已经修复 primary score。
