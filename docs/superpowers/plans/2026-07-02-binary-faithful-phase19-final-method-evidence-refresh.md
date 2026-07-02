# Binary-Faithful Phase 19 Final Method Evidence Refresh Plan

> REQUIRED: Use `superpowers:executing-plans` and
> `superpowers:verification-before-completion`. Do not use subagents, Task/Spawn,
> dispatching-parallel-agents, `tool_search`, or multi-agent workflows. Work only
> under `/home/shx/projects/binary_faithful_decompilation`.

## Goal

Phase 18 passed with the updated final input policy:

`source_literal_char_interleave`

Phase 19 refreshes paper-facing evidence so the readiness/runtime tables no
longer describe the older Phase 12/16 `fixture_neighbor_first` default.

## Inputs

- Phase 18 unified records:
  `analysis_outputs/decompile_faithfulness/phase18_source_literal_char_policy/unified_low_budget/*/records_budgeted.jsonl`
- Phase 18 unified summary:
  `analysis_outputs/decompile_faithfulness/phase18_source_literal_char_policy/phase12_unified_low_budget.json`

## Outputs

- `docs/paper_agent/decompile_faithfulness_phase19_final_method_readiness.json`
- `docs/paper_agent/decompile_faithfulness_phase19_final_method_readiness.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase19_experiment_section_draft.md`
- `docs/paper_agent/decompile_faithfulness_phase19_final_runtime_risk.json`
- `docs/paper_agent/decompile_faithfulness_phase19_final_runtime_risk.zh.md`

## Verification

```bash
python -m analysis.decompile_faithfulness.run_phase14_paper_readiness \
  --phase12-json analysis_outputs/decompile_faithfulness/phase18_source_literal_char_policy/phase12_unified_low_budget.json \
  --records-dir analysis_outputs/decompile_faithfulness/phase18_source_literal_char_policy/unified_low_budget \
  --output-json docs/paper_agent/decompile_faithfulness_phase19_final_method_readiness.json \
  --output-zh docs/paper_agent/decompile_faithfulness_phase19_final_method_readiness.zh.md \
  --draft-md docs/paper_agent/decompile_faithfulness_phase19_experiment_section_draft.md

python -m analysis.decompile_faithfulness.run_phase16_runtime_risk_breakdown \
  --phase12-dir analysis_outputs/decompile_faithfulness/phase18_source_literal_char_policy/unified_low_budget \
  --output-dir analysis_outputs/decompile_faithfulness/phase19_final_runtime_risk \
  --output-json docs/paper_agent/decompile_faithfulness_phase19_final_runtime_risk.json \
  --output-zh docs/paper_agent/decompile_faithfulness_phase19_final_runtime_risk.zh.md \
  --strategy-id source_literal_char_interleave

python -m json.tool docs/paper_agent/decompile_faithfulness_phase19_final_method_readiness.json
python -m json.tool docs/paper_agent/decompile_faithfulness_phase19_final_runtime_risk.json
git diff --check
```
