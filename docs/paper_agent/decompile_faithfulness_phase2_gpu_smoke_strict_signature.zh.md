# Decompilation Faithfulness Phase 2 GPU Smoke

- GPU smoke gate passed: `True`
- Label diversity gate passed: `True`
- Model loaded: `True`
- Device: `cuda:2`
- Generations: `8`
- Parsed candidates: `6`
- Evaluated candidates: `6`
- Compile pass count: `2`
- Behavior labels: `{'faithful': 1, 'plausible_wrong': 1, 'compile_fail': 4}`
- Paired cases for trace AUC: `0`
- Trace metrics interpretable: `False`
- Cleaning statuses: `{'parsed_function': 6, 'parse_failed': 2}`
- Fixture collapse: `True`
- Trace pairwise AUC: `0.0000`

raw output 和 prompt 文件都保存在 output directory 下，便于失败归因。脚本不会设置 `CUDA_VISIBLE_DEVICES`；实际约束由 `--device cuda:2` 和显式 `.to(device)` 完成。

如果 `Paired cases for trace AUC` 为 0，则当前样本还没有同一 case 内的 faithful/wrong 配对，`fixture_collapse` 和 `trace_pairwise_auc` 只能作为占位统计，不能解读为 Dynamic Trace v2 失败。
