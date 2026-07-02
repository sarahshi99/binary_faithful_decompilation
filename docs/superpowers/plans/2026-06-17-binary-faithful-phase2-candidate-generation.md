# Binary-Faithful Decompilation Phase 2 Candidate Generation Plan

> **For agentic workers:** Use `superpowers:brainstorming` and `superpowers:writing-plans` style planning only. Execute locally and serially. Do not use `superpowers:subagent-driven-development`, Task/Spawn subagents, reviewer subagents, `tool_search`, multi-agent discovery, network, dependency installation, or GPU jobs while writing this plan. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Design, but do not run, a Phase 2 candidate-generation experiment for the existing source-known benchmark. The goal is to create realistic generated candidates that can be evaluated by Dynamic Trace v2.

## Why This Is Only Planning

Phase 1K-v2 and Phase 1L succeeded inside the narrowed source-known localized-bug setting:

- Dynamic Trace v2 AUC: `0.9531`
- `gcd_positive`: `1.0000`
- Phase 1L leakage verdict: `no-label-or-output-leakage-found`

But real-project transfer has not been validated. Phase 2 starts as candidate generation inside the current 8-case benchmark.

## Task 1: Write Planning Summary

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase2_candidate_generation_plan.zh.md`

- [x] **Step 1: Explain Phase 2 gate**

State clearly:

- Phase 1 did not prove general decompilation faithfulness.
- Phase 1K-v2 / 1L did prove enough to plan source-known candidate generation.
- GPU is not started by this plan.

- [x] **Step 2: Define experiment scope**

Include:

- existing 8 source-known cases only;
- `label=unknown` for generated candidates;
- behavior gate resolves labels;
- Dynamic Trace v2 is primary evaluation.

## Task 2: Define Manifest And Metadata

**Files:**

- Modify or reference: `docs/paper_agent/decompile_faithfulness_candidate_format.md`
- Create or include in plan: Phase 2 metadata schema.

- [x] **Step 1: Reuse existing manifest**

Use the existing per-case manifest with:

- `case_id`
- `candidate_id`
- `label`
- `mutation_type`
- `function_source`

- [x] **Step 2: Add optional metadata**

Define optional fields:

- `source_kind`
- `source_name`
- `prompt_id`
- `raw_output_path`
- `cleaning_status`
- `generation_index`
- `sampling`

Do not require evaluator changes for optional metadata.

## Task 3: Define Prompt Families

**Files:**

- Create or include in plan: prompt-family definitions.

- [x] **Step 1: Signature + natural spec**

Candidate generation from signature and behavior summary only.

- [x] **Step 2: Source rewrite**

Candidate generation from original source, asking for equivalent rewrite.

- [x] **Step 3: Bug-seeding**

Candidate generation from original source, asking for plausible subtle bugs.

## Task 4: Define Cleaning And Validation

- [x] **Step 1: Cleaning rules**

Rules:

- exactly one expected C function;
- expected function name;
- no `main`;
- no includes/preprocessor directives;
- no helper functions unless evaluator is extended;
- raw output preserved.

- [x] **Step 2: Validation gates**

Rules:

- manifest JSON parses;
- each `case_id` exists;
- candidate ids are stable and unique within case;
- cleaned `function_source` compiles or is recorded as compile fail.

## Task 5: Define Evaluation Commands

- [x] **Step 1: CPU-only manifest/evaluator smoke**

Plan a smoke that validates manifest loading and compile/behavior gate before GPU generation.

- [x] **Step 2: Dynamic Trace v2 evaluation**

Plan a generated-candidate evaluator that computes:

- compile pass rate;
- behavior-label distribution;
- Dynamic Trace v2 score distribution;
- per-case and per-prompt summaries.

## Task 6: Define Optional GPU Run

- [x] **Step 1: Local model availability probe**

No network. Probe local model paths only.

- [x] **Step 2: GPU command template**

If later approved, first check `nvidia-smi`. In the current `llmxy` environment, do not set `CUDA_VISIBLE_DEVICES`; CUDA probing failed when devices were masked. Use explicit device placement instead:

```bash
/home/shx/miniconda3/envs/llmxy/bin/python -m analysis.decompile_faithfulness.run_phase2_gpu_smoke --device cuda:2
```

Include:

- model path;
- environment;
- output directories;
- candidates per case;
- prompt family;
- runtime budget;
- stop condition.

## Task 7: Success / Stop Conditions

- [x] **Step 1: Smoke gate**

Pass if:

- manifest validates;
- at least 2 candidates per case compile;
- at least one faithful and one plausible-wrong generated candidate exist overall;
- Dynamic Trace v2 evaluator runs.

- [x] **Step 2: Full gate**

Pass if:

- all 8 cases represented;
- at least 5 compiling generated candidates per case;
- both labels appear in at least 5 cases;
- v2 remains non-oracle-like.

Stop if:

- generated candidates mostly fail to compile;
- all candidates collapse to faithful trivial rewrites;
- all candidates collapse to obvious test-failing bugs;
- evaluation becomes fixture-only.

## Task 8: Verification

- [x] **Step 1: Check docs**

Run:

```bash
rg -n "TODO|TBD|subagent|Task/Spawn|tool_search" docs/superpowers/specs/2026-06-17-binary-faithful-phase2-candidate-generation-design.md docs/superpowers/plans/2026-06-17-binary-faithful-phase2-candidate-generation.md docs/paper_agent/decompile_faithfulness_phase2_candidate_generation_plan.zh.md
```

Expected:

- no TODO/TBD;
- subagent/tool_search only appear in prohibition text.

- [x] **Step 2: diff hygiene**

Run:

```bash
git diff --check
```

- [x] **Step 3: confirm no GPU execution**

Run:

```bash
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
```
