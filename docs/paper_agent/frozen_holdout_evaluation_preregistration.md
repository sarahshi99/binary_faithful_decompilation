# Frozen Holdout Evaluation Preregistration

Generated: 2026-07-03

This document preregisters Phase 1e before executing or importing the frozen final auditor on the sealed holdout. The evaluation starts from Phase 1d final HEAD `ef2d721202d19f8aed55ac10db6e96b6770a722c` and the sealed holdout hash `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`.

Frozen final method: `source_literal_char_interleave`.
Method freeze commit: `06dda89912103b94fc065d6f073581a7811154b1`.

## Non-Modification Rules

Phase 1e may evaluate the sealed holdout, but it must not modify source-literal extraction, fixture-neighbor generation, admissibility filtering, generic fallback probes, interleaving order, stable deduplication, output normalization, mismatch semantics, selected functions, fixtures, natural or controlled candidates, exact labels, declared domains, mutation grammar, or sealed manifest artifacts. Candidates or labels must not be regenerated after observing auditor results.

## Preflight

Every evaluation run must require a successful preflight that recomputes the SHA-256 of `analysis/decompile_faithfulness/holdout_sealed_manifest_v2.json`, checks equality with `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`, verifies every hashed sealed artifact recorded by the manifest, verifies all method-affecting file hashes against the method freeze commit, records the current result-producing commit and environment, and fails if any sealed artifact changed.

## Evaluation Populations

### Natural Ghidra Execution Stratum

The natural execution stratum is all 16 compile-ready natural Ghidra candidates labeled `no_mismatch_under_exact_holdout_domain`. This stratum has no semantic-wrong candidate and therefore no natural-Ghidra detection-rate denominator. It is used only to report successful auditor execution, generated probe counts, exact-domain and out-of-domain probe rates, any in-domain unexpected mismatch, and any separately adjudicated out-of-domain mismatch.

### All Controlled Semantic-Wrong Candidates

All 60 compile-ready controlled candidates labeled `semantic_wrong` form the secondary all-wrong detection population.

### Primary Fixture-Passing Semantic-Wrong Population

Before generated-probe auditing, replay the four sealed fixtures for every compile-ready controlled candidate. A candidate is fixture-passing only if the source and candidate both execute normally on all four fixtures and their normalized outputs agree on all four fixtures. The primary auditing denominator is candidates that are both fixture-passing and `semantic_wrong` under exact enumeration. This status depends only on sealed fixtures, candidates, and exact labels.

### Low-Density Localized Subset

For every semantic-wrong candidate, define mismatch density as `rho = total_mismatching_input_count / exact_domain_size`, using only sealed exact-label data. Report buckets:

- `0 < rho <= 0.01`
- `0.01 < rho <= 0.10`
- `0.10 < rho <= 0.50`
- `0.50 < rho <= 1.00`

The low-density localized subset is fixture-passing semantic-wrong candidates with `rho <= 0.10`. Remaining candidates are still included in aggregate reporting.

### No-Mismatch Comparison Population

The no-mismatch comparison population includes 16 natural Ghidra no-mismatch candidates and 18 controlled no-mismatch candidates. An in-domain source/candidate mismatch on this population is an unexpected mismatch requiring adjudication. An out-of-domain mismatch is not a false positive relative to the sealed exact-domain label and is reported separately with repeated-execution confirmation.

## Evaluated Policies

Budgets are `B in {1, 2, 4, 8, 16, 32}`. All policies use the same sealed candidates and sealed fixtures.

### Frozen Final

`source_literal_char_interleave` must call the exact frozen implementation. It must not be copied and altered.

### Deterministic Direct Baselines

The deterministic baselines are:

- `fixture_neighbor_only`
- `source_literal_only`
- `neighbor_first_concatenation`
- `literal_first_concatenation`
- `operator_char_first`
- `generic_fallback_only`
- `generic_type_boundaries`

For policies built from final-method components, reuse the frozen component implementations without changing their internal behavior.

`generic_type_boundaries` is source-agnostic and must not inspect source bodies or exact mismatch witnesses. Use only values admissible for the declared argument type:

- signed integer-like arguments: `{-32, -1, 0, 1, 31}`
- unsigned integer-like arguments: `{0, 1, 63}`
- character-like arguments: `{0, 1, 31, 32, 47, 48, 57, 64, 65, 90, 97, 122, 127}`

For multi-argument functions, the ordering first changes one position at a time around sealed fixtures in fixture order and argument-index order. It then appends a bounded Cartesian fallback over the admissible per-type boundary sets in lexicographic tuple order. Stable deduplication preserves first occurrence.

### Random Baselines

The random baselines are:

- `uniform_random_domain`
- `randomized_union_order`

The 30 fixed random seeds are:

`101, 202, 303, 404, 505, 606, 707, 808, 909, 1001, 1102, 1203, 1304, 1405, 1506, 1607, 1708, 1809, 1910, 2011, 2112, 2213, 2314, 2415, 2516, 2617, 2718, 2819, 2920, 3021`.

`uniform_random_domain` samples without replacement from the declared exact domain. `randomized_union_order` uses the same deduplicated union of fixture-neighbor, source-literal, and generic fallback probes as the final method, but randomly permutes the union. Seeds must not be selected or discarded after observing results.

## Trace Semantics

For every candidate, policy, budget, random seed where applicable, and ordered probe position, record the input tuple, source output, candidate output, mismatch flag, exact-domain membership, source-literal-derived flag, fixture-neighbor-derived flag, generic-fallback-derived flag, duplicate-removal provenance, elapsed generation time, and elapsed execution time.

Do not clamp, replace, or remove an out-of-domain probe because that would alter the frozen policy. For primary exact-domain metrics, count a candidate as detected only when an in-domain probe produces a reproducible mismatch covered by the sealed oracle. Report out-of-domain witnesses separately. Also report extended-domain operational results using all executed probes.

## Metrics

For every deterministic policy and budget, report Detection@B on the primary fixture-passing semantic-wrong population, Detection@B on the low-density subset, Detection@B on all controlled semantic-wrong candidates, survivors@B, median and p95 first-witness rank, median and p95 time to first witness, exact-domain probe fraction, out-of-domain witness count, and unexpected in-domain mismatch count on no-mismatch candidates.

For stochastic policies, report mean, standard deviation, median, 2.5th and 97.5th seed percentiles, and best/worst seeds as descriptive values only.

## Stratified Analyses

Report candidate micro, function/case macro, project macro, and leave-one-project-out sensitivity by project. Include only projects containing at least one candidate in the relevant denominator.

Before reporting results, enumerate actually realized mutation-family counts. For every realized family, report attempts, compile-ready, semantic wrong, fixture-passing semantic wrong, low-density semantic wrong, Detection@8 for every deterministic policy, and median witness rank.

Report results by mismatch-density bucket, source-literal availability, one versus two arguments, character-like argument present versus integer-only, and exact-domain size 64, 128, or 4096.

## Statistical Comparisons

For the primary fixture-passing population, compare final versus `fixture_neighbor_only`, `source_literal_only`, `generic_type_boundaries`, `uniform_random_domain`, and `randomized_union_order`. Use paired per-candidate comparisons for deterministic policies. Report absolute Detection@8 difference, exact paired win/tie/loss counts, bootstrap intervals resampling at function/case level, project-level sensitivity, and first-witness-rank differences on jointly detected candidates. Candidate-level bootstrap is not the main confidence interval. AUC is secondary only.

## Interpretation Gates

Strong held-out mechanism support requires all of:

- final Detection@8 >= 0.85 on primary fixture-passing wrong candidates;
- final Detection@8 >= 0.70 on the low-density subset;
- final is on the low-budget Pareto frontier for B <= 8;
- final is not worse than `fixture_neighbor_only` by more than 0.02;
- final improves either Detection@8 by at least 0.05 or median witness rank by at least 25% over the strongest source-agnostic deterministic baseline;
- no unresolved in-domain mismatch occurs on the no-mismatch population.

Moderate support requiring claim narrowing is triggered by any of:

- primary Detection@8 in `[0.70, 0.85)`;
- low-density Detection@8 in `[0.50, 0.70)`;
- final only improves character-literal functions;
- final ties fixture-neighbor and generic boundaries;
- results are dominated by fixture-overfit or high-density mutations.

Weak support is triggered by any of:

- primary Detection@8 < 0.70;
- low-density Detection@8 < 0.50;
- random or generic boundaries dominate final in the `B <= 8` regime;
- final advantage disappears under project/case macro averaging.

The gates control paper claims only and must not stop or modify the experiment.
