# Decompilation Faithfulness Phase 2 GPU Smoke

- GPU smoke gate passed: `True`
- Label diversity gate passed: `True`
- Paired generation gate passed: `True`
- Model loaded: `True`
- Device: `combined`
- Generations: `100`
- Parsed candidates: `78`
- Parsed rate: `0.7800`
- Evaluated candidates: `78`
- Compile pass count: `63`
- Compile rate among parsed: `0.8077`
- Behavior labels: `{'faithful': 34, 'plausible_wrong': 29, 'compile_fail': 15}`
- Paired cases for trace AUC: `8`
- Trace metrics interpretable: `True`
- Cleaning statuses: `{'parsed_function': 78, 'parse_failed': 22}`
- Fixture collapse: `False`
- Trace pairwise AUC: `0.9623`

raw output 和 prompt 文件都保存在 output directory 下，便于失败归因。脚本不会设置 `CUDA_VISIBLE_DEVICES`；实际约束由 `--device cuda:2` 和显式 `.to(device)` 完成。

如果 `Paired cases for trace AUC` 为 0，则当前样本还没有同一 case 内的 faithful/wrong 配对，`fixture_collapse` 和 `trace_pairwise_auc` 只能作为占位统计，不能解读为 Dynamic Trace v2 失败。

## Full Gate 判断

结论：`pass-phase2-full-candidate-generation`。

- 8 cases 全覆盖。
- 每 case 编译通过候选数均 >= 5：
  - `absdiff=7`
  - `clamp8=6`
  - `count_bits8=5`
  - `gcd_positive=7`
  - `is_power_of_two=11`
  - `max3=12`
  - `signum=9`
  - `sum_to_n=6`
- 8/8 cases 同时包含 `faithful` 和 `plausible_wrong`。
- `fixture_collapse=False`，说明没有退化成 fixture-only oracle。
- `trace_pairwise_auc=0.9623`，Dynamic Trace v2 在 generated candidate distribution 上仍然保持强区分度。

Prompt 分布符合预期：

- `strict_rewrite`：`faithful=25`，`plausible_wrong=3`，`compile_fail=7`。
- `strict_bug`：`faithful=9`，`plausible_wrong=26`，`compile_fail=8`。

下一步不建议继续堆 GPU 生成量。当前更应该做 result analysis：按 case / prompt / error type 分析哪些 generated bugs 被 Dynamic Trace v2 捕获、哪些 compile/cleaning failure 需要归因，以及这组结果如何支持 source-known localized semantic bug auditing 的论文边界。
