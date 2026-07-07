# Phase 3a Natural Error Census Handoff

Updated: 2026-07-07T10:04:46Z

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
- Project eligibility census: complete.
- Selected functions and fixtures seal: complete.
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

- Projects scanned: 39.
- Projects represented: 21.
- Eligible functions: 111.
- Selected functions: 80.
- Fixtures: 320.
- Candidate attempts: 0.
- Parse-ready candidates: 0.
- Compile-ready candidates: 0.
- Semantic-wrong candidates: 0.
- Fixture-passing semantic-wrong candidates: 0.
- No-mismatch candidates: 0.
- Non-evaluable candidates: 0.
- Low-density natural wrong candidates: 0.
- Multi-argument/loop/lookup natural wrong candidates: 0.

Candidate and label counts remain zero because Phase 3a has not yet entered
candidate generation or semantic labeling.

## Corpus Target Status

The original 120-function target was infeasible under the preregistered
per-project cap after the primary/fallback census. A pre-candidate,
pre-label, pre-auditor feasibility amendment was committed in
`docs/paper_agent/phase3a_function_corpus_feasibility_amendment.md`.

The sealed reduced corpus contains 80 selected functions across 21 represented
projects. Exact-domain labeling remains complete for future Phase 3a labeling.

## Authorization Status

Phase 3a completed project acquisition and function corpus construction after
the producer availability gate passed. Candidate generation has not begun and
should not begin until explicitly instructed.

Phase 3b auditor evaluation is not authorized.

## Tests

- `python -m unittest discover tests` -> 194 tests passed.
- `python -m unittest discover analysis/decompile_faithfulness/tests` -> 96 tests passed.

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

## Infrastructure Recovery

Recovery log:
`docs/paper_agent/phase3a_infrastructure_recovery_log.md`.

- Branch: `phase3a-prospective-natural-error-census`
- Local HEAD before recovery: `c647f856e69da0dcc0037abd44f8976af3d70d10`
- Backup bundle: `backups/phase3a_corpus_blocker_c647f85.bundle`
- Bundle verification: passed.
- Patch backups: `backups/0001-Preregister-Phase-3a-natural-error-census.patch`, `backups/0002-Record-Phase-3a-producer-availability.patch`, `backups/0003-Add-Phase-3a-corpus-blocker-census.patch`
- Push credential diagnosis during recovery: origin initially used an SSH deploy key that authenticated as `sarahshi99/dllm_infilling`, not as a write-capable credential for `sarahshi99/binary_faithful_decompilation`.
- Push status after user-side credential fix: `git push -u origin phase3a-prospective-natural-error-census` returned `Everything up-to-date`, and `git ls-remote --heads origin phase3a-prospective-natural-error-census` returned `76a6969fe138efe5bc250c34d41b7e4dc6df3b3d`.
- Network diagnosis: direct sandbox networking could not reach GitHub, but approved host-side `git clone` / `git ls-remote` commands could reach external project repositories.
- Direct clone status after resume: unblocked for 38 of 39 preregistered projects. `libyaml` was acquired and pinned to `893682bb98d5ed663a3e314c46dceaf9b1c8802f`; `qbe` still had no resolved checkout HEAD and is recorded as an acquisition failure.
- Proxy or mirror mode used: no mirror mode was used; no unverified cached source tree was treated as newly acquired.
- Source acquisition status: unblocked enough to complete the preregistered primary/fallback census and proceed to reduced-feasible corpus sealing.
- Corpus acquisition rerun: yes, after the infrastructure recovery amendment and feasibility amendment were committed.

No candidate generation occurred during infrastructure recovery.

No semantic labeling occurred during infrastructure recovery.

No auditor was run during infrastructure recovery.

## Resume Verification And Network Rediagnosis

Resume verification date: `Tue Jul  7 09:54:58 UTC 2026`.

- Branch: `phase3a-prospective-natural-error-census`
- Local HEAD at resume: `76a6969fe138efe5bc250c34d41b7e4dc6df3b3d`
- Remote branch HEAD at resume: `76a6969fe138efe5bc250c34d41b7e4dc6df3b3d`
- Remote: `git@github-bfd:sarahshi99/binary_faithful_decompilation.git`
- Git LFS status: clean; no staged or unstaged LFS objects.

Producer setup remained valid without reinstalling producers:

- Ghidra 12.1.2 headless smoke on `/bin/true`: passed with explicit Java 21 environment.
- Java version: OpenJDK `21.0.7`.
- angr import/version check: angr `9.2.102`, claripy `9.2.102`, z3 `4.10.2`.
- LLM4Decompile 22B v2 local snapshot: present; tokenizer SHA-256 `722f46f56e1dd32bdd7288f5257e749f34303c5be777712d4319c0cd4987c1dc`.
- Fixed `mycodex` API configuration: `OPENAI_API_KEY` present; no candidate requests were made.
- RetDec: still blocked; no `retdec-decompiler` executable was found on `PATH`.

Network rediagnosis:

- Proxy environment: `HTTP_PROXY=http://127.0.0.1:7890`, `HTTPS_PROXY=http://127.0.0.1:7890`, `ALL_PROXY=http://127.0.0.1:7890`.
- Sandbox DNS checks for `github.com`, `api.github.com`, and `gitlab.com`: failed with `gaierror(-2, 'Name or service not known')`.
- `curl -I --max-time 20 https://github.com`: failed with `Couldn't connect to server`.
- `curl -I --max-time 20 https://api.github.com`: failed with `Couldn't connect to server`.
- `git ls-remote https://github.com/yaml/libyaml.git HEAD`: succeeded, returning `893682bb98d5ed663a3e314c46dceaf9b1c8802f`.
- `git ls-remote https://github.com/akheron/jansson.git HEAD`: succeeded, returning `a8b3c5999e752d895030360c553ba66fa6630ed0`.
- `git ls-remote https://github.com/lz4/lz4.git HEAD`: succeeded, returning `0774d05537f9762f838f7ab541b7765f1a729cb5`.

Source acquisition decision: direct source acquisition through git was usable.
The corpus script's first internal `libyaml` clone attempt still reported
`Couldn't connect to server`, so `libyaml` was acquired through the verified
top-level `git clone` path and then rerun through the normal corpus scanner and
seal pipeline. No mirror mode, fake data, unpinned local source tree, or Phase
1/2 source project was used.

## Function Corpus And Fixture Seal Milestone

Updated: 2026-07-07T10:02:21Z

- Branch: `phase3a-prospective-natural-error-census`
- Current HEAD at corpus command and seal generation: `76a6969fe138efe5bc250c34d41b7e4dc6df3b3d`
- Remote branch HEAD at resume: `76a6969fe138efe5bc250c34d41b7e4dc6df3b3d`
- Producer setup commit: `5532b6d`
- Projects scanned: `39`
- Projects represented: `21`
- Primary projects used: `20`
- Fallback projects used: `18`
- Fallback needed: `True`
- Eligible function count: `111`
- Selected function count: `80`
- Selected functions by project: `{"brotli": 3, "c-ares": 1, "ccan": 12, "cmark": 9, "freetype": 2, "htslib": 8, "jansson": 1, "json-c": 1, "klib": 3, "libevent": 4, "libidn2": 2, "libucl": 2, "libuv": 3, "libxdiff": 1, "lz4": 1, "mpack": 1, "nanoprintf": 10, "nghttp2": 4, "open62541": 2, "pcre2": 1, "zstd": 9}`
- Selected functions by argument count: `{"1": 60, "2": 12, "3": 8}`
- Structural-feature coverage: `{"arity_1": 60, "arity_2": 12, "arity_3": 8, "bitwise": 27, "branches4": 3, "interacting_args": 17, "lookup": 8, "loop": 8, "switch_like": 1}`
- Exact-domain size distribution: `{"128": 59, "4096": 20, "5": 1}`
- Exclusion counts and reasons: `{"compile_failure": 28, "dependency_blacklist": 48, "external_function_call": 180, "macro_or_external_identifier": 65, "project_acquisition_failed": 1, "runtime_failure_1": 6, "signature_filter_failed": 7540, "unsupported_or_oversized_domain": 3}`
- Feasibility amendment needed: `True`
- Fixture count: `320`
- Function/fixture seal hash: `2bba63e1a191050f2ec0e15a8f58ed7eff9a5c9bf1f21b672b7ab9bfc64c1494`
- Tests run: `python -m unittest discover tests` -> 194 tests passed; `python -m unittest discover analysis/decompile_faithfulness/tests` -> 96 tests passed.

Gate status: `reduced_feasible`.

No candidate generation occurred in this milestone.

No semantic labeling occurred in this milestone.

No auditor was run in this milestone.
