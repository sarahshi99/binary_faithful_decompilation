# Binary-Faithful Decompilation Phase 1K Three-Route Scout Design

> **Scope guard:** Work only under `/home/shx/projects/binary_faithful_decompilation`. Do not use subagents, Task/Spawn, reviewer subagents, `tool_search`, multi-agent discovery, or any other parallel-agent mechanism.

## Context

Phase 1A-1J show that lightweight static binary features are useful diagnostics but are not robust enough for transfer:

- Raw global binary distance failed on realistic faithful rewrites (`Phase 1B`, AUC `0.5000`).
- Multi-opt slot concentration was promising, then became borderline on harder cases (`Phase 1G`, AUC `0.7552`).
- Component-combination failed leave-one-case-out (`Phase 1I`, LOCO `0.6719`).
- CFG/return-binding static motifs also failed (`Phase 1J`, LOCO `0.6823`).

The next gate should not keep hand-patching static motifs. It should test three different recovery routes at scout scale before deciding whether this paper direction remains viable.

## Design Decision

Run Phase 1K as a **three-route scout**, not as a single Route A dynamic-trace experiment.

The three routes are:

1. **Route A: Dynamic trace gate**
2. **Route B: Symbolic / concolic feasibility probe**
3. **Route C: Narrowed localized-bug framing audit**

Route A is the first implementation-heavy experiment because it can run CPU-only on existing artifacts. Route B is a tooling/dependency feasibility probe first, not a full solver implementation. Route C is a research-claim audit that should happen before interpreting A/B as paper evidence.

Do not start GPU 2/3 jobs during Phase 1K scout. GPU will only be used later if the project explicitly switches to LLM/decompiler candidate generation and has a candidate manifest, prompt/extraction command, compile gate, label policy, and success criteria.

## Route A: Dynamic Trace Gate

Compile original and candidate C functions with a generated trace harness. Run both over deterministic generated inputs, then score output-vector differences and generic input-bucket mismatch rates.

### Purpose

Test whether a runtime semantic signal can separate faithful rewrites from localized semantic bugs on the existing 8-case / 56-candidate source-known set.

### Dynamic Trace Architecture

Create:

- `analysis/decompile_faithfulness/dynamic_trace.py`
- `analysis/decompile_faithfulness/run_dynamic_trace_audit.py`

Core responsibilities:

- Generate deterministic trace inputs from function arity and generic integer boundary values.
- Render a trace harness that prints one integer output per input.
- Compile and run original/candidate functions with the trace harness.
- Parse output vectors.
- Compute dynamic trace distances without using labels.
- Read Phase 1H artifact roots and evaluate candidate formulas with leave-one-case-out.

### Trace Input Policy

The primary score must use generated inputs, not the existing fixture tests.

Input generation:

- Infer arity from `case.tests[0].args`.
- Use a fixed integer value pool:
  - `-16, -8, -5, -3, -2, -1, 0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 12, 14, 16, 17, 21, 25, 31, 63, 127, 128, 170, 255, 256, 300`
- Include single-argument values directly for arity 1.
- For arity 2, include:
  - pair grid over compact pool `[-8, -3, -1, 0, 1, 2, 3, 5, 8, 12, 17, 25, 255]`
  - equality pairs
  - swapped fixture-like pairs
- For arity 3, include:
  - selected triples from compact pool `[-8, -1, 0, 1, 2, 3, 5, 8, 17]`
  - all-equal triples
  - ascending and descending triples
- Exclude exact tuples already present in `case.tests` from the primary generated set.
- Cap per case at `256` generated inputs, sorted deterministically.

Fixture tests are still run as diagnostics:

- `fixture_behavior_passed`
- `fixture_mismatch_rate`

but they are not the primary score.

### Route A Score Components

For each candidate:

- `trace_input_count`
- `trace_mismatch_count`
- `trace_mismatch_rate`
- `trace_abs_error_mean`
- `trace_abs_error_max`
- `trace_sign_mismatch_rate`
- `trace_zero_mismatch_rate`
- `trace_boundary_mismatch_rate`
- `trace_total`

`trace_total` is:

```text
trace_mismatch_rate
+ 0.25 * squashed(trace_abs_error_mean)
+ 0.25 * trace_sign_mismatch_rate
+ 0.25 * trace_zero_mismatch_rate
+ 0.25 * trace_boundary_mismatch_rate
```

Candidate formulas:

- `trace_mismatch_rate`
- `trace_total`
- `trace_total_plus_min_slot_0.10`
- `trace_total_plus_min_slot_0.25`
- `min_slot`

### Route A Gate

Success:

- LOCO AUC `>= 0.85`
- every hard case `>= 0.75`
- report shows generated-trace score is not identical to fixture-test pass/fail

Kill:

- LOCO AUC `< 0.75`
- two or more hard cases `< 0.667`
- the only useful signal is fixture behavior pass/fail
- scoring requires case-specific hand rules

## Route B: Symbolic / Concolic Feasibility Probe

Use symbolic path constraints, concolic execution, or a lightweight bounded relation summary to test whether solver-style semantics could explain the hard cases that static motifs miss.

### Purpose

Do not implement a full symbolic engine yet. First determine whether the local environment and project scope can support such a route without making dependency/tooling the paper.

### Probe Scope

The probe should report:

- availability of local packages such as `z3`, `angr`, or compiler/runtime tools;
- whether a no-new-dependency fallback exists for tiny bounded domains;
- which hard cases are plausible symbolic targets:
  - `signum`
  - `max3`
  - `gcd_positive`
  - `sum_to_n`
- what exact dependency plan would be required if external tools are needed.

### Route B Gate

Success:

- produces a concrete next plan for at least one case-general symbolic/concolic signature;
- identifies dependencies and failure modes clearly;
- avoids case-specific hand rules.

Kill:

- requires a large dependency install before any useful probe;
- solver/tooling complexity becomes the main work;
- only feasible by writing case-specific symbolic rules.

## Route C: Narrowed Localized-Bug Framing Audit

Re-evaluate the research claim after the negative static-feature results. This is a paper-scope audit, not a code experiment.

### Purpose

Decide whether the project should stop claiming general decompilation faithfulness and instead target source-known localized semantic bug auditing.

### Required Output

Create a claim matrix that states:

- which claims Phase 1A-1J support;
- which claims Phase 1A-1J refute or weaken;
- which claims would require real-project transfer;
- which claims are still possible after Phase 1K;
- what static binary features can be called:
  - primary verifier,
  - auxiliary diagnostic,
  - negative-result baseline.

### Route C Gate

Success:

- produces a defensible paper scope even if A/B are only partial positives;
- clearly separates source-known auditing from real-project decompiler transfer;
- explains how static features remain useful as diagnostics or baselines.

Kill:

- scope becomes too narrow to be interesting;
- contribution becomes mostly benchmark bookkeeping;
- no route can produce evidence beyond existing behavior tests.

## Combined Phase 1K Decision

After A/B/C are complete, write a combined Phase 1K decision:

- `continue-dynamic-trace`: Route A passes and is not oracle-like.
- `continue-symbolic-probe`: Route B finds a feasible, general symbolic/concolic route.
- `narrow-localized-bug-paper`: Route C gives a defensible narrowed paper even without transfer.
- `stop-current-direction`: none of A/B/C gives a defensible next step.

## GPU Policy

No GPU is used in Phase 1K three-route scout.

GPU 2/3 can be used only after a separate candidate-generation plan is written. That future plan must specify:

- model or decompiler source;
- prompt or extraction command;
- candidate manifest path;
- compile gate;
- label policy;
- success/failure criteria.

## Outputs

Route A creates:

- `analysis/decompile_faithfulness/dynamic_trace.py`
- `analysis/decompile_faithfulness/run_dynamic_trace_audit.py`
- `tests/test_decompile_faithfulness_dynamic_trace.py`
- `tests/test_decompile_faithfulness_dynamic_trace_audit.py`
- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.json`
- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.md`
- `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.zh.md`
- `analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace/records.jsonl`

Route B creates:

- `docs/paper_agent/decompile_faithfulness_phase1k_symbolic_probe.md`
- `docs/paper_agent/decompile_faithfulness_phase1k_symbolic_probe.zh.md`
- optionally `analysis_outputs/decompile_faithfulness/phase1k_symbolic_probe/environment.json`

Route C creates:

- `docs/paper_agent/decompile_faithfulness_phase1k_claim_matrix.zh.md`

Combined decision creates:

- `docs/paper_agent/decompile_faithfulness_phase1k_three_route_decision.zh.md`
- updates `docs/paper_agent/decompile_faithfulness_phase1_overview_and_next_steps.zh.md`

## Spec Self-Review

- Placeholder scan: no TBD/TODO placeholders remain.
- Internal consistency: this design now includes Route A/B/C and no longer defers B/C out of Phase 1K.
- Scope check: the design decomposes into three scout tasks plus one combined decision; each task is independently testable or reviewable.
- Ambiguity check: GPU usage is explicitly disallowed for Phase 1K; generated trace inputs exclude existing fixture tests from Route A primary score.
