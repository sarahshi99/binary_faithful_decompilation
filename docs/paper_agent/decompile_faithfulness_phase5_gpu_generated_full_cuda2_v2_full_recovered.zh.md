# Decompilation Faithfulness Phase 5 GPU Generated Full

- Verdict: `needs-more-phase5-gpu-generated-samples`
- Candidate manifest verdict: `needs-full-candidate-generation`
- Model loaded: `True`
- Device: `cuda:2`
- Cases: `38`
- Prompt IDs: `['strict_rewrite', 'strict_bug']`
- Generations: `224`
- Parsed candidates: `157`
- Compile pass count: `57`
- Behavior labels: `{'faithful': 35, 'plausible_wrong': 22, 'compile_fail': 100}`
- Paired case count: `8`
- Fixture-passing wrong count: `0`
- Trace pairwise AUC: `1.0000`
- Fixture collapse: `True`
- Cleaning statuses: `{'parsed_function': 157, 'parse_failed': 67}`
- Records: `analysis_outputs/decompile_faithfulness/phase5_gpu_generated_full_cuda2_v2_full_recovered/records.jsonl`

这是 Phase 5 real-project source-known candidate generation/audit 输出。它回答 full-scale 数据规模风险，但最终 CCF-A/SOTA 结论仍必须等 Phase 5 result analysis 比较 fixture-only、static/binary motif、v1/v2/v3 baselines 后才能下。
