# Source-Behavioral Diversity Handoff

## Git

- Branch: `phase2a-source-behavioral-diversity-prototype`
- Preregistration commit: `af95093e5889e66665263f4b9c1783eb863245a8`
- Result artifact commit: `e634d786266284f22146e7848178120c716e0796`
- Final HEAD: the commit containing this handoff.
- Phase 1h starting HEAD: `3bdb9f26621d2af4aea87aaa3923457532e549b0`
- Development baseline method freeze commit: `06dda89912103b94fc065d6f073581a7811154b1`

## Instrumentation

- Implementation: `clang_trace_pc_guard_v1` via clang trace-pc-guard over trusted source only.
- Supported source-function count: `42`
- Unsupported functions and reasons: `{}`
- Local GPU usage: `none`; subprocesses clear `CUDA_VISIBLE_DEVICES`.

## Detection

- Natural LLM Detection@1/2/4/8: `[(0, 2), (0, 2), (0, 2), (0, 2)]`
- Controlled Detection@1/2/4/8/16/32: `[(15, 37), (28, 37), (32, 37), (33, 37), (35, 37), (35, 37)]`
- Controlled low-density Detection: `[(1, 16), (7, 16), (11, 16), (12, 16), (14, 16), (14, 16)]`
- No-mismatch unexpected mismatches: `0`
- v1 delta at B=8: `0`
- Generic-boundary delta at B=8: `1`
- libFuzzer eval-count B=8 controlled primary: `0.411`
- libFuzzer 0.1s wall-clock controlled primary: `1.000`
- libFuzzer eval-count B=8 natural LLM primary: `0.000`
- libFuzzer 0.1s wall-clock natural LLM primary: `0.717`

## Costs

- source_pool_generation candidates/source=: `0.081986` seconds; source executions `0`
- source_instrumentation_compile candidates/source=: `3.634725` seconds; source executions `0`
- source_only_execution candidates/source=: `90.749791` seconds; source executions `19392`
- source_only_selection candidates/source=: `50.481012` seconds; source executions `0`
- per_candidate_audit_execution_median candidates/source=1: `0.015045` seconds; source executions `0`
- amortized_end_to_end candidates/source=1: `144.962561` seconds; source executions `19392.0`
- amortized_end_to_end candidates/source=2: `72.488803` seconds; source executions `9696.0`
- amortized_end_to_end candidates/source=4: `36.251924` seconds; source executions `4848.0`
- amortized_end_to_end candidates/source=8: `18.133485` seconds; source executions `2424.0`
- amortized_end_to_end candidates/source=16: `9.074265` seconds; source executions `1212.0`

## Ablations

- source_behavioral_diversity controlled_primary_fixture_passing_wrong B=8: `33/37` = `0.892`
- output_diversity_only controlled_primary_fixture_passing_wrong B=8: `31/37` = `0.838`
- coverage_diversity_only controlled_primary_fixture_passing_wrong B=8: `31/37` = `0.838`
- output_then_coverage controlled_primary_fixture_passing_wrong B=8: `34/37` = `0.919`
- coverage_then_output controlled_primary_fixture_passing_wrong B=8: `34/37` = `0.919`
- source_behavioral_diversity_no_distance controlled_primary_fixture_passing_wrong B=8: `34/37` = `0.919`
- source_behavioral_diversity natural_llm_primary_fixture_passing_wrong B=8: `0/2` = `0.000`
- output_diversity_only natural_llm_primary_fixture_passing_wrong B=8: `0/2` = `0.000`
- coverage_diversity_only natural_llm_primary_fixture_passing_wrong B=8: `0/2` = `0.000`
- output_then_coverage natural_llm_primary_fixture_passing_wrong B=8: `0/2` = `0.000`
- coverage_then_output natural_llm_primary_fixture_passing_wrong B=8: `0/2` = `0.000`
- source_behavioral_diversity_no_distance natural_llm_primary_fixture_passing_wrong B=8: `0/2` = `0.000`

## Natural Cases

- `libb64::src_cdecode.c::base64_decode_value::0001::7b72285f2481::llm::clang_O2::P1` input 61 output `-2`, ranks `{"coverage_diversity_only": null, "coverage_then_output": 15, "output_diversity_only": 14, "output_then_coverage": 14, "source_behavioral_diversity": 14, "source_behavioral_diversity_no_distance": 14}`, SBDW B8 `False`
- `libb64::src_cdecode.c::base64_decode_value::0001::7b72285f2481::llm::clang_O2::P2` input 61 output `-2`, ranks `{"coverage_diversity_only": null, "coverage_then_output": 15, "output_diversity_only": 14, "output_then_coverage": 14, "source_behavioral_diversity": 14, "source_behavioral_diversity_no_distance": 14}`, SBDW B8 `False`

## Development Gate

- Outcome: `stop_method_redesign`
- Minimum feasibility gate: `False`
- Strong prototype gate: `False`
- Stop condition: `True`
- Exact recommendation: stop the method paper or reposition as development characterization.

This Phase 2a prototype used Phase 1 data only as development data and did not start a new prospective holdout.
