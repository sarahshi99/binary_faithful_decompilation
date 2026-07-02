# Decompilation Faithfulness Phase 1K Dynamic Trace Audit

## 数据集

- Cases: `8`
- Candidates: `56`
- Faithful candidates: `24`
- Plausible-wrong candidates: `32`

## Leave-One-Case-Out

- Pairwise AUC: `0.8750`
- Fixture collapse: `False`
- Verdict: `borderline-dynamic-trace`

| Held-out case | Selected formula | Train AUC | Held-out AUC |
|---|---|---:|---:|
| `absdiff` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |
| `clamp8` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |
| `count_bits8` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |
| `gcd_positive` | `trace_mismatch_rate` | `0.9464` | `0.5000` |
| `is_power_of_two` | `trace_total_plus_min_slot_0.10` | `0.9167` | `0.7500` |
| `max3` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |
| `signum` | `trace_total_plus_min_slot_0.10` | `0.9167` | `0.7500` |
| `sum_to_n` | `trace_total_plus_min_slot_0.10` | `0.8810` | `1.0000` |

## Hard Cases

| Case | Held-out AUC |
|---|---:|
| `signum` | `0.7500` |
| `gcd_positive` | `0.5000` |
| `max3` | `1.0000` |
| `sum_to_n` | `1.0000` |

## 解释

这是 Phase 1K 三路线 scout 的 Route A。主分数使用 generated trace inputs；fixture-test 行为只作为诊断字段，用来判断结果是否退化成已有测试 oracle。
