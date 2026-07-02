# Binary-Faithful Decompilation Phase 3 Readiness Plan

> **For agentic workers:** Use `superpowers:executing-plans` style execution only. Do not use `superpowers:subagent-driven-development`, Task/Spawn subagents, reviewer subagents, `tool_search`, multi-agent discovery, network, dependency installation, or GPU jobs. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Decide whether Phase 3 can start now. This plan should produce a CPU-only readiness report and, if needed, stop before GPU or real-project transfer.

## Task 1: Write Phase 2 -> Phase 3 Transition

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase2_phase3_transition.zh.md`

- [x] **Step 1: Explain what succeeded**

Cover:

- Phase 1K-v2 method gate;
- Phase 1L leakage/ablation;
- Phase 2 generated candidate gate;
- Phase 2 v3 boundary-trace refinement.

- [x] **Step 2: Explain what did not succeed**

State clearly:

- no general verifier claim;
- no arbitrary real-project transfer;
- no binary-only equivalence;
- no need to keep increasing GPU generation volume before source selection.

## Task 2: Write Phase 3 Readiness Design

**Files:**

- Create: `docs/superpowers/specs/2026-06-18-binary-faithful-phase3-readiness-design.md`

- [x] **Step 1: Define Phase 3 as readiness**

Use the narrowed name: source-known small-function transfer readiness check.

- [x] **Step 2: Define source selection criteria**

Require:

- exact source path;
- exact function name;
- integer-only first pass;
- bounded input domain;
- fixtures;
- oracle policy.

## Task 3: Implement CPU-only Preflight

**Files:**

- Create: `analysis/decompile_faithfulness/run_phase3_readiness_preflight.py`
- Create: `tests/test_decompile_faithfulness_phase3_readiness_preflight.py`

- [x] **Step 1: Read Phase 2 v3 method gate**

Load `docs/paper_agent/decompile_faithfulness_phase2_v3_boundary_trace.json` and require:

- verdict `pass-v3-boundary-trace`;
- pairwise AUC at least `0.9623`;
- `fixture_collapse=False`;
- trace-zero blind spot wrong count `0`.

- [x] **Step 2: Scan repository source candidates**

Find `.c` / `.h` files outside generated/documentation/test directories. Exclude:

- `.git`;
- `analysis_outputs`;
- `docs`;
- `tests`;
- `__pycache__`.

- [x] **Step 3: Check Phase 3 source manifest**

Look for `docs/paper_agent/decompile_faithfulness_phase3_source_manifest.json`.

Verdicts:

- `blocked-method-gate`;
- `needs-phase3-source-manifest`;
- `needs-more-phase3-sources`;
- `needs-oracle-fixture-coverage`;
- `ready-for-phase3-cpu-audit`.

## Task 4: Run Preflight

**Command:**

```bash
python -m analysis.decompile_faithfulness.run_phase3_readiness_preflight
```

Expected current outcome:

- method gate passes;
- Phase 3 source manifest is missing;
- verdict is `needs-phase3-source-manifest`;
- no GPU job is started.

## Task 5: Verification

- [x] **Step 1: Unit tests**

```bash
python -m unittest tests.test_decompile_faithfulness_phase3_readiness_preflight
```

- [x] **Step 2: Run preflight**

```bash
python -m analysis.decompile_faithfulness.run_phase3_readiness_preflight
```

- [x] **Step 3: Full test suite**

```bash
python -m unittest discover -s tests
```

- [x] **Step 4: Diff hygiene**

```bash
git diff --check
```

## Next Decision

## Task 6: Combinatorial Source Selection

**Files:**

- Create: `analysis_inputs/decompile_faithfulness/phase3_sources/*.c`
- Create: `docs/paper_agent/decompile_faithfulness_phase3_source_pool.json`
- Create: `analysis/decompile_faithfulness/select_phase3_source_subsets.py`
- Create: `tests/test_decompile_faithfulness_phase3_source_selection.py`
- Create: `docs/paper_agent/decompile_faithfulness_phase3_source_selection.zh.md`
- Create: `docs/paper_agent/decompile_faithfulness_phase3_source_selection.json`

- [x] **Step 1: Build source pool**

Create 12 source-known small C functions covering:

- branch;
- loop;
- bitwise;
- division/modulo;
- sign/zero;
- boundary;
- multi-argument behavior.

- [x] **Step 2: Validate pool**

Compile each original source and run fixtures.

- [x] **Step 3: Enumerate subsets**

Enumerate all eligible 5-10 function subsets and rank them by critical tag and risk-family coverage.

- [x] **Step 4: Avoid one-shot selection**

Report:

- best subset for each size 5-10;
- recommended minimal 5, balanced 7, broad 10, and low-overlap backup subsets;
- explicit negative-conclusion policy.

## Updated Next Decision

The current source-selection verdict is `ready-for-combinatorial-phase3-cpu-audit`.

## Task 7: Combinatorial CPU Audit

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase3_candidate_pool.json`
- Create: `analysis/decompile_faithfulness/run_phase3_combinatorial_cpu_audit.py`
- Create: `tests/test_decompile_faithfulness_phase3_combinatorial_cpu_audit.py`
- Create: `docs/paper_agent/decompile_faithfulness_phase3_combinatorial_cpu_audit.zh.md`
- Create: `docs/paper_agent/decompile_faithfulness_phase3_combinatorial_cpu_audit.json`

- [x] **Step 1: Build manual stress candidates**

Include both obvious fixture-failing candidates and fixture-passing semantic drifts.

- [x] **Step 2: Run v3 boundary trace over all 12 functions**

Use source-known original functions as oracle and evaluate manual candidates.

- [x] **Step 3: Evaluate recommended subsets**

Require minimal / balanced / broad / low-overlap subsets to avoid fixture collapse.

- [x] **Step 4: Record verdict**

Observed:

- candidate count `28`;
- overall AUC `1.0000`;
- 5/5 recommended subsets AUC `1.0000`;
- fixture collapse `False`;
- fixture-passing wrong count `4`;
- verdict `pass-combinatorial-phase3-cpu-audit`.

## Task 8: Phase 3 GPU Generated Smoke Preparation

**Files:**

- Create: `analysis/decompile_faithfulness/run_phase3_gpu_generated_smoke.py`
- Create: `tests/test_decompile_faithfulness_phase3_gpu_generated_smoke.py`

- [x] **Step 1: Prepare GPU smoke script**

Default run targets recommended subset rank 1, with `strict_rewrite` and `strict_bug` prompts.

- [x] **Step 2: Keep GPU launch gated**

Do not launch while GPU 2/3 are busy. The script uses explicit `--device cuda:2` / `cuda:3` placement and does not set `CUDA_VISIBLE_DEVICES`.

## Task 9: Phase 3 GPU Generated Runs

**Files:**

- Create: `analysis/decompile_faithfulness/analyze_phase3_gpu_generated_smoke.py`
- Create: `tests/test_decompile_faithfulness_phase3_gpu_generated_analysis.py`
- Create: `docs/paper_agent/decompile_faithfulness_phase3_gpu_generated_combined_analysis.zh.md`
- Create: `docs/paper_agent/decompile_faithfulness_phase3_gpu_generated_combined_analysis.json`

- [x] **Step 1: Launch cuda:2 / cuda:3 base smoke**

Initial `torch_dtype=auto` runs loaded the model but failed during generation with CUDA OOM. Raw outputs were empty and the verdict was `needs-generation-cleaning`.

- [x] **Step 2: Re-run with fp16**

Re-ran both GPUs with:

- `--torch-dtype float16`;
- `--steps 24`;
- explicit `--device cuda:2` / `cuda:3`;
- separate output directories.

- [x] **Step 3: Top up bug prompts**

Ran targeted `strict_bug` top-ups with `temperature=0.4`, `top_p=0.95`, and `candidates-per-prompt=3`.

- [x] **Step 4: Combined analysis**

Combined four runs:

- `cuda2_base`;
- `cuda2_bugtopup`;
- `cuda3_base`;
- `cuda3_bugtopup`.

Observed:

- generated candidates `47`;
- compile-pass candidates `28`;
- labels: `faithful=16`, `plausible_wrong=12`, `compile_fail=19`;
- paired cases `5`;
- pair count `26`;
- pairwise AUC `1.0000`;
- fixture collapse `False`;
- fixture-passing trace mismatch count `1`;
- verdict `pass-phase3-gpu-generated-combined-analysis`.

## Updated Next Decision

Phase 3 now has both CPU manual-stress evidence and GPU generated-candidate evidence on the new source pool. The next work should be result analysis / claim shaping, not another immediate GPU run, unless we specifically want to expand paired-case coverage beyond 5 cases.
