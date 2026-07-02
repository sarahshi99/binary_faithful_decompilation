# Decompilation Faithfulness Phase 3 GPU Generated Smoke

- Verdict: `needs-more-phase3-gpu-generated-samples`
- Model loaded: `True`
- Device: `cuda:2`
- Cases: `['sat_add8', 'within_range_inclusive', 'parity8', 'gcd_nonnegative', 'safe_div_round0']`
- Prompt IDs: `['strict_bug']`
- Generations: `15`
- Parsed candidates: `10`
- Parsed rate: `0.6667`
- Evaluated candidates: `10`
- Compile pass count: `4`
- Compile rate among parsed: `0.4000`
- Behavior labels: `{'faithful': 1, 'plausible_wrong': 3, 'compile_fail': 6}`
- Paired case count: `0`
- Trace pairwise AUC: `0.0000`
- Fixture collapse: `True`
- Cleaning statuses: `{'parse_failed': 5, 'parsed_function': 10}`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase3_gpu_generated_smoke_cuda2_subset1_bugtopup_fp16/records.jsonl`

脚本不会设置 `CUDA_VISIBLE_DEVICES`；只通过 `--device cuda:2` 或 `--device cuda:3` 显式放置模型和输入。运行前仍必须检查 GPU 2/3 是否不会干扰他人任务。
