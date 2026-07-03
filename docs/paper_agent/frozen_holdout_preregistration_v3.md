# Frozen Holdout Preregistration v3

Generated: 2026-07-03T03:48:33.879478+00:00

Final method remains frozen at `06dda89912103b94fc065d6f073581a7811154b1`. This phase acquires and seals a project-disjoint exact-oracle holdout. The frozen final auditor and its ordered probes must not be invoked before seal review.

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

## Sampling And Fixtures

Sampling seed: `2026070301`. Fixture seed: `2026070302`. Mutation seed: `2026070303`.

If fewer than 48 eligible functions across at least 8 projects are available, or if the cap-constrained sampling capacity is below 48, stop before candidate generation and push the census for review. Otherwise sample 48-64 functions from at least 8 projects, cap each project at 8 functions, and generate exactly four source-agnostic fixtures per function from function ID, signature, declared domain, and fixture seed only.

## Candidate Strata

Primary natural-output stratum: Ghidra 12.1.2 headless outputs from GCC `-O0` and Clang `-O2` builds where technically possible. Raw output, parsed extraction, minimally normalized candidate, and transformation logs are stored separately.

Secondary controlled-stress stratum: fixed grammar sealed in `docs/paper_agent/holdout_mutation_grammar.md`. Controlled candidates are never pooled with natural outputs in the primary generalization claim.

## Exact Labels And Seal

Compile/runtime/sanitizer/timeout/harness/nondeterminism failures are `non_evaluable`. A candidate is `semantic_wrong` only with a reproducible source-candidate mismatch under complete declared-domain enumeration. The seal hashes projects, source files, functions, domains, fixtures, tool configurations, candidates, labels, witnesses, and exclusions before final-auditor evaluation.
