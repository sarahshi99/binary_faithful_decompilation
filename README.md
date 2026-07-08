# Binary Faithful Decompilation

Research artifact for source-known localized semantic drift auditing in
decompiled or decompiler-like C candidates.

## Current Claim

The current supported claim is deliberately narrow:

> Source-literal-aware, low-budget dynamic re-execution can expose localized
> semantic drift in source-known C decompilation candidates that fixture-only
> and static scoring baselines miss.

This repository does **not** claim a general binary-only verifier or decompiler
generation SOTA.

## Project Stop Status

The later Phase 3 natural-error census did not produce a sufficient primary
natural-error population for CCF-A-style auditor evaluation. See:

- `docs/paper_agent/project_stop_report.md`
- `docs/paper_agent/artifact_index.md`
- `docs/paper_agent/future_restart_checklist.md`

## Final Method

The current final method is:

`source_literal_char_interleave`

It interleaves fixture-neighbor probes with character-literal probes extracted
from the original source. This keeps the low input budget while fixing the
Ghidra `char_boundary` and `multi_arg` misses found by earlier policies.

## Main Results

Budget: `8` generated/re-executed inputs per candidate.

| Dataset | Candidates | Paired cases | Fixture AUC | Static AUC | Final AUC | Detection | Avg inputs | Missed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Public static-hard | 478 | 50 | 0.9211 | 0.6806 | 1.0000 | 1.0000 | 6.64 | 0 |
| LLM-public | 136 | 24 | 0.9741 | 0.7759 | 1.0000 | 1.0000 | 6.69 | 0 |
| Ghidra | 166 | 26 | 0.5000 | 0.8207 | 1.0000 | 1.0000 | 6.97 | 0 |

Key result documents:

- `docs/paper_agent/decompile_faithfulness_current_status_and_ccfa_gap.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase18_source_literal_char_policy.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase19_final_method_readiness.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase19_final_runtime_risk.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase20_paper_tables.md`

## Repository Layout

- `analysis/decompile_faithfulness/`: experiment runners, analyzers, and method code.
- `analysis_inputs/decompile_faithfulness/`: source-known function pools.
- `analysis_outputs/decompile_faithfulness/`: lightweight JSON/JSONL experiment records.
- `docs/paper_agent/`: research notes, phase reports, paper skeletons, and table drafts.
- `docs/superpowers/`: local project plans/specs used during the research workflow.
- `tests/`: unit tests for experiment runners and analysis utilities.

Large local artifacts such as tool installs, generated executables, raw traces,
external cloned repositories, and compiled candidates are intentionally ignored
by Git.

## Quick Verification

Run the focused regression suite:

```bash
python -m unittest \
  tests.test_decompile_faithfulness_compile \
  tests.test_decompile_faithfulness_phase11_input_ordering \
  tests.test_decompile_faithfulness_phase17_operator_char_policy \
  tests.test_decompile_faithfulness_phase18_source_literal_char_policy \
  tests.test_decompile_faithfulness_phase20_paper_tables \
  tests.test_decompile_faithfulness_phase16_runtime_risk \
  tests.test_decompile_faithfulness_phase14_paper_readiness
```

Latest local verification before upload:

- `27` focused tests passed.
- `git diff --check` passed.
- No common GitHub/OpenAI/AWS token patterns were found in the upload package.

## Project Protocol

See `AGENTS.md` and `docs/superpowers/protocol.md`.

Subagents are disabled for this project.
