# Binary-Faithful Decompilation Phase 1J CFG/Return-Binding Plan

> **For agentic workers:** Use `superpowers:executing-plans` only, or execute manually in the current session. Do not use `superpowers:subagent-driven-development`, dispatching/parallel agents, Task/Spawn subagents, reviewer subagents, `tool_search`, or multi-agent reviewer discovery.

## Goal

Implement and run a CPU-only Phase 1J audit that tests whether structured CFG/return-binding features improve over Phase 1I component combination. This is a source-known kill-gate, not real-project transfer.

## Current Baseline

- Dataset: 8 cases / 56 candidates from Phase 1H artifacts.
- Phase 1G multi-opt min slot concentration: `0.7552`.
- Phase 1I best in-sample formula: `0.7604`.
- Phase 1I leave-one-case-out: `0.6719`.
- Current verdict: `do-not-transfer-yet`.

## Files

Create:

- `analysis/decompile_faithfulness/structured_features.py`
- `analysis/decompile_faithfulness/run_structural_binding_audit.py`
- `tests/test_decompile_faithfulness_structured_features.py`
- `tests/test_decompile_faithfulness_structural_binding_audit.py`
- `docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.json`
- `docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.md`
- `docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.zh.md`
- `analysis_outputs/decompile_faithfulness/phase1j_structural_binding/records.jsonl`

Modify only if needed:

- `analysis/decompile_faithfulness/features.py`
- `analysis/decompile_faithfulness/localization.py`

## Task 1: Structural Feature Tests

- [ ] Add tests for parsing objdump instruction lines into address/opcode/operands records.
- [ ] Add tests for splitting a short synthetic instruction stream into basic blocks.
- [ ] Add tests for extracting branch-return binding motifs, including a signum-like branch-to-`-1/0/1` pattern.
- [ ] Add tests that behavior-preserving instruction reordering can change bigrams without forcing a high structured suspiciousness score.

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_structured_features.py
```

## Task 2: Implement `structured_features.py`

Implement:

- `StructuredInstruction`
- `BasicBlock`
- `StructuredFeatureVector`
- `parse_objdump_instructions(text: str) -> list[StructuredInstruction]`
- `build_basic_blocks(instructions: list[StructuredInstruction]) -> list[BasicBlock]`
- `extract_structured_features(object_path: Path) -> StructuredFeatureVector`
- `structured_feature_distance(left, right) -> dict[str, float]`

Feature components:

- `basic_block_shape_l1`
- `terminal_opcode_l1`
- `cfg_edge_motif_l1`
- `branch_return_binding_l1`
- `compare_branch_return_l1`
- `loop_update_binding_l1`
- `structured_binding_total`

Implementation constraints:

- Use only Python standard library plus existing `/usr/bin/objdump`.
- Do not use Ghidra, RetDec, angr, LLM APIs, network, GPU, or training.
- Keep parsing conservative and deterministic; unknown patterns should become absent motifs, not crashes.

## Task 3: Structural Audit Runner Tests

- [ ] Add tests for object-path lookup from Phase 1H-style artifact roots.
- [ ] Add tests for per-opt aggregation over `O0/O1/O2/O3`.
- [ ] Add tests for leave-one-case-out formula selection.
- [ ] Add tests that labels are used only for offline evaluation, not feature extraction.

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_structural_binding_audit.py
```

## Task 4: Implement `run_structural_binding_audit.py`

The runner should accept:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_structural_binding_audit \
  --artifact-roots \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1e \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1f \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1g \
  --output-json docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.json \
  --output-md docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.md \
  --output-zh docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.zh.md \
  --output-jsonl analysis_outputs/decompile_faithfulness/phase1j_structural_binding/records.jsonl
```

Candidate formulas:

- `min_slot`
- `mean_slot`
- `mean_slot_plus_structured_0.10`
- `mean_slot_plus_structured_0.25`
- `min_slot_plus_branch_return_0.10`
- `min_slot_plus_cfg_edge_0.10`
- `structured_only`
- `structured_binding_total`

The runner must report:

- in-sample formula AUCs
- leave-one-case-out aggregate AUC
- per-held-out-case selected formula and AUC
- hard-case AUCs for `signum`, `gcd_positive`, `max3`, `sum_to_n`
- verdict: `continue-structured-binding`, `borderline-structured-binding`, or `do-not-transfer-yet`

## Task 5: Run The Audit

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_structural_binding_audit \
  --artifact-roots \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1e \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1f \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1g \
  --output-json docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.json \
  --output-md docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.md \
  --output-zh docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.zh.md \
  --output-jsonl analysis_outputs/decompile_faithfulness/phase1j_structural_binding/records.jsonl
```

## Task 6: Verification

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest \
  tests/test_decompile_faithfulness_structured_features.py \
  tests/test_decompile_faithfulness_structural_binding_audit.py

/home/shx/miniconda3/envs/dllm_env/bin/python -m py_compile \
  analysis/decompile_faithfulness/structured_features.py \
  analysis/decompile_faithfulness/run_structural_binding_audit.py

git diff --check
```

## Success Gate

Continue only if:

- leave-one-case-out AUC `>= 0.80`
- `signum`, `gcd_positive`, `max3`, and `sum_to_n` held-out AUCs are each `>= 0.667`
- the report shows structured features help semantic bugs without mainly punishing faithful rewrites

## Kill Gate

Stop or pivot if:

- leave-one-case-out AUC `< 0.75`
- two or more hard cases remain `< 0.60`
- improvement is only in-sample
- selected formulas are case-specific or hard to defend

## Decision After Task 6

If the success gate passes, write the next small transfer design. If it fails, record Phase 1J as negative evidence and pivot to dynamic trace / symbolic trace / narrower problem framing.
