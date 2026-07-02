# Binary-Faithful Decompilation Phase 2 Candidate Generation Design

> **Superpowers mode:** This design uses `superpowers:brainstorming` and `superpowers:writing-plans` style reasoning. Execution remains local and serial only. Do not use `superpowers:subagent-driven-development`, Task/Spawn subagents, reviewer subagents, `tool_search`, multi-agent discovery, network, dependency installation, or GPU jobs while writing this plan.

## Why Phase 2 Planning Is Justified

Phase 2 is justified as **planning**, not immediate execution, because Phase 1 has passed only the narrowed source-known localized-bug gate:

- Phase 1K-v2 domain-aware dynamic trace passed:
  - LOCO AUC: `0.9531`
  - `gcd_positive`: `1.0000`
  - `fixture_collapse`: `False`
- Phase 1L ablation / leakage audit passed:
  - v2 AUC: `0.9531`
  - v1 mixed-domain AUC: `0.8906`
  - fixture-only oracle AUC: `1.0000`
  - static-only `min_slot` AUC: `0.8021`
  - leakage verdict: `no-label-or-output-leakage-found`

What did **not** succeed:

- General real-project decompilation faithfulness is not established.
- Static binary motifs are not a robust primary verifier.
- Symbolic/concolic route is not implemented; local dependencies are absent.

Therefore Phase 2 should not be real-project transfer. It should be candidate generation inside the existing source-known benchmark, using Phase 1K-v2 as the evaluator.

## Research Question

Can realistic generated candidates, produced by an LLM or decompiler-like source, create a useful candidate distribution for source-known localized semantic bug auditing, and does Dynamic Trace v2 remain informative on that distribution?

## Scope

In scope:

- Existing 8 built-in source-known C cases.
- Candidate generation only for those cases.
- Candidate labels start as `unknown`.
- Behavior gate maps generated candidates to:
  - `faithful`
  - `plausible_wrong`
  - `compile_fail`
- Dynamic Trace v2 is the primary scoring/evaluation method.
- GPU 2/3 may be used only after CPU-only manifest/evaluator checks pass.

Out of scope:

- Real-project transfer.
- New source cases.
- Network downloads.
- Dependency installation.
- Symbolic solver route.
- Training or fine-tuning.
- Claiming a general decompiler faithfulness verifier.

## Candidate Sources

Phase 2 should support multiple candidate sources, but the first runnable plan should start with the simplest available source.

### Source A: Local LLM Candidate Generation

Purpose:

- Generate multiple C function candidates per source-known case.
- Produce realistic faithful rewrites, partial bugs, and compile failures.

Constraints:

- Must use local model files only.
- In the current `llmxy` environment, do not set `CUDA_VISIBLE_DEVICES`; CUDA probing failed when devices were masked. Instead, check `nvidia-smi` first and explicitly move the model/tensors to `--device cuda:2` or `--device cuda:3`.
- Must write raw generations before cleaning.
- Must preserve prompt, sampling settings, model id/path, and generation timestamp.

### Source B: Decompiler-Like Candidate Import

Purpose:

- Allow future Ghidra/RetDec/other decompiler outputs to enter the same manifest format.

Constraints:

- This plan does not install or run those tools.
- It only defines the import contract.

### Source C: Manual / Synthetic Stress Candidates

Purpose:

- Preserve manually curated hard negatives as controls.

Constraints:

- Should not dominate Phase 2 metrics.
- Must be separately identified by `mutation_type`.

## Manifest Format

Reuse the existing `docs/paper_agent/decompile_faithfulness_candidate_format.md` shape, with optional metadata fields. Required fields remain:

```json
{
  "case_id": "gcd_positive",
  "candidates": [
    {
      "candidate_id": "llm_gcd_positive_0001",
      "label": "unknown",
      "mutation_type": "llm_generated",
      "function_source": "int gcd_positive(int a, int b) { ... }"
    }
  ]
}
```

Optional Phase 2 metadata fields:

```json
{
  "source_kind": "local_llm",
  "source_name": "model-or-tool-name",
  "prompt_id": "phase2_v1_signature_only",
  "raw_output_path": "analysis_outputs/decompile_faithfulness/phase2_candidate_generation/raw/...",
  "cleaning_status": "parsed_function",
  "generation_index": 0,
  "sampling": {
    "temperature": 0.6,
    "top_p": 0.95,
    "max_new_tokens": 512
  }
}
```

The current loader ignores optional fields, so Phase 2 can add metadata without breaking existing candidate ranking. If richer metadata is needed later, add a sidecar JSONL rather than changing evaluator semantics.

## Prompt Families

Use at least two prompt families so the generated distribution is not one-note.

### Prompt Family 1: Signature + Natural Spec

Input:

- function signature
- concise natural-language behavior summary
- constraints from fixture-domain inference

No original implementation body.

Expected candidates:

- realistic implementations;
- possible off-by-one, branch, loop, sign, or boundary bugs.

### Prompt Family 2: Rewrite From Source

Input:

- original function source
- instruction to rewrite equivalently using a different structure

Expected candidates:

- faithful rewrites;
- accidental semantic drift.

### Prompt Family 3: Bug-Seeding Prompt

Input:

- original function source
- instruction to produce a plausible but subtly wrong implementation

Expected candidates:

- useful hard negatives;
- must be marked `label=unknown` initially unless manually curated.

## Candidate Cleaning Rules

Cleaning must be deterministic and auditable:

- Extract exactly one C function with the expected function name.
- Reject candidates that include extra helper functions unless the evaluator is extended first.
- Reject candidates with preprocessor directives, includes, main functions, or comments that hide multiple implementations.
- Preserve raw output separately.
- Write cleaned function source into manifest only after extraction.

## Evaluation Pipeline

Phase 2 generated candidates should flow through:

1. Manifest validation.
2. Compile gate with `/usr/bin/gcc`.
3. Existing fixture behavior gate:
   - pass -> `faithful`
   - fail -> `plausible_wrong`
   - compile failure -> `compile_fail`
4. Dynamic Trace v2 audit over generated candidates.
5. Summary by:
   - case
   - prompt family
   - source kind
   - compile status
   - behavior label
   - Dynamic Trace v2 score

## Success Gates

Planning gate:

- Manifest schema is clear.
- Prompt families are defined.
- Output directories are defined.
- Compile/behavior/dynamic-trace evaluation path is defined.
- GPU command and stop conditions are explicit.

Smoke execution gate, for later:

- At least 2 candidates per case compile.
- At least 1 faithful and 1 plausible-wrong candidate are produced overall.
- Dynamic Trace v2 report runs without fixture collapse.

Full execution gate, for later:

- At least 8 cases represented.
- At least 5 compiling generated candidates per case.
- Both faithful and plausible-wrong labels appear in at least 5 cases.
- Dynamic Trace v2 remains non-oracle-like and shows separable score distributions.

## GPU Policy

No GPU was used while writing the original plan. GPU smoke execution was later approved and must remain small, local, and non-interfering with existing processes.

The current tested command pattern is:

```bash
/home/shx/miniconda3/envs/llmxy/bin/python -m analysis.decompile_faithfulness.run_phase2_gpu_smoke --device cuda:2
```

Do not set `CUDA_VISIBLE_DEVICES` in this environment unless CUDA availability has been re-tested after masking.

Minimum required command metadata:

- exact model path or model id;
- Python environment;
- script path;
- output manifest path;
- raw output path;
- max samples per case;
- prompt family;
- stop condition;
- expected runtime budget.

## Outputs

Plan-writing outputs:

- `docs/superpowers/specs/2026-06-17-binary-faithful-phase2-candidate-generation-design.md`
- `docs/superpowers/plans/2026-06-17-binary-faithful-phase2-candidate-generation.md`
- `docs/paper_agent/decompile_faithfulness_phase2_candidate_generation_plan.zh.md`

Later execution outputs, not created by this planning step:

- `analysis_outputs/decompile_faithfulness/phase2_candidate_generation/raw/`
- `analysis_outputs/decompile_faithfulness/phase2_candidate_generation/manifest.json`
- `analysis_outputs/decompile_faithfulness/phase2_candidate_generation/metadata.jsonl`
- `analysis_outputs/decompile_faithfulness/phase2_candidate_generation/eval/`

## Spec Self-Review

- Placeholder scan: no TODO/TBD placeholders remain.
- Scope check: this is a plan, not GPU execution.
- Boundary check: supports source-known localized semantic bug auditing, not real-project transfer.
- Safety check: no subagents, network, dependency installation, or GPU jobs are used during planning.
