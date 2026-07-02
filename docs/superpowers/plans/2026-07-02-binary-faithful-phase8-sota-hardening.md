# Binary-Faithful Phase 8 SOTA Hardening Plan

> REQUIRED: Use `superpowers:executing-plans` during execution and
> `superpowers:test-driven-development` for the new analysis script. Do not use
> subagents, Task/Spawn, dispatching-parallel-agents, `tool_search`, or
> multi-agent workflows. Work only under
> `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Phase 8 checks whether the strongest Phase 7 evidence is statistically stable
and whether a stronger non-oracle re-execution baseline erases the apparent
Dynamic Trace v3 margin.

This phase is CPU-only. It reads existing full records and does not launch GPU
generation.

## Inputs

- Phase 7C2 static-hard public records:
  `analysis_outputs/decompile_faithfulness/phase7_static_hard/records.jsonl`
- Phase 7E LLM public combined run summary:
  `docs/paper_agent/decompile_faithfulness_phase7_llm_public_combined.json`
- Phase 6R Ghidra full records:
  `analysis_outputs/decompile_faithfulness/phase6r_ghidra_full/records.jsonl`
- Phase 6R Ghidra gcc9 full records:
  `analysis_outputs/decompile_faithfulness/phase6r_ghidra_gcc9_full/records.jsonl`

## Task 1: Case-level Bootstrap CI

Create:

- `analysis/decompile_faithfulness/run_phase8_sota_hardening.py`
- `tests/test_decompile_faithfulness_phase8_sota_hardening.py`
- `docs/paper_agent/decompile_faithfulness_phase8_sota_hardening.json`
- `docs/paper_agent/decompile_faithfulness_phase8_sota_hardening.zh.md`

Requirements:

- Bootstrap over paired cases, not individual candidates.
- Report AUC point estimates and 95% confidence intervals for:
  - fixture-only;
  - static structured proxy;
  - fuzzing mismatch rate;
  - fuzzing any-mismatch;
  - Dynamic Trace v3 total.
- Report delta CI for:
  - v3 versus legacy best baseline: max(fixture, static);
  - v3 versus strong best baseline: max(fixture, static, fuzzing mismatch, fuzzing any-mismatch).

## Task 2: Strong-baseline Audit

Treat generated-input re-execution as a stronger non-oracle baseline:

- `fuzzing_mismatch_rate`: score is `trace_mismatch_rate`.
- `fuzzing_any_mismatch`: score is `1` if `trace_mismatch_rate > 0`, else `0`.

This baseline intentionally does not use v3's richer components such as
absolute error, sign mismatch, zero mismatch, boundary mismatch, or static
features. If it reaches the same AUC as v3, Phase 8 must report that v3's extra
components are not yet supported as a SOTA-margin contribution on the current
records.

## Gates

Primary gate on Phase 7C2 static-hard:

- `legacy_delta_ci_lower_gt_zero`: v3 delta versus legacy best baseline has
  lower 95% CI bound greater than `0`.
- `strong_baseline_not_erased`: v3 delta versus strong best baseline is at
  least `0.01`.

Verdicts:

- `pass-phase8-sota-hardening` if both primary gates pass.
- `strong-baseline-erases-v3-extra-margin` if legacy delta is stable but the
  strong fuzzing-style baseline erases v3's extra margin.
- `needs-more-stable-phase7c2-margin` otherwise.

## Verification

```bash
python -m unittest tests.test_decompile_faithfulness_phase8_sota_hardening
python -m py_compile analysis/decompile_faithfulness/run_phase8_sota_hardening.py
python -m analysis.decompile_faithfulness.run_phase8_sota_hardening
python -m json.tool docs/paper_agent/decompile_faithfulness_phase8_sota_hardening.json
git diff --check
```
