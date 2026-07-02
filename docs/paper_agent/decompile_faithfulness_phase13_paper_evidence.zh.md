# Decompilation Faithfulness Phase 13 Paper Evidence Synthesis

- Verdict: `paper-evidence-ready-for-method-table`
- Method: `fixture-neighbor-first low-budget dynamic re-execution`
- Scope: `source-known localized semantic drift auditing`
- Default budget: `8`

## Main Paper Table Draft

| Dataset | Candidates | Paired cases | Fixture AUC | Static AUC | Original-order budget-8 AUC | Unified budget-8 AUC | Wrong detection rate | Avg inputs | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `phase6r_ghidra_full` | `166` | `26` | `0.5000` | `0.8207` | `0.9565` | `0.9891` | `0.9730` | `6.97` | `2` |
| `phase7c2_static_hard_public` | `478` | `50` | `0.9211` | `0.6806` | `0.9956` | `1.0000` | `1.0000` | `6.64` | `0` |
| `phase7e_llm_public_full_topup` | `136` | `24` | `0.9741` | `0.7759` | `0.9828` | `1.0000` | `1.0000` | `6.69` | `0` |

## Supported Claims

- Budget-8 targeted dynamic re-execution passes current public static-hard, LLM-public, and Ghidra gates.
- Fixture-neighbor input ordering improves low-budget detection with negligible average-input overhead.
- The method is stronger than fixture-only and static structured legacy baselines in the current source-known setting.
- The clean paper scope is source-known localized semantic drift auditing, not decompiler generation quality.

## Unsupported Claims

- Universal external benchmark SOTA over decompilation-generation papers.
- Cross-decompiler robustness beyond the current Ghidra-centered compile-ready evidence.
- Replacing full semantic equivalence checking in unbounded programs.
- Dynamic Trace v3 scoring components beat a strong generated-input mismatch baseline on current data.

## CCF-A Gap

- Add direct public-benchmark rows or clearly justify the CodeFuse/public subset as the paper benchmark.
- Add cost/runtime table, not only input-count table.
- Add confidence intervals for Phase12 unified budget-8 deltas.
- Add failure-case taxonomy for the remaining Ghidra budget-8 misses.
- Add second compile-ready decompiler or explicitly state Ghidra-centered scope.
- Write related-work comparison as validation/auditing, not generation leaderboard.

## Interpretation

The evidence now supports a low-budget targeted dynamic re-execution auditor.
The strongest paper story is not that a complex v3 scoring formula beats every
strong baseline; Phase 8 showed that simple generated-input mismatch is already
very strong. The new contribution is the low-budget targeted input policy and a
clean source-known semantic-drift auditing setup where fixture/static checks miss
localized errors.
