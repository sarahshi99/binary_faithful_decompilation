# Frozen Holdout Preregistration

Date: 2026-07-02

Final method is frozen as `source_literal_char_interleave` at the paper-freeze commit recorded in `analysis/decompile_faithfulness/paper_freeze_manifest.json`. Do not tune source literal extraction, fixture-neighbor generation, admissibility filters, fallback probes, interleaving order, deduplication, budget handling, output normalization, scoring, or mismatch semantics on holdout data.

## Excluded Current Sources

Current evidence has already used projects: CodeFuse-DeBench, c_algorithms, thealgorithms_c. The prospective holdout must be project-disjoint from these and must not reuse their fixtures, candidates, source literals, inspected failures, or development examples.

## Candidate Upstream Projects

Candidate unseen projects for sourcing small scalar C functions:

| Project | Why eligible if freshly sampled |
|---|---|
| `libtommath` | integer arithmetic functions, project-disjoint from current sources |
| `cJSON` | small parser/helper routines with deterministic scalar subfunctions |
| `uthash` examples | compact C helper functions, separate upstream |
| `musl` | mature C library; select only isolated pure scalar helpers |
| `zlib` | checksum/table helpers; select bounded scalar wrappers |
| `mbedtls` | utility/math helpers; avoid crypto stateful paths |
| `sqlite` | pure utility functions only; avoid database state |
| `qsort_bench` or similar tiny C benchmark suites | project-disjoint scalar cases |

Eligibility must be established from a fresh clone or archived release after this freeze. A project is ineligible if any function, fixture, candidate, source literal, inspected failure, or development note from it influenced this method.

## Eligibility Criteria

1. Project-disjoint from `CodeFuse-DeBench`, `thealgorithms_c`, and `c_algorithms`.
2. One C function per case, source-known, deterministic, recompilable with `/usr/bin/gcc -std=c11`.
3. Integer or char scalar parameters only for this holdout round; no heap, I/O, global mutable state, threads, environment, time, or undefined behavior.
4. Fixtures must be generated and stored before running the final auditor.
5. Candidate generation and labeling must be completed before inspecting final-method misses.
6. No prompt or mutation family may be edited after seeing holdout auditor outcomes.

## Independent Label Oracles

Finite char domains: exhaustive enumeration over every char-like argument in 0..127 crossed with a fixed small independent set for non-char integer arguments. Label wrong if any source/candidate output differs or candidate fails compile/runtime.

Single integer arguments: use an independently specified bounded domain combining fixtures, hand-declared semantic boundaries, and stratified random integers from a committed seed. The final budget-8 prefix must be withheld from label generation until labels are sealed.

Multi-argument functions: use pairwise/combinatorial coverage over independently declared per-argument domains plus seed-committed random Cartesian samples. For small domains, exhaustive enumeration is preferred.

## Witness Exposure Risks

Current pipeline locations that can expose labeling witnesses to the auditor:

1. `docs/paper_agent/*function_manifest.json` stores fixtures used by fixture-neighbor generation.
2. `phase5b_hard_trace_inputs` derives label hard probes from fixture values and char anchors; using the same family in final fallback creates shared-family overlap.
3. Candidate records store `trace_mismatch_count` and labels before final rerun.
4. `analysis_outputs/.../records_budgeted.jsonl` stores per-budget detection outcomes.
5. Trace harness files under `analysis_outputs/.../traces/` preserve concrete final probes.
6. Phase 16/17/18 docs expose inspected misses such as `ta_infix_precedence_two`.

## Minimum Viable Holdout

Use at least 8 project-disjoint upstream projects, 60 source functions, and 240 compile-ready candidates, with at least 80 independently labeled wrong candidates and at least 30 paired cases. This is a minimum viability target; larger is better if labeling remains independent.

## Current Evidence Status

Exact witness overlap in current evidence: 354 / 377 wrong candidates (0.9390). Current three-dataset perfect tables should be described as pre-freeze/development evidence, not as fully independent holdout test evidence.
