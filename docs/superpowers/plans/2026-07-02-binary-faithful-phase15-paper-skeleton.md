# Binary-Faithful Phase 15 Paper Skeleton Plan

> REQUIRED: Use `superpowers:executing-plans` during execution. Do not use
> subagents, Task/Spawn, dispatching-parallel-agents, `tool_search`, or
> multi-agent workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Create a paper skeleton that reflects the current Phase 13/14 evidence, not the
older Phase 4 v3-centered framing.

## Inputs

- Phase 4 paper synthesis and old outline.
- Phase 13 paper evidence synthesis.
- Phase 14 paper readiness summary and experiment-section draft.
- Current status / CCF-A gap document.

## Outputs

- `docs/paper_agent/decompile_faithfulness_phase15_paper_skeleton.md`
- `docs/paper_agent/decompile_faithfulness_phase15_paper_skeleton.zh.md`

## Required Framing

Main method:

`fixture-neighbor-first low-budget dynamic re-execution`

Main scope:

`source-known localized semantic drift auditing`

Supported:

- budget-8 targeted dynamic re-execution;
- stronger than fixture/static legacy baselines in current datasets;
- public static-hard, LLM-public, and Ghidra rows pass;
- CI and miss taxonomy are now available.

Unsupported:

- decompiler generation SOTA;
- general binary-only verifier;
- v3 scoring component superiority over strong generated-input mismatch;
- broad cross-decompiler robustness.

## Verification

```bash
test -s docs/paper_agent/decompile_faithfulness_phase15_paper_skeleton.md
test -s docs/paper_agent/decompile_faithfulness_phase15_paper_skeleton.zh.md
git diff --check
```
