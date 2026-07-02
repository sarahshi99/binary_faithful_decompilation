# Decompilation Faithfulness Phase 8 SOTA Hardening

- Verdict: `strong-baseline-erases-v3-extra-margin`
- Bootstrap iterations: `2000`
- Seed: `20260702`
- Interpretation: Dynamic Trace v3 keeps the legacy fixture/static margin, but generated-input fuzzing-style re-execution reaches the same AUC on the current records. The paper should claim dynamic re-execution evidence, not v3 component SOTA margin, unless a harder dataset shows v3-only gains.

## Point Estimates

| Dataset | Paired cases | Fixture AUC | Static AUC | Fuzz mismatch AUC | Fuzz any AUC | V3 AUC | V3 - legacy best | V3 - strong best |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `50` | `0.9218` | `0.6831` | `1.0000` | `1.0000` | `1.0000` | `0.0782` | `0.0000` |
| `phase7e_llm_public_full_topup` | `24` | `0.9741` | `0.7759` | `1.0000` | `1.0000` | `1.0000` | `0.0259` | `0.0000` |
| `phase6r_ghidra_full` | `26` | `0.5000` | `0.8207` | `1.0000` | `1.0000` | `1.0000` | `0.1793` | `0.0000` |
| `phase6r_ghidra_gcc9_full` | `26` | `0.5000` | `0.8424` | `1.0000` | `1.0000` | `1.0000` | `0.1576` | `0.0000` |

## Delta CI

| Dataset | V3 - legacy best CI95 | V3 - strong best CI95 | Strong best baseline |
|---|---:|---:|---|
| `phase7c2_static_hard_public` | `0.0394`, `0.1276` | `0.0000`, `0.0000` | `fuzzing_mismatch_rate` |
| `phase7e_llm_public_full_topup` | `0.0000`, `0.0714` | `0.0000`, `0.0000` | `fuzzing_mismatch_rate` |
| `phase6r_ghidra_full` | `0.1087`, `0.2619` | `0.0000`, `0.0000` | `fuzzing_mismatch_rate` |
| `phase6r_ghidra_gcc9_full` | `0.0870`, `0.2381` | `0.0000`, `0.0000` | `fuzzing_mismatch_rate` |

## Gate

| Gate | Passed |
|---|---:|
| `phase7c2_present` | `True` |
| `legacy_delta_ci_lower_gt_zero` | `True` |
| `strong_baseline_not_erased` | `False` |

## Interpretation

Phase 8 separates two claims:

1. Dynamic re-execution versus legacy fixture/static baselines.
2. Dynamic Trace v3's richer components versus a stronger generated-input fuzzing-style baseline.

If `fuzzing_mismatch_rate` or `fuzzing_any_mismatch` reaches the same AUC as
`v3_trace_total`, then the current evidence supports dynamic re-execution as the
core mechanism, but not a separate SOTA-margin claim for v3's extra trace
components.
