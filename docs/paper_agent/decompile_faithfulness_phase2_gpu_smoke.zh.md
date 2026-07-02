# Decompilation Faithfulness Phase 2 GPU Smoke

- GPU smoke gate passed: `True`
- Label diversity gate passed: `False`
- Model loaded: `True`
- Device: `cuda:2`
- Generations: `4`
- Parsed candidates: `1`
- Evaluated candidates: `1`
- Compile pass count: `1`
- Behavior labels: `{'faithful': 0, 'plausible_wrong': 1, 'compile_fail': 0}`
- Paired cases for trace AUC: `0`
- Trace metrics interpretable: `False`
- Cleaning statuses: `{'parse_failed': 3, 'parsed_function': 1}`
- Fixture collapse: `True`
- Trace pairwise AUC: `0.0000`

raw output 和 prompt 文件都保存在 output directory 下，便于失败归因。脚本不会设置 `CUDA_VISIBLE_DEVICES`；实际约束由 `--device cuda:2` 和显式 `.to(device)` 完成。

如果 `Paired cases for trace AUC` 为 0，则当前样本还没有同一 case 内的 faithful/wrong 配对，`fixture_collapse` 和 `trace_pairwise_auc` 只能作为占位统计，不能解读为 Dynamic Trace v2 失败。
