# Decompilation Faithfulness Phase 6R Ghidra Full

- Verdict: `pass-phase6r-real-decompiler-output-main-evidence`
- Candidates: `228`
- Ghidra decompiled count: `228`
- Compile pass count: `166`
- Source functions: `38`
- Paired case count: `26`
- Fixture-only AUC: `0.5000`
- Static structured proxy AUC: `0.8207`
- Dynamic Trace v3 AUC: `1.0000`
- SOTA delta vs best non-oracle baseline: `0.1793`
- V3 behavior-preserving rewrite FP rate: `0.0000`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_ghidra_full/records.jsonl`

## Gate

| Gate | Passed |
|---|---:|
| `source_function_scale_gate` | `True` |
| `compile_pass_scale_gate` | `True` |
| `paired_function_gate` | `True` |
| `v3_beats_fixture_gate` | `True` |
| `v3_beats_static_gate` | `True` |
| `sota_delta_gate` | `True` |
| `behavior_preserving_fp_gate` | `True` |

## Failure Taxonomy

| Category | Count |
|---|---:|
| `ghidra_or_normalization_failure` | `62` |
| `fixture_passing_semantic_drift` | `74` |
| `behavior_preserving_rewrite_false_positive` | `0` |
| `trace_domain_miss` | `0` |

## Interpretation

这是真实 Ghidra headless decompiler-output full run。候选先被编译成二进制对象，再由 Ghidra 12.1.2 导出 C，随后做轻量 normalization 并用 source-known oracle、fixture-only、static structured proxy 和 Dynamic Trace v3 评估。

## CCF-A Self-check

- Full evidence: this is the planned Phase 6R full run over all `38` Phase5 functions, two optimization levels, and three candidate roles. It is no longer a smoke run.
- Baseline/SOTA status: `SOTA delta` here means improvement over the strongest in-project non-oracle baseline in this run, not an external-paper SOTA claim.
- Current limitation: `62` Ghidra outputs did not become compile-ready C under the current lightweight normalization, so external-tool generalization still needs a follow-up cross-tool / normalization-ablation phase.
