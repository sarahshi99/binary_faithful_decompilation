# Decompilation Faithfulness Phase 5 Result Analysis

- Verdict: `scale-positive-sota-delta-not-established`
- Source functions: `38`
- Source projects: `['c_algorithms', 'thealgorithms_c']`
- Candidates: `450`
- Compile pass count: `303`
- Behavior labels: `{'faithful': 109, 'plausible_wrong': 194, 'compile_fail': 147}`
- Paired case count: `38`
- Fixture-passing wrong count: `0`
- Fixture-only AUC: `1.0000`
- V3 trace total AUC: `1.0000`
- SOTA delta vs best non-oracle baseline: `0.0000`
- Fixture collapse: `True`
- Candidate manifest verdict: `pass-phase5-full-candidate-generation`

## Gate Check

| Gate | Passed |
|---|---:|
| `scale_gate` | `True` |
| `auc_gate` | `True` |
| `sota_delta_gate` | `False` |
| `fixture_collapse_gate` | `False` |
| `fixture_passing_wrong_gate` | `False` |

## By Candidate Source

| Source Kind | Candidates | Compile Pass | Paired Cases | Fixture-passing Wrong | Fixture-only AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|---:|
| `deterministic_phase5` | `190` | `190` | `38` | `0` | `1.0000` | `1.0000` |
| `local_llm` | `103` | `56` | `10` | `0` | `1.0000` | `1.0000` |
| `local_llm_recovered` | `157` | `57` | `8` | `0` | `1.0000` | `1.0000` |

## Interpretation

Phase 5 的规模门槛可以由 deterministic candidate layer 支撑，但这不自动等价于 CCF-A/SOTA 贡献。当前最严格的问题是：如果 fixture-only baseline 已经能分开大部分 deterministic/manual stress wrong candidates，那么 V3 的机制优势还没有被充分证明。

因此后续应把注意力放在 fixture-passing wrong / subtle semantic drift 的候选分布上：LLM/decompiler candidates、targeted boundary bugs、以及 Phase 6 decompiler-output。只有当 V3 在这些更难候选上比 fixture-only 和其他 non-oracle baseline 至少高 `0.05` AUC，才可以写成强 SOTA contribution。
