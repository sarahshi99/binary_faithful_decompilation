# Decompilation Faithfulness Phase 1D Slot-Calibration Audit

## Question

slot-vote concentration 是否能比 raw global feature distance 更好地区分局部 semantic bugs 和大范围 behavior-preserving rewrite drift？

## Dataset

- Records：`6`
- Faithful candidates：`3`
- Plausible-wrong candidates：`3`
- Candidate source：Phase 1B 的 realistic manual candidates
- Compiler optimization：`O0`

## Metrics

- Pairwise slot-concentration AUC：`1.0000`
- Mean faithful slot concentration：`0.6263`
- Mean wrong slot concentration：`0.7559`
- Verdict：`continue-slot-calibration`

## Interpretation

这个 audit 使用 Phase 1B 同一组 realistic manual candidates，但不再用 total binary feature distance 排序，而是用 slot-local votes 的 concentration 作为 suspiciousness score。

结果支持方法修正：behavior-preserving rewrites 往往有更大的全局 binary distance，但 mismatch 分布更分散；plausible-wrong candidates 的 mismatch 更集中在少数 slot 上。因此，raw global distance 不能直接作为任意 C candidate 的 faithful ranker，但 slot-local mismatch / calibration 是更有希望的方向。

## Next Route

下一步应扩大 slot-calibration audit，而不是直接进入 real-project transfer。优先增加更多 realistic hard negatives、行为保持 rewrites、不同 optimization level，并检查 slot-concentration 是否仍能区分局部语义错误和整体实现漂移。当前 O2 follow-up 已显示信号变弱，因此 optimization-aware calibration 是必须解决的问题。
