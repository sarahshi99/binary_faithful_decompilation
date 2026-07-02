# Binary-Faithful Phase 6R Real Decompiler Dependency Design

> Superpowers mode: `superpowers:brainstorming` for route comparison, `superpowers:writing-plans` for this design, and `superpowers:executing-plans` for later execution. Subagents remain forbidden.

## Goal

Turn Phase 6 from an `assembly_context_decompiler_like` proxy into a real decompiler-output experiment.

The source-known oracle and Dynamic Trace v3 scoring stay unchanged. Only the candidate source changes:

- Phase 6 proxy: deterministic decompiler-like candidates with `objdump` context.
- Phase 6R: C code emitted by an actual decompiler tool from locally compiled binaries.

## Current Evidence

Phase 6 proxy is positive but not sufficient for a CCF-A main claim:

- `38` source-known functions.
- `430/430` compile-pass decompiler-like candidates.
- Dynamic Trace v3 AUC `1.0000`.
- Best non-oracle baseline AUC `0.9487`.
- Delta `+0.0513`.
- V3 behavior-preserving false positive rate `0.0000`.
- Real decompiler output available: `False`.

The gate decision is therefore `needs-decompiler-dependency-plan`.

## Local Tool State

Available:

- `/usr/bin/gcc`
- `/usr/bin/objdump`
- `/usr/bin/unzip`
- `/usr/bin/tar`
- `/usr/bin/docker`, but no relevant local image
- `/home/shx/miniconda3/bin/conda`
- `/home/shx/miniconda3/bin/mamba`

Unavailable in PATH:

- `ghidraRun`
- `ghidra-analyzeHeadless`
- `analyzeHeadless`
- `retdec-decompiler`
- `r2`
- `radare2`

APT has a `radare2` candidate (`4.2.1+dfsg-2`) but it is not installed.

## Route Brainstorming

### Route A: radare2 First

Use Ubuntu `radare2` as the quickest real decompiler-adjacent tool.

Pros:

- Lowest installation cost if apt works.
- CLI-first and easy to batch.
- Good for validating binary import, symbol targeting, optimization-level workflow, and candidate extraction plumbing.

Risks:

- The focal package may not provide high-quality C decompilation.
- `pdc`/pseudo-C output may be less publishable than Ghidra output.
- r2dec plugin may require additional installation.

Verdict: best first dependency smoke, not enough alone for a top-tier realism claim unless output quality is strong.

### Route B: Ghidra Main Evidence

Install Ghidra and use `analyzeHeadless` to export decompiler C.

Pros:

- Strongest credibility for real decompiler-output experiments.
- Headless mode is reproducible.
- Easier to defend to reviewers.

Risks:

- Requires Java and a larger download/install.
- Export scripting is more work.
- Generated C can include helper macros/types and may require cleanup before compile-based oracle evaluation.

Verdict: recommended main Phase 6R route after dependency approval.

### Route C: RetDec Secondary

Install RetDec and batch decompile ELF objects.

Pros:

- Also recognizable as a real decompiler.
- CLI-focused.

Risks:

- Larger and less likely to be available through local package managers.
- Output may require heavier normalization.

Verdict: optional second-tool robustness, not first.

## Recommended Route

Use a two-step Phase 6R:

1. Phase 6R-A: install/probe `radare2`; run a small importability check only.
2. Phase 6R-B: install/probe Ghidra; run the full `38` function real decompiler-output experiment.

Do not count Phase 6R-A as the CCF-A main evidence unless it produces compile-pass, source-known paired candidates at scale and output quality is clearly decompiler-derived C.

## Experimental Gate

Phase 6R passes only if:

- At least `20` functions have real decompiler-output candidates.
- At least `50` decompiler-output candidates compile after documented normalization.
- At least `10` paired functions have faithful/wrong labels.
- Dynamic Trace v3 beats fixture-only and static structured baselines.
- V3 delta over best non-oracle baseline is at least `0.05`.
- Behavior-preserving rewrite false-positive rate is `<= 10%`.
- Every compile or decompiler failure is assigned a taxonomy label.
- The paper claim clearly says source-known bounded semantic auditing, not binary-only equivalence.

## CCF-A Self-Check

Full-scale risk:

- Phase 6 proxy already passed full proxy scale, but Phase 6R must rerun at real-tool scale.
- A smoke-only decompiler run is useful for feasibility but not publishable as the main result.

SOTA/baseline risk:

- The current proxy margin is positive but thin (`+0.0513`).
- Real decompiler-output may reduce or erase the margin.
- The main CCF-A claim should emphasize the new auditing problem and source-known oracle design, not claim to outperform decompiler generation systems.

## Decision

`write-phase6r-dependency-plan-before-install`
