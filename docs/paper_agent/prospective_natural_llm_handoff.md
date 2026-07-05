# Prospective Natural LLM Handoff

## Git And Seals

- Branch: `phase1h-prospective-natural-llm-candidates`
- Preregistration commit: `c9e66590b6fda02158ffc4c1da8ca4df342e30e2`
- Candidate-seal commit: `a97ab31731573d60f938fd44281cac12fb820bf1`
- Candidate-seal hash: `883e7c36443348660b47e401a4b37ae5855fe7851737349e07bd3b5abef674cf`
- Evaluation-population seal commit: `bf20104cd01245f82a30b986c688542d0b0c87df`
- Evaluation-population seal hash: `d53093a9847918ac8d070f4eea616c2030bba160c9db0fda9cdbb34e36fbe12b`
- Result artifact commit: `e272d73903450cdc0e87ff5e761a36cf7d4bf332`
- Final HEAD: the commit containing this handoff.
- Sealed holdout hash: `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`
- Frozen method commit: `06dda89912103b94fc065d6f073581a7811154b1`

## Provider

- Provider/model: `mycodex` / `gpt-5.5`
- API call count: `168`
- API cost: `unknown unless provider usage metadata includes billing`
- Local GPU usage: `none`
- KLEE usage: `none`
- Second traditional decompiler integration: `none`

## Candidate Counts

- Attempts: `168`
- Parse-ready: `168`
- Compile-ready: `168`
- Semantic wrong: `2`
- No-mismatch: `166`
- Non-evaluable: `0`
- Fixture-passing semantic-wrong: `2`
- Low-density count: `2`
- Project distribution: `{"libb64": 2}`
- Prompt-family distribution: `{"P1": 1, "P2": 1}`
- Semantic-wrong project span: `1`

## Final Policy

- B=1: `0/2` = `0.000`
- B=2: `0/2` = `0.000`
- B=4: `0/2` = `0.000`
- B=8: `0/2` = `0.000`
- B=16: `0/2` = `0.000`
- B=32: `0/2` = `0.000`

## Baselines

- generic_type_boundaries B=8: `0/2` = `0.000`
- literal_first_concatenation B=8: `0/2` = `0.000`
- libFuzzer evaluation_count 8: mean Detection `0.000`
- libFuzzer evaluation_count 32: mean Detection `0.033`
- libFuzzer evaluation_count 128: mean Detection `0.367`
- libFuzzer wall_clock 0.1: mean Detection `0.717`
- No-mismatch false alarms in libFuzzer summaries: `0`

## Integrity

- No-mismatch unexpected mismatches: `0`
- Sealed artifacts unchanged: `True`
- Method hashes unchanged: `True`
- Frozen auditor was not run before candidate and population seals.
- Candidate prompts excluded trusted source bodies, fixtures, labels, witnesses, source literals extracted separately, and final-policy probes.

## Interpretation

- Gate result: `negative_or_feasibility_result`
- Paper consequence: Report as feasibility or characterization study and stop further experiments after Phase 1h.
- Natural evidence gate failed because only `2` fixture-passing semantic-wrong candidates were found, both from `libb64`.

## Tests

- `CUDA_VISIBLE_DEVICES= python -m py_compile analysis/decompile_faithfulness/prospective_natural_llm.py`
- `CUDA_VISIBLE_DEVICES= python -m unittest analysis.decompile_faithfulness.tests.test_prospective_natural_llm`
- `CUDA_VISIBLE_DEVICES= python -m unittest discover analysis/decompile_faithfulness/tests`
- `CUDA_VISIBLE_DEVICES= python - <<'PY' ... prospective_natural_llm.preflight_checks(...) ... PY`

The complete Phase 1h run stayed CPU-only locally, did not install or run KLEE, did not generate new controlled mutations, and did not modify the frozen method or sealed holdout artifacts.
