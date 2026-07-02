# Decompilation Faithfulness Phase 7E LLM Public Generation

- Verdict: `needs-more-phase7-llm-public-samples`
- Model loaded: `True`
- Device: `cuda:2`
- Cases: `1`
- Generations: `1`
- Parsed candidates: `1`
- Evaluated candidates: `1`
- Compile pass count: `1`
- Behavior labels: `{'plausible_wrong': 1}`
- Cleaning status counts: `{'parsed_function': 1}`
- Paired case count: `0`
- Fixture-passing wrong count: `0`
- Fixture-only AUC: `0.0000`
- Static structured proxy AUC: `0.0000`
- Dynamic Trace v3 AUC: `0.0000`
- Delta vs best non-oracle baseline: `0.0000`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase7_llm_public_preflight_bug500_cuda2/records.jsonl`

## Interpretation

This is the GPU-backed public benchmark LLM candidate layer. It uses CodeFuse-DeBench source-known scalar C functions and evaluates generated candidates with the same Dynamic Trace v3 plus static structured proxy used in Phase 7C/C2.
