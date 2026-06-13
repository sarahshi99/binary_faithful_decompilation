# Decompilation Faithfulness External Candidate Format

This file defines the Phase 1B input format for realistic LLM, decompiler, or manually written hard-negative candidates.

## JSON Format

Use a list of per-case manifests:

```json
[
  {
    "case_id": "absdiff",
    "candidates": [
      {
        "candidate_id": "llm_candidate_001",
        "label": "unknown",
        "mutation_type": "llm_generated",
        "function_source": "int absdiff(int a, int b) { if (a > b) return a - b; return b - a; }"
      }
    ]
  }
]
```

A single manifest object with `case_id` and `candidates` is also accepted by the loader.

## Fields

- `case_id`: one of the built-in source-known cases, such as `absdiff`, `clamp8`, or `count_bits8`.
- `candidate_id`: stable identifier for this candidate within the case.
- `label`: `unknown`, `faithful`, or `plausible_wrong`.
- `mutation_type`: source of the candidate, such as `llm_generated`, `ghidra_output`, `retdec_output`, `angr_output`, or `manual_hard_negative`.
- `function_source`: complete C function source for the case function.

## Label Semantics

Use `unknown` for realistic outputs whose faithfulness has not been manually adjudicated. The audit compiles the candidate and runs the deterministic source-known behavior gate:

- behavior passes -> `faithful`
- behavior fails -> `plausible_wrong`
- compile fails -> excluded from ranking and recorded as `compile_fail`

Use `faithful` or `plausible_wrong` only for manually curated candidates whose label should be preserved.

## Usage

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_candidate_ranking_audit \
  --external-candidates-json docs/paper_agent/example_external_candidates.json
```

The external candidates run through the same compile, behavior, feature-distance, ranking, and reporting path as controlled mutations. Their `mutation_type` values remain separate, so controlled mutation buckets and realistic negative buckets are not merged.

## Scope

Phase 1B only defines the input format and ranking-pipeline hook. It does not require Ghidra, RetDec, angr, LLM APIs, network access, GPU, or training. Those systems can later write this JSON format without changing the Phase 1A ranking code.
