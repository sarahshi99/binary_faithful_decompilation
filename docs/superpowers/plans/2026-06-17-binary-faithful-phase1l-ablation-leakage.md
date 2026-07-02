# Binary-Faithful Decompilation Phase 1L Ablation / Leakage Audit Plan

> **For agentic workers:** Use `superpowers:executing-plans` style local serial execution only. Do not use `superpowers:subagent-driven-development`, Task/Spawn subagents, reviewer subagents, `tool_search`, multi-agent discovery, GPU jobs, network, or dependency installation. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Audit Phase 1K-v2 to show that its improvement is not fixture oracle collapse, label leakage, candidate-output leakage, or static-only `min_slot`.

## Inputs

- `analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace/records.jsonl`
- `analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace_v2/records.jsonl`

## Task 1: TDD Ablation Scoring

**Files:**

- Create: `tests/test_decompile_faithfulness_phase1l_ablation.py`
- Create: `analysis/decompile_faithfulness/run_phase1l_ablation_audit.py`

- [x] **Step 1: Add failing unit tests**

Test:

- pairwise AUC scores wrong candidates above faithful candidates within each case;
- variant scorer reads the requested feature field;
- fixture identity check detects when two score vectors are identical;
- leakage audit summary reports no label/output/candidate-id use.

- [x] **Step 2: Run failing tests**

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_phase1l_ablation.py
```

- [x] **Step 3: Implement ablation runner**

Implement:

- `_read_jsonl`
- `_variant_summary`
- `_pairwise_auc`
- `_case_pairwise_auc`
- `_score_vectors_identical`
- `_leakage_audit`
- `run_audit`
- report writers

Keep this runner read-only over existing records.

- [x] **Step 4: Verify tests pass**

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_phase1l_ablation.py
```

## Task 2: Run Phase 1L Audit

- [x] **Step 1: Run audit**

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_phase1l_ablation_audit \
  --v1-records analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace/records.jsonl \
  --v2-records analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace_v2/records.jsonl \
  --output-json docs/paper_agent/decompile_faithfulness_phase1l_ablation.json \
  --output-md docs/paper_agent/decompile_faithfulness_phase1l_ablation.md \
  --output-zh docs/paper_agent/decompile_faithfulness_phase1l_ablation.zh.md
```

- [x] **Step 2: Read verdict**

```bash
jq '{variants, leakage_audit, verdict}' docs/paper_agent/decompile_faithfulness_phase1l_ablation.json
```

## Task 3: Update Research Docs

- [x] **Step 1: Update Phase 1 overview**

Add Phase 1L row and next-step recommendation.

- [x] **Step 2: Update Phase 1K decision**

Add Phase 1L ablation result under the v2 decision.

## Task 4: Verification

- [x] **Step 1: Focused tests**

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest \
  tests/test_decompile_faithfulness_phase1l_ablation.py \
  tests/test_decompile_faithfulness_dynamic_trace.py \
  tests/test_decompile_faithfulness_dynamic_trace_v2.py
```

- [x] **Step 2: Full suite**

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest discover -s tests
```

- [x] **Step 3: py_compile**

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m py_compile \
  analysis/decompile_faithfulness/run_phase1l_ablation_audit.py
```

- [x] **Step 4: diff hygiene**

```bash
git diff --check
```

- [x] **Step 5: confirm no GPU use**

```bash
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
```
