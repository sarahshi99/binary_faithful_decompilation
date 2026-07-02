# Decompilation Faithfulness Phase 3 GPU Generated Smoke

- Verdict: `pass-phase3-gpu-generated-smoke`
- Model loaded: `True`
- Device: `cuda:3`
- Cases: `['sat_add8', 'within_range_inclusive', 'parity8', 'high_nibble', 'gcd_nonnegative', 'days_before_month', 'safe_div_round0']`
- Prompt IDs: `['strict_bug']`
- Generations: `21`
- Parsed candidates: `15`
- Parsed rate: `0.7143`
- Evaluated candidates: `15`
- Compile pass count: `10`
- Compile rate among parsed: `0.6667`
- Behavior labels: `{'faithful': 5, 'plausible_wrong': 5, 'compile_fail': 5}`
- Paired case count: `4`
- Trace pairwise AUC: `1.0000`
- Fixture collapse: `False`
- Cleaning statuses: `{'parsed_function': 15, 'parse_failed': 6}`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase3_gpu_generated_smoke_cuda3_subset2_bugtopup_fp16/records.jsonl`

脚本不会设置 `CUDA_VISIBLE_DEVICES`；只通过 `--device cuda:2` 或 `--device cuda:3` 显式放置模型和输入。运行前仍必须检查 GPU 2/3 是否不会干扰他人任务。
