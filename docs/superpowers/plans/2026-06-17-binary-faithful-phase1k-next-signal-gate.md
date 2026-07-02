# Binary-Faithful Decompilation Phase 1K Next-Signal Gate Plan

> **For agentic workers:** Use local serial execution only. Do not use subagents, Task/Spawn, dispatching/parallel agents, reviewer subagents, `tool_search`, or multi-agent discovery. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Why This Plan Exists

Phase 1J did not pass:

- LOCO AUC: `0.6823`
- Hard cases:
  - `signum`: `0.5000`
  - `gcd_positive`: `0.5833`
  - `max3`: `0.6667`
  - `sum_to_n`: `0.5833`
- Verdict: `do-not-transfer-yet`

This means the current lightweight static binary motif direction should not be pushed directly into real-project transfer or expensive GPU-driven candidate generation.

## Goal

Run a three-route scout that can decide whether this paper direction remains viable:

1. Dynamic trace gate
2. Symbolic / concolic trace gate
3. Narrowed localized-bug framing

The output should be a clear go/no-go decision for real-project transfer and for any GPU 2/3 usage.

## GPU Policy

GPU 2/3 are allowed only for candidate generation or model inference after the candidate-generation task is explicitly defined.

Do not use GPU for:

- `gcc`
- `objdump`
- `nm`
- existing static feature audits
- Phase 1J-style formula search
- documentation-only work

If a GPU job is introduced, it must use:

```bash
CUDA_VISIBLE_DEVICES=2,3
```

and it must write candidates into the existing manifest format documented at:

- `docs/paper_agent/decompile_faithfulness_candidate_format.md`

## Candidate Phase 1K Routes

### Route A: Dynamic Trace Gate

Question:

Can lightweight runtime signatures distinguish faithful rewrites from localized semantic bugs on the existing 8-case / 56-candidate source-known set?

Possible signals:

- output vector over deterministic tests
- output vector over generated/random bounded tests
- branch/path coverage if instrumentation is feasible
- mismatch localization by input bucket

Controls:

- Do not count the existing behavior label itself as the method result.
- Report when a signal collapses into the existing test oracle.
- Compare faithful rewrite drift vs plausible-wrong drift separately.

Success gate:

- LOCO AUC `>= 0.85`, because dynamic evidence is stronger and should clear a higher bar.
- `signum`, `gcd_positive`, `max3`, `sum_to_n` each `>= 0.75`.
- Report must show more than “candidate failed an existing unit test.”

Kill gate:

- Signal is just behavior pass/fail under existing tests.
- Hard cases still below `0.667`.
- Requires case-specific hand instrumentation.

### Route B: Symbolic / Concolic Trace Gate

Question:

Can path constraints or input-output relation summaries explain the hard cases that static motifs miss?

Constraints:

- First check local dependency availability.
- Do not add heavy dependencies without a separate dependency plan.
- Current observed environment does not provide `angr` or `z3` in `dllm_env`; this route likely starts as a design/probe, not immediate implementation.

Success gate:

- Produces case-general signatures for at least `signum`, `max3`, and `gcd_positive`.
- Does not require custom rules per case.

Kill gate:

- Tooling cost dominates the paper question.
- Dependency installation or solver brittleness becomes the main work.

### Route C: Narrowed Localized-Bug Framing

Question:

Should the project stop claiming general decompilation faithfulness and instead target source-known localized semantic bug auditing?

Required output:

- New problem statement.
- Positive and negative evidence from Phase 1A-1J.
- Minimal benchmark definition.
- Which claims are no longer made.

Success gate:

- Produces a defensible paper scope without requiring real-project transfer immediately.
- Explains why static features are diagnostic tooling, not the main verifier.

Kill gate:

- Scope becomes too narrow to be interesting.
- Method contribution becomes mostly benchmark bookkeeping.

## Recommended Execution Order

1. Write or update the Phase 1K design note so Route A/B/C are all in scope.
2. Run Route C first as a claim-framing audit; this defines what A/B need to prove.
3. Implement Route A with TDD and CPU-only dynamic traces over existing Phase 1H artifacts.
4. Run Route B as a dependency and feasibility probe only; do not install heavy dependencies inside Phase 1K.
5. Write a combined Phase 1K decision comparing all three route outcomes.
6. Only after the combined decision is positive, write a real-project transfer or GPU candidate-generation plan.

## Immediate Decision

Do not start GPU 2/3 jobs yet.

Reason:

- No current runnable GPU experiment exists in this repo.
- Phase 1J failed the gate that would justify real-project transfer.
- GPU candidate generation would create expensive data before the scoring/evaluation signal is trustworthy.

The next concrete action is to execute the three-route scout plan: claim matrix, dynamic trace audit, symbolic feasibility probe, then combined decision.
