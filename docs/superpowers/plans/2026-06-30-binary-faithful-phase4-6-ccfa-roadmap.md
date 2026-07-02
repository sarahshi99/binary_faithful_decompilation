# Binary-Faithful Phase 4-6 CCF-A Roadmap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` only. Do not use `superpowers:subagent-driven-development`, `superpowers:dispatching-parallel-agents`, Task/Spawn subagents, reviewer subagents, `tool_search`, or multi-agent workflows. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert Phase 1-3 evidence into a CCF-A-oriented roadmap, then execute Phase 4 paper synthesis before starting Phase 5/6 experiments.

**Architecture:** Phase 4 produces paper-facing artifacts and exact gates. Phase 5 expands the benchmark to real-project source-known C functions. Phase 6 evaluates decompiler-output or decompiler-like candidates while keeping original source as oracle.

**Tech Stack:** Python 3 standard library, existing `analysis.decompile_faithfulness` modules, existing JSON/Markdown reports, `unittest`, local C compiler flow already used by prior phases.

---

## File Structure

Create or modify these files during roadmap execution:

- Create: `docs/paper_agent/decompile_faithfulness_phase4_paper_synthesis.zh.md`
  - Chinese Phase 4 paper synthesis report.
- Create: `docs/paper_agent/decompile_faithfulness_phase4_evidence_index.json`
  - Machine-readable evidence map from Phase 1-3 reports.
- Create: `docs/paper_agent/decompile_faithfulness_phase4_paper_outline.md`
  - English 6-8 page paper skeleton.
- Create: `docs/paper_agent/decompile_faithfulness_phase5_real_project_transfer_design.zh.md`
  - Phase 5 design and function-selection policy.
- Create: `docs/superpowers/specs/2026-06-30-binary-faithful-phase5-real-project-transfer-design.md`
  - Executable Phase 5 spec.
- Create: `docs/superpowers/plans/2026-06-30-binary-faithful-phase5-real-project-transfer.md`
  - Executable Phase 5 plan.
- Create: `docs/paper_agent/decompile_faithfulness_phase6_decompiler_output_design.zh.md`
  - Phase 6 feasibility design.
- Create: `docs/superpowers/specs/2026-06-30-binary-faithful-phase6-decompiler-output-design.md`
  - Executable Phase 6 spec.
- Create: `docs/superpowers/plans/2026-06-30-binary-faithful-phase6-decompiler-output.md`
  - Executable Phase 6 plan.
- Optional after Phase 4: `analysis/decompile_faithfulness/build_phase4_evidence_index.py`
  - Deterministically builds the Phase 4 evidence index from existing JSON reports.
- Optional after Phase 4: `tests/test_decompile_faithfulness_phase4_evidence_index.py`
  - Unit tests for the evidence-index builder.

## Task 1: Phase 4 Evidence Inventory

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase4_evidence_index.json`
- Create: `docs/paper_agent/decompile_faithfulness_phase4_paper_synthesis.zh.md`

- [ ] **Step 1: Read the completed evidence reports**

Read these files:

```text
docs/paper_agent/decompile_faithfulness_phase1k_three_route_decision.zh.md
docs/paper_agent/decompile_faithfulness_phase1l_ablation.zh.md
docs/paper_agent/decompile_faithfulness_phase2_v3_boundary_trace.zh.md
docs/paper_agent/decompile_faithfulness_phase3_combinatorial_cpu_audit.zh.md
docs/paper_agent/decompile_faithfulness_phase3_gpu_generated_combined_analysis.zh.md
docs/paper_agent/decompile_faithfulness_ccf_a_readiness_audit.zh.md
```

- [ ] **Step 2: Write the evidence index JSON**

Create `docs/paper_agent/decompile_faithfulness_phase4_evidence_index.json` with this exact top-level shape:

```json
{
  "project_claim": "source-known recompilable bounded-input localized semantic bug auditing",
  "negative_evidence": [
    {"phase": "1B", "result": "naive global binary feature distance failed", "auc": 0.5},
    {"phase": "1I", "result": "static component combination borderline", "loco_auc": 0.6719},
    {"phase": "1J", "result": "structural binding still insufficient", "loco_auc": 0.6823}
  ],
  "positive_evidence": [
    {"phase": "1K-v2", "result": "domain-aware dynamic trace", "loco_auc": 0.9531, "fixture_collapse": false},
    {"phase": "2-v3", "result": "boundary-preserving dynamic trace on generated candidates", "pairwise_auc": 1.0, "fixture_collapse": false},
    {"phase": "3-cpu", "result": "source-known combinatorial CPU audit", "pairwise_auc": 1.0, "fixture_collapse": false},
    {"phase": "3-gpu", "result": "source-known generated-candidate smoke/top-up", "pairwise_auc": 1.0, "fixture_collapse": false}
  ],
  "known_limits": [
    "not a general binary-only verifier",
    "real-project source-known transfer not yet run",
    "decompiler-output feasibility not yet run",
    "Phase 3 generated paired cases remain small"
  ],
  "next_required_phases": ["Phase 4", "Phase 5", "Phase 6"]
}
```

- [ ] **Step 3: Write the Chinese synthesis report**

Create `docs/paper_agent/decompile_faithfulness_phase4_paper_synthesis.zh.md` with these sections:

```markdown
# Decompilation Faithfulness Phase 4 Paper Synthesis

## 当前可防守 claim

## 为什么不是 general verifier

## 负结果链条

## 正结果链条

## 方法核心假设

## 论文贡献草案

## 主结果表草案

## 失败案例和 non-oracle examples

## Phase 5/6 必须补的证据

## Phase 4 Gate
```

- [ ] **Step 4: Verify Phase 4 documents**

Run:

```bash
python -m json.tool docs/paper_agent/decompile_faithfulness_phase4_evidence_index.json >/tmp/phase4_evidence_index.pretty.json
```

Expected: exit code `0`.

## Task 2: Phase 4 Paper Skeleton

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase4_paper_outline.md`

- [ ] **Step 1: Write the paper skeleton**

Create `docs/paper_agent/decompile_faithfulness_phase4_paper_outline.md` with this exact section structure:

```markdown
# Boundary-Preserving Dynamic Traces for Source-Known Decompilation Faithfulness Auditing

## Abstract

## 1. Introduction

## 2. Motivation And Problem Definition

## 3. Method

## 4. Experimental Setup

## 5. Results

## 6. Analysis

## 7. Threats To Validity

## 8. Related Work

## 9. Conclusion

## Appendix A. Function And Candidate Manifests

## Appendix B. Additional Ablations
```

- [ ] **Step 2: Add the three contribution bullets**

Use these contribution bullets unless Phase 4 evidence contradicts them:

```text
1. We identify a failure mode of lightweight static/binary motifs and fixture-only validation for localized semantic faithfulness auditing.
2. We propose a boundary-preserving generated dynamic trace policy for source-known, bounded-input C functions.
3. We provide a staged empirical audit from curated cases to source-known generated candidates, with explicit gates for real-project and decompiler-output transfer.
```

- [ ] **Step 3: Add paper-facing claim boundary**

Add this paragraph to the Introduction and Threats sections:

```text
We do not claim binary-only equivalence checking or whole-program decompilation verification. The studied setting is source-known, recompilable, bounded-input, localized semantic bug auditing, where original source acts as the trace oracle.
```

- [ ] **Step 4: Verify paper skeleton has no placeholder markers**

Run:

```bash
rg "T[B]D|T[O]DO|F[I]XME|P[L]ACEHOLDER" docs/paper_agent/decompile_faithfulness_phase4_paper_outline.md
```

Expected: no matches and exit code `1`.

## Task 3: Phase 5 Real-Project Transfer Spec

**Files:**

- Create: `docs/superpowers/specs/2026-06-30-binary-faithful-phase5-real-project-transfer-design.md`
- Create: `docs/paper_agent/decompile_faithfulness_phase5_real_project_transfer_design.zh.md`

- [ ] **Step 1: Write the Phase 5 spec**

Create the spec with these required decisions:

```markdown
# Binary-Faithful Phase 5 Real-Project Source-Known Transfer Design

## Goal

Evaluate Dynamic Trace v3 on source-known functions extracted from small real C projects.

## Function Eligibility

- deterministic;
- integer-only first pass;
- bounded input domain;
- no I/O;
- no heap allocation;
- no external mutable state;
- original source can be compiled as oracle;
- fixtures cover ordinary and boundary behavior.

## Dataset Gate

- at least 30 eligible functions;
- at least 2 source projects;
- at least 100 compile-pass candidates;
- at least 20 paired functions.

## Method Gate

- Dynamic Trace v3 pairwise AUC >= 0.85;
- Dynamic Trace v3 beats best non-oracle baseline by >= 0.05 AUC;
- fixture_collapse=False;
- no undocumented risk-family AUC below 0.60.
```

- [ ] **Step 2: Write the Chinese Phase 5 design**

Create the Chinese report with these sections:

```markdown
# Decompilation Faithfulness Phase 5 Real-Project Source-Known Transfer

## 为什么 Phase 5 不是 binary-only

## 项目和函数选择标准

## Candidate 来源

## Baseline Matrix

## 成功 Gate

## 失败归因规则

## 预计产物
```

## Task 4: Phase 5 Executable Plan

**Files:**

- Create: `docs/superpowers/plans/2026-06-30-binary-faithful-phase5-real-project-transfer.md`

- [ ] **Step 1: Write Phase 5 plan header**

Use this exact header:

```markdown
# Binary-Faithful Phase 5 Real-Project Source-Known Transfer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` only. Do not use subagents or multi-agent workflows.

**Goal:** Build and evaluate a real-project source-known C function benchmark for Dynamic Trace v3.

**Architecture:** Select eligible functions, compile original source as oracle, create candidates, run v3 and baselines, then report paired AUC and failure taxonomy.

**Tech Stack:** Python 3, existing `analysis.decompile_faithfulness` modules, local C compiler, `unittest`.
```

- [ ] **Step 2: Add implementation tasks**

The plan must include these tasks with exact output files:

```text
Task 1: Real-project candidate source discovery
  output: docs/paper_agent/decompile_faithfulness_phase5_project_candidates.zh.md
Task 2: Function manifest and fixtures
  output: docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json
Task 3: Oracle compile preflight
  output: docs/paper_agent/decompile_faithfulness_phase5_preflight.json
Task 4: Candidate generation or import
  output: docs/paper_agent/decompile_faithfulness_phase5_candidate_manifest.json
Task 5: Baseline and v3 evaluation
  output: docs/paper_agent/decompile_faithfulness_phase5_result_analysis.zh.md
Task 6: Gate decision
  output: docs/paper_agent/decompile_faithfulness_phase5_gate_decision.zh.md
```

## Task 5: Phase 6 Decompiler-Output Feasibility Spec

**Files:**

- Create: `docs/superpowers/specs/2026-06-30-binary-faithful-phase6-decompiler-output-design.md`
- Create: `docs/paper_agent/decompile_faithfulness_phase6_decompiler_output_design.zh.md`

- [ ] **Step 1: Write the Phase 6 spec**

Create the spec with this gate:

```markdown
# Binary-Faithful Phase 6 Decompiler-Output Feasibility Design

## Goal

Evaluate source-known dynamic trace auditing on real decompiler-output or decompiler-like candidates.

## Scope Boundary

Original source remains the oracle. This phase does not claim binary-only equivalence.

## Success Gate

- at least 20 source-known functions with decompiler-output or decompiler-like candidates;
- at least 50 compile-pass candidates;
- at least 10 paired functions;
- Dynamic Trace v3 beats fixture-only and static-only baselines;
- behavior-preserving rewrite false-positive rate <= 10%, or every false positive has a documented trace-domain cause.
```

- [ ] **Step 2: Write the Chinese Phase 6 design**

Create the Chinese report with these sections:

```markdown
# Decompilation Faithfulness Phase 6 Decompiler-Output Feasibility

## 为什么仍然保留 source-known oracle

## 候选来源

## 工具依赖策略

## False Positive Control

## Failure Taxonomy

## 成功 Gate

## 何时可以写进 CCF-A 主实验
```

## Task 6: Phase 6 Executable Plan

**Files:**

- Create: `docs/superpowers/plans/2026-06-30-binary-faithful-phase6-decompiler-output.md`

- [ ] **Step 1: Write Phase 6 plan header**

Use this exact header:

```markdown
# Binary-Faithful Phase 6 Decompiler-Output Feasibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` only. Do not use subagents or multi-agent workflows.

**Goal:** Test whether Dynamic Trace v3 remains useful on decompiler-output or decompiler-like C candidates while preserving source-known oracle semantics.

**Architecture:** Probe available tools, import or generate candidates, compile candidates, run v3 and baselines, evaluate false positives and failure taxonomy.

**Tech Stack:** Python 3, existing `analysis.decompile_faithfulness` modules, local C compiler, optional local decompiler tools if already installed.
```

- [ ] **Step 2: Add dependency feasibility step**

The first task must check for local tools without installing anything:

```bash
command -v ghidraRun
command -v retdec-decompiler
command -v r2
command -v objdump
```

Expected interpretation:

- if no decompiler is available, write a `needs-decompiler-dependency-plan` verdict;
- if at least one decompiler is available, continue with source-known binary compilation and candidate import.

## Task 7: Verification

**Files:**

- Verify all files created above.

- [ ] **Step 1: Markdown/spec placeholder scan**

Run:

```bash
rg "T[B]D|T[O]DO|F[I]XME|P[L]ACEHOLDER" docs/paper_agent/decompile_faithfulness_phase4_evidence_index.json docs/paper_agent/decompile_faithfulness_phase4_paper_synthesis.zh.md docs/paper_agent/decompile_faithfulness_phase4_paper_outline.md docs/paper_agent/decompile_faithfulness_phase5_real_project_transfer_design.zh.md docs/paper_agent/decompile_faithfulness_phase6_decompiler_output_design.zh.md docs/superpowers/specs/2026-06-30-binary-faithful-phase5-real-project-transfer-design.md docs/superpowers/specs/2026-06-30-binary-faithful-phase6-decompiler-output-design.md docs/superpowers/plans/2026-06-30-binary-faithful-phase5-real-project-transfer.md docs/superpowers/plans/2026-06-30-binary-faithful-phase6-decompiler-output.md
```

Expected: no matches and exit code `1`.

- [ ] **Step 2: Subagent-template leak scan**

Run:

```bash
rg 'Subagent-Driven \(recommended\)|Use `superpowers:subagent-driven-development` \(recommended\)' docs/superpowers/specs/2026-06-30-binary-faithful-phase5-real-project-transfer-design.md docs/superpowers/specs/2026-06-30-binary-faithful-phase6-decompiler-output-design.md docs/superpowers/plans/2026-06-30-binary-faithful-phase5-real-project-transfer.md docs/superpowers/plans/2026-06-30-binary-faithful-phase6-decompiler-output.md
```

Expected: no matches and exit code `1`. Explicit bans on subagents are allowed; recommended subagent execution is not.

- [ ] **Step 3: JSON validation**

Run:

```bash
python -m json.tool docs/paper_agent/decompile_faithfulness_phase4_evidence_index.json >/tmp/phase4_evidence_index.pretty.json
```

Expected: exit code `0`.

- [ ] **Step 4: Diff hygiene**

Run:

```bash
git diff --check
```

Expected: exit code `0`.

## Execution Order

1. Execute Task 1 and Task 2 first. Do not start Phase 5 until the Phase 4 paper skeleton exists.
2. Execute Task 3 and Task 4 only after Phase 4 gate is accepted.
3. Execute Task 5 and Task 6 only after Phase 5 either passes or produces a specific blocker that Phase 6 can test.
4. Run Task 7 before claiming any phase is complete.

## Plan Self-Review

Spec coverage: The plan covers Phase 4 paper synthesis, Phase 5 real-project source-known transfer, and Phase 6 decompiler-output feasibility.

Placeholder scan: No unresolved placeholder markers are used as future work markers.

Subagent policy: The plan explicitly requires `superpowers:executing-plans` only.

Scope check: Phase 4 is the immediate executable target. Phase 5 and Phase 6 are written as gated follow-on plans, not automatic experiment launches.
