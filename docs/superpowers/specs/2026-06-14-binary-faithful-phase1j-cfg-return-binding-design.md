# Binary-Faithful Decompilation Phase 1J Design

> For agentic workers: use local serial Superpowers-style design and planning only. Do not use `superpowers:subagent-driven-development`, dispatching/parallel agents, Task/Spawn subagents, reviewer subagents, `tool_search`, or multi-agent discovery.

## Goal

Design the next CPU-only kill-gate after Phase 1I failed to transfer. Phase 1J tests whether a structured CFG/return-binding representation can repair the Phase 1G/1H blind spots without punishing behavior-preserving rewrites.

## Current Evidence

- Phase 1B killed raw global feature distance on realistic negatives: `pairwise_auc=0.5000`.
- Phase 1G multi-opt min slot concentration was borderline: `0.7552`.
- Phase 1H showed diagnostic order-sensitive features can expose `signum/manual_signum_reversed_signs`.
- Phase 1I simple component combination failed: best in-sample `0.7604`, leave-one-case-out `0.6719`, verdict `do-not-transfer-yet`.

## Design Decision

Do not start real-project transfer. Do not add more cases as the next move. Redesign the representation first.

The preferred Phase 1J experiment is a source-known structured-feature audit:

1. Parse object-code instruction streams into basic blocks.
2. Build lightweight CFG and terminal-block motifs.
3. Bind conditional branches and compare/test immediates to nearby return/update values.
4. Score structured distances separately from old slot concentration.
5. Evaluate with leave-one-case-out formula selection.

## Primary Hypothesis

The failures are not caused only by insufficient data. They come from a representation mismatch: flat binary feature bags lose branch/path-to-return binding. A structured representation should improve `signum`, `gcd_positive`, `max3`, and `sum_to_n` held-out performance if this direction remains viable.

## Inputs

Use existing Phase 1H artifacts:

- `analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1e`
- `analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1f`
- `analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1g`

For each root and opt level:

- read `o0/o1/o2/o3/records.jsonl`
- read matching `candidates/*__<OPT>.function.o`

## Candidate Feature Families

- `basic_block_shape_l1`
- `cfg_edge_motif_l1`
- `branch_return_binding_l1`
- `compare_branch_return_l1`
- `loop_update_binding_l1`
- `structured_binding_total`
- `structured_slot_concentration`

Keep existing components as controls:

- `min_slot`
- `mean_slot`
- `instruction_bigram_l1`
- `branch_return_immediate_pair_l1`
- Phase 1I formulas

## Evaluation

Report both in-sample and leave-one-case-out:

- case count and candidate count
- faithful vs plausible-wrong counts
- per-formula pairwise AUC
- selected formula per held-out case
- aggregate held-out pairwise AUC
- held-out AUC for `signum`, `gcd_positive`, `max3`, `sum_to_n`

## Success Gate

Continue only if:

- leave-one-case-out AUC `>= 0.80`
- each hard held-out case is `>= 0.667`
- qualitative inspection shows wins come from branch/return/update binding, not from over-penalizing faithful rewrites

## Kill Gate

Stop or pivot if:

- leave-one-case-out AUC `< 0.75`
- two or more hard cases remain `< 0.60`
- the selected formulas mainly score faithful rewrites as suspicious
- improvement requires case-specific hand rules

## Recommended Next Prompt

Use this prompt in a fresh Codex session rooted at `/home/shx/projects/binary_faithful_decompilation`:

```text
Use local serial Superpowers executing-plans only; do not use subagents, Task/Spawn, parallel-agent dispatch, tool_search, or reviewer discovery.

Project root: /home/shx/projects/binary_faithful_decompilation.

Read:
- docs/superpowers/plans/2026-06-14-binary-faithful-phase1j-cfg-return-binding.md
- docs/paper_agent/decompile_faithfulness_phase1j_cfg_return_binding_design.zh.md
- docs/paper_agent/decompile_faithfulness_phase1i_component_combination.zh.md

Implement Phase 1J CFG/return-binding audit exactly as planned. Keep it CPU-only. Do not start real-project transfer. Run focused tests, py_compile, the Phase 1J audit command, and git diff --check. Report whether the LOCO gate passes.
```
