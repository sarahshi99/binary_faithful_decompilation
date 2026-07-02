# Decompilation Faithfulness Phase 7E LLM Public Generation

- Verdict: `needs-more-phase7-llm-public-samples`
- Model loaded: `True`
- Device: `cuda:2`
- Cases: `28`
- Generations: `56`
- Parsed candidates: `51`
- Evaluated candidates: `51`
- Compile pass count: `39`
- Behavior labels: `{'faithful': 28, 'compile_fail': 12, 'plausible_wrong': 11}`
- Cleaning status counts: `{'parsed_function': 51, 'parse_failed': 5}`
- Paired case count: `5`
- Fixture-passing wrong count: `1`
- Fixture-only AUC: `1.0000`
- Static structured proxy AUC: `0.9000`
- Dynamic Trace v3 AUC: `1.0000`
- Delta vs best non-oracle baseline: `0.0000`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase7_llm_public_cuda2_s0/records.jsonl`

## Interpretation

This is the GPU-backed public benchmark LLM candidate layer. It uses CodeFuse-DeBench source-known scalar C functions and evaluates generated candidates with the same Dynamic Trace v3 plus static structured proxy used in Phase 7C/C2.
