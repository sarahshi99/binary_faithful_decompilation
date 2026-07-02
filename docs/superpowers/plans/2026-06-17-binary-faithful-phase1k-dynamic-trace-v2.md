# Binary-Faithful Decompilation Phase 1K Dynamic Trace v2 Implementation Plan

> **For agentic workers:** Use `superpowers:executing-plans` style local serial execution only. Do not use `superpowers:subagent-driven-development`, Task/Spawn subagents, reviewer subagents, `tool_search`, multi-agent discovery, GPU jobs, network, or dependency installation. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Improve Phase 1K Route A by replacing v1's mixed signed generated inputs with fixture-domain-aware generated inputs. The immediate target is to fix `gcd_positive` without lowering overall leave-one-case-out performance or collapsing into fixture behavior.

## Success Gate

- overall LOCO AUC `>= 0.8750`;
- `gcd_positive` held-out AUC `> 0.5000`;
- `fixture_collapse == false`;
- focused and full test suites pass;
- no GPU 2/3 use.

## Task 1: TDD Domain-Aware Input Generation

**Files:**

- Modify: `analysis/decompile_faithfulness/dynamic_trace.py`
- Modify: `tests/test_decompile_faithfulness_dynamic_trace.py`

- [x] **Step 1: Add failing tests**

Add tests that assert:

- `infer_trace_domain(fixtures.case_by_id("gcd_positive"))` marks the case as strictly positive.
- `generate_domain_trace_inputs(gcd_positive, ...)` excludes zero/negative values.
- `generate_domain_trace_inputs(signum, ...)` still includes negative, zero, and positive values.
- fixture tuples remain excluded from the primary generated set unless explicitly requested.

- [x] **Step 2: Run failing tests**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace.py
```

- [x] **Step 3: Implement domain-aware generation**

Add:

- `TraceDomain` dataclass.
- `infer_trace_domain(case) -> TraceDomain`.
- `generate_domain_trace_inputs(case, max_inputs=256, include_fixture_tests=False) -> list[TraceInput]`.

Implementation constraints:

- Use only fixture argument values and case metadata.
- Do not inspect labels or candidate outputs.
- Reuse existing v1 generator where no domain filter applies.
- Keep deterministic sorting and max-input cap.

- [x] **Step 4: Verify tests pass**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace.py
```

## Task 2: v2 Audit Runner

**Files:**

- Create: `analysis/decompile_faithfulness/run_dynamic_trace_v2_audit.py`
- Create: `tests/test_decompile_faithfulness_dynamic_trace_v2.py`

- [x] **Step 1: Add failing v2 runner tests**

Test that:

- v2 dynamic distance uses `generate_domain_trace_inputs`.
- v2 records include domain diagnostics.
- v2 formulas remain compatible with v1.

- [x] **Step 2: Run failing tests**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace_v2.py
```

- [x] **Step 3: Implement v2 runner**

Reuse v1 aggregation/scoring/report writing where possible, but write separate v2 outputs.

- [x] **Step 4: Verify v2 runner tests pass**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace_v2.py
```

## Task 3: Run v2 Audit

- [x] **Step 1: Run full v2 audit**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_dynamic_trace_v2_audit \
  --artifact-roots \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1e \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1f \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1g \
  --output-json docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.json \
  --output-md docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.md \
  --output-zh docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.zh.md \
  --output-jsonl analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace_v2/records.jsonl
```

- [x] **Step 2: Read v2 verdict**

Run:

```bash
jq '{best_in_sample, leave_one_case_out, hard_case_auc, fixture_collapse, verdict}' docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace_v2.json
```

## Task 4: Update Research Docs

**Files:**

- Modify: `docs/paper_agent/decompile_faithfulness_phase1k_three_route_decision.zh.md`
- Modify: `docs/paper_agent/decompile_faithfulness_phase1_overview_and_next_steps.zh.md`

- [x] **Step 1: Update Phase 1K decision**

Record the v2 result and whether it passes the gate.

- [x] **Step 2: Update Phase 1 overview**

Add a Phase 1K-v2 row or paragraph.

## Task 5: Verification

- [x] **Step 1: Run focused tests**

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest \
  tests/test_decompile_faithfulness_dynamic_trace.py \
  tests/test_decompile_faithfulness_dynamic_trace_audit.py \
  tests/test_decompile_faithfulness_dynamic_trace_v2.py
```

- [x] **Step 2: Run full suite**

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest discover -s tests
```

- [x] **Step 3: py_compile**

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m py_compile \
  analysis/decompile_faithfulness/dynamic_trace.py \
  analysis/decompile_faithfulness/run_dynamic_trace_audit.py \
  analysis/decompile_faithfulness/run_dynamic_trace_v2_audit.py
```

- [x] **Step 4: diff hygiene**

```bash
git diff --check
```

- [x] **Step 5: confirm no GPU use**

```bash
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
```
