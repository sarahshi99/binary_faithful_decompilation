# Binary-Faithful Phase 6 Decompiler-Output Feasibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` only. Do not use subagents or multi-agent workflows.

**Goal:** Test whether Dynamic Trace v3 remains useful on decompiler-output or decompiler-like C candidates while preserving source-known oracle semantics.

**Architecture:** Probe available tools, import or generate candidates, compile candidates, run v3 and baselines, evaluate false positives and failure taxonomy.

**Tech Stack:** Python 3, existing `analysis.decompile_faithfulness` modules, local C compiler, optional local decompiler tools if already installed.

---

## Task 1: Dependency And Tool Feasibility

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase6_tool_feasibility.zh.md`

- [ ] **Step 1: Probe local tools without installing anything**

Run:

```bash
command -v ghidraRun
command -v retdec-decompiler
command -v r2
command -v objdump
```

- [ ] **Step 2: Write feasibility report**

Create `docs/paper_agent/decompile_faithfulness_phase6_tool_feasibility.zh.md` with sections:

```markdown
# Phase 6 Tool Feasibility

## Tool Probe

## Available Candidate Sources

## Dependency Decision

## Verdict
```

Allowed verdicts:

- `ready-for-real-decompiler-output-import`
- `ready-for-assembly-context-decompiler-like-generation`
- `needs-decompiler-dependency-plan`

## Task 2: Candidate Manifest

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase6_candidate_manifest.json`

- [ ] **Step 1: Create candidate manifest**

Use this top-level shape:

```json
{
  "phase": "phase6_decompiler_output_feasibility",
  "candidate_sources": [],
  "optimization_levels": [],
  "candidate_count": 0,
  "compile_pass_count": 0,
  "paired_function_count": 0,
  "candidates": []
}
```

Each candidate must include:

```json
{
  "candidate_id": "phase6_case_candidate",
  "case_id": "case_id",
  "source": "real_decompiler_output",
  "tool": "ghidra",
  "optimization_level": "O2",
  "candidate_path": "relative/path.c",
  "label_source": "source_known_oracle",
  "expected_role": "unknown"
}
```

- [ ] **Step 2: Enforce scale gate**

The main Phase 6 gate requires:

- at least 20 source-known functions with candidates;
- at least 50 compile-pass candidates;
- at least 10 paired functions.

If this is not met, set:

```json
"verdict": "phase6-feasibility-only"
```

## Task 3: Candidate Compile And Label Preflight

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase6_compile_preflight.json`
- Optional Create: `analysis/decompile_faithfulness/run_phase6_compile_preflight.py`
- Optional Create: `tests/test_decompile_faithfulness_phase6_compile_preflight.py`

- [ ] **Step 1: Compile candidates**

For each candidate:

- compile candidate function;
- reject forbidden calls;
- run fixtures;
- run source-known generated trace inputs;
- record timeout and crash outcomes.

- [ ] **Step 2: Write preflight JSON**

Use this top-level shape:

```json
{
  "phase": "phase6_compile_preflight",
  "candidate_count": 0,
  "compile_pass_count": 0,
  "runtime_timeout_count": 0,
  "failure_counts": {},
  "verdict": "not-run"
}
```

Allowed verdicts:

- `pass-phase6-compile-preflight`
- `phase6-feasibility-only`
- `blocked-candidate-compile`

## Task 4: Baseline And V3 Evaluation

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase6_result_analysis.zh.md`
- Optional Create: `analysis/decompile_faithfulness/run_phase6_decompiler_output_audit.py`
- Optional Create: `tests/test_decompile_faithfulness_phase6_decompiler_output_audit.py`

- [ ] **Step 1: Run baseline matrix**

Evaluate:

- fixture-only mismatch;
- static-only min-slot or structural score;
- Dynamic Trace v2 domain-aware;
- Dynamic Trace v3 boundary-preserving.

- [ ] **Step 2: Write result report**

The report must include:

- overall pairwise AUC;
- AUC by tool or candidate source;
- AUC by optimization level;
- AUC by risk family;
- fixture-passing wrong count;
- behavior-preserving rewrite false-positive rate;
- failure taxonomy.

## Task 5: Gate Decision

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase6_gate_decision.zh.md`

- [ ] **Step 1: Apply gate**

Phase 6 passes only if:

- at least 20 functions have decompiler-output or decompiler-like candidates;
- at least 50 compile-pass candidates;
- at least 10 paired functions;
- v3 beats fixture-only and static-only baselines;
- behavior-preserving rewrite false-positive rate `<= 10%`, or every false positive is explained.

- [ ] **Step 2: Write next decision**

Allowed decisions:

- `pass-phase6-ccfa-main-experiment-ready`
- `phase6-feasibility-only`
- `needs-decompiler-dependency-plan`
- `needs-more-decompiler-output-candidates`
- `method-negative-realistic-candidates`

## Task 6: Verification

- [ ] **Step 1: Validate JSON outputs**

Run:

```bash
python -m json.tool docs/paper_agent/decompile_faithfulness_phase6_candidate_manifest.json
python -m json.tool docs/paper_agent/decompile_faithfulness_phase6_compile_preflight.json
```

Expected: each command exits `0` after the corresponding file exists.

- [ ] **Step 2: Run targeted tests if scripts were created**

Run:

```bash
python -m unittest tests.test_decompile_faithfulness_phase6_compile_preflight tests.test_decompile_faithfulness_phase6_decompiler_output_audit
```

Expected: exit code `0`, unless a script was intentionally not created.

- [ ] **Step 3: Diff hygiene**

Run:

```bash
git diff --check
```

Expected: exit code `0`.
