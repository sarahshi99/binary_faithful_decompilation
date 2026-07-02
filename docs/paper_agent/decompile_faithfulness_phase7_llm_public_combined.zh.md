# Decompilation Faithfulness Phase 7E LLM Public Combined

- Verdict: `method-negative-phase7-llm-public`
- Source functions: `56`
- Generations: `224`
- Parsed candidates: `195`
- Evaluated candidates: `195`
- Compile pass count: `143`
- Behavior labels: `{'faithful': 107, 'compile_fail': 52, 'plausible_wrong': 36}`
- Cleaning status counts: `{'parsed_function': 195, 'parse_failed': 29}`
- Paired case count: `24`
- Fixture-passing wrong count: `3`
- Fixture-only AUC: `0.9741`
- Static structured proxy AUC: `0.7759`
- Dynamic Trace v3 AUC: `1.0000`
- Delta vs best non-oracle baseline: `0.0259`

## Gate Check

| Gate | Passed |
|---|---:|
| `missing_inputs_gate` | `True` |
| `compile_pass_scale_gate` | `True` |
| `paired_case_gate` | `True` |
| `parsed_rate_gate` | `True` |
| `v3_beats_fixture_gate` | `True` |
| `v3_beats_static_gate` | `True` |
| `sota_delta_gate` | `False` |
| `fixture_collapse_gate` | `True` |

## By Prompt

| Prompt | Candidates | Compile Pass | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|---:|
| `strict_bug` | `100` | `69` | `12` | `1.0000` | `0.7500` | `1.0000` |
| `strict_rewrite` | `95` | `74` | `5` | `0.8000` | `0.9000` | `1.0000` |

## Interpretation

This combines the GPU 2/3 Phase 7E public LLM shards. It is a model-generated candidate baseline, not a decompiler-output baseline. If the scale gates fail, top-up generation should target missing paired cases and cleaning/compile failures.
