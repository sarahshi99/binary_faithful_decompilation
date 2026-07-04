# Strong Baselines And Mechanism Handoff

## Git

- Branch: `phase1f-strong-baselines-and-mechanism`
- Preregistration commit: `b905690dcd1ce27a4015eae64f9c15be4bb641a1`
- Result commit: `b905690dcd1ce27a4015eae64f9c15be4bb641a1` (pre-commit working tree context at generation)
- Verified holdout seal: `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`
- Method freeze commit: `06dda89912103b94fc065d6f073581a7811154b1`

## Populations

- Primary fixture-passing semantic-wrong candidates: `37`
- Low-density fixture-passing wrong candidates: `16`
- Non-fixture-overfit fixture-passing wrong candidates: `15`
- Exact-domain no-mismatch comparison candidates: `34`

## Final Versus Literal-First

- B=1: final `15/37`, literal-first `18/37`, delta `-0.081`
- B=2: final `25/37`, literal-first `27/37`, delta `-0.054`
- B=4: final `30/37`, literal-first `30/37`, delta `0.000`
- B=8: final `33/37`, literal-first `33/37`, delta `0.000`
- B=16: final `34/37`, literal-first `34/37`, delta `0.000`
- B=32: final `34/37`, literal-first `34/37`, delta `0.000`

## Paired Discordance At B=8

- Final versus generic-boundary wins/losses: `2/1`
- B=8 final misses: `["musl::src_network_inet_pton.c::hexval::0001::a0a6dbc2a411::controlled::comparison_operator_replacement_00", "musl::src_regex_regcomp.c::hexval::0004::5a81c0c932f7::controlled::return_value_perturbation_00", "sbase::find.c::cmp_eq::0002::16afa3d71aab::controlled::fixture_overfit_construction_01", "sbase::find.c::cmp_lt::0003::3ff7fb5ec166::controlled::fixture_overfit_construction_00"]`
- B=32 final misses: `["musl::src_network_inet_pton.c::hexval::0001::a0a6dbc2a411::controlled::comparison_operator_replacement_00", "musl::src_regex_regcomp.c::hexval::0004::5a81c0c932f7::controlled::return_value_perturbation_00", "sbase::find.c::cmp_eq::0002::16afa3d71aab::controlled::fixture_overfit_construction_01"]`
- Non-fixture-overfit Detection@8: `0.867`

## Out-Of-Domain

- Final B=8 primary generated probes: `289`
- Final B=8 primary out-of-domain probes: `2`
- Final B=8 primary distinct out-of-domain witnesses: `2`
- Confirmed final B=8 distinct out-of-domain witnesses: `2`

## External Baselines

- KLEE status: `not_run_blocked`; supported candidates `0`.
- libFuzzer status: `completed`; supported candidates `37`.
- libFuzzer evaluation-count Detection@8 mean: `0.411`.
- libFuzzer no-mismatch false-alarm rows at B=8: `0`.
- libFuzzer wall-clock matrix: `not_run_blocked` due to CPU-budget gate.

## Exhaustive Reference

- Exact-label reference rows: `94`
- Total enumeration time was not recorded in the sealed label artifact; the reference table reports input-domain cost and first-witness rank.

## Interpretation Gates

- Interleaving classification: `literal-first is better`
- Strong low-budget execution claim supported: `False`
- Paper-claim consequence: do not claim the strong low-budget Pareto gate; report final as a solver-free deterministic concrete policy, note literal-first dominates at B=1/2, and report KLEE unavailable

## Tests Run

- `python -m py_compile analysis/decompile_faithfulness/strong_baselines_and_mechanism.py`
- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze analysis.decompile_faithfulness.tests.test_submission_evidence_corrections analysis.decompile_faithfulness.tests.test_holdout_acquisition analysis.decompile_faithfulness.tests.test_holdout_evaluation analysis.decompile_faithfulness.tests.test_strong_baselines_and_mechanism`

The Phase 1f generator consumes immutable Phase 1e traces and sealed holdout artifacts. It does not import or call the frozen final scheduler, regenerate holdout material, or alter method-affecting files.
