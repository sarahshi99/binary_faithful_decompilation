# Frozen Holdout Preregistration v4

Generated: 2026-07-03

Final method remains frozen at `06dda89912103b94fc065d6f073581a7811154b1`. This phase generates and seals a project-disjoint exact-domain holdout. The frozen final auditor and its ordered probes must not be invoked before independent seal review.

This v4 protocol applies the pre-label feasibility amendment recorded in `docs/paper_agent/holdout_feasibility_amendment.md`.

## Supported Function Class

Retain only functions with exactly one or two scalar integral or character arguments, scalar integral or character return, deterministic behavior, no pointer/array arguments, no pointer return, no mutable global state, no heap ownership, no I/O/network/environment/locale/time/thread dependence, no callback dependence, no undefined or implementation-dependent behavior over the declared domain, isolated harness compilation, and no project runtime initialization. Zero-argument functions are excluded.

Selection must not depend on source character literals, comparison constants, or structures favorable to the final method.

## Exact Domains

- signed char and signed char-like values: `[0, 127]` under the sealed char model;
- unsigned char: `[0, 127]`;
- bool: `{0, 1}`;
- signed short/int/long-like arguments: `[-32, 31]`;
- unsigned short/int/long-like arguments: `[0, 63]`;
- enum arguments are excluded unless representation and admissible values are sealed without source-specific manual choice.

One-argument domains are exhaustive. Two-argument domains are exhaustive Cartesian products. The bounded domain is the formal evaluation domain; no full C-type equivalence outside it is claimed.

## Project Pool

Primary ordered pool: libtommath, cJSON, uthash, musl, zlib, mbedtls, sqlite utility-only subset, libb64, inih, tiny-AES-c utility subset.

Fallback ordered pool: libtomcrypt, BearSSL, libdeflate, xxHash, TinyCC, chibicc, sbase.

Excluded prior sources: CodeFuse-DeBench, c_algorithms, thealgorithms_c, and any prior development fixtures/candidates/examples.

## Feasibility Amendment

Phase 1c observed only source eligibility and sanitizer feasibility. It did not generate fixtures, decompiler candidates, semantic labels, labeling witnesses, or final-auditor results.

The preregistered pool yielded 86 eligible functions across 10 projects with at least one eligible function. Under `PROJECT_CAP=8`, the project-cap-constrained capacity is 42 functions.

The original 48-function target is infeasible without either increasing project concentration or adding projects after the census. To preserve project diversity and avoid an open-ended project search, the target is revised to exactly the maximum capped census capacity: 42 functions from all 10 eligible projects. `PROJECT_CAP=8` remains unchanged.

The Phase 1c requirement that a selected project must provide at least four functions is removed. Every project with at least one eligible function is part of the sampling frame.

This is a pre-label feasibility amendment, not a result-driven change.

## Sampling And Fixtures

Sampling seed: `2026070301`. Fixture seed: `2026070302`. Mutation seed: `2026070303`.

Build the set of projects with at least one eligible function. Preserve preregistered project-pool order for project traversal. Within each project, sort by stable function ID and shuffle using the committed acquisition seed. Select one function from every eligible project, then continue deterministic round-robin selection until each project reaches `PROJECT_CAP=8` or has no remaining eligible functions. Select exactly 42 functions, the full capped capacity observed in the Phase 1c census.

Generate exactly four source-agnostic fixtures per selected function from function ID, signature, declared domain, and fixture seed only.

## Candidate Strata

Primary natural-output stratum: Ghidra 12.1.2 headless outputs from GCC `-O0` and Clang `-O2` builds where technically possible. Raw output, parsed extraction, minimally normalized candidate, and transformation logs are stored separately.

Secondary controlled-stress stratum: fixed grammar sealed in `docs/paper_agent/holdout_mutation_grammar.md`. Controlled candidates are never pooled with natural outputs in the primary generalization claim.

## Exact Labels And Seal

Compile/runtime/sanitizer/timeout/harness/nondeterminism failures are `non_evaluable`. A candidate is `semantic_wrong` only with a reproducible source-candidate mismatch under complete declared-domain enumeration. The seal hashes projects, source files, functions, domains, fixtures, tool configurations, candidates, labels, witnesses, execution logs, and exclusions before final-auditor evaluation.
