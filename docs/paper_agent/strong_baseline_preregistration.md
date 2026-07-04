# Strong Baseline And Mechanism Preregistration

Generated: 2026-07-04

This document preregisters Phase 1f before running KLEE, libFuzzer, or new candidate-level mechanism analyses. It starts from Phase 1e result commit `f302bb51eb9371c0dad51bce92be53f58fc1a341`.

Frozen method commit: `06dda89912103b94fc065d6f073581a7811154b1`.
Verified holdout seal: `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`.
Phase 1e preregistration commit: `758707882eacf905545cd3b42d7b83fc94f52bc9`.

No final-method behavior, sealed holdout functions, fixtures, candidates, exact labels, mutation grammar, or Phase 1e traces may be modified.

## Populations

Use the immutable Phase 1e populations:

- Primary fixture-passing semantic-wrong candidates: 37.
- Low-density fixture-passing semantic-wrong candidates: 16.
- Exact-domain no-mismatch comparison candidates: 34.
- Non-fixture-overfit fixture-passing semantic-wrong subset: 15.

The non-fixture-overfit subset is defined as primary fixture-passing semantic-wrong candidates whose mutation family is not `fixture_overfit_construction`. The population must not be changed or regenerated.

## Candidate-Level Mechanism Analysis

Use only immutable `results/decompile_faithfulness/holdout_policy_traces.jsonl`, `holdout_first_witness.csv`, Phase 1e summaries, sealed labels, sealed fixtures, and candidate manifests.

Compare these policies at budgets `1, 2, 4, 8, 16, 32`:

- `source_literal_char_interleave`;
- `literal_first_concatenation`;
- `generic_type_boundaries`;
- `fixture_neighbor_only`;
- `randomized_union_order`;
- `uniform_random_domain`.

For every candidate, comparator, and budget, compute exact paired sets: detected by both, final only, comparator only, and neither. At budget 8, list stable candidate IDs for final-only/generic-boundary-only, final-only/literal-first-only, final-only/fixture-neighbor-only, all four final misses, and the three candidates still missed by final at budget 32. For every listed candidate, report project, function, signature, source-literal availability, mutation family, mismatch density, exact mismatch summary, sealed fixtures, ordered prefixes, first witness and probe origin, and why the losing policy missed.

Use paired win/tie/loss counts and McNemar-style discordant counts. Do not overinterpret small-denominator significance.

## Interleaving Analysis

Compare final and `literal_first_concatenation` at every budget. Report Detection@B difference, paired wins/losses, median and mean first-witness rank, project macro, low-density subset, source-literal-present subset, and non-fixture-overfit subset.

Classify evidence into exactly one:

1. interleaving improves early ranks or low budgets;
2. interleaving is non-inferior but not distinguishable;
3. literal-first is better;
4. evidence is mixed.

Do not alter the final method based on the result.

## Out-Of-Domain Analysis

Use Phase 1e traces only. For every deterministic policy and budget, report generated/executed probes, out-of-domain probe count and fraction, candidates receiving out-of-domain probes, out-of-domain mismatching probes, and candidates with out-of-domain witnesses.

For final at budget 8, separately report primary fixture-passing wrong, low-density subset, no-mismatch comparison, and natural Ghidra no-mismatch populations. Out-of-domain mismatches are not false positives relative to the sealed exact-domain oracle.

Confirm every distinct final-policy budget-8 out-of-domain witness by reproducible repeated source/candidate execution and record sanitizer-clean status.

## KLEE Baseline

Use a pinned KLEE release if available and record KLEE, LLVM, and Clang versions. If KLEE is unavailable or the LLVM miter cannot preserve sealed scalar semantics, stop the baseline and report the blocker; do not substitute another symbolic engine.

For supported candidates, construct a miter that creates symbolic scalar inputs, constrains each input to the sealed exact domain, executes source and candidate under equivalent scalar semantics, and reaches a designated assertion/error state exactly when normalized outputs differ. KLEE must not receive exact mismatch witnesses or final-method probes.

Wall-clock limits per candidate:

- 0.1 seconds;
- 1 second;
- 5 seconds.

Record setup/build success, support coverage, setup failure, solver/runtime timeout, witness found, confirmed valid witness, time to first confirmed witness, paths/states where available, no-mismatch false alarms, and unsupported reasons. Report both supported-candidate denominators and all-candidate denominators.

## libFuzzer Baseline

Use a pinned Clang/libFuzzer version if available. If libFuzzer cannot be built or executed, report the blocker and do not substitute another fuzzing engine.

Construct an in-process differential harness that maps fuzzer bytes deterministically to the sealed exact domain, executes source and candidate, triggers on normalized output disagreement, rejects no admissible in-domain tuple, starts from only the four sealed fixtures as seed corpus, and uses no source-literal dictionary and no exact mismatch witness.

Use the 30 fixed seeds:

`101, 202, 303, 404, 505, 606, 707, 808, 909, 1001, 1102, 1203, 1304, 1405, 1506, 1607, 1708, 1809, 1910, 2011, 2112, 2213, 2314, 2415, 2516, 2617, 2718, 2819, 2920, 3021`.

Evaluation-count budgets:

- 1;
- 2;
- 4;
- 8;
- 16;
- 32;
- 128;
- 1024.

Wall-clock limits:

- 0.01 seconds where measurable;
- 0.1 seconds;
- 1 second;
- 5 seconds.

Record actual ordered input sequence for every run, completed source-candidate input evaluations, time to first witness, evaluations to first witness, unique domain coverage, exact-domain coverage fraction, and no-mismatch false alarms. Best/worst seed values are descriptive only.

The primary libFuzzer baseline must not use a source-literal dictionary. Any source-literal dictionary variant is secondary and source-conditioned.

## Exhaustive Enumeration Reference

Use sealed exact-label outcomes only as an oracle-cost reference. Report domain size, canonical first-witness rank, total enumeration time if available, fraction of domain evaluated before first witness, and complete-domain cost. Exhaustive enumeration is not a practical low-budget baseline.

## Interpretation Gates

### Strong Low-Budget Execution Claim

Supported if the frozen final policy remains on the Detection/evaluation-count Pareto frontier for `B <= 8`, materially exceeds libFuzzer at 8 completed evaluations, has no unresolved in-domain mismatch on no-mismatch candidates, and retains at least 0.85 Detection@8 on both primary and non-fixture-overfit subsets.

Claim consequence: “effective in the single-digit concrete-execution regime.”

### Interleaving-Specific Claim

Supported only if final improves over literal-first in at least one of Detection for `B <= 4`, low-density Detection, median witness rank by at least 20%, or project-macro Detection, without meaningful regression elsewhere.

Otherwise state: “interleaving is a deterministic non-inferior scheduling realization, not a proven uniquely superior scheduler.”

### Symbolic Comparison

If KLEE detects more candidates but requires materially higher setup/time, report distinct cost regimes. If KLEE dominates both detection and end-to-end time on the supported population, do not claim final is the best low-cost auditor; position it as a solver-free deterministic concrete-testing policy.

### Fuzzing Comparison

If libFuzzer matches final within 8 completed evaluations, substantially weaken the source-conditioned mechanism claim. If libFuzzer catches up only at 128/1024 evaluations or longer wall-clock budgets, emphasize early witness yield rather than eventual coverage.
