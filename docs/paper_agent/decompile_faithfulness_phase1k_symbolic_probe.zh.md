# Decompilation Faithfulness Phase 1K Symbolic Probe

## 依赖环境快照

在 `/home/shx/miniconda3/envs/dllm_env/bin/python` 里探测到当前没有可用的 symbolic/concolic 工具栈：

| 依赖 | 是否可用 |
|---|---:|
| `z3` | false |
| `angr` | false |
| `claripy` | false |
| `capstone` | false |
| `unicorn` | false |

Phase 1K 明确不安装新依赖、不联网，所以 Route B 本轮不能直接运行严格的 symbolic 或 concolic 实验。

## 不安装依赖的 fallback

不新增依赖时，只能做 source-level harness 上的有限输入枚举。这个能力已经由 Route A dynamic trace 更直接地覆盖了。没有 `z3` 约束求解，或者 `angr`/`claripy` 的 binary lifting，再强行包装成 symbolic 会变成新的手写 heuristic，不能提供足够独立的证据。

## 候选 hard cases

| Case | 意义 |
|---|---|
| `gcd_positive` | Route A 仍然不能可靠区分 faithful 和 plausible-wrong，是最需要解释的失败点。 |
| `signum` | 分支边界紧凑，适合未来用路径约束检查，但当前仍有弱点。 |
| `max3` | 工具可用后适合作为 branch-order 等价的 sanity target。 |
| `sum_to_n` | 可以检查 loop summary 是否提供 dynamic trace 之外的增量价值。 |

## 结论

`needs-dependency-plan`

Route B 在科学上仍然值得保留，尤其适合解释 hard cases；但它需要单独的依赖控制计划，不能在本轮 Phase 1K 里强行推进，也不能单独证明现在就该启动 GPU candidate generation。
