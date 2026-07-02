# Boundary-Preserving Dynamic Traces for Source-Known Decompilation Faithfulness Auditing

## Abstract

Existing decompiler and LLM-decompiler evaluations often emphasize compilation success, fixture re-execution, static similarity, readability, or benchmark-level functional correctness. These signals are useful, but they can miss localized semantic drift in source-known C candidates: a candidate may pass a small fixture suite while still changing behavior around sign, zero, bit width, range endpoints, or loop boundaries. This paper studies a narrower setting: source-known, recompilable, bounded-input localized semantic bug auditing. We propose a boundary-preserving generated dynamic trace policy that compares an original source function and a decompiler/LLM-generated candidate over generated inputs while protecting semantically important boundary probes. Across curated cases, generated candidates, and a source-known small-function transfer audit, the method outperforms lightweight static/binary motifs and avoids fixture-only collapse. The current evidence supports a semantic auditing signal, not a binary-only verifier; real-project and decompiler-output transfer remain required for a full CCF-A submission.

## 1. Introduction

Decompilation faithfulness is difficult to evaluate because syntactic similarity, readability, and compilation success are not semantic correctness. A candidate can look plausible and pass a small fixture suite while still being wrong on boundary-localized behavior.

This work focuses on source-known auditing rather than binary-only equivalence. We do not claim binary-only equivalence checking or whole-program decompilation verification. The studied setting is source-known, recompilable, bounded-input, localized semantic bug auditing, where original source acts as the trace oracle.

Contributions:

1. We identify a failure mode of lightweight static/binary motifs and fixture-only validation for localized semantic faithfulness auditing.
2. We propose a boundary-preserving generated dynamic trace policy for source-known, bounded-input C functions.
3. We provide a staged empirical audit from curated cases to source-known generated candidates, with explicit gates for real-project and decompiler-output transfer.

The paper must state early that Phase 1-3 are not enough for a CCF-A final claim. They support the method direction and define the next full-scale gates.

## 2. Motivation And Problem Definition

Problem setting:

- Original source function `f` is available and recompilable.
- Candidate function `g` is produced by a decompiler, an LLM decompiler, or a controlled mutation/generation pipeline.
- Input domain `D` is bounded and explicit.
- Fixture set `F` is available but may be incomplete.
- Generated trace set `T` is used to compare `f` and `g`.
- Boundary probes `B` protect semantic boundaries such as zero, sign, bit width, range endpoints, division/modulo corners, and loop termination points.

Goal:

Rank or flag candidates by localized semantic drift without collapsing to fixture-only validation and without relying on brittle static/binary motifs.

Motivating examples:

- `count_bits8`: fixture-passing candidate counts 16 bits instead of 8 bits.
- `safe_div_round0`: generated Phase 3 candidate passes fixtures but mismatches trace behavior.
- Manual stress examples: `sat_add8`, `parity8`, `mod3_sum_digits`, and `safe_div_round0` expose fixture-passing wrong candidates.

## 3. Method

Dynamic Trace v1:

- Generates mixed-domain inputs.
- Fails on domain-sensitive cases such as positive-only GCD because out-of-domain inputs create false positives.

Dynamic Trace v2:

- Infers domain constraints from fixture argument values.
- Avoids label leakage and candidate-output leakage.
- Improves `gcd_positive` held-out AUC from `0.5000` to `1.0000`.

Dynamic Trace v3:

- Preserves boundary probes such as `0`, `-1`, and `1`.
- Avoids the v2 blind spot where fixture exclusion may accidentally exclude important boundary points.
- Does not use `fixture_mismatch_rate` as the primary score.

Score:

`S(f, g, T)` measures mismatch rate and mismatch severity between source outputs and candidate outputs over generated trace inputs.

Design principle:

Boundary preservation is not a heuristic patch. It encodes the empirical observation that localized decompilation bugs often sit at semantic boundaries.

## 4. Experimental Setup

Completed experiments:

| Experiment | Scale | Purpose |
|---|---:|---|
| Phase 1 static/binary motifs | curated cases | negative baseline |
| Phase 1K-v2 dynamic trace | 8 cases / 56 candidates | method discovery |
| Phase 1L ablation/leakage | 8 cases / 56 candidates | leakage control |
| Phase 2 generated candidates | 100 generations / 63 compile-pass | generated candidate distribution |
| Phase 3 source selection | 12 functions / 3289 subsets | selection robustness |
| Phase 3 CPU audit | 12 functions / 28 candidates | source-known transfer readiness |
| Phase 3 GPU smoke/top-up | 47 generated candidates / 28 compile-pass | generated candidate smoke |

Full-vs-smoke boundary:

- Phase 2 can be described as a full gate for the 8 curated cases.
- Phase 3 source selection reduces one-shot selection risk.
- Phase 3 GPU remains smoke/top-up scale and cannot be the final CCF-A main experiment.

Required full-scale experiments:

- Phase 5 real-project source-known transfer.
- Phase 6 decompiler-output or decompiler-like feasibility.

## 5. Results

Negative results:

| Signal | Result | Interpretation |
|---|---:|---|
| naive binary distance | AUC `0.5000` | no meaningful ranking |
| static component combination | LOCO AUC `0.6719` | borderline |
| structural binding | LOCO AUC `0.6823` | still insufficient |

Positive results:

| Signal | Result | Interpretation |
|---|---:|---|
| Dynamic Trace v2 | LOCO AUC `0.9531` | main signal appears |
| Phase 1L leakage audit | no leakage found | v2 is not fixture-only collapse |
| Phase 2 v3 | AUC `1.0000` | boundary trace fixes zero/sign blind spots |
| Phase 3 CPU | AUC `1.0000` | source-known transfer readiness |
| Phase 3 GPU | AUC `1.0000` | positive generated-candidate smoke |

Result interpretation:

The completed experiments support a strong paper seed. They do not yet establish CCF-A-level external validity.

## 6. Analysis

Why small-pool and smoke evidence is not enough:

- Small curated functions are good for mechanism discovery.
- Smoke runs are good for failure detection.
- CCF-A claims require full-scale evidence over real-project source-known functions and decompiler-output candidates.

SOTA positioning:

This paper should not claim that it generates better decompiled code than SOTA LLM or industrial decompilers. The claim is that it provides a better auditing signal for localized semantic drift in a source-known bounded setting.

Baseline families:

- fixture-only or re-execution-only validation;
- lightweight static/binary similarity;
- v1 mixed-domain trace;
- v2 domain-aware trace;
- v3 boundary-preserving trace;
- symbolic/concolic or fuzzing-inspired checks when available;
- LLM judge or LLM self-repair baselines when relevant;
- real decompiler benchmark metrics for Phase 6.

Expected CCF-A proof obligation:

Dynamic Trace v3 must beat the best non-oracle auditing baseline on real-project source-known transfer and remain useful for decompiler-output or decompiler-like candidates.

## 7. Threats To Validity

We do not claim binary-only equivalence checking or whole-program decompilation verification. The studied setting is source-known, recompilable, bounded-input, localized semantic bug auditing, where original source acts as the trace oracle.

Threats:

- Current function pools are small.
- Phase 3 GPU paired cases are limited.
- Candidate generation may bias the bug distribution.
- Boundary trace may miss semantic drift not expressible through current input domains.
- Behavior-preserving rewrites may create false positives if the trace domain is wrong.
- SOTA progress must be measured against auditing baselines, not decompiler generation quality alone.

Mitigations:

- Phase 5 full-scale real-project source-known transfer.
- Phase 6 decompiler-output feasibility.
- Baseline matrix.
- Risk-family breakdown.
- False-positive controls with behavior-preserving rewrites.

## 8. Related Work

Initial literature anchors to verify before final submission:

- LLM4Decompile and Decompile-Eval: LLM-based decompilation with recompilability and re-executability metrics.
- ISSTA 2024 decompiler evaluation: semantic evaluation of industrial decompilers.
- DecompileBench and Decompile-Bench: real-world decompilation benchmarks emphasizing semantic fidelity and functionality correctness.
- Semantic equivalence checking of decompiled binaries: heavier equivalence-oriented direction.
- Symbolic execution and fuzzing for semantic checking: potential stronger baselines or complementary methods.

Verified starting sources:

- LLM4Decompile / Decompile-Eval: `https://arxiv.org/abs/2403.05286`
- ISSTA 2024, Evaluating the Effectiveness of Decompilers: `https://2024.issta.org/details/issta-2024-papers/40/Evaluating-the-Effectiveness-of-Decompilers`
- DecompileBench, ACL Findings 2025: `https://aclanthology.org/2025.findings-acl.1194/`
- Decompile-Bench, NeurIPS 2025 Datasets and Benchmarks: `https://proceedings.neurips.cc/paper_files/paper/2025/hash/079cf13ae174c31f148207d94d213bdc-Abstract-Datasets_and_Benchmarks_Track.html`

The final paper needs a systematic related-work table that separates generation systems from auditing/evaluation signals.

## 9. Conclusion

Boundary-preserving generated dynamic traces are a promising source-known auditing signal for localized semantic bugs in decompiler/LLM-generated C candidates. Phase 1-3 show that the signal is stronger than lightweight static/binary motifs and can expose fixture-passing semantic drift. The next step is not to overclaim. The next step is to run full-scale Phase 5/6 experiments that prove whether the signal remains useful on real-project source-known functions and decompiler-output candidates.

## Appendix A. Function And Candidate Manifests

Include:

- Phase 1 curated cases.
- Phase 2 generated candidate manifest.
- Phase 3 source pool.
- Phase 3 candidate pool.
- Future Phase 5 real-project function manifest.
- Future Phase 6 decompiler-output candidate manifest.

## Appendix B. Additional Ablations

Include:

- static-only min-slot;
- v1 mixed-domain trace;
- v2 domain-aware trace;
- v3 boundary-preserving trace;
- fixture-only oracle upper bound;
- trace budget sensitivity;
- boundary policy ablations;
- compiler optimization level robustness;
- behavior-preserving rewrite false-positive controls.
