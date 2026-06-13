# Decompilation Faithfulness Phase 1E Expanded Slot-Calibration Audit

## Question

扩大 realistic candidate set，并扫 `O0/O1/O2/O3` 后，slot-vote concentration 是否仍能区分 behavior-preserving rewrites 和局部 semantic bugs？

## Dataset

- Cases：`3`
- Candidates：`21`
- Faithful candidates：`9`
- Plausible-wrong candidates：`12`
- Candidate source：扩展的 manual realistic rewrites 和 hard negatives
- Optimization levels：`O0`、`O1`、`O2`、`O3`

## Results

| Opt | Slot-concentration AUC | Raw global-distance AUC | Faithful mean | Wrong mean | Verdict |
|---|---:|---:|---:|---:|---|
| `O0` | `0.9028` | `0.1111` | `0.5036` | `0.7481` | `continue-slot-calibration` |
| `O1` | `0.7361` | `0.5000` | `0.3429` | `0.6606` | `weak-signal` |
| `O2` | `0.6944` | `0.5000` | `0.3435` | `0.6589` | `weak-signal` |
| `O3` | `0.7500` | `0.5833` | `0.3621` | `0.6483` | `continue-slot-calibration` |

## Per-Case AUC

| Opt | `absdiff` | `clamp8` | `count_bits8` |
|---|---:|---:|---:|
| `O0` | `0.7500` | `1.0000` | `0.9583` |
| `O1` | `0.6667` | `0.6667` | `0.8750` |
| `O2` | `0.6667` | `0.6667` | `0.7500` |
| `O3` | `0.6667` | `0.6667` | `0.9167` |

## Multi-Opt Aggregation

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.8472` |
| mean slot concentration | `0.8056` |
| max slot concentration | `0.7639` |
| range slot concentration | `0.4306` |

## Interpretation

扩展实验确认了 Phase 1D 的方向：raw global binary distance 不能直接作为任意 C rewrite 的 faithful ranking score，但 slot-local concentration 仍然保留了有用信号。

主要弱点是 optimization sensitivity。单独看 `O1/O2` 会低于强 gate，原因主要是一些 faithful rewrite 在优化后也会呈现局部集中的 binary delta。把 `O0/O1/O2/O3` 的 slot concentration 做保守聚合，取每个 candidate 的最小值，可以把 AUC 恢复到 `0.8472`。

## Verdict

继续推进 multi-opt slot-local calibration。下一步不要把单一 optimization-level score 作为最终 suspiciousness；应把它作为诊断指标，并用 multi-opt conservative score 作为进入 real-project transfer 前的主信号。
