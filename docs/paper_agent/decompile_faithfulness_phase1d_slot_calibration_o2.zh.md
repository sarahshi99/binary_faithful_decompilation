# Decompilation Faithfulness Phase 1D Slot-Calibration O2 Follow-Up

## Question

slot-vote concentration 在 `O2` 编译优化下是否仍能区分局部 semantic bugs 和 behavior-preserving rewrite drift？

## Dataset

- Records：`6`
- Faithful candidates：`3`
- Plausible-wrong candidates：`3`
- Candidate source：Phase 1B 的 realistic manual candidates
- Compiler optimization：`O2`

## Metrics

- Pairwise slot-concentration AUC：`0.6667`
- Mean faithful slot concentration：`0.4352`
- Mean wrong slot concentration：`0.7000`
- Verdict：`weak-signal`

## Interpretation

`O2` 下 slot-concentration 信号仍有方向性，但明显弱于 `O0`：AUC 从 `1.0000` 降到 `0.6667`。主要风险是优化器会把 faithful rewrite 和 original 编译成完全相同或非常不同的形态，也会改变局部 feature delta 的集中程度。

这个结果说明 slot-local calibration 比 raw global distance 更有希望，但还不能直接进入真实项目迁移。下一步需要 optimization-aware calibration：至少同时报告 `O0/O2`，并把 compiler-induced rewrite drift 和 semantic bug drift 分开建模。
