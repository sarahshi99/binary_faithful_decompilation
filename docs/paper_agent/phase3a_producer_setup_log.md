# Phase 3a Producer Setup Log

Created: 2026-07-07T04:51:30Z

Branch: `phase3a-prospective-natural-error-census`

Preregistration commit: `2b0e62472b3ee766bba9f64a440d52f0f53bedf9`

This setup was performed after the preregistration commit and before any Phase
3a project corpus acquisition, candidate generation, semantic labeling, or
auditor execution.

No Phase 1/2 auditor policy was run. No libFuzzer run was started. No budget
curve or auditor result table was generated.

## Summary

Available producers:

- Ghidra 12.1.2.
- angr 9.2.102.
- LLM4Decompile 22B v2.
- Fixed `mycodex` Responses API provider returning `gpt-5.5`.

Blocked producers:

- RetDec.

Producer availability gate: passed. Four producers are available, satisfying
the preregistered requirement of at least three producers before function corpus
construction or candidate generation.

## Ghidra

Status: available.

Environment:

- `JAVA_HOME=/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/root/usr/lib/jvm/java-21-openjdk-amd64`
- `PATH` prefix:
  `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/root/usr/lib/jvm/java-21-openjdk-amd64/bin`
- `analyzeHeadless`:
  `analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/ghidra_12.1.2_PUBLIC/support/analyzeHeadless`
- Ghidra version: `12.1.2`.
- Java version: OpenJDK `21.0.7`.

Smoke command:

```sh
JAVA_HOME=/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/root/usr/lib/jvm/java-21-openjdk-amd64 PATH=/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/root/usr/lib/jvm/java-21-openjdk-amd64/bin:$PATH analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/ghidra_12.1.2_PUBLIC/support/analyzeHeadless /tmp phase3a_ghidra_smoke2 -import /bin/true -deleteProject -noanalysis
```

Result: passed. The smoke input was `/bin/true`, not a prior Phase 1/2 source
function.

## angr

Status: available.

Environment: `/home/shx/.venvs/phase3a-angr`.

Install command:

```sh
/home/shx/.venvs/phase3a-angr/bin/python -m pip install angr==9.2.102
```

Recorded versions:

- Python: `3.9.23`.
- angr: `9.2.102`.
- claripy: `9.2.102`.
- z3: `4.10.2`.

Smoke command:

```sh
/home/shx/.venvs/phase3a-angr/bin/python -c "import angr; p=angr.Project('/bin/true', auto_load_libs=False); cfg=p.analyses.CFGFast(normalize=True); main=p.kb.functions.function(name='main'); d=p.analyses.Decompiler(main, cfg=cfg.model); print(str(d.codegen.text)[:160])"
```

Result: passed. The smoke input was `/bin/true`, not a prior Phase 1/2 source
function. angr produced decompiler output for `main`.

## RetDec

Status: blocked.

Repository: `https://github.com/avast/retdec`.

Pinned source commit/tag: `53e55b4b26e9b843787f0e06d867441e32b1604e`.

Source path: `external/phase3a_tools/retdec-v5.0`.

Initial checks found no usable `retdec-decompiler` on `PATH`, no apt package,
and no conda-forge package.

The first source-build attempt used CMake 4.3.4 and Ninja in
`external/phase3a_tools/retdec-v5.0-build`. It failed because the vendored LLVM
project declares `cmake_minimum_required(VERSION 3.4.3)`, which CMake 4.3.4 no
longer accepts. The same attempt also exposed a YARA configuration issue where
the cached `YARA_MAKE_PROGRAM` became `OFF`.

The second source-build attempt downgraded the isolated build environment to
CMake 3.27.9 and used Unix Makefiles:

```sh
/home/shx/.venvs/phase3a-retdec-build/bin/python -m pip install 'cmake==3.27.9'
PATH=/home/shx/.conda/envs/phase3a-retdec-build/bin:/home/shx/.venvs/phase3a-retdec-build/bin:$PATH /home/shx/.venvs/phase3a-retdec-build/bin/cmake -S external/phase3a_tools/retdec-v5.0 -B external/phase3a_tools/retdec-v5.0-build-make -G 'Unix Makefiles' -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/home/shx/projects/binary_faithful_decompilation/external/phase3a_tools/retdec-v5.0-install -DOPENSSL_ROOT_DIR=/home/shx/miniconda3 -DOPENSSL_INCLUDE_DIR=/home/shx/miniconda3/include -DOPENSSL_SSL_LIBRARY=/home/shx/miniconda3/lib/libssl.so -DOPENSSL_CRYPTO_LIBRARY=/home/shx/miniconda3/lib/libcrypto.so -DZLIB_INCLUDE_DIR=/home/shx/miniconda3/envs/llmxy/include -DZLIB_LIBRARY=/home/shx/miniconda3/envs/llmxy/lib/libz.so -DRETDEC_COMPILE_YARA=OFF
PATH=/home/shx/.conda/envs/phase3a-retdec-build/bin:/home/shx/.venvs/phase3a-retdec-build/bin:$PATH /home/shx/.venvs/phase3a-retdec-build/bin/cmake --build external/phase3a_tools/retdec-v5.0-build-make --target retdec-decompiler -j 4
```

Configure succeeded, but the build failed while downloading official RetDec
dependencies through the restricted network. The failed dependency downloads
included YARA, LLVM, and Capstone. The sandbox error reported that the
configured proxy `127.0.0.1:7890` could not be reached.

An escalated rerun of the same build command was requested because the failure
was network-related. The approval service rejected the request with:
`model not found: codex-auto-review`.

No replacement decompiler was substituted for RetDec.

## LLM4Decompile

Status: available.

Repository: `https://github.com/albertan017/LLM4Decompile.git`.

Repository commit: `85b364bf093eb2ee4f3687cfe38a203fca89f23e`.

Model: `LLM4Binary/llm4decompile-22b-v2`.

Resolved model snapshot: `be2ac0bbb3bfa508d9f8a4790329250f1cb13ddc`.

Model path:
`/home/shx/.cache/huggingface/hub/models--LLM4Binary--llm4decompile-22b-v2/snapshots/be2ac0bbb3bfa508d9f8a4790329250f1cb13ddc`.

This is an official LLM4Decompile model. `Dream-org/Dream-Coder-v0-Instruct-7B`
was not used and is not treated as a substitute.

The model README identifies the 22B v2 checkpoint as an LLM4Decompile-Ref model
that refines Ghidra pseudocode. The Phase 3a input contract for this producer is
therefore: selected function binary/build view to Ghidra pseudocode, plus sealed
signature and build metadata. The input must not contain trusted source bodies,
fixtures, labels, witnesses, extracted source literals, auditor probes, or Phase
1/2 failure examples.

Framework and hardware:

- Torch: `2.5.1+cu121`.
- CUDA runtime reported by Torch: `12.1`.
- Transformers: `4.38.2`.
- Hugging Face Hub: `0.36.2`.
- Accelerate: `1.13.0`.
- NVIDIA driver: `580.159.03`.
- GPU: NVIDIA H200 NVL, 143771 MiB total memory.
- Precision: BF16.
- Maximum batch size tested: 1.

Smoke command used the local snapshot, BF16, greedy decoding, batch size 1, and
a synthetic Ghidra-like pseudocode prompt. The prompt did not use any prior
Phase 1/2 function or future selected function.

Smoke result:

- Input tokens: 48.
- Output tokens: 21.
- Load time: 9.784 s.
- Generate time: 1.566 s.
- Total time: 11.416 s.
- Model memory after load: 43329.4 MiB.
- Peak memory during generation: 43392.7 MiB.
- Output preview:

```c
int func0(int x, int y) {
  return x + y;
}
```

Model-file hashes are recorded in
`results/decompile_faithfulness/phase3a_producer_availability.json`.

## Fixed General-Purpose API Producer

Status: available.

Provider: `mycodex`.

Endpoint: `https://wokeme.dpdns.org/v1/responses`.

Wire API: Responses API.

Requested model: `gpt-5.5`.

Returned model from smoke test: `gpt-5.5`.

Generation parameters to seal for future candidate generation:

- `temperature=0`.
- `max_output_tokens=2048`.
- `stream=false`.

Smoke test: passed with request id
`resp_01bf9d56c7c616b3016a4c771b4f308191a05dbc161e11e720` and total usage of
36 tokens. The smoke prompt was a non-project text prompt and did not use a
prior Phase 1/2 function or future selected source function.

Candidate generation must use one fixed reconstruction prompt per
function/build view. The API producer must not request multiple responses and
select the most favorable one.

## Gate Decision

Available producers after setup attempts: 4.

Blocked producers after setup attempts: 1.

The preregistered minimum of at least three available producers is satisfied.
Phase 3a may proceed to project acquisition, eligibility census construction,
function selection, fixture sealing, candidate generation, candidate sealing,
and exhaustive labeling.

