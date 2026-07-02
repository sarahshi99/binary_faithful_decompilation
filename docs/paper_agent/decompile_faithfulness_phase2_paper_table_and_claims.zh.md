# Decompilation Faithfulness Phase 2 Paper Table And Claims

## Paper-facing Claim

Phase 2 支持的主张应写成：

> 在 source-known、小函数、bounded generated inputs 的 localized semantic bug auditing 设置下，Dynamic Trace v2 在本地 LLM 生成候选分布上仍保持强区分度，并且没有退化成 fixture-only oracle。

不应写成：

> 我们已经证明了 general decompilation faithfulness verifier，或者已经完成 real-project transfer。

## Experimental Setup

- Source cases：8 个 built-in source-known C functions。
- Candidate source：本地 `Dream-Coder-v0-Instruct-7B`。
- Prompt families：
  - `strict_rewrite`：要求等价改写。
  - `strict_bug`：要求生成 plausible subtle bug。
- Initial label：所有 LLM candidates 均为 `unknown`。
- Label resolution：
  - fixture behavior pass -> `faithful`
  - fixture behavior fail -> `plausible_wrong`
  - compile / runtime failure -> `compile_fail`
- Primary score：Dynamic Trace v2 `trace_total`。
- Evaluation unit：同一 case 内比较 `faithful` vs `plausible_wrong` 的 pairwise AUC。

## Main Result Table

| Metric | Value |
|---|---:|
| Generations | 100 |
| Parsed candidates | 78 |
| Evaluated candidates | 78 |
| Compile-passed candidates | 63 |
| Faithful fixture-passing candidates | 34 |
| Plausible-wrong candidates | 29 |
| Compile-fail candidates | 15 |
| Cases represented | 8 / 8 |
| Cases with faithful/wrong pair | 8 / 8 |
| Min compile-passed candidates per case | 5 |
| Fixture collapse | False |
| Dynamic Trace v2 pairwise AUC | 0.9623 |

Verdict：`pass-phase2-result-analysis`。

## Per-case Result Table

| Case | Generations | Parsed | Compiled | Faithful | Wrong | Compile Fail | AUC | Note |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `absdiff` | 10 | 8 | 7 | 4 | 3 | 1 | 1.0000 | clean separation |
| `clamp8` | 10 | 7 | 6 | 2 | 4 | 1 | 1.0000 | small but positive margin |
| `count_bits8` | 10 | 8 | 5 | 3 | 2 | 3 | 1.0000 | includes hidden fixture-passing semantic drift |
| `gcd_positive` | 10 | 8 | 7 | 3 | 4 | 1 | 1.0000 | v2 keeps Phase 1K gain on hard case |
| `is_power_of_two` | 20 | 13 | 11 | 4 | 7 | 2 | 0.9286 | zero-boundary blind spot remains |
| `max3` | 20 | 17 | 12 | 11 | 1 | 5 | 1.0000 | few wrong candidates, but separated |
| `signum` | 10 | 10 | 9 | 4 | 5 | 1 | 0.9000 | zero-boundary blind spot remains |
| `sum_to_n` | 10 | 7 | 6 | 3 | 3 | 1 | 1.0000 | clean separation |

## Prompt-family Result Table

| Prompt | Generations | Parsed | Compiled | Faithful | Wrong | Compile Fail | Faithful Rate Among Compiled | Wrong Rate Among Compiled |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `strict_rewrite` | 50 | 35 | 28 | 25 | 3 | 7 | 0.8929 | 0.1071 |
| `strict_bug` | 50 | 43 | 35 | 9 | 26 | 8 | 0.2571 | 0.7429 |

Interpretation：

- `strict_rewrite` 主要生成 fixture-passing rewrites，适合检查 false positive。
- `strict_bug` 主要生成 plausible wrong candidates，适合检查 bug detection。
- 两个 prompt 都有少量 drift，说明不能把 prompt intent 当 label；必须保留 behavior gate。

## Non-oracle Evidence

最关键的 positive example 是 `count_bits8`：

```c
int count_bits8(int x) {
    int total = 0;
    for (int i = 0; i < 16; i++) {
        if ((x & (1 << i)) != 0) {
            total++;
        }
    }
    return total;
}
```

它通过了 fixture behavior gate，但 Dynamic Trace v2 在更宽的 generated inputs 上发现 mismatch。这个例子说明：

- `faithful` 在当前实验中只是 fixture-passing，不是完整语义真值。
- Dynamic Trace v2 不是简单复读 fixture label。
- 论文应强调 localized semantic bug auditing，而不是完整等价证明。

## Remaining Blind Spots

最低分 wrong candidates 暴露出一个 v2 blind spot：

- `signum` 的 zero bug 被 fixture gate 抓到，但 primary trace score 为 0。
- `is_power_of_two` 的 zero / non-positive boundary bug 也出现类似现象。

这说明 v2 generated trace inputs 对某些 exact boundary values 覆盖不足。下一步 v3 不应继续堆 GPU generation，而应做 boundary/fixture-aware scoring 的 CPU-only 诊断：

1. 检查 `trace_total + boundary_mismatch` 是否能解决 zero-boundary blind spot。
2. 将 `fixture_mismatch` 作为 diagnostic upper bound，而不是直接作为主方法。
3. 如果 fixture-aware score 明显提升但 boundary-only score 不提升，则说明需要重新生成 boundary trace inputs，而不是只改 reranking 公式。

## V3 Boundary Trace Update

已完成 CPU-only v3 boundary trace 实验：

- 输出：`docs/paper_agent/decompile_faithfulness_phase2_v3_boundary_trace.zh.md`
- 方法：不使用 `fixture_mismatch_rate` 作为主分数，只在 primary generated trace inputs 中强制保留通用 boundary probes，例如 `0`, `-1`, `1`。
- Candidates：63 个 compile-passed candidates。
- Pairwise AUC：`1.0000`。
- Case AUC：8/8 cases 均为 `1.0000`。
- `fixture_collapse=False`。
- trace-zero blind spot wrong count：`0`。

这说明 v2 的 zero-boundary blind spot 主要来自 input-generation policy，而不是 Dynamic Trace score 本身失效。论文里可以把 v3 写成一个小但关键的 refinement：保留 domain-aware trace，同时确保 generic boundary values 不会因为和 fixture args 重合而被删掉。

## Claim Text For Draft

可写入论文的版本：

> To test whether Dynamic Trace v2 remains useful beyond controlled mutations, we generated 100 candidates from a local code model over 8 source-known C functions. After deterministic cleaning and compilation, 63 candidates were executable, covering both fixture-passing and fixture-failing behaviors in every case. Dynamic Trace v2 achieved 0.9623 pairwise AUC when ranking fixture-failing candidates above fixture-passing candidates within the same source case, with no fixture-collapse. The generated distribution also exposed a fixture-passing but trace-mismatching candidate in `count_bits8`, suggesting that trace-based auditing can identify semantic drift not covered by the original fixture tests.

如果纳入 v3 boundary trace refinement，可写成：

> A boundary-preserving v3 trace input policy, which retains generic boundary probes even when they overlap with fixture inputs, improves the generated-candidate pairwise AUC from 0.9623 to 1.0000 and repairs the remaining `signum` and `is_power_of_two` boundary failures without using fixture mismatch as a scoring feature.

必须同时写入的限制：

> This experiment is source-known and bounded-input. It does not establish full semantic equivalence, a general decompiler faithfulness verifier, or real-project transfer.
