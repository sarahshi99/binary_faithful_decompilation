# Phase 3a Natural Error Census Preregistration

## Paper Direction

Working title:

`Auditing the Auditors: Witness Leakage and Generalization in Decompilation Faithfulness Testing`

This phase supports an empirical study of decompilation-faithfulness auditing.
The central question is how decompilation-faithfulness auditors should be
evaluated, and how well apparently strong low-budget auditing methods
generalize from development-derived errors to prospective natural candidates.

Phase 3a is a candidate-generation and semantic-labeling census only. It does
not run, tune, compare, or develop any auditing policy.

## Prior Evidence Boundary

Prior Phase 1 and Phase 2 collections are development evidence and negative
evidence for method generalization. They are not the prospective population for
Phase 3a.

The following prior conclusions motivate Phase 3a but must not be used to
select, tune, repair, or score Phase 3a candidates:

- Development collections showed perfect or near-perfect low-budget detection
  but severe reconstructed witness overlap.
- The sealed controlled holdout gave 33/37 Detection@8 for the frozen policy.
- Literal-first matched the frozen policy at B=8.
- Generic type boundaries detected 32/37 controlled fixture-passing wrong
  candidates.
- libFuzzer detected 37/37 controlled fixture-passing wrong candidates at
  0.1 seconds wall-clock.
- Prospective LLM candidates produced only 2 natural semantic errors, both from
  libb64, and deterministic policies missed both.
- Source-behavioral diversity also missed both natural errors and had high
  source-side cost.

No function, project, candidate, fixture, label, witness, prompt, or failure
case from Phase 1 or Phase 2 may enter the Phase 3a prospective population.

## Hard Prohibitions

Phase 3a must not run, import for execution, tune, or inspect results from:

- `source_literal_char_interleave`
- `source_behavioral_diversity`
- `literal_first_concatenation`
- `generic_type_boundaries`
- `fixture_neighbor_only`
- `source_literal_only`
- random-domain or randomized policies
- libFuzzer
- any policy using Phase 1 or Phase 2 failure cases

Phase 3a must not generate auditor result tables, budget curves, or detection
metrics. Any accidental auditor execution triggers an immediate stop and
blocker handoff.

## Starting Point

The required starting branch is:

`phase2a-source-behavioral-diversity-prototype`

The required starting HEAD is:

`a2c975609aed5975431ec1a770c9cd92c37c2b1f`

The Phase 3a branch is:

`phase3a-prospective-natural-error-census`

This preregistration must be committed before producer setup, project download,
candidate generation, model inference, or semantic labeling.

The preregistration commit must be recorded in every later Phase 3a seal.

## Producer Setup And Availability Protocol

1. The server sanity check found Ghidra available, with Java environment
   configuration required.
2. The server sanity check found angr, RetDec, and LLM4Decompile unavailable.
3. After preregistration, the experiment may attempt to install or activate
   these producers in isolated, version-pinned environments.
4. A producer may be marked `blocked` only after an explicit installation or
   activation attempt has failed and the blocker has been recorded.
5. The existing `Dream-org/Dream-Coder-v0-Instruct-7B` model is not a valid
   LLM4Decompile substitute.
6. H200 GPU use is allowed for LLM4Decompile inference and model setup only.
   GPU use is not allowed for auditor development or any Phase 1/2 method.
7. The experiment may use controlled GPU batching for LLM4Decompile. Record GPU
   model, memory use, batch size, precision, throughput, and software versions.
8. CPU decompiler jobs may run in parallel with controlled worker limits. Record
   worker counts and avoid oversubscription.
9. If fewer than three candidate producers are available after setup attempts,
   stop before candidate generation and push a producer-availability blocker
   report.
10. If at least three producers are available, proceed with the Phase 3a
    function corpus, candidate generation, sealing, and exhaustive labeling.

Producer setup outputs:

- `results/decompile_faithfulness/phase3a_producer_availability.json`
- `docs/paper_agent/phase3a_producer_setup_log.md`

Available producers may include Ghidra, angr, RetDec, LLM4Decompile, and a fixed
general-purpose API model. The preferred minimum mix is at least one traditional
decompiler, at least one neural or API model, and one additional independent
producer.

## Project Pool

The primary project pool is ordered:

1. libyaml
2. jansson
3. expat
4. lz4
5. zstd
6. libpng
7. libjpeg-turbo
8. utf8proc
9. cmark
10. miniz
11. mpack
12. parson
13. picohttpparser
14. klib
15. bstrlib
16. libcsv
17. nanoprintf
18. sds
19. libconfuse
20. libucl

The ordered fallback project pool is:

21. json-c
22. yyjson
23. qbe
24. htslib
25. libevent
26. libuv
27. brotli
28. nghttp2
29. c-ares
30. mbedtls-testdata-excluded is forbidden because mbedtls appeared before; do
    not use it
31. cwalk
32. mxml
33. libxdiff
34. ccan
35. open62541 utility subset
36. pcre2 scalar/helper subset
37. libunistring scalar/helper subset
38. libidn2 scalar/helper subset
39. freetype scalar/helper subset
40. harfbuzz scalar/helper subset

Forbidden prior projects include CodeFuse-DeBench, c_algorithms,
thealgorithms_c, libtommath, cJSON, uthash, musl, zlib, mbedtls, sqlite,
libb64, inih, tiny-AES-c, libtomcrypt, BearSSL, libdeflate, xxHash, TinyCC,
chibicc, and sbase.

Before function extraction, each used project must have:

- canonical upstream repository resolved;
- exact commit or release tag pinned, including resolved commit;
- acquisition date recorded;
- license metadata recorded;
- scanned source files hashed.

Fallback projects may be used only if the primary pool cannot satisfy the
function population requirements. No project may be added after semantic labels
are observed.

## Function Eligibility

Eligible functions are deterministic, isolated C functions with:

- one, two, or three scalar integral, character, or enum arguments;
- scalar integral, character, or enum return type;
- no pointer or array arguments in the primary population;
- no pointer return;
- no mutable global state dependence;
- no heap, file, network, environment, locale, time, or thread dependence;
- no callbacks;
- no project runtime initialization;
- deterministic behavior under the declared domain;
- sanitizer-clean execution under complete domain enumeration;
- compilability in an isolated wrapper;
- extractability as an individual binary function.

Unlike earlier phases, functions are not restricted to structurally trivial
cases. Functions may contain loops, lookup tables, switch statements, bitwise
operations, multi-branch control flow, multiple interacting arguments, and
arithmetic state updates.

Before candidate generation, record source-derived structural features:

- argument count and types;
- AST node count;
- cyclomatic complexity;
- branch count;
- loop count;
- switch presence;
- lookup-table or indexed constant-data access;
- bitwise-operation count;
- comparison count;
- character-literal count;
- integer-literal count.

These features may be used for stratified sampling, but not to predict
candidate failure.

## Exact Audit Domains

Every selected function receives a finite declared audit domain. The complete
Cartesian domain must contain no more than 32,768 input tuples.

Domain rules:

- one-argument char-like functions: all values in [0, 127];
- one-argument signed integral functions: [-64, 63];
- one-argument unsigned integral functions: [0, 127];
- two-argument functions: up to 64 values per argument with a complete Cartesian
  product;
- three-argument functions: exactly 16 deterministic type-aware values per
  argument where possible, with a complete Cartesian product of at most 4,096
  tuples;
- enum functions: include all declared values plus fixed adjacent and invalid
  representation values only when execution remains defined.

Domain construction may inspect type declarations but must not inspect future
candidate behavior or mismatch witnesses.

The trusted source must execute over the complete declared domain under the
sealed sanitizer configuration. Exclude every function exhibiting undefined
behavior, sanitizer failure, nondeterminism, timeout, harness failure, or
unsupported external dependence.

## Function Corpus Feasibility

Target population:

- 120 selected functions;
- at least 12 represented projects;
- at least 30 one-argument functions;
- at least 50 two-argument functions;
- at least 20 three-argument functions;
- minimum 5 selected functions per represented project where available;
- maximum 10 selected functions per project where possible;
- no project over 10% of the final population when 120 functions are available.

Structural coverage targets may overlap:

- at least 25 functions containing a loop;
- at least 25 with lookup-table or indexed constant-data access;
- at least 30 with bitwise operations;
- at least 30 with at least four branches;
- at least 30 with multiple interacting arguments;
- at least 20 with switch-like categorical behavior.

Sampling seed:

`phase3a_function_sampling_seed = 2026070701`

Sampling may use only project, signature, domain feasibility, and precomputed
structural features. It must not use candidate generation success, semantic
labels, mismatch witnesses, or auditor behavior.

If fewer than 12 projects produce eligible functions, stop before candidate
generation. If fewer than 80 eligible functions are available across at least
10 projects, stop before candidate generation.

If at least 80 but fewer than 120 functions are available, create and commit
`docs/paper_agent/phase3a_function_corpus_feasibility_amendment.md` before
candidate generation. The amendment must preserve project diversity, maximum
10 functions per project where possible, no single project over 15%, structural
feature reporting, and complete exact-domain labeling. The minimum viable
empirical-paper gate remains unchanged unless explicitly updated before
candidate generation.

## Source-Agnostic Fixtures

Generate exactly four fixtures per selected function.

Fixture seed:

`phase3a_fixture_seed = 2026070702`

Fixture generation may use only stable function ID, signature, declared audit
domain, and the fixture seed. It must not inspect source body, source literals,
branch predicates, candidate code, candidate labels, known witnesses, or any
auditing policy.

Store fixtures and trusted-source outputs before candidate generation. Seal and
commit:

- `results/decompile_faithfulness/phase3a_fixtures.jsonl`
- `analysis/decompile_faithfulness/phase3a_function_fixture_seal.json`
- `analysis/decompile_faithfulness/phase3a_function_fixture_seal.sha256`

## Candidate Producers

### Traditional Decompilers

Attempt all available traditional producers from Ghidra, angr decompiler, and
RetDec. For every selected function, attempt both build views:

- GCC -O0
- Clang -O2

If a producer supports only one view reliably, record the missing view as
producer-specific unavailable.

For each attempt preserve the original source function, isolated wrapper source,
compiler command, binary, symbol metadata, raw decompiler output, parsed
function, minimally normalized compile candidate, transformation log, and
compile log. Do not use the trusted source body to repair candidate semantics.

### LLM4Decompile

Attempt one officially released LLM4Decompile model. Use the largest officially
released model that fits reliably on the H200 without OOM.

Record repository URL, repository commit, model identifier, model-file hashes,
tokenizer hash or identifier, framework versions, CUDA version, GPU type,
precision, decoding parameters, maximum batch size tested, smoke-test input,
and smoke-test output metadata.

Model input may contain assembly or disassembly for the selected function,
function signature, architecture, and compiler/build-view identifier. It must
not contain trusted source body, fixtures, source outputs, labels, witnesses,
extracted source literals, auditor probes, or Phase 1/2 failure examples.

Use fixed decoding parameters. Do not sample multiple generations and select
the best. Do not use `Dream-org/Dream-Coder-v0-Instruct-7B` as a substitute.

### General-Purpose API Producer

Reuse the existing fixed `mycodex` provider only if the exact returned model
identifier, prompt, parameters, and response metadata can be sealed.

Use one fixed reconstruction prompt per function/build view. Do not request
multiple responses and select the most favorable one. Do not provide trusted
source body, fixtures, source outputs, labels, witnesses, extracted source
literals, previous failure examples, or auditor probes.

If the API configuration is unavailable, record the producer as blocked. Do not
substitute a new provider after candidate labels are observed.

## Candidate Normalization

The normalization pipeline must be deterministic and committed before semantic
labeling.

Allowed normalization:

- Markdown-fence removal;
- extraction of the first complete function;
- fixed-width header insertion;
- deterministic function renaming;
- syntax-only declaration repair;
- fixed harness adapters;
- deterministic type adaptation using the already sealed signature.

Forbidden normalization:

- source-aware constant repair;
- source-aware branch repair;
- fixture-guided repair;
- execution-feedback repair;
- model retry after compilation failure;
- choosing among several candidate variants;
- semantic patching.

Store raw and normalized candidates separately. Candidate statuses are
`raw_candidate`, `minimally_normalized_candidate`, `parse_failure`,
`compile_failure`, `decompilation_failure`, and `harness_failure`. Failures are
non-evaluable and are never semantic wrong.

## Candidate Seal

After all candidate producers have completed, create and commit:

- `analysis/decompile_faithfulness/phase3a_candidate_seal.json`
- `analysis/decompile_faithfulness/phase3a_candidate_seal.sha256`

The seal hashes preregistration, project commits, source files, selected
functions, domains, fixtures, build commands, binaries, producer versions,
prompts and model configurations, raw outputs, normalized candidates,
transformation logs, and compile logs.

The candidate seal must be committed before exhaustive semantic labeling.

## Exhaustive Semantic Labeling

For every compile-ready candidate:

1. execute trusted source and candidate over the complete declared domain;
2. use identical input and output normalization;
3. record total domain size;
4. record total mismatching inputs;
5. record mismatch density;
6. record the canonical first mismatch;
7. hash the full mismatch set or deterministic mismatch trace;
8. repeat the first mismatch to confirm reproducibility;
9. record sanitizer and runtime status.

Labels:

- `semantic_wrong`
- `no_mismatch_under_exact_audit_domain`
- `non_evaluable`

No auditing policy may be invoked while labeling.

## Fixture Replay

For every semantic-wrong candidate, replay the four sealed fixtures.

The primary natural-error population is:

`semantic_wrong AND source/candidate agreement on all four fixtures AND normal execution on all fixtures`

Fixture-failing wrong candidates are stored separately and do not enter the
primary natural-error population.

## Natural-Error Descriptors And Taxonomy

Before any auditor evaluation, compute only candidate-independent and
oracle-derived descriptors:

- project;
- producer;
- build view;
- function;
- argument count;
- structural source features;
- domain size;
- mismatch count;
- mismatch density;
- number of connected mismatch intervals for one-dimensional domains;
- boundary distance;
- fixture distance;
- whether mismatches are concentrated in one categorical value;
- whether disagreement depends on argument interaction;
- compile-normalization extent.

Preliminary taxonomy tags:

- condition-boundary error;
- categorical/default-case error;
- lookup-table or range-compression error;
- signedness or width error;
- arithmetic error;
- return/default-value error;
- loop/state error;
- multi-argument interaction error;
- control-flow recovery error;
- unknown/mixed.

These tags must not use auditor results.

Generate a manual-review packet containing source, binary metadata, raw
candidate, normalized candidate, mismatch summary, and proposed tags. Do not
manually discard difficult or ambiguous semantic-wrong candidates.

## Census Gates

Minimum viable CCF-A empirical population requires all:

- at least 25 fixture-passing natural semantic-wrong candidates;
- at least 15 distinct source functions;
- at least 8 projects;
- at least 3 candidate producers;
- at least two producers each contribute at least 5 wrong candidates;
- no single project contributes more than 25% of wrong candidates;
- no single producer contributes more than 50%;
- at least 10 wrong candidates have mismatch density <= 0.10;
- at least four preliminary error categories contain at least three candidates
  each.

Strong population requires all minimum gates plus:

- at least 40 fixture-passing natural semantic-wrong candidates;
- at least 10 projects;
- at least 4 producers;
- at least 20 low-density candidates;
- at least six error categories;
- at least 15 multi-argument or loop/lookup-table errors.

If the complete selected-function producer matrix fails the minimum gate, do
not add more projects, generate more prompts, lower gates, create controlled
mutations, or start auditor evaluation. Report that the available natural-error
population is insufficient for the planned CCF-A empirical paper.

## Compute, API, And Parallelism Budgets

CPU work is allowed for project scanning, source validation, traditional
decompilation, candidate normalization, and exhaustive labeling.

CPU decompiler jobs may run with controlled worker limits. The initial limit is
no more than 4 concurrent decompiler workers unless a later committed setup log
records a lower or higher safe limit based on observed CPU and memory pressure.

GPU use is allowed only for LLM4Decompile setup and inference. Record total GPU
time, peak memory, GPU model, batch size, precision, throughput, generated
candidate count, failures, and retries. Do not use GPU for auditor development,
policy execution, or non-LLM4Decompile models.

API budget for the fixed general-purpose API producer:

- at most 1 smoke request before candidate generation;
- at most one candidate request per selected function/build view;
- no retry to improve semantic quality;
- retry only for transport failure, at most one retry, with both attempts
  sealed;
- maximum planned candidate requests: 240 for a 120-function corpus and 2 build
  views;
- maximum total requests including smoke and transport retries: 260.

## Required Outputs

Machine-readable outputs:

- `results/decompile_faithfulness/phase3a_project_manifest.json`
- `results/decompile_faithfulness/phase3a_eligibility_census.csv`
- `results/decompile_faithfulness/phase3a_selected_functions.csv`
- `results/decompile_faithfulness/phase3a_fixtures.jsonl`
- `results/decompile_faithfulness/phase3a_candidate_manifest.jsonl`
- `results/decompile_faithfulness/phase3a_candidate_provenance.csv`
- `results/decompile_faithfulness/phase3a_exact_labels.jsonl`
- `results/decompile_faithfulness/phase3a_label_summary.csv`
- `results/decompile_faithfulness/phase3a_fixture_replay.jsonl`
- `results/decompile_faithfulness/phase3a_natural_error_descriptors.csv`
- `results/decompile_faithfulness/phase3a_taxonomy_review_packet.jsonl`

Table and figure-data outputs:

- `paper/tables/phase3a_function_corpus.tex`
- `paper/tables/phase3a_candidate_yield.tex`
- `paper/tables/phase3a_natural_error_census.tex`
- `figures/data/phase3a_candidate_flow.json`
- `figures/data/phase3a_error_density.csv`
- `figures/data/phase3a_error_producer_distribution.csv`

Do not generate auditor result tables or budget curves.

## Tests

Add tests for:

- project disjointness from all prior phases;
- deterministic eligibility and sampling;
- structural quota reconciliation;
- exact-domain completeness;
- source sanitizer validation;
- source-agnostic fixture generation;
- producer-version pinning;
- no source/fixture/witness leakage into neural prompts;
- deterministic normalization;
- no execution-feedback repair;
- candidate seal reproducibility;
- exhaustive label reproducibility;
- fixture-pass reconstruction;
- mismatch descriptor calculation;
- census-gate reconciliation;
- guard preventing auditor imports or execution.

Use explicit test commands:

- `python -m unittest discover tests`
- `python -m unittest discover analysis/decompile_faithfulness/tests`

Do not rely on `python -m unittest discover -v` from the repository root,
because it discovers zero tests.

## Handoff And Progress Reporting

Create and update:

`docs/paper_agent/phase3a_natural_error_census_handoff.md`

Update it at these milestones:

1. repository/server sanity check complete;
2. preregistration committed;
3. project eligibility census complete;
4. selected functions and fixtures sealed;
5. candidate producer availability checked;
6. candidate generation complete and sealed;
7. exhaustive labeling complete;
8. census gates evaluated;
9. final tests and push complete.

The handoff must include producer setup attempts, exact setup commands,
producer availability status, reasons each blocked producer is blocked,
three-producer gate outcome, Java/Ghidra environment settings, H200 GPU use,
LLM4Decompile model identity and hashes if available, function-corpus size or
pre-label feasibility amendment status, and confirmation that no auditing
policy was run.

## Stop Rules

Stop and push a partial but complete handoff if any of these occurs:

1. fewer than three producers are available after setup attempts;
2. fewer than 12 projects yield eligible functions;
3. fewer than 80 eligible functions are available across at least 10 projects;
4. candidate generation completes but the natural-error population fails the
   minimum viable CCF-A empirical gate;
5. any accidental auditor execution occurs.

Do not lower gates after seeing labels. Do not add controlled mutations. Do not
develop a new method. Do not begin Phase 3b automatically.
