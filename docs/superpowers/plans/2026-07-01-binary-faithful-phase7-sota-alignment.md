# Binary-Faithful Phase 7 SOTA Alignment Plan

> REQUIRED: Use `superpowers:executing-plans` only during execution. Use `superpowers:test-driven-development` for new scripts. Do not use subagents, Task/Spawn, dispatching-parallel-agents, `tool_search`, or multi-agent workflows. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Move beyond Phase 6/6R by aligning the project with related-work SOTA evidence.

Phase 6 is considered complete for:

- Ghidra real decompiler-output main evidence.
- Ghidra cross-toolchain robustness.
- radare2 importability.

Phase 7 must determine whether the project can support an external-paper SOTA claim, or whether it should keep a narrower source-known semantic auditing claim.

## Task 1: Freeze Phase 6 Status

**Files:**

- Read: `docs/paper_agent/decompile_faithfulness_phase6r_cross_toolchain_summary.zh.md`
- Update: `docs/paper_agent/decompile_faithfulness_phase7_sota_alignment_plan.zh.md`

Steps:

- [ ] Record Phase 6 status as `complete-for-ghidra-cross-toolchain`.
- [ ] Record that external-paper SOTA is still `not-ready`.
- [ ] Record blockers:
  - no public benchmark row yet;
  - no explicit related-work baseline matrix yet;
  - no second compile-ready decompiler beyond Ghidra yet;
  - radare2 is importability only.

## Task 2: Public Benchmark Feasibility Preflight

**Files:**

- Create: `analysis/decompile_faithfulness/run_phase7_benchmark_feasibility.py`
- Create: `tests/test_decompile_faithfulness_phase7_benchmark_feasibility.py`
- Create: `docs/paper_agent/decompile_faithfulness_phase7_benchmark_feasibility.json`
- Create: `docs/paper_agent/decompile_faithfulness_phase7_benchmark_feasibility.zh.md`

Implementation requirements:

- Probe local project tree for public benchmark artifacts:
  - Decompile-Eval / HumanEval-style;
  - ExeBench-style;
  - DecompileBench;
  - CodeFuse-DeBench.
- Probe whether benchmark repos/data already exist locally under this project.
- Do not download anything unless the user explicitly approves network/dependency work.
- Emit a benchmark availability matrix with:
  - `benchmark_name`;
  - `local_path`;
  - `available`;
  - `expected_input_format`;
  - `source_known_possible`;
  - `compile_harness_needed`;
  - `license_or_repro_note`;
  - `recommended_next_action`.

Gate:

- `ready-public-benchmark-import` if at least one usable benchmark artifact exists locally.
- `blocked-needs-benchmark-download-approval` if none exists locally.
- `blocked-benchmark-format-unknown` if files exist but format cannot be identified.

Verification:

```bash
python -m unittest tests.test_decompile_faithfulness_phase7_benchmark_feasibility
python -m json.tool docs/paper_agent/decompile_faithfulness_phase7_benchmark_feasibility.json
git diff --check
```

## Task 3: Related-work Baseline Matrix

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase7_related_work_baseline_matrix.zh.md`

Steps:

- [ ] Convert Phase 4 literature anchors into a baseline matrix.
- [ ] For each related-work family, record:
  - what metric it reports;
  - whether Phase 7 can reproduce it;
  - what proxy baseline is acceptable if exact reproduction is infeasible;
  - whether GPU/API/dependency is needed.
- [ ] Explicitly separate:
  - decompiler generation quality;
  - decompiler output validation;
  - source-known semantic drift auditing.

Minimum rows:

- LLM4Decompile / Decompile-Eval.
- DecompileBench.
- Decompile-Bench.
- CodeFuse-DeBench.
- fixture-only / re-execution-only.
- static structured similarity.
- Dynamic Trace v1/v2/v3 ablations.
- LLM judge baseline.
- symbolic/fuzzing-style baseline.

Gate:

- `ready-baseline-implementation` if every main baseline has either a reproduction route or a documented proxy.
- `blocked-baseline-definition` otherwise.

## Task 4: Public Benchmark Importer Plan

Only execute after Task 2 finds a local or approved benchmark source.

**Files:**

- Create: `analysis/decompile_faithfulness/run_phase7_public_benchmark_import.py`
- Create: `tests/test_decompile_faithfulness_phase7_public_benchmark_import.py`
- Create: `docs/paper_agent/decompile_faithfulness_phase7_public_function_manifest.json`

Implementation requirements:

- Convert selected public benchmark functions into the existing source-known manifest format.
- Preserve original benchmark IDs.
- Record compiler/toolchain metadata.
- Record why a function is included or excluded.
- Do not silently filter failures.

Gate:

- At least `50` source-known functions imported.
- At least `30` compile in the local harness.
- At least `2` optimization/toolchain variants feasible.

## Task 5: Main Public Benchmark Evaluation

Only execute after Task 4 passes.

**Files:**

- Create: `analysis/decompile_faithfulness/run_phase7_public_benchmark_eval.py`
- Create: `tests/test_decompile_faithfulness_phase7_public_benchmark_eval.py`
- Create: `docs/paper_agent/decompile_faithfulness_phase7_public_benchmark_result.json`
- Create: `docs/paper_agent/decompile_faithfulness_phase7_public_benchmark_result.zh.md`
- Create: `docs/paper_agent/decompile_faithfulness_phase7_sota_gate_decision.zh.md`

Baselines:

- fixture-only;
- static structured;
- Dynamic Trace v1/v2/v3;
- optional LLM judge if approved;
- optional symbolic/fuzzing-style if dependencies are approved.

Gate:

- At least `100` compile-pass candidates.
- At least `30` paired faithful/wrong functions.
- Dynamic Trace v3 beats fixture-only and static structured baselines.
- Delta over best non-oracle baseline `>= 0.05`.
- Behavior-preserving false positive rate `<= 10%`.
- Per-risk-family breakdown is reported.

## Task 6: Second Compile-ready Decompiler Decision

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase7_second_decompiler_decision.zh.md`

Steps:

- [ ] Probe local availability of RetDec / rev.ng / angr AIL / Binary Ninja / Hex-Rays.
- [ ] Determine which can produce compile-ready C or evaluable IR.
- [ ] If none are available, write a dependency approval prompt.

Gate:

- `ready-second-decompiler-run`
- `blocked-awaiting-second-decompiler-approval`
- `skip-second-decompiler-narrow-ghidra-claim`

## Task 7: GPU 0/1 Decision

Do not use GPU before CPU benchmark preflight passes.

Use GPU 0/1 only for:

- LLM candidate generation;
- LLM repair/refinement baseline;
- local LLM judge baseline.

Before launching GPU:

- [ ] Check `nvidia-smi`.
- [ ] Record current users/processes.
- [ ] Prefer GPU 0/1 only if free or explicitly approved despite existing load.
- [ ] Write model/prompt/decoding manifest.

## Task 8: Final SOTA Readiness Review

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase7_sota_readiness_review.zh.md`

Questions to answer:

- Can the paper claim external-paper SOTA?
- If not, what narrower claim is defensible?
- Which result table is the main CCF-A table?
- Which benchmark rows are still missing?
- Which claims must be moved to limitations?

## Immediate Next Action

Execute Task 1-3 first. Do not download benchmarks or start GPU until Task 2 says what is missing and the user approves any external dependency/network route.
