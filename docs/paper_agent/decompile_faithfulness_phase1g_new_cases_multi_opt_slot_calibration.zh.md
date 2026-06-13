# Decompilation Faithfulness Phase 1G New-Cases Multi-Opt Slot Calibration

## Question

在新增 `signum`、`is_power_of_two`、`gcd_positive` 后，multi-opt slot-local calibration 是否仍然稳健？

## Dataset

- Cases：`3`
- Candidates：`21`
- Faithful candidates：`9`
- Plausible-wrong candidates：`12`
- Optimization levels：`O0`、`O1`、`O2`、`O3`

## Results

| Opt | Slot-concentration AUC | Faithful mean | Wrong mean | Verdict |
|---|---:|---:|---:|---|
| `O0` | `0.6250` | `0.5296` | `0.6513` | `weak-signal` |
| `O1` | `0.7639` | `0.3523` | `0.6525` | `continue-slot-calibration` |
| `O2` | `0.6250` | `0.3935` | `0.5695` | `weak-signal` |
| `O3` | `0.6250` | `0.3958` | `0.5695` | `weak-signal` |

## Multi-Opt Aggregation

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.6389` |
| mean slot concentration | `0.7222` |
| max slot concentration | `0.7083` |
| range slot concentration | `0.4306` |

## Per-Case Diagnosis

| Case | min AUC | mean AUC | max AUC |
|---|---:|---:|---:|
| `gcd_positive` | `0.5833` | `0.6667` | `0.5833` |
| `is_power_of_two` | `0.8333` | `0.8333` | `0.8333` |
| `signum` | `0.5000` | `0.6667` | `0.7083` |

## Interpretation

Phase 1G 是一个有价值的负结果：multi-opt min slot concentration 在新增 cases 上降到 `0.6389`，低于 continue gate。主要问题来自 `signum` 和 `gcd_positive`。其中 `signum` 暴露了一个明确盲点：返回常量符号互换这类错误可能在当前 binary feature + slot-vote 映射下得到很低 suspiciousness。

合并所有已有 8 cases 后，multi-opt min slot concentration AUC 为 `0.7552`，只刚刚越过 continue gate。也就是说方法没有被完全打掉，但已经不能继续只靠“扩大 case”推进；下一步应优先修 feature blind spot。

## Verdict

暂停 real-project transfer。下一步应做 Phase 1H：补强常量/操作数敏感特征，尤其是返回常量、条件跳转、compare immediate 和符号方向相关的 normalized instruction signature。
