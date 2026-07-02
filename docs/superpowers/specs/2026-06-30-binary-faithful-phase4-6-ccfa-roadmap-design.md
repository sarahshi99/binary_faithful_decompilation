# Binary-Faithful Decompilation Phase 4-6 CCF-A Roadmap Design

> **Superpowers mode:** This design was produced using the local Superpowers plugin documents for `superpowers:brainstorming`, `superpowers:using-git-worktrees`, and `superpowers:writing-plans`. The current Codex session did not expose `superpowers:*` as first-class skills, so the workflow was followed from the installed plugin cache. Project override remains active: do not use `superpowers:subagent-driven-development`, `superpowers:dispatching-parallel-agents`, Task/Spawn subagents, reviewer subagents, `tool_search`, or multi-agent workflows. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Context

The project has moved from broad exploratory decompilation faithfulness checking to a narrower and better-supported claim:

> Source-known, recompilable, bounded-input localized semantic bug auditing for decompiler/LLM-generated C candidates.

The evidence is strong for this narrowed setting but insufficient for a CCF-A submission as a general binary-only verifier.

Key evidence:

- Phase 1 static/binary motif route is negative or borderline: Phase 1B AUC `0.5000`, Phase 1I LOCO `0.6719`, Phase 1J LOCO `0.6823`.
- Phase 1K-v2 dynamic trace passes the localized-bug gate: LOCO AUC `0.9531`, `gcd_positive=1.0000`, `fixture_collapse=False`.
- Phase 1L finds no label/output leakage and shows dynamic trace is stronger than static-only min-slot.
- Phase 2 v3 boundary trace passes on generated candidates: AUC `1.0000`, 8/8 case AUC `1.0000`, `fixture_collapse=False`.
- Phase 3 source-known transfer readiness is positive: 12 source-known functions, 3289 enumerated subsets, CPU manual-stress AUC `1.0000`.
- Phase 3 GPU generated combined analysis is positive but still small: 47 generated candidates, 28 compile-pass, 5 paired cases, AUC `1.0000`, `fixture_collapse=False`.

## Brainstorming Review

### Approach A: Linear Gate Roadmap

Phase 4 synthesizes the paper and locks the claim boundary. Phase 5 expands to real-project source-known transfer. Phase 6 then tests decompiler-output or binary-oriented feasibility.

Pros:

- Keeps claims aligned with evidence.
- Prevents Phase 5/6 from becoming open-ended experiment sprawl.
- Makes failures diagnosable by phase.
- Produces paper artifacts early enough to guide experiments.

Cons:

- Slower to reach real decompiler outputs.
- Requires disciplined stopping gates.

### Approach B: Parallel Phase 5/6 Immediately

Run real-project transfer and decompiler-output experiments at the same time.

Pros:

- Faster discovery if tooling works.
- May surface paper-facing examples early.

Cons:

- High risk of mixing source selection, decompiler tool failures, candidate labeling, and method failures.
- Harder to know whether a negative result is a method problem or an experimental setup problem.
- More likely to overclaim before the problem statement is stable.

### Approach C: Paper-Only Before Any New Experiment

Freeze experiments and write a full draft before Phase 5.

Pros:

- Clarifies the argument and contribution.
- Forces the negative-result story and method formalization to become explicit.

Cons:

- CCF-A evidence will remain too narrow.
- The draft may become disconnected from the external-validity experiments reviewers will ask for.

## Final Design Decision

Use Approach A.

Phase 4 is mandatory before major new experiments. Phase 5 starts only after Phase 4 identifies the exact baseline matrix, result table shape, and claim boundary. Phase 6 starts only after Phase 5 passes a real-project source-known transfer gate or produces a clear blocking diagnosis.

## Worktree Decision

`superpowers:using-git-worktrees` was reviewed and the current repository was checked:

- `git rev-parse --git-dir`: `.git`
- `git rev-parse --git-common-dir`: `.git`
- current branch: `phase1a-audit`
- no superproject path

This is a normal checkout, not a linked worktree. For this roadmap-only change, do not create a new worktree because the current working tree contains many uncommitted Phase 1-3 experiment artifacts that are part of the planning context. Future implementation branches may use worktrees after the relevant experiment artifacts are committed or otherwise snapshotted.

## Phase 4: Paper Synthesis And Claim Shaping

### Goal

Turn Phase 1-3 into a defensible paper package: problem definition, method formalization, evidence map, main tables, negative-result story, and Phase 5/6 experiment requirements.

### Research Question

What is the strongest claim that Phase 1-3 evidence supports without overstating the method as a general binary-only decompilation verifier?

### In Scope

- Paper skeleton.
- Claim boundary.
- Contribution bullets.
- Method formalization.
- Literature and baseline matrix.
- Evidence inventory.
- Main result table.
- Negative-result table.
- Non-oracle motivating examples.
- Phase 5/6 gate definitions.

### Out Of Scope

- New GPU generation.
- Real-project transfer.
- Decompiler installation.
- Symbolic/concolic dependency installation.
- Binary-only equivalence claims.

### Success Gate

Phase 4 passes when all of the following are true:

- A 6-8 page paper skeleton exists.
- The paper has exactly 3 primary contribution bullets.
- Every contribution maps to at least one completed experiment and one planned external-validity experiment.
- The claim boundary explicitly says source-known, recompilable, bounded-input, localized semantic bug auditing.
- A literature/baseline matrix identifies at least 5 baseline families.
- Main positive and negative result tables are drafted.
- At least 2 non-oracle examples are written in paper-facing form.
- Phase 5 and Phase 6 are each reduced to executable gates rather than vague future work.

## Phase 5: Real-Project Source-Known Transfer

### Goal

Test whether Dynamic Trace v3 transfers from curated small functions to source-known functions extracted from small real C projects.

### Research Question

Does the boundary-preserving dynamic trace signal remain useful on real-project source-known functions, while outperforming fixture-only and static/binary similarity baselines?

### In Scope

- 2-3 small C projects or self-contained real-project modules.
- Deterministic integer-returning C functions.
- No I/O, no heap, no external state, no callbacks in the first pass.
- Original source compiled as oracle.
- Bounded generated inputs.
- Manual stress candidates and generated or decompiler-like candidates.
- Baselines:
  - fixture-only mismatch;
  - static-only min-slot or available structural score;
  - v1 mixed-domain dynamic trace;
  - v2 domain-aware trace;
  - v3 boundary trace.

### Out Of Scope

- Arbitrary project-wide decompilation.
- Functions with complex memory ownership.
- Functions requiring system calls, files, networking, nondeterminism, or undefined behavior.
- Binary-only oracle-free equivalence.

### Success Gate

Phase 5 passes if:

- At least 30 source-known real-project functions pass compile, fixture, and oracle preflight.
- At least 100 compile-pass candidates are evaluated across the function set.
- At least 20 functions have faithful/wrong pairs.
- Dynamic Trace v3 has pairwise AUC at least `0.85`.
- Dynamic Trace v3 beats the best non-oracle baseline by at least `0.05` AUC.
- `fixture_collapse=False`.
- At least 5 fixture-passing wrong candidates are either found or the report explains why the candidate source did not produce them.
- No risk family has catastrophic collapse, defined as paired-case AUC below `0.60` without a documented hard-case explanation.

Phase 5 is borderline, not failed, if data coverage is insufficient but the method signal remains positive. It fails only when there is enough paired data and v3 does not beat baselines.

## Phase 6: Decompiler-Output / Binary-Oriented Feasibility

### Goal

Check whether the source-known trace-oracle method remains useful when candidate code comes from real decompiler outputs or decompiler-like generation.

### Research Question

Can source-known dynamic trace auditing detect localized semantic drift in decompiler-output candidates without punishing behavior-preserving rewrites too aggressively?

### In Scope

- Source-known original C functions remain the oracle.
- Binaries may be generated at multiple optimization levels.
- Candidate sources may come from real decompiler output if tools are available, or decompiler-style LLM generations if not.
- Behavior-preserving rewrites are included as false-positive controls.
- Failure taxonomy is required.

### Out Of Scope

- Full binary-only semantic equivalence.
- Whole-program decompilation correctness.
- Automatic proof of correctness.
- Installing heavyweight dependencies without a separate dependency plan.

### Success Gate

Phase 6 passes if:

- At least 20 source-known functions have decompiler-output or decompiler-like candidates.
- At least 50 compile-pass candidates are evaluated.
- At least 10 functions have faithful/wrong pairs.
- Dynamic Trace v3 beats fixture-only and static-only baselines.
- False-positive rate on behavior-preserving rewrites is at most `10%`, or every false positive is categorized with a concrete trace-domain issue.
- The report contains a failure taxonomy with at least these categories:
  - decompiler syntax failure;
  - compile failure;
  - undefined-behavior mismatch;
  - trace-domain miss;
  - fixture-passing semantic drift;
  - behavior-preserving rewrite false positive.

Phase 6 may be split into Phase 6A dependency/tool feasibility and Phase 6B candidate evaluation if decompiler tooling is unavailable.

## CCF-A Readiness Interpretation

The project is not CCF-A complete after Phase 3. It becomes a credible CCF-A candidate only if:

- Phase 4 gives a clear paper story and contribution map.
- Phase 5 establishes external validity on real-project source-known functions.
- Phase 6 demonstrates feasibility on decompiler-output or decompiler-like candidates, while keeping claims source-known and bounded.

The safest final claim remains:

> Boundary-preserving generated dynamic traces provide a lightweight, source-known semantic auditing signal for localized decompilation/LLM-candidate bugs, outperforming fixture-only and lightweight static/binary motifs in bounded small-function settings.

## Design Self-Review

Placeholder scan: no unresolved placeholder markers or unspecified phase gates remain.

Internal consistency: Phase 4 is paper synthesis, Phase 5 is real-project source-known transfer, and Phase 6 is decompiler-output feasibility. Each later phase depends on the previous phase's gates.

Scope check: This design is a roadmap with three gated subprojects. The implementation plan should keep Phase 4 as the immediate executable target and define Phase 5/6 as gated follow-on plans.

Ambiguity check: The design explicitly rejects general binary-only equivalence claims and subagent workflows.
