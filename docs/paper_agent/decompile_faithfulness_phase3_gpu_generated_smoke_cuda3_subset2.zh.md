# Decompilation Faithfulness Phase 3 GPU Generated Smoke

- Verdict: `needs-generation-cleaning`
- Model loaded: `True`
- Device: `cuda:3`
- Cases: `['sat_add8', 'within_range_inclusive', 'parity8', 'high_nibble', 'gcd_nonnegative', 'days_before_month', 'safe_div_round0']`
- Prompt IDs: `['strict_rewrite', 'strict_bug']`
- Generations: `14`
- Parsed candidates: `0`
- Parsed rate: `0.0000`
- Evaluated candidates: `0`
- Compile pass count: `0`
- Compile rate among parsed: `0.0000`
- Behavior labels: `{'faithful': 0, 'plausible_wrong': 0, 'compile_fail': 0}`
- Paired case count: `0`
- Trace pairwise AUC: `0.0000`
- Fixture collapse: `False`
- Cleaning statuses: `{'empty_output': 14}`
- Records: `/home/shx/projects/binary_faithful_decompilation/analysis_outputs/decompile_faithfulness/phase3_gpu_generated_smoke_cuda3_subset2/records.jsonl`

脚本不会设置 `CUDA_VISIBLE_DEVICES`；只通过 `--device cuda:2` 或 `--device cuda:3` 显式放置模型和输入。运行前仍必须检查 GPU 2/3 是否不会干扰他人任务。
