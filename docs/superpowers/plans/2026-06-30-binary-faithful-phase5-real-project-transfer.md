# Binary-Faithful Phase 5 Real-Project Source-Known Transfer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` only. Do not use subagents or multi-agent workflows.

**Goal:** Build and evaluate a real-project source-known C function benchmark for Dynamic Trace v3.

**Architecture:** Select eligible functions, compile original source as oracle, create candidates, run v3 and baselines, then report paired AUC and failure taxonomy.

**Tech Stack:** Python 3, existing `analysis.decompile_faithfulness` modules, local C compiler, `unittest`.

---

## Task 1: Real-Project Candidate Source Discovery

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase5_project_candidates.zh.md`

- [ ] **Step 1: List local candidate source trees**

Run from `/home/shx/projects/binary_faithful_decompilation`:

```bash
find /home/shx/projects/binary_faithful_decompilation -path '*/.git' -prune -o -name '*.c' -print
```

Record local source trees only. Do not enter unrelated projects.

- [ ] **Step 2: Write the candidate report**

Create `docs/paper_agent/decompile_faithfulness_phase5_project_candidates.zh.md` with sections:

```markdown
# Phase 5 Project Candidates

## Candidate Source Trees

## Exclusion Rules

## Selected Projects

## Scale Risk

## Next Gate
```

The `Scale Risk` section must state whether the local repository can provide 30 eligible real-project functions. If not, the verdict must be `needs-external-source-plan`, not `pass`.

## Task 2: Function Manifest And Fixtures

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json`

- [ ] **Step 1: Create manifest schema**

Use this exact top-level shape:

```json
{
  "phase": "phase5_real_project_source_known_transfer",
  "function_count": 0,
  "source_projects": [],
  "functions": []
}
```

Each function entry must contain:

```json
{
  "case_id": "project_function_name",
  "project": "project_name",
  "source_path": "relative/path.c",
  "function_name": "function_name",
  "signature": "int function_name(int x)",
  "risk_families": ["boundary"],
  "domain": {"arity": 1, "values": [-2, -1, 0, 1, 2]},
  "fixtures": [{"args": [0], "expected": 0}],
  "eligibility": {
    "deterministic": true,
    "integer_only": true,
    "no_io": true,
    "no_heap": true,
    "no_external_state": true,
    "bounded_domain": true
  }
}
```

- [ ] **Step 2: Enforce scale gate**

If fewer than 30 eligible functions exist, write the manifest anyway and set:

```json
"verdict": "needs-more-real-project-functions"
```

Do not proceed to candidate generation when this verdict is present.

## Task 3: Oracle Compile Preflight

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase5_preflight.json`
- Optional Create: `analysis/decompile_faithfulness/run_phase5_preflight.py`
- Optional Create: `tests/test_decompile_faithfulness_phase5_preflight.py`

- [ ] **Step 1: Check each source oracle**

For each manifest function:

- compile original source;
- run fixtures;
- execute generated boundary inputs;
- record timeout or undefined behavior evidence.

- [ ] **Step 2: Write preflight output**

Use this top-level shape:

```json
{
  "phase": "phase5_preflight",
  "eligible_functions": 0,
  "compile_pass": 0,
  "fixture_pass": 0,
  "oracle_ready": 0,
  "verdict": "not-run"
}
```

Allowed verdicts:

- `pass-phase5-preflight`
- `needs-more-real-project-functions`
- `blocked-oracle-compile`
- `blocked-fixture-coverage`

## Task 4: Candidate Generation Or Import

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase5_candidate_manifest.json`

- [ ] **Step 1: Build candidate layers**

Create candidate entries for these layers:

- behavior-preserving rewrite;
- manual stress bug;
- LLM strict rewrite;
- LLM strict bug.

- [ ] **Step 2: Enforce no-smoke gate**

The candidate manifest must target:

- at least 100 compile-pass candidates;
- target 100-200 compile-pass candidates;
- at least 20 paired functions.

If the manifest cannot support this, set verdict:

```json
"verdict": "needs-full-candidate-generation"
```

## Task 5: Baseline And V3 Evaluation

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase5_result_analysis.zh.md`
- Optional Create: `analysis/decompile_faithfulness/run_phase5_real_project_transfer.py`
- Optional Create: `tests/test_decompile_faithfulness_phase5_real_project_transfer.py`

- [ ] **Step 1: Run required baselines**

Evaluate:

- fixture-only mismatch;
- static-only min-slot or structural score;
- Dynamic Trace v1 mixed-domain;
- Dynamic Trace v2 domain-aware;
- Dynamic Trace v3 boundary-preserving.

- [ ] **Step 2: Write result report**

The report must include:

- overall pairwise AUC;
- AUC by source project;
- AUC by risk family;
- AUC by candidate source;
- fixture-passing wrong count;
- behavior-preserving rewrite false-positive rate;
- compile failures;
- timeout count;
- failure attribution.

## Task 6: Gate Decision

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase5_gate_decision.zh.md`

- [ ] **Step 1: Apply pass gate**

Phase 5 passes only if:

- at least 30 eligible functions;
- at least 100 compile-pass candidates;
- at least 20 paired functions;
- v3 pairwise AUC `>= 0.85`;
- v3 beats best non-oracle baseline by `>= 0.05`;
- `fixture_collapse=False`;
- behavior-preserving false-positive rate `<= 10%`, or all false positives are explained.

- [ ] **Step 2: Decide next phase**

Allowed decisions:

- `pass-phase5-start-phase6-planning`
- `needs-more-real-project-functions`
- `needs-full-candidate-generation`
- `needs-risk-family-hardcase-analysis`
- `method-negative-real-project-transfer`

## Task 7: Verification

- [ ] **Step 1: Validate JSON outputs**

Run:

```bash
python -m json.tool docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json
python -m json.tool docs/paper_agent/decompile_faithfulness_phase5_preflight.json
python -m json.tool docs/paper_agent/decompile_faithfulness_phase5_candidate_manifest.json
```

Expected: each command exits `0` after the corresponding file exists.

- [ ] **Step 2: Run targeted tests if scripts were created**

Run:

```bash
python -m unittest tests.test_decompile_faithfulness_phase5_preflight tests.test_decompile_faithfulness_phase5_real_project_transfer
```

Expected: exit code `0`, unless a script was intentionally not created.

- [ ] **Step 3: Diff hygiene**

Run:

```bash
git diff --check
```

Expected: exit code `0`.
