# Binary-Faithful Phase 6R Real Decompiler Dependency Plan

> REQUIRED: Use `superpowers:executing-plans` only during execution. Do not use subagents, Task/Spawn, dispatching-parallel-agents, `tool_search`, or multi-agent workflows. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Install or activate a real decompiler tool, import real decompiler output for the Phase 5 source-known functions, and rerun the Phase 6 Dynamic Trace v3 evaluation without changing the oracle.

## Task 1: Confirm Current Blocker

**Files:**

- Already created: `docs/paper_agent/decompile_faithfulness_phase6_tool_feasibility.zh.md`
- Create: `docs/paper_agent/decompile_faithfulness_phase6r_dependency_decision.zh.md`

- [ ] Step 1: Probe local real decompiler commands.

Run:

```bash
command -v ghidraRun
command -v ghidra-analyzeHeadless
command -v analyzeHeadless
command -v retdec-decompiler
command -v r2
command -v radare2
```

Expected before install: no real decompiler command is found.

- [ ] Step 2: Write dependency decision doc.

The doc must record:

- Current Phase 6 proxy metrics.
- Local tool state.
- Why proxy success is not enough for CCF-A.
- Recommended dependency order.

Allowed decisions:

- `ready-run-real-decompiler-output`
- `install-radare2-smoke-first`
- `install-ghidra-main-evidence`
- `blocked-awaiting-user-approval`

## Task 2: Dependency Install Proposal

No installation should happen unless the user explicitly approves the dependency route.

Recommended options:

1. **Fast smoke route:** install Ubuntu `radare2`.
   - Intended use: validate real-tool import plumbing.
   - Not enough as final CCF-A evidence unless C-like output is usable.
2. **Main evidence route:** install Ghidra.
   - Intended use: full real decompiler-output experiment.
   - Requires Java and a Ghidra release package.
3. **Secondary robustness route:** install RetDec.
   - Intended use: optional second-tool robustness table.

## Task 3: Real Decompiler Output Importer

**Files after dependency approval:**

- Create: `analysis/decompile_faithfulness/run_phase6r_real_decompiler_output.py`
- Create: `tests/test_decompile_faithfulness_phase6r_real_decompiler_output.py`
- Create: `docs/paper_agent/decompile_faithfulness_phase6r_real_decompiler_manifest.json`

Implementation requirements:

- Compile each source-known function to object or executable at `O0` and `O2`.
- Run the selected decompiler headlessly.
- Extract a single candidate C function for the target symbol.
- Save raw decompiler output and normalized candidate C separately.
- Never silently discard failed functions; record taxonomy.

## Task 4: Real Output Preflight

**Files after dependency approval:**

- Create: `docs/paper_agent/decompile_faithfulness_phase6r_compile_preflight.json`

Gate:

- At least `20` functions have imported real decompiler output.
- At least `50` normalized candidates compile.
- At least `10` paired functions exist.

If this fails, write `needs-more-real-decompiler-output-candidates`.

## Task 5: Baseline And V3 Analysis

**Files after dependency approval:**

- Create: `docs/paper_agent/decompile_faithfulness_phase6r_result_analysis.json`
- Create: `docs/paper_agent/decompile_faithfulness_phase6r_result_analysis.zh.md`
- Create: `docs/paper_agent/decompile_faithfulness_phase6r_gate_decision.zh.md`

Evaluate:

- fixture-only AUC
- static structured proxy AUC
- Dynamic Trace v3 mismatch-rate AUC
- Dynamic Trace v3 trace-total AUC
- v3 delta over best non-oracle baseline
- behavior-preserving false-positive rate
- failure taxonomy by tool and optimization level

Pass decision:

- `pass-phase6r-real-decompiler-output-main-evidence`

Failure decisions:

- `needs-more-real-decompiler-output-candidates`
- `method-negative-real-decompiler-output`
- `blocked-decompiler-output-normalization`

## Task 6: Verification

Run:

```bash
python -m unittest tests.test_decompile_faithfulness_phase6r_real_decompiler_output
python -m json.tool docs/paper_agent/decompile_faithfulness_phase6r_real_decompiler_manifest.json
python -m json.tool docs/paper_agent/decompile_faithfulness_phase6r_compile_preflight.json
python -m json.tool docs/paper_agent/decompile_faithfulness_phase6r_result_analysis.json
git diff --check
```

Expected: all pass after real decompiler output exists.
