# Decompilation Faithfulness Phase 3 GPU Generated Smoke

- Verdict: `needs-more-phase3-gpu-generated-samples`
- Model loaded: `True`
- Device: `cuda:3`
- Cases: `['sat_add8', 'within_range_inclusive', 'parity8', 'high_nibble', 'gcd_nonnegative', 'days_before_month', 'safe_div_round0']`
- Prompt IDs: `['strict_rewrite', 'strict_bug']`
- Generations: `14`
- Parsed candidates: `12`
- Parsed rate: `0.8571`
- Evaluated candidates: `12`
- Compile pass count: `7`
- Compile rate among parsed: `0.5833`
- Behavior labels: `{'faithful': 4, 'plausible_wrong': 3, 'compile_fail': 5}`
- Paired case count: `1`
- Trace pairwise AUC: `1.0000`
- Fixture collapse: `True`
- Cleaning statuses: `{'parsed_function': 12, 'parse_failed': 2}`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase3_gpu_generated_smoke_cuda3_subset2_fp16/records.jsonl`

脚本不会设置 `CUDA_VISIBLE_DEVICES`；只通过 `--device cuda:2` 或 `--device cuda:3` 显式放置模型和输入。运行前仍必须检查 GPU 2/3 是否不会干扰他人任务。
