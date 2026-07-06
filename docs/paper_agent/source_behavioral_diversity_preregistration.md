# Phase 2a Source-Behavioral Diversity Preregistration

## Scope

This preregisters Source-Behavioral Diversity Witnessing (SBDW), implemented
as `source_behavioral_diversity`, as a candidate-independent development
prototype. The Phase 1 controlled holdout and prospective natural LLM
candidate collections are development data for this prototype. They must not
be described as held-out evidence for SBDW.

This phase is CPU-only. It will not use a GPU, generate a new holdout, generate
new LLM candidates, integrate a second decompiler, run KLEE, or modify the
previous `source_literal_char_interleave` implementation.

## Source-Only Probe Pool

For each sealed source function, construct a deterministic source-only input
pool from the union of:

1. the four sealed fixtures;
2. frozen fixture-neighbor probes as defined by the Phase 1 evaluator;
3. source character-literal-derived probes;
4. generic type boundaries;
5. generic fallback probes;
6. deterministic domain sampling.

For declared exact domains with size at most `4096`, include the complete
domain. For larger exact domains, include at most `4096` deterministic samples
using committed seed `2026070601` and type-aware stratification across each
argument domain. Pool construction must not read candidate code, candidate
outputs, candidate coverage, mismatch witnesses, exact candidate labels, or
final-policy misses as hard-coded constants.

Sealed fixture inputs are retained in the source-only pool for source-side
feature computation and distance measurement, but SBDW audit prefixes exclude
fixture inputs unless an explicit fixture-replay baseline is being computed.

## Source-Side Behavioral Features

Execute only the trusted source over every pool input. For each source/input
record store:

- normalized source output;
- source edge-coverage signature;
- source branch-coverage signature when available;
- stable lightweight trace hash;
- execution status;
- source execution time.

The minimum behavior signature is:

`(normalized_source_output, edge_coverage_signature)`.

The Phase 2a prototype may use the existing sealed source harness execution
path and a deterministic source-side instrumentation shim. If reliable edge
instrumentation is unavailable for the development functions, the phase must
stop and report the blocker rather than substituting candidate behavior.

The source-only behavior cache is keyed by source function hash, build
configuration, declared domain, instrumentation version, and pool
configuration.

## Selection Objective

For each budget `B in {1, 2, 4, 8, 16, 32}`, select a deterministic prefix
without executing any candidate. SBDW uses greedy priority:

1. exclude sealed fixture inputs from generated audit probes;
2. maximize unseen normalized source-output classes;
3. then maximize new source edge coverage;
4. then maximize trace-signature novelty;
5. then maximize input-space distance from sealed fixtures and already
   selected probes;
6. break ties by canonical input order.

The selection objective and tie-breaking are global and must not be tuned per
candidate, mutation family, project, or known failure.

## Ablations

Evaluate these candidate-independent ablations:

- `output_diversity_only`;
- `coverage_diversity_only`;
- `output_then_coverage`;
- `coverage_then_output`;
- `source_behavioral_diversity_no_distance`.

All ablations use the same source-only pool and behavior cache.

## Budgets And Costs

Candidate-execution budgets are `B in {1, 2, 4, 8, 16, 32}`.

Report costs separately:

1. one-time source-side pool generation and instrumentation;
2. one-time source-only execution and selection;
3. per-candidate audit execution.

Count every source-only execution. Report amortized end-to-end cost for `1`,
`2`, `4`, `8`, and `16` candidates per source. Candidate-execution count must
not be presented as total work without source preselection cost.

## Development Populations

Primary development populations are immutable Phase 1 populations:

- controlled primary: 37 fixture-passing semantic-wrong candidates;
- controlled low-density: 16 fixture-passing semantic-wrong candidates;
- controlled no-mismatch: 34 candidates;
- prospective natural LLM: 2 fixture-passing semantic-wrong candidates from
  `base64_decode_value`;
- prospective natural LLM no-mismatch: 166 candidates.

Existing pre-freeze collections may be reported only as secondary development
data. Labels and populations must not be changed.

## Baselines

Compare SBDW against:

- `source_literal_char_interleave`;
- `literal_first_concatenation`;
- `generic_type_boundaries`;
- `fixture_neighbor_only`;
- `uniform_random_domain`;
- `randomized_union_order`;
- libFuzzer evaluation-count results;
- libFuzzer 0.1-second wall-clock results.

Reuse immutable Phase 1 results where possible.

## Success Gates

Minimum feasibility gate requires all of:

- both Phase 1h natural LLM wrong candidates detected by `B <= 8`;
- controlled primary Detection@8 at least `33/37`;
- controlled low-density Detection@8 at least `14/16`;
- no unexpected in-domain mismatch on any no-mismatch candidate;
- deterministic output across repeated runs;
- source-only selection does not inspect candidate behavior.

Strong prototype gate requires all minimum gates plus:

- controlled primary Detection@8 at least `35/37`;
- at least 2 more controlled candidates detected than
  `generic_type_boundaries`;
- median controlled first-witness rank improves over
  `source_literal_char_interleave`;
- both natural errors detected by `B <= 4`;
- amortized end-to-end latency competitive with libFuzzer at four or more
  candidates per source.

Stop the CCF-A method redesign if any of:

- either natural LLM error remains undetected at `B=8`;
- controlled primary Detection@8 falls below `33/37`;
- source instrumentation is unreliable across development functions;
- source-side selection cost remains worse than libFuzzer even when amortized
  over eight candidates;
- natural errors are detected only through candidate-specific or manually
  inserted constants.

The gates must not be weakened after seeing results.

## Interpretation

If the strong prototype gate passes, recommend freezing SBDW for a new
prospective holdout. If the minimum gate passes but the strong gate fails,
recommend revising the design before any new holdout. If a stop condition
fires, recommend stopping the method paper or repositioning it as a
development characterization rather than a new-method claim.
