# Decompilation Faithfulness Phase 5 GPU Generated Full

- Verdict: `needs-more-phase5-gpu-generated-samples`
- Candidate manifest verdict: `needs-full-candidate-generation`
- Model loaded: `True`
- Device: `cuda:3`
- Cases: `19`
- Prompt IDs: `['strict_rewrite', 'strict_bug']`
- Generations: `114`
- Parsed candidates: `61`
- Compile pass count: `37`
- Behavior labels: `{'faithful': 23, 'plausible_wrong': 14, 'compile_fail': 24}`
- Paired case count: `7`
- Fixture-passing wrong count: `0`
- Trace pairwise AUC: `1.0000`
- Fixture collapse: `True`
- Cleaning statuses: `{'parsed_function': 61, 'parse_failed': 53}`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase5_gpu_generated_full_cuda3_s1/records.jsonl`

这是 Phase 5 real-project source-known candidate generation/audit 输出。它回答 full-scale 数据规模风险，但最终 CCF-A/SOTA 结论仍必须等 Phase 5 result analysis 比较 fixture-only、static/binary motif、v1/v2/v3 baselines 后才能下。
