# Decompilation Faithfulness Phase 2 GPU Smoke

- GPU smoke gate passed: `True`
- Label diversity gate passed: `True`
- Paired generation gate passed: `True`
- Model loaded: `True`
- Device: `cuda:2`
- Generations: `80`
- Parsed candidates: `60`
- Parsed rate: `0.7500`
- Evaluated candidates: `60`
- Compile pass count: `50`
- Compile rate among parsed: `0.8333`
- Behavior labels: `{'faithful': 27, 'plausible_wrong': 23, 'compile_fail': 10}`
- Paired cases for trace AUC: `8`
- Trace metrics interpretable: `True`
- Cleaning statuses: `{'parsed_function': 60, 'parse_failed': 20}`
- Fixture collapse: `False`
- Trace pairwise AUC: `0.9733`

raw output 和 prompt 文件都保存在 output directory 下，便于失败归因。脚本不会设置 `CUDA_VISIBLE_DEVICES`；实际约束由 `--device cuda:2` 和显式 `.to(device)` 完成。

如果 `Paired cases for trace AUC` 为 0，则当前样本还没有同一 case 内的 faithful/wrong 配对，`fixture_collapse` 和 `trace_pairwise_auc` 只能作为占位统计，不能解读为 Dynamic Trace v2 失败。
