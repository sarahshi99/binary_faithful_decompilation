# Phase 3a Natural Error Census Handoff

Updated: 2026-07-07T04:51:30Z

Branch: `phase3a-prospective-natural-error-census`

Base branch: `phase2a-source-behavioral-diversity-prototype`

Base HEAD: `a2c975609aed5975431ec1a770c9cd92c37c2b1f`

Preregistration commit: `2b0e62472b3ee766bba9f64a440d52f0f53bedf9`

Study direction: `Auditing the Auditors: Witness Leakage and Generalization in
Decompilation Faithfulness Testing`.

Phase 3a scope: candidate generation and semantic labeling only. No
decompilation-faithfulness auditing policy has been run.

## Milestones

- Repository/server sanity check: complete before Phase 3a branch creation.
- Preregistration: complete and committed.
- Producer setup and availability check: complete; producer gate passed.
- Project eligibility census: pending.
- Selected functions and fixtures seal: pending.
- Candidate generation and seal: pending.
- Exhaustive semantic labeling: pending.
- Census gates: pending.
- Final tests and push: pending.

## Confirmed Initial State

- Git LFS was OK.
- `holdout_policy_traces.jsonl` was real content, not an LFS pointer.
- Required starting branch was
  `phase2a-source-behavioral-diversity-prototype`.
- Required starting HEAD was
  `a2c975609aed5975431ec1a770c9cd92c37c2b1f`.
- Prior tests passed: `tests` 194 passed and
  `analysis/decompile_faithfulness/tests` 82 passed, 276 total.
- H200 was available for LLM4Decompile setup/inference only.

## Producer Setup Outcome

Producer setup details are sealed in:

- `docs/paper_agent/phase3a_producer_setup_log.md`
- `results/decompile_faithfulness/phase3a_producer_availability.json`

Available producers:

- Ghidra 12.1.2 with explicit Java 21 environment.
- angr 9.2.102 in `/home/shx/.venvs/phase3a-angr`.
- LLM4Decompile 22B v2, model snapshot
  `be2ac0bbb3bfa508d9f8a4790329250f1cb13ddc`.
- Fixed `mycodex` API provider returning `gpt-5.5`.

Blocked producers:

- RetDec. Source build attempts were made from pinned RetDec commit
  `53e55b4b26e9b843787f0e06d867441e32b1604e`; the CMake 4/Ninja attempt failed
  on old vendored LLVM compatibility and YARA make detection, and the CMake
  3.27.9/Unix Makefiles attempt failed on restricted-network dependency
  downloads. Escalated rerun was rejected by the approval service with
  `model not found: codex-auto-review`. No substitute decompiler was used.

Producer availability gate: passed. Four producers are available; at least
three were required.

## Java/Ghidra Environment

- `JAVA_HOME=/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/root/usr/lib/jvm/java-21-openjdk-amd64`
- `PATH` must prepend:
  `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/root/usr/lib/jvm/java-21-openjdk-amd64/bin`
- `analyzeHeadless`:
  `analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/ghidra_12.1.2_PUBLIC/support/analyzeHeadless`
- Ghidra version: 12.1.2.
- Java version: OpenJDK 21.0.7.

## LLM4Decompile / H200

- Official model used: `LLM4Binary/llm4decompile-22b-v2`.
- Repository commit: `85b364bf093eb2ee4f3687cfe38a203fca89f23e`.
- Snapshot: `be2ac0bbb3bfa508d9f8a4790329250f1cb13ddc`.
- GPU: NVIDIA H200 NVL.
- Precision: BF16.
- Maximum batch size tested so far: 1.
- Smoke peak memory: 43392.7 MiB.
- Smoke generation throughput: 21 output tokens in 1.566 s.
- `Dream-org/Dream-Coder-v0-Instruct-7B` was not used.

The 22B v2 model is an LLM4Decompile-Ref model. For Phase 3a candidate
generation, its input must be derived from the selected function binary/build
view through Ghidra pseudocode and sealed metadata only; no trusted source body,
fixtures, labels, witnesses, extracted source literals, auditor probes, or
Phase 1/2 failure examples may be included.

## API Usage

The only API call in producer setup was a minimal non-project smoke test for
the fixed `mycodex` provider. It returned model `gpt-5.5` with request id
`resp_01bf9d56c7c616b3016a4c771b4f308191a05dbc161e11e720` and 36 total tokens.

No Phase 3a candidate requests have been made yet.

## Current Counts

- Projects scanned: 0.
- Projects represented: 0.
- Eligible functions: 0.
- Selected functions: 0.
- Candidate attempts: 0.
- Parse-ready candidates: 0.
- Compile-ready candidates: 0.
- Semantic-wrong candidates: 0.
- Fixture-passing semantic-wrong candidates: 0.
- No-mismatch candidates: 0.
- Non-evaluable candidates: 0.
- Low-density natural wrong candidates: 0.
- Multi-argument/loop/lookup natural wrong candidates: 0.

These counts are zero because the run has not yet entered project acquisition
or candidate generation.

## Corpus Target Status

The original target of 120 selected functions remains active. No pre-label
function-corpus feasibility amendment has been used.

## Authorization Status

Phase 3a is authorized to proceed to project acquisition and function corpus
construction because the producer availability gate passed.

Phase 3b auditor evaluation is not authorized.

## Tests

No new tests were run after the preregistration commit during producer setup.
The next test run must use explicit discovery commands:

```sh
python -m unittest discover tests
python -m unittest discover analysis/decompile_faithfulness/tests
```

Any new Phase 3a tests outside those discovery paths must be run directly.

## Audit Policy Prohibition Confirmation

No execution of the following occurred in Phase 3a producer setup:

- `source_literal_char_interleave`
- `source_behavioral_diversity`
- `literal_first_concatenation`
- `generic_type_boundaries`
- `fixture_neighbor_only`
- `source_literal_only`
- random-domain policies
- libFuzzer

No auditor result tables, budget curves, or auditor detection checks were
generated.

## Function Corpus And Fixture Seal Milestone

Updated: 2026-07-07T05:38:30Z

- Branch: `phase3a-prospective-natural-error-census`
- Current HEAD at corpus command run: `5532b6d4f601a8d926ca19f1d911ac6a16999f83`
- Producer setup commit: `5532b6d`
- Projects scanned: `39`
- Projects represented: `0`
- Primary projects used: `0`
- Fallback projects used: `0`
- Fallback needed: `True`
- Eligible function count: `0`
- Selected function count: `0`
- Selected functions by project: `{}`
- Selected functions by argument count: `{}`
- Structural-feature coverage: `{}`
- Exact-domain size distribution: `{}`
- Exclusion counts and reasons: `{"project_acquisition_failed:couldnt_connect_to_server": 39}`
- Feasibility amendment needed: `False`
- Fixture count: `0`
- Function/fixture seal hash: ``
- Tests run: `python -m unittest discover tests` -> 194 passed; `python -m unittest discover analysis/decompile_faithfulness/tests` -> 92 passed.

Gate status: `stopped_before_fixture_generation_insufficient_project_count`.

Blocker: project acquisition could not complete. All 39 preregistered primary
and fallback project clone attempts failed inside the sandbox with `Couldn't
connect to server`. An escalated rerun of the same corpus acquisition command
was requested, but the approval service rejected it with `model not found:
codex-auto-review`. No alternate project pool, cached prior-phase project, or
substitute source corpus was used.

Function/fixture seal status: not created, because the preregistered stop rule
triggered before fixture generation. There are fewer than 12 projects with
eligible functions and fewer than 80 eligible functions.

Push status: initial `git push -u origin
phase3a-prospective-natural-error-census` failed before this milestone with
`Permission to sarahshi99/binary_faithful_decompilation.git denied to deploy
key`. A final push attempt should be retried after credentials are fixed.

No candidate generation occurred in this milestone.

No semantic labeling occurred in this milestone.

No auditor was run in this milestone.
