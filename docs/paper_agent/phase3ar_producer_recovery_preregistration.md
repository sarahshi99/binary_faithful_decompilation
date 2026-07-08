# Phase 3a-R Producer Recovery Preregistration

Created: 2026-07-08

Branch: `phase3ar-producer-recovery-census`

Starting Phase 3a branch: `phase3a-prospective-natural-error-census`

Starting Phase 3a HEAD: `db5a9fc78e43d2702f9490184d0ae690a6a57c4d`

Study direction: `Auditing the Auditors: Witness Leakage and Generalization in
Decompilation Faithfulness Testing`.

Phase 3a-R is a producer-recovery census. It is not Phase 3b.

## Scope

Phase 3a produced a sealed natural-error census. The original candidate seal is:

`e34f3c7532a8a2b399ef5be4c7a931b3f4d5e7c982c6f5d29adb14a89c8971f4`

The original Phase 3a census failed the minimum viable CCF-A gate because the
primary fixture-passing semantic-wrong population was zero:

- candidate attempts: 640;
- compile-ready candidates: 215;
- semantic-wrong candidates: 10;
- fixture-passing semantic-wrong candidates: 0;
- fixture-failing semantic-wrong candidates: 10;
- no-mismatch candidates: 194;
- non-evaluable candidates: 436;
- minimum gate: failed;
- Phase 3b authorization: false.

This recovery preserves that original result as a failed sealed census. Original
Phase 3a artifacts must not be overwritten.

## Recovery Motivation

This recovery is motivated only by infrastructure failures recorded in Phase 3a:

1. `compiler_unavailable:clang` for the Clang-O2 build view.
2. LLM4Decompile generation failure caused by `token_type_ids` being passed to
   a model that does not use it.

The recovery does not use auditor results. No auditor was run in Phase 3a.

The recovery must not use the identities, witnesses, mismatch traces, fixture
outcomes, or taxonomy of the 10 Phase 3a semantic-wrong candidates to select
functions, prompts, producers, or repairs.

## Immutable Inputs

Phase 3a-R uses exactly the same:

- 80 selected functions;
- declared exact audit domains;
- source-agnostic fixtures;
- trusted-source fixture outputs;
- project set;
- source files;
- function/fixture seal.

The canonical Phase 3a function/fixture seal is:

`2bba63e1a191050f2ec0e15a8f58ed7eff9a5c9bf1f21b672b7ab9bfc64c1494`

No project may be added. The function corpus must not be expanded. The natural
error census gates must not be lowered.

## Recovery Matrix

The recovery attempts only previously infrastructure-blocked matrix cells:

- all Clang-O2 cells that were unavailable because Clang was unavailable;
- LLM4Decompile cells blocked by the `token_type_ids` model-interface error.

Previously successful GCC-O0 non-LLM4Decompile cells must not be regenerated.

Existing Phase 3a successful candidates, labels, and fixture replay records
remain immutable and may be included only in combined summaries.

Recovery cells are eligible only if the original Phase 3a manifest records one
of the infrastructure reasons above. Candidate-specific parse failures, compile
failures, runtime failures, semantic labels, and fixture outcomes are not used to
select recovery cells.

## Clang Recovery Protocol

After this preregistration is committed, Clang availability may be diagnosed and
recovered in this order:

1. existing system package;
2. conda-forge clang/llvm toolchain;
3. existing module or environment if present.

Record exact install or activation commands and the final compiler paths. Run
only synthetic non-project smoke tests before applying Clang-O2 to the sealed
Phase 3a functions. The smoke test must confirm Clang-O2 compilation, symbol
metadata extraction, and consumption by the pinned Ghidra and angr producers.

If Clang cannot be fixed, mark Clang recovery blocked and continue only with
LLM4Decompile interface recovery.

## LLM4Decompile Interface Recovery Protocol

The `token_type_ids` failure is a model-interface bug, not a semantic repair.

Allowed adapter changes:

- remove `token_type_ids` from model inputs when the model or generation function
  does not accept it;
- filter tokenizer kwargs against the model forward/generate signature;
- use an official model-specific generation API if documented.

Forbidden adapter changes:

- changing the prompt template;
- changing decoding parameters;
- adding source bodies;
- adding fixtures;
- adding source outputs;
- adding known witnesses;
- adding auditor probes;
- adding Phase 1/2 failure examples;
- adding Phase 3a semantic-wrong examples;
- retrying failed outputs with new prompts;
- using Dream-Coder or any non-LLM4Decompile model as a substitute.

Run a synthetic non-project binary/function smoke test and record model ID,
snapshot/hash, tokenizer identity/hash, adapter change, smoke prompt hash, output
status, GPU model, precision, batch size, peak memory if measurable, CUDA
version, and software versions.

If LLM4Decompile still fails, mark it blocked and do not substitute another
model.

## Candidate Generation And Sealing

Candidate generation must be sealed before labeling.

Recovered candidate IDs must be distinct from original Phase 3a candidate IDs.

For recovered traditional decompiler cells, compile the selected function under
the recovered Clang-O2 build view, decompile only the target function, store raw
output, extract deterministically, apply only minimal syntax/harness
normalization, and compile against the sealed harness.

For recovered mycodex API cells, use the same fixed prompt template and
generation parameters as Phase 3a, with Clang-O2 disassembly/build metadata.
Request exactly one response per eligible cell.

For recovered LLM4Decompile cells, use the same prompt template and decoding
parameters as Phase 3a. Use fixed H200 batching. Request exactly one generation
per eligible cell.

Model inputs may contain only assembly/disassembly for the selected target
function, function signature, architecture, compiler/build-view identifier, and
the producer prompt template.

Model inputs must not contain trusted source body, fixtures, source outputs,
labels, known witnesses, extracted source literals, auditor probes, Phase 1/2
failure examples, Phase 3a semantic-wrong examples, or controlled mutation
examples.

After recovery candidate generation, create and commit the Phase 3a-R candidate
seal before exhaustive semantic labeling.

## Labeling And Combined Census

Label every recovered compile-ready candidate using the same exhaustive exact
domain protocol as Phase 3a:

1. execute trusted source and candidate over the complete declared exact domain;
2. use identical input and output normalization;
3. record total domain size;
4. record total mismatching inputs;
5. record mismatch density;
6. record canonical first mismatch;
7. hash the full mismatch set or deterministic mismatch trace;
8. repeat the first mismatch to confirm reproducibility;
9. record sanitizer/runtime status.

Labels are `semantic_wrong`, `no_mismatch_under_exact_audit_domain`, and
`non_evaluable`. Failures are non-evaluable, never semantic wrong.

For every recovered semantic-wrong candidate, replay the four sealed fixtures.

Create a combined census from immutable original Phase 3a results and new
Phase 3a-R recovered results. Do not duplicate original failed cells if a
recovered replacement exists; record both original and recovered status.

Recovered candidates count as recovery-phase natural candidates and must be
reported separately as well as in the combined population.

## Gates And Stop Rule

The original minimum viable CCF-A empirical population gate is unchanged. It
requires all of:

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

If the recovered combined population still fails the minimum gate, stop. Do not
add projects, prompts, producers, controlled mutations, gate changes, or auditor
evaluation. Report that the recovery census remains insufficient for the planned
CCF-A empirical paper.

If the minimum gate passes, do not begin Phase 3b automatically. Report that
Phase 3b auditor evaluation is authorized for review.

## Prohibitions

Do not run any auditor. Do not run libFuzzer. Do not generate budget curves. Do
not generate auditor result tables. Do not inspect whether any auditor would
detect recovered errors. Do not modify, tune, or develop an auditing policy. Do
not add controlled mutations.
