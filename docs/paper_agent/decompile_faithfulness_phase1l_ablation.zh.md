# Decompilation Faithfulness Phase 1L Ablation / Leakage Audit

## 数据集

- Cases: `8`
- Candidates: `56`
- Verdict: `pass-phase1l-ablation`

## 消融结果

| Variant | Feature | AUC | gcd_positive | signum | max3 | sum_to_n |
|---|---|---:|---:|---:|---:|---:|
| `mixed_domain_v1_trace_mismatch` | `trace_mismatch_rate` | `0.8906` | `0.5000` | `0.7500` | `1.0000` | `1.0000` |
| `domain_aware_v2_trace_mismatch` | `trace_mismatch_rate` | `0.9531` | `1.0000` | `0.7500` | `1.0000` | `1.0000` |
| `domain_aware_v2_trace_total` | `trace_total` | `0.9531` | `1.0000` | `0.7500` | `1.0000` | `1.0000` |
| `fixture_only_oracle` | `fixture_mismatch_rate` | `1.0000` | `1.0000` | `1.0000` | `1.0000` | `1.0000` |
| `static_only_min_slot` | `min_slot` | `0.8021` | `0.6667` | `0.4583` | `1.0000` | `0.8333` |

## 泄漏审计

- Domain inference source: `fixture_argument_values_only`
- Uses labels: `False`
- Uses candidate outputs: `False`
- Uses candidate ids: `False`
- V2 identical to fixture-only: `False`
- Domain-filtered cases: `count_bits8, gcd_positive`
- Leakage verdict: `no-label-or-output-leakage-found`

## 解释

Phase 1L 是只读消融，不重新编译、不重新运行 trace。它比较 v1 mixed-domain、v2 domain-aware、fixture-only oracle 和 static-only min_slot，目的是确认 v2 的提升不是 fixture oracle collapse，也不是 label / candidate-output leakage。
