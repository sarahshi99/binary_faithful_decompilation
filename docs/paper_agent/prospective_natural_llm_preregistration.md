# Prospective Natural LLM Candidate Preregistration

Generated: 2026-07-05

This document preregisters Phase 1h before any model API request, candidate
generation, semantic labeling, final-policy evaluation, or libFuzzer baseline
on the prospective natural LLM stratum.

Branch: `phase1h-prospective-natural-llm-candidates`

Starting branch and HEAD: `phase1g-libfuzzer-wallclock` at
`f9fdca2a001a9c07d2fecd507692a2d383105b91`.

Frozen method commit:
`06dda89912103b94fc065d6f073581a7811154b1`.

Sealed holdout hash:
`cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`.

Phase 1e frozen evaluation:
`f302bb51eb9371c0dad51bce92be53f58fc1a341`.

Phase 1f strong baselines:
`b626b38dd9f1398945a7c604b3213f589b936b8a`.

Phase 1g wall-clock result:
`f9fdca2a001a9c07d2fecd507692a2d383105b91`.

No local GPU will be used. KLEE will not be installed or run. No traditional
decompiler will be integrated. The frozen final method, sealed holdout
functions, domains, fixtures, prior labels, prior controlled candidates, prior
natural Ghidra candidates, Phase 1e policy traces, Phase 1f evaluation-count
results, and Phase 1g wall-clock results must remain unchanged.

## Sealed Function Population

Use exactly the 42 selected functions from
`results/decompile_faithfulness/holdout_selected_functions.csv`:

- musl: 8
- sqlite: 8
- TinyCC: 8
- sbase: 8
- mbedtls: 2
- libb64: 2
- libtomcrypt: 2
- BearSSL: 2
- xxHash: 1
- chibicc: 1

Use the existing declared exact domains from the selected-functions CSV and the
four sealed source-agnostic fixtures from
`results/decompile_faithfulness/holdout_fixtures.jsonl`. Functions must not be
resampled, excluded, or replaced based on LLM outputs, compilation outcomes,
semantic labels, final-policy behavior, source literals, or fixture behavior.

## Binary And Build Views

For each selected function, use only already sealed Phase 1d natural-Ghidra
binary views recorded in
`results/decompile_faithfulness/holdout_candidate_manifest.jsonl`:

- GCC `-O0` view, represented by the sealed object file and same-view raw
  Ghidra pseudocode when present;
- Clang `-O2` view, represented by the sealed object file and same-view raw
  Ghidra pseudocode when present.

The architecture is recovered from the sealed object file with `file`/`objdump`
metadata and is expected to be ELF x86-64 for the current sealed artifacts.
Disassembly is produced from the sealed object file for the target function
only. If a build view, object file, or same-view raw Ghidra pseudocode is
missing, the attempt is recorded as unavailable rather than substituting
another input.

The trusted source body and source comments are not used in prompts.

## Provider And Model

Use the existing remote API configuration already present in the execution
environment and Codex configuration:

- provider configuration name: `mycodex`;
- API base URL: `https://wokeme.dpdns.org/v1`;
- wire API: OpenAI-compatible Responses API;
- authentication: `OPENAI_API_KEY` from the environment;
- requested model identifier: `gpt-5.5`;
- expected returned model identifier: `gpt-5.5`.

The exact `model` field returned by the API must be stored for every response.
If any response returns a different model identifier, the discrepancy is
recorded and the run stops before labeling.

The preregistration intentionally does not probe the API before this commit.
If the configured provider or requested model is unavailable after this commit,
Phase 1h stops and reports the blocker rather than selecting another provider
or using a local model.

## Generation Parameters

Use deterministic generation where the API supports it:

- one response per request;
- temperature: `0`;
- top_p: `1`;
- max output tokens: `2048`;
- no streaming;
- no tool calls;
- no response repair request;
- no retry that changes prompt, parameters, or candidate selection;
- provider-side seed: omitted unless the API supports an explicit deterministic
  seed, in which case use `2026070501` and record the returned seed metadata.

Network or provider failures may be retried up to two times with the identical
request body. All attempts, request IDs, finish reasons, token counts, and
errors are recorded. A failed request remains failed; another model response is
not sampled as a replacement after semantic information is available.

API-cost ceiling: stop before exceeding USD 25 equivalent for this phase. If
the provider does not return price metadata, estimate cost from token counts
when a public or configured price is available; otherwise record cost as
unknown and stop if request count reaches the declared matrix maximum.

## Candidate Matrix

For every available function/build view, make exactly one request for each
prompt family:

- P1: direct behavioral reconstruction from the provided assembly/decompiler
  view;
- P2: independent clean-C reconstruction emphasizing compilability and
  preservation of observable scalar return behavior without execution feedback.

Maximum matrix:
42 functions x 2 build views x 2 prompt families = 168 attempts.

Do not sample multiple responses and choose the best. Do not regenerate
candidates after inspecting labels, fixture replay, final-policy results, or
libFuzzer results.

## Prompt Inputs

Allowed prompt payload fields:

- stable function ID;
- project name;
- function name and signature;
- target architecture;
- compiler/build-view identifier (`gcc_O0` or `clang_O2`);
- target-function disassembly from the sealed object file;
- same-view raw Ghidra pseudocode if already sealed and available;
- a fixed instruction to produce one compilable C implementation.

Forbidden prompt payload fields:

- trusted source body;
- source comments copied from the source implementation;
- source literals extracted separately;
- fixtures or fixture outputs;
- source outputs;
- exact labels;
- mismatch witnesses;
- controlled mutations;
- final-auditor probes or ordered prefixes;
- information about prior final-policy, comparator, KLEE, or libFuzzer misses.

Prompt payloads are stored exactly as sent.

## Prompt Templates

P1 template:

```text
You are reconstructing one C function from a sealed binary-view artifact.
Use only the signature, build-view metadata, target-function disassembly, and
same-view decompiler pseudocode provided below. Do not assume access to the
original source. Produce exactly one compilable C function with the requested
signature. Return only C code for the function, with no Markdown fences and no
explanation.

Function ID: {function_id}
Project: {project}
Build view: {build_view}
Target architecture: {architecture}
Required signature: {signature}

Target-function disassembly:
{disassembly}

Same-view raw Ghidra pseudocode, if available:
{raw_ghidra}
```

P2 template:

```text
Write an independent clean C reconstruction for the scalar function described
by this sealed binary view. Preserve the observable return behavior implied by
the target-function disassembly and same-view pseudocode. Do not use or infer
from original source text, tests, fixtures, witnesses, or feedback. Produce
exactly one compilable C function with the requested signature. Return only C
code for the function, with no Markdown fences and no explanation.

Function ID: {function_id}
Project: {project}
Build view: {build_view}
Target architecture: {architecture}
Required signature: {signature}

Target-function disassembly:
{disassembly}

Same-view raw Ghidra pseudocode, if available:
{raw_ghidra}
```

## Parsing And Compile Normalization

Before semantic labels are inspected, implement and commit a deterministic
candidate-processing pipeline. Allowed processing:

- remove Markdown fences;
- extract the first complete C function from the response;
- add fixed-width integer headers when needed;
- map the generated function to the sealed harness name;
- apply syntax-only declaration normalization;
- add a fixed wrapper or adapter that does not change the generated body.

Forbidden processing:

- consulting the trusted source body to repair behavior;
- changing constants based on source values;
- changing branches based on fixture failures;
- asking the model to repair compilation or semantic errors;
- selecting among multiple candidate bodies;
- applying candidate-specific semantic patches.

Store raw model response, extracted candidate, normalized compile candidate,
transformation log, and compile log separately. Candidate statuses are:

- `natural_llm_raw`;
- `natural_llm_minimally_normalized`;
- `non_evaluable_parse_failure`;
- `non_evaluable_compile_failure`;
- `non_evaluable_harness_failure`.

## Candidate Seal

After model requests and deterministic normalization are complete, and before
semantic labeling, create:

- `analysis/decompile_faithfulness/natural_llm_candidate_seal.json`
- `analysis/decompile_faithfulness/natural_llm_candidate_seal.sha256`

The seal hashes the preregistration, provider/model configuration, prompt
templates, exact prompt payloads, raw responses, extracted functions,
normalized candidates, transformation logs, compile logs, and request metadata.
The candidate-seal commit must be recorded before exhaustive labeling starts.

## Exhaustive Labeling

For every compile-ready natural LLM candidate:

1. enumerate the complete sealed declared domain in canonical order;
2. execute source and candidate under identical harness semantics;
3. record total inputs;
4. record total mismatching inputs;
5. record exact mismatch density;
6. record canonical first mismatch;
7. repeat the first mismatch to confirm reproducibility;
8. record sanitizer/runtime status.

Labels are exactly:

- `semantic_wrong`;
- `no_mismatch_under_exact_holdout_domain`;
- `non_evaluable`.

Compile failure, timeout, sanitizer failure, nondeterminism, runtime failure,
and harness failure are `non_evaluable`, not `semantic_wrong`.

The frozen final auditor must not be invoked during labeling.

## Fixture Replay And Evaluation Population

After exact labels are complete, replay the four sealed fixtures for every
compile-ready semantic-wrong LLM candidate.

Primary natural-candidate population:

`semantic_wrong` and agreement with source on all four sealed fixtures.

Low-density natural subset:

primary natural-candidate population with mismatch density `rho <= 0.10`.

Before running the final auditor or libFuzzer, create and commit:

- `analysis/decompile_faithfulness/natural_llm_evaluation_population.json`
- `analysis/decompile_faithfulness/natural_llm_evaluation_population.sha256`

This population seal contains all candidate IDs, labels, fixture-pass status,
density, project/function membership, no-mismatch population, and
non-evaluable exclusions and reasons.

## Deterministic Policy Evaluation

Only after the evaluation-population seal commit, run the frozen Phase 1e
policy implementations on the sealed natural LLM population:

- `source_literal_char_interleave`;
- `literal_first_concatenation`;
- `fixture_neighbor_only`;
- `source_literal_only`;
- `generic_type_boundaries`;
- `uniform_random_domain`;
- `randomized_union_order`.

Budgets: `1, 2, 4, 8, 16, 32`.

Stochastic policies use the fixed Phase 1e/1f seed list:

`101, 202, 303, 404, 505, 606, 707, 808, 909, 1001, 1102, 1203, 1304, 1405, 1506, 1607, 1708, 1809, 1910, 2011, 2112, 2213, 2314, 2415, 2516, 2617, 2718, 2819, 2920, 3021`.

Primary metrics:

- Detection@B on fixture-passing natural semantic-wrong candidates;
- Detection@B on low-density natural candidates;
- project macro;
- function/case macro;
- survivors@B;
- median first-witness rank;
- time to first witness;
- no-mismatch unexpected in-domain mismatches.

## libFuzzer Baseline

Reuse the exact Phase 1f/1g harness semantics and configuration:

- byte-to-domain mapping;
- differential mismatch condition;
- normalized output comparison;
- four sealed fixtures as the only seed corpus;
- no source-literal dictionary;
- no exact mismatch witnesses;
- no final-policy probes;
- fixed 30-seed list.

Evaluation-count budgets: 8, 32, 128 completed evaluations.

Wall-clock budget: 0.1 seconds end-to-end only.

Do not rerun 1-second or 5-second wall-clock budgets in Phase 1h unless
explicitly requested after review.

## Statistical Units And Reporting

Candidate-level outcomes are the primary statistical unit. Also report project
macro and function/case macro results. Seed-level libFuzzer variation is
reported with means, seed percentiles, and candidate-level both/final-only/
libFuzzer-only/neither sets. No-mismatch populations report unexpected
in-domain mismatches separately from crashes, timeouts, and infrastructure
failures.

Candidate counts are reported by project, function, build view, prompt family,
signature, source-literal availability, and density bucket. No minimum number
of wrong candidates is manufactured or required by changing generation after
labels are inspected.

## Interpretation Gates

Sufficient natural evidence is satisfied only if:

- at least 15 fixture-passing semantic-wrong candidates exist;
- they span at least 6 projects;
- at least 8 are low-density or nontrivial structured errors;
- no single prompt family or project contributes more than 50%.

Strong method recovery is supported only if, on the natural primary population:

- final Detection@8 >= 0.80;
- final exceeds generic_type_boundaries by at least 0.10 absolute, or improves
  median first-witness rank by at least 25%;
- final exceeds fixture_neighbor_only by at least 0.10 absolute;
- final is not worse than literal-first by more than 0.02;
- final materially exceeds libFuzzer at 8 completed evaluations;
- final has either higher Detection or materially lower witness cost than
  libFuzzer at 0.1 seconds;
- no unresolved in-domain mismatch occurs on no-mismatch candidates.

If enough natural wrong candidates exist but final only ties generic boundaries
or literal-first, the method is positioned as deterministic complementary
probing without a superior scheduling claim.

Stop all new experiments after Phase 1h if any negative stopping condition
holds:

- fewer than 15 fixture-passing natural wrong candidates;
- libFuzzer again dominates final in both Detection and practical cost;
- generic boundaries match or exceed final;
- results are dominated by one project or prompt family.

The frozen method is not modified in response to any result.
