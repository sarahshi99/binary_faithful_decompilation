# Binary-Faithful Phase 5 Real-Project Source-Known Transfer Design

> **Superpowers mode:** Use `superpowers:executing-plans` only for execution. Do not use subagents, dispatching-parallel-agents, Task/Spawn, reviewer subagents, `tool_search`, or multi-agent workflows. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Evaluate Dynamic Trace v3 on source-known functions extracted from small real C projects. Phase 5 is the first full-scale external-validity experiment; it must not be treated as another smoke run.

## Why Phase 5 Exists

Phase 1-3 show a strong signal on curated and generated small-function pools, but the evidence is not enough for a CCF-A main claim. The main reviewer objection is predictable:

> The method works on small curated functions and smoke-scale generated candidates, but does it transfer to real source projects and representative baselines?

Phase 5 answers that objection while retaining the source-known oracle boundary.

## SOTA Positioning

This project should not claim to generate better decompiled code than SOTA decompilers or LLM decompilers. The Phase 5 claim is narrower:

> Dynamic Trace v3 is a stronger source-known auditing signal for localized semantic drift than fixture-only validation and lightweight static/binary baselines.

Literature anchors for positioning:

- LLM4Decompile: recompilability and re-executability are central LLM decompilation metrics. Source: `https://arxiv.org/abs/2403.05286`.
- Evaluating the Effectiveness of Decompilers, ISSTA 2024: semantic consistency and readability remain hard for mainstream decompilers. Source: `https://2024.issta.org/details/issta-2024-papers/40/Evaluating-the-Effectiveness-of-Decompilers`.
- DecompileBench, ACL Findings 2025: real-world functions, runtime-aware validation, and functionality correctness are key benchmark dimensions. Source: `https://aclanthology.org/2025.findings-acl.1194.pdf`.
- Decompile-Bench, NeurIPS 2025 Datasets and Benchmarks: large-scale binary-source function pairs are becoming a core resource for LLM decompilation evaluation. Source: `https://proceedings.neurips.cc/paper_files/paper/2025/hash/079cf13ae174c31f148207d94d213bdc-Abstract-Datasets_and_Benchmarks_Track.html`.

## Function Eligibility

First-pass eligible functions must satisfy all of the following:

- deterministic;
- integer-only arguments and integer return value;
- bounded input domain can be specified without symbolic reasoning;
- no file I/O;
- no networking;
- no heap allocation;
- no external mutable state;
- no callbacks;
- no undefined behavior under the bounded domain;
- original source can be compiled as oracle;
- fixtures cover ordinary and boundary behavior.

Functions that fail these requirements may be listed as excluded, but they must not enter the Phase 5 main table.

## Dataset Gate

Phase 5 is full-scale only if all of these are true:

- at least `30` eligible functions;
- target range `30-50` eligible functions;
- at least `2` source projects;
- at least `100` compile-pass candidates;
- target range `100-200` compile-pass candidates;
- at least `20` functions with faithful/wrong pairs;
- every major risk family has at least `3` paired functions when possible.

Risk families:

- arithmetic saturation / overflow-like boundaries;
- sign and zero;
- bit width / masking;
- division / modulo;
- loop termination;
- range endpoints;
- multi-argument order or comparison.

## Candidate Sources

Candidate sources should be layered:

1. Behavior-preserving rewrites for false-positive control.
2. Manual stress candidates for known localized bug families.
3. LLM-generated `strict_rewrite` and `strict_bug` candidates.
4. Decompiler-like candidates if already available without Phase 6 tooling.

The main Phase 5 table should report results separately by candidate source.

## Baseline Matrix

Required baselines:

| Baseline | Role |
|---|---|
| fixture-only mismatch | Shows whether v3 finds bugs that fixtures miss |
| static-only min-slot or structural score | Compares against lightweight binary/static motif route |
| Dynamic Trace v1 mixed-domain | Shows domain-awareness necessity |
| Dynamic Trace v2 domain-aware | Shows boundary-preservation necessity |
| Dynamic Trace v3 boundary-preserving | Main method |

Optional baselines:

| Baseline | Activation condition |
|---|---|
| LLM judge | Only if prompts/costs are controlled and source oracle remains ground truth |
| symbolic/concolic probe | Only if dependencies are already available or a separate dependency plan is approved |
| fuzzing-style random input baseline | Use if it can run deterministically with the same input budget |

## Method Gate

Phase 5 passes if:

- Dynamic Trace v3 pairwise AUC `>= 0.85`;
- Dynamic Trace v3 beats the best non-oracle baseline by `>= 0.05` AUC;
- `fixture_collapse=False`;
- at least `5` fixture-passing wrong candidates are found, or the report explains why the candidate source did not produce them;
- no undocumented risk-family AUC is below `0.60`;
- false-positive rate on behavior-preserving rewrites is at most `10%`, or every false positive has a documented trace-domain cause.

## Failure Attribution

Phase 5 failures must be categorized before drawing a method-level negative conclusion:

- source extraction failure;
- original oracle compile failure;
- fixture design failure;
- bounded-domain design failure;
- candidate generation failure;
- insufficient faithful/wrong pairs;
- baseline stronger than v3;
- v3 trace-domain miss;
- v3 false positive on behavior-preserving rewrite.

## Output

Expected outputs:

- `docs/paper_agent/decompile_faithfulness_phase5_project_candidates.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json`
- `docs/paper_agent/decompile_faithfulness_phase5_preflight.json`
- `docs/paper_agent/decompile_faithfulness_phase5_candidate_manifest.json`
- `docs/paper_agent/decompile_faithfulness_phase5_result_analysis.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase5_gate_decision.zh.md`

## Design Self-Review

Scope check: Phase 5 remains source-known and bounded; it does not claim binary-only equivalence.

Scale check: The gate explicitly rejects smoke-scale evidence as sufficient for CCF-A.

SOTA check: The comparison target is auditing-signal quality, not decompiler generation quality.
