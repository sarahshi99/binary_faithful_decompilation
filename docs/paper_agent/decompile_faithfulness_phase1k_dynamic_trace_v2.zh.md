# Decompilation Faithfulness Phase 1K Dynamic Trace v2 Audit

## 数据集

- Cases: `8`
- Candidates: `56`
- Faithful candidates: `24`
- Plausible-wrong candidates: `32`

## Leave-One-Case-Out

- Pairwise AUC: `0.9531`
- Fixture collapse: `False`
- Verdict: `pass-dynamic-trace-v2-localized-bug`

| Held-out case | Selected formula | Train AUC | Held-out AUC |
|---|---|---:|---:|
| `absdiff` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `clamp8` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `count_bits8` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `gcd_positive` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `is_power_of_two` | `trace_mismatch_rate` | `0.9643` | `0.8750` |
| `max3` | `trace_mismatch_rate` | `0.9464` | `1.0000` |
| `signum` | `trace_mismatch_rate` | `0.9821` | `0.7500` |
| `sum_to_n` | `trace_mismatch_rate` | `0.9464` | `1.0000` |

## Hard Cases

| Case | Held-out AUC |
|---|---:|
| `signum` | `0.7500` |
| `gcd_positive` | `1.0000` |
| `max3` | `1.0000` |
| `sum_to_n` | `1.0000` |

## 解释

Dynamic Trace v2 使用 fixture-domain-aware generated inputs。它只从 source-known fixture 的参数值推断输入域，不读取 candidate label，也不根据 candidate output 反向选择输入。
