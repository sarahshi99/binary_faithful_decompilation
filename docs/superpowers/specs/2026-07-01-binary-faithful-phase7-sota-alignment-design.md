# Binary-Faithful Phase 7 SOTA Alignment Design

> Superpowers mode: `superpowers:writing-plans` for this design, then `superpowers:executing-plans` and `superpowers:test-driven-development` for implementation. Subagents remain forbidden. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Phase 6/6R is complete as real-decompiler-output and cross-toolchain evidence:

- Ghidra real decompiler output passes on `38` source-known functions.
- Two binary-producing GCC toolchains pass (`default-gcc`, `gcc-9.4.0`).
- radare2 importability passes, but its `pdc` output is pseudo-C and not compile-ready.

Phase 7 should answer a different question:

> Can Dynamic Trace v3 be positioned against related-work SOTA baselines on public or SOTA-aligned decompilation benchmarks?

This is not another Phase 6 run. It is a claim-alignment and external-baseline phase.

## Related-work Positioning

The project should not claim to be a better decompiler generator unless we actually generate better source. The safer paper position is:

> Dynamic Trace v3 is a source-known semantic drift auditor for decompiler / LLM-generated C candidates.

Related work to align with:

- LLM4Decompile / Decompile-Eval: focuses on re-compilability and re-executability as practical decompilation metrics. Source: `https://arxiv.org/abs/2403.05286`.
- DecompileBench: emphasizes real-world functions, runtime-aware validation, functionality correctness, and semantic fidelity. Source: `https://aclanthology.org/2025.findings-acl.1194/`.
- Decompile-Bench: million-scale binary-source function pairs and real-world evaluation splits. Source: `https://openreview.net/forum?id=RhhP5A7C5W`.
- CodeFuse-DeBench: benchmark framework with readability, recompilation, and functionality stages. Source: `https://github.com/codefuse-ai/CodeFuse-DeBench`.
- Recent LLM decompilation methods increasingly report multi-compiler, multi-optimization, and re-executability improvements, so Phase 7 must avoid a single-tool / single-split claim.

## Claim Boundary

Allowed Phase 7 claims if successful:

1. Dynamic Trace v3 is a strong auditor for fixture-passing semantic drift on source-known bounded functions.
2. The signal transfers from curated/project-local functions to public or SOTA-aligned benchmark functions.
3. It complements re-compilability / re-executability metrics by finding semantic drifts that fixture-only validation misses.

Forbidden Phase 7 claims unless later evidence supports them:

1. Binary-only semantic equivalence.
2. Better decompiler generation than LLM4Decompile / DecompileBench systems.
3. External-paper SOTA without explicit public benchmark and baseline rows.

## Routes

### Route A: Public Benchmark Preflight

Import or emulate a public benchmark split without training:

- Decompile-Eval / HumanEval-style functions.
- ExeBench-style functions.
- DecompileBench or CodeFuse-DeBench subset if locally obtainable.

Outputs:

- Benchmark availability matrix.
- License / reproducibility notes.
- Function extraction feasibility.
- Compile/run feasibility.

Pros: establishes external-validity path.

Risks: public datasets may require download, dependency setup, or nontrivial adapters.

Decision: must run first.

### Route B: External Baseline Matrix

Evaluate Dynamic Trace v3 against baselines on the imported split:

- fixture-only / re-execution-only.
- static structured proxy.
- Dynamic Trace v1/v2/v3 ablations.
- LLM judge baseline if a local/API judge is approved.
- optional fuzzing-style / symbolic sanity if dependencies become available.

Outputs:

- AUC / recall at fixed FP.
- behavior-preserving false positive rate.
- fixture-passing wrong recall.
- runtime/cost per candidate.

Pros: this is the actual SOTA-alignment table.

Risks: LLM judge baseline may require GPU/API; symbolic baseline may require dependencies.

Decision: run after Route A confirms an importable split.

### Route C: Second Compile-ready Decompiler Source

Add at least one compile-ready decompiler beyond Ghidra:

- RetDec if installable.
- rev.ng if installable.
- angr/AIL if feasible.
- Hex-Rays / Binary Ninja only if licenses/tools are already available.

Outputs:

- compile-ready candidate count.
- paired case count.
- v3 delta vs baselines.
- failure taxonomy.

Pros: addresses the current biggest Phase 6R limitation.

Risks: dependency and normalization cost.

Decision: recommended, but can run after Route A/B if dependency setup is expensive.

### Route D: GPU LLM Candidate / Baseline

Use GPU 0/1 only when the experiment genuinely needs model inference:

- LLM decompiler candidate generation.
- LLM repair/refinement baseline.
- LLM judge baseline if local model is used.

Outputs:

- model/cuda manifest.
- prompt and decoding settings.
- compile-pass and re-executability metrics.
- semantic drift detection metrics.

Pros: directly connects to LLM decompilation papers.

Risks: cost, prompt sensitivity, model availability.

Decision: do not start before CPU benchmark preflight passes.

## Success Gates

### Phase 7A Preflight Gate

Pass if:

- At least one public or SOTA-aligned benchmark source is usable.
- At least `50` functions can be extracted or represented as source-known functions.
- At least `30` functions compile and run in the local harness.
- At least `2` optimization levels or compiler variants are feasible.
- The plan records whether network/download approval was needed.

Fail states:

- `blocked-no-public-benchmark`
- `blocked-benchmark-license-or-format`
- `blocked-compile-harness`

### Phase 7B Main Alignment Gate

Pass if:

- At least `100` compile-pass candidates.
- At least `30` paired faithful/wrong functions.
- Dynamic Trace v3 beats fixture-only and static structured baselines.
- Delta over best non-oracle baseline is `>= 0.05`.
- Behavior-preserving false positive rate is `<= 10%`.
- Report includes per-risk-family breakdown and failure taxonomy.

Fail states:

- `method-negative-public-benchmark`
- `needs-more-public-candidates`
- `blocked-baseline-reproduction`

### Phase 7C External SOTA Claim Gate

External SOTA claim is allowed only if:

- There is a public benchmark row.
- There are explicit related-work baseline rows or faithfully reproduced proxies.
- There is at least one non-Ghidra compile-ready decompiler candidate source, or the paper narrows the claim to Ghidra/source-known auditing.
- Metrics match the literature language: re-compilability, re-executability/functionality, semantic drift detection, false positive rate, and cost.

Otherwise the claim must stay:

`SOTA-aligned source-known semantic auditing evidence`, not `external-paper SOTA`.

## Expected Output Files

- `docs/paper_agent/decompile_faithfulness_phase7_sota_alignment_plan.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase7_benchmark_feasibility.json`
- `docs/paper_agent/decompile_faithfulness_phase7_benchmark_feasibility.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase7_public_benchmark_result.json`
- `docs/paper_agent/decompile_faithfulness_phase7_public_benchmark_result.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase7_sota_gate_decision.zh.md`

## Design Decision

`start-phase7a-public-benchmark-preflight`

Do not start GPU 0/1 yet. Do not claim external SOTA yet. First build the benchmark feasibility and baseline alignment harness.
