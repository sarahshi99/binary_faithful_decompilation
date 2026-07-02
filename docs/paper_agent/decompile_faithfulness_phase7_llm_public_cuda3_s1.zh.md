# Decompilation Faithfulness Phase 7E LLM Public Generation

- Verdict: `needs-more-phase7-llm-public-samples`
- Model loaded: `True`
- Device: `cuda:3`
- Cases: `28`
- Generations: `56`
- Parsed candidates: `49`
- Evaluated candidates: `49`
- Compile pass count: `39`
- Behavior labels: `{'faithful': 26, 'plausible_wrong': 13, 'compile_fail': 10}`
- Cleaning status counts: `{'parsed_function': 49, 'parse_failed': 7}`
- Paired case count: `8`
- Fixture-passing wrong count: `2`
- Fixture-only AUC: `1.0000`
- Static structured proxy AUC: `0.6875`
- Dynamic Trace v3 AUC: `1.0000`
- Delta vs best non-oracle baseline: `0.0000`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase7_llm_public_cuda3_s1/records.jsonl`

## Interpretation

This is the GPU-backed public benchmark LLM candidate layer. It uses CodeFuse-DeBench source-known scalar C functions and evaluates generated candidates with the same Dynamic Trace v3 plus static structured proxy used in Phase 7C/C2.
