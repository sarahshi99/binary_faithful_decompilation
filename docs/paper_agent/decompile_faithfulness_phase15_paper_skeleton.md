# Source-Literal-Aware Dynamic Re-Execution for Source-Known Decompilation Faithfulness Auditing

## Abstract

Decompiler and LLM-decompiler evaluations often rely on recompilability, fixture re-execution, static similarity, or benchmark-level functionality checks. These signals are useful, but they can miss localized semantic drift: a candidate may pass available tests while changing behavior around boundary inputs, argument interactions, character classes, or operator-precedence corner cases. This paper studies a deliberately scoped setting: source-known, recompilable, bounded-input auditing of localized semantic drift in C candidates. We propose source-literal-aware fixture-neighbor low-budget dynamic re-execution, which compares the original source function and a candidate over a deterministic prefix of generated inputs near fixtures and source-level character literals. Across public static-hard candidates, LLM-generated public candidates, and real Ghidra decompiler outputs, a budget of eight generated inputs achieves AUC and wrong-detection rate 1.0000 on all three datasets, with case-level bootstrap CI95 [1.0000, 1.0000] and zero missed wrong candidates. The evidence supports a low-budget source-known auditing method, not a general binary-only verifier or a decompiler-generation SOTA claim.

## 1. Introduction

Semantic faithfulness is a central problem in decompilation evaluation. Decompiled or LLM-generated C can compile, look plausible, and pass a small fixture suite while still being wrong on nearby or boundary inputs. This is especially problematic for localized semantic drift: small changes in comparison operators, argument order, branch constants, bit-width assumptions, range endpoints, character classes, or precedence rules may remain invisible to shallow test suites.

This paper focuses on an auditing problem rather than a generation problem. Given an original source function `f`, a candidate C function `g`, and a bounded input domain, we ask whether a lightweight dynamic signal can expose semantic drift that fixture-only and static similarity checks miss. The setting is intentionally source-known: the original source acts as the oracle. This restriction makes the method unsuitable as a general binary-only verifier, but it matches source-known benchmark construction, decompiler evaluation pipelines, and regression auditing workflows where original source or trusted reference implementations are available.

Our main observation is that many plausible wrong candidates overfit the visible fixtures. A cheap way to stress this failure mode is not to sample broadly, but to execute fixture-neighbor inputs first. Character-heavy functions need one extra source-known cue: source literals such as `'*'`, `'/'`, `'%'`, `'+'`, and `'-'` often define semantic classes that fixtures under-cover. The final method therefore interleaves fixture-neighbor probes with character literals extracted from the original source.

The current paper contribution should be stated as:

1. We characterize why lightweight static/binary motifs and fixture-only checks are insufficient for localized decompilation faithfulness auditing.
2. We propose source-literal-aware fixture-neighbor low-budget dynamic re-execution as a source-known semantic auditing signal.
3. We evaluate the method across public static-hard candidates, LLM-generated public candidates, and real Ghidra outputs, including full budget-8 evaluation, case-level bootstrap intervals, runtime, risk-family breakdown, and negative ablations.

Non-goals must be explicit:

- We do not claim binary-only semantic equivalence checking.
- We do not claim decompiler generation SOTA over systems such as LLM4Decompile or DecompileBench-style generation leaderboards.
- We do not claim that richer Dynamic Trace v3 scoring components beat a strong generated-input mismatch baseline on the current data.
- We do not claim broad cross-decompiler robustness beyond the current Ghidra-centered compile-ready evidence.

## 2. Problem Definition

### Setting

Let `f` be a trusted original C function and `g` be a candidate C function produced by a decompiler, LLM, rewrite, or controlled candidate generator. Let `F = {(x_i, f(x_i))}` be the fixture set and let `D` be a bounded input domain inferred from the function signature, fixture values, and benchmark metadata.

The auditor constructs a deterministic generated-input list:

`T = [t_1, t_2, ..., t_k]`, where each `t_i in D`.

At budget `b`, the auditor executes:

`f(t_1...t_b)` and `g(t_1...t_b)`.

The primary score is the budgeted mismatch signal:

`S_b(f, g) = (1 / b) * sum_i 1[f(t_i) != g(t_i)]`.

The candidate is considered detected as wrong if any mismatch appears in the budget prefix.

### Task

The task is not to prove equivalence. The task is to rank or flag candidate functions that exhibit localized semantic drift under bounded generated inputs, while controlling cost and avoiding fixture-only collapse.

### Metrics

- AUC: whether wrong candidates rank above faithful candidates within paired cases.
- Wrong-detection rate: fraction of wrong candidates with at least one mismatch in the budget prefix.
- Average actual inputs: input-evaluation cost proxy.
- Runtime: wall-clock compile/run time in the current trace harness.
- Miss taxonomy: which wrong candidates remain undetected at budget 8.

## 3. Method

### 3.1 From Static Motifs to Dynamic Auditing

Early experiments showed that raw global binary feature distance and lightweight static motifs are brittle. Behavior-preserving rewrites can look far away statically, while localized semantic bugs can look close. This motivates using behavior rather than structure as the primary auditing signal.

### 3.2 Source-Literal-Aware Fixture-Neighbor Policy

The final method uses `source_literal_char_interleave` ordering:

1. Start from fixture argument tuples.
2. Generate one-step perturbations around fixture values.
3. Respect simple domain constraints such as nonnegative or positive-only domains.
4. Include char/range boundary values when signatures imply them.
5. For `char` parameters, extract character literals from the original source.
6. Interleave source-literal probes with fixture-neighbor probes.
7. Deduplicate generated inputs while preserving priority order.
8. Execute only the first budgeted prefix, with default budget 8.

This policy targets fixture-overfit candidates and character-class under-coverage without front-loading a generic operator list.

### 3.3 Why Low Budget Matters

Phase 8 showed that a full generated-input mismatch baseline can be very strong, sometimes erasing the extra margin of richer v3 trace scoring. The scientific question therefore shifts from "does a complex trace score beat mismatch?" to "can targeted generated inputs achieve strong detection at low cost?" Phase 18 and Phase 19 answer yes for the current datasets.

### 3.4 Claim Boundary

The method is a source-known semantic auditor. It assumes reference execution of the original source. It should be positioned beside fixture re-execution, static similarity, fuzzing-style checks, and symbolic/concolic checks, not as a standalone decompiler.

## 4. Experimental Setup

### Datasets

We use three main evaluation rows.

| Dataset | Candidate source | Role |
|---|---|---|
| `phase7c2_static_hard_public` | Public CodeFuse-style functions with static-hard localized perturbations | public source-known static-hard benchmark |
| `phase7e_llm_public_full_topup` | LLM-generated candidates over public functions | LLM-public stress test |
| `phase6r_ghidra_full` | Real Ghidra decompiler outputs and normalized candidates | real decompiler evidence |

### Baselines and Ablations

The main table compares:

- fixture-only AUC;
- static structured AUC;
- original-order budget-8 dynamic execution;
- fixture-neighbor budget-8 dynamic execution;
- source-literal-aware fixture-neighbor budget-8 dynamic execution.

Phase 8 checks strong generated-input mismatch baselines and shows that richer v3 scoring components should not be claimed as a separate SOTA margin. Phase 17 checks a generic `operator_char_class_first` policy and shows that it is too aggressive: it improves one Ghidra subfamily while regressing broader char/boundary coverage.

### Evaluation Protocol

For each dataset, candidates are filtered to compile-ready or executable records with faithful/plausible-wrong labels. AUC is computed within paired cases. Detection rate is computed over plausible-wrong candidates. Case-level bootstrap with 2000 iterations estimates uncertainty for the final budget-8 method.

## 5. Main Results

### 5.1 Final Budget-8 Results

| Dataset | Candidates | Paired cases | Fixture AUC | Static AUC | Final budget-8 AUC | Wrong detection | Avg inputs | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `phase6r_ghidra_full` | 166 | 26 | 0.5000 | 0.8207 | 1.0000 | 1.0000 | 6.97 | 0 |
| `phase7c2_static_hard_public` | 478 | 50 | 0.9211 | 0.6806 | 1.0000 | 1.0000 | 6.64 | 0 |
| `phase7e_llm_public_full_topup` | 136 | 24 | 0.9741 | 0.7759 | 1.0000 | 1.0000 | 6.69 | 0 |

The final input policy improves the earlier Ghidra fixture-neighbor row from AUC 0.9891 and detection 0.9730 to 1.0000/1.0000, without regressing the public or LLM-public rows.

### 5.2 Stability

| Dataset | AUC | AUC CI95 | Wrong detection | Detection CI95 | Avg inputs | Input evals | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|---:|
| `phase6r_ghidra_full` | 1.0000 | [1.0000, 1.0000] | 1.0000 | [1.0000, 1.0000] | 6.97 | 1157 | 0 |
| `phase7c2_static_hard_public` | 1.0000 | [1.0000, 1.0000] | 1.0000 | [1.0000, 1.0000] | 6.64 | 3172 | 0 |
| `phase7e_llm_public_full_topup` | 1.0000 | [1.0000, 1.0000] | 1.0000 | [1.0000, 1.0000] | 6.69 | 910 | 0 |

### 5.3 Runtime

| Dataset | Candidates | Total seconds | Mean sec/candidate | P95 sec/candidate | Input evals/sec |
|---|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | 478 | 85.60 | 0.1782 | 0.0923 | 37.05 |
| `phase7e_llm_public_full_topup` | 136 | 7.94 | 0.0573 | 0.0874 | 114.65 |
| `phase6r_ghidra_full` | 166 | 11.21 | 0.0660 | 0.1031 | 103.25 |

Timing includes trace harness compilation and execution in the current Python runner. Original traces are cached per case/optimization level.

### 5.4 Risk-Family Breakdown

All risk-family rows with at least three paired cases pass AUC and detection gates. The important Phase 16 weaknesses are fixed:

| Dataset | Risk family | Paired cases | AUC | Detection | Missed wrong |
|---|---|---:|---:|---:|---:|
| `phase6r_ghidra_full` | `char_boundary` | 3 | 1.0000 | 1.0000 | 0 |
| `phase6r_ghidra_full` | `multi_arg` | 4 | 1.0000 | 1.0000 | 0 |

## 6. Ablations and Negative Results

### Static/Binary Motifs

Raw global binary distance and static motif combinations are not reliable as a primary signal:

- Raw global distance collapses on realistic faithful rewrites, AUC 0.5000.
- Static component combination reaches only LOCO AUC 0.6719.
- Structural binding reaches only LOCO AUC 0.6823.

These negative results motivate behavior-based auditing.

### v3 Scoring Components

Dynamic Trace v3 is useful as part of the method-discovery history, but Phase 8 shows that strong generated-input mismatch baselines can erase v3's extra scoring margin. Therefore, the final claim should emphasize targeted low-budget execution, not complex trace score superiority.

### Proxy vs Actual Low Budget

Phase 9's proxy suggested budget-8 would work broadly. Phase 10 actual rerun showed the proxy was optimistic for Ghidra. Phase 11/12 fixed much of this with fixture-neighbor ordering, but Phase 16 still found char-boundary and multi-argument weaknesses. Phase 18 fixes those by adding source-literal-aware char probes.

### Operator-First Negative Result

Phase 17 tested `operator_char_class_first`, a generic list of common operator characters. It fixed the `multi_arg` Ghidra weakness but harmed `char_boundary`, public static-hard, and LLM-public rows by pushing useful letter/range probes out of budget 8. This negative result motivates extracting literals from the actual source instead of front-loading a universal operator list.

## 7. Related Work Positioning

This paper should be positioned as validation/auditing, not generation.

Relevant comparison axes:

- decompilation generation systems: LLM4Decompile, DecompileBench-style evaluations, CodeFuse-style benchmarks;
- decompiler evaluation: recompilability, re-executability, functionality correctness, semantic fidelity;
- semantic checking: fuzzing, symbolic execution, concolic execution, equivalence checking;
- LLM judge and repair baselines.

The paper must state that it does not compete on generation quality metrics such as pass@k decompilation generation. Instead, it studies whether a source-known auditor can expose localized semantic drift missed by fixtures and static checks.

## 8. Threats to Validity

### Source-Known Oracle

The method requires the original source or a trusted reference implementation. It is not a binary-only verifier.

### Bounded Inputs

The method audits a bounded generated-input domain. Bugs outside the generated domain may be missed.

### Candidate Distribution

Static-hard and fixture-overfit candidates may overrepresent localized bugs. LLM-public and Ghidra rows reduce this risk but do not exhaust real-world decompiler failures.

### Decompiler Coverage

Ghidra is the only compile-ready real decompiler row. radare2 was tested for importability but did not provide compile-ready C. A second compile-ready decompiler would strengthen cross-tool claims.

### Source-Literal Dependency

The final char policy uses literals from the original source. This is appropriate for source-known auditing, but it should not be described as binary-only evidence.

## 9. Conclusion

Source-literal-aware fixture-neighbor low-budget dynamic re-execution provides a strong source-known auditing signal for localized semantic drift in C candidates. With a default budget of eight generated inputs, it passes public static-hard, LLM-public, and Ghidra gates with zero missed wrong candidates on the current full datasets. The method should be claimed as a lightweight semantic auditor, not as a general decompilation verifier or generation SOTA system.

## Appendix A. Reproducibility Checklist

- Function manifests.
- Candidate manifests.
- Trace input generation policy.
- Budgeted records.
- Bootstrap script and seed.
- Runtime/risk script outputs.
- Compile-ready filtering rules.

## Appendix B. Tables to Add Before Submission

- Final LaTeX main table.
- Ablation table: fixture-only, static, original-order, fixture-neighbor, source-literal-aware.
- Phase 17 negative-result table.
- Related-work/SOTA positioning matrix.
- Second compile-ready decompiler table, if available.
