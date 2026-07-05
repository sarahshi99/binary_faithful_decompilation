# libFuzzer Wall-Clock Handoff

## Git And Seals

- Branch: `phase1g-libfuzzer-wallclock`
- Preregistration commit: `4c433ba7d953deeeb67c5b822a4b30d1db3c4ed7`
- Generated-at commit context: `4c433ba7d953deeeb67c5b822a4b30d1db3c4ed7`
- Result commit and final HEAD: the commit containing this handoff; the exact hash is available after commit creation.
- Verified holdout seal: `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`
- Frozen method commit: `06dda89912103b94fc065d6f073581a7811154b1`
- Phase 1e result: `f302bb51eb9371c0dad51bce92be53f58fc1a341`
- Phase 1f artifact commit: `66b60c7a1ec0981c1ff5b307e0ee85efcf7d9589`
- Preflight OK: `True`

## Environment

- Clang/libFuzzer: `Ubuntu clang version 11.0.0-2~ubuntu20.04.1`
- CPU: `AMD EPYC 9334 32-Core Processor`
- OS: `Linux-5.15.0-67-generic-x86_64-with-glibc2.31`
- Worker configuration: `4` workers; CPU affinity `none_explicit`
- GPU usage: `none; CUDA_VISIBLE_DEVICES cleared for libFuzzer subprocesses`
- Runs completed: `6120` supported runs plus `270` unsupported rows

## Detection

- 0.1s primary Detection mean `1.000` (median `1.000`); low-density `1.000`; non-fixture-overfit `1.000`
- 1s primary Detection mean `1.000` (median `1.000`); low-density `1.000`; non-fixture-overfit `1.000`
- 5s primary Detection mean `1.000` (median `1.000`); low-density `1.000`; non-fixture-overfit `1.000`

## Cost And Failures

- Frozen final B=8 Detection: `33/37`.
- Frozen final median complete-prefix time: `0.18743639159947634`.
- Frozen final median simulated early-stop time: `0.022025296930223703`.
- libFuzzer 0.1s median evaluations `10.0`, median end-to-end witness time `0.10742383648175746`, median in-process witness time `0.00047900000000000004`, no-mismatch false alarms `0`, crashes `0`, timeouts `930`, infrastructure failures `0`
- libFuzzer 1s median evaluations `10.0`, median end-to-end witness time `0.19216276746010408`, median in-process witness time `0.00048249999999999996`, no-mismatch false alarms `0`, crashes `0`, timeouts `930`, infrastructure failures `1`
- libFuzzer 5s median evaluations `10.0`, median end-to-end witness time `0.254513775522355`, median in-process witness time `0.00048`, no-mismatch false alarms `0`, crashes `0`, timeouts `930`, infrastructure failures `45`

## Candidate Sets

- At 5s, both final and libFuzzer detect `33` primary candidates.
- At 5s, final-only candidates: `[]`
- At 5s, libFuzzer-only candidates: `["musl::src_network_inet_pton.c::hexval::0001::a0a6dbc2a411::controlled::comparison_operator_replacement_00", "musl::src_regex_regcomp.c::hexval::0004::5a81c0c932f7::controlled::return_value_perturbation_00", "sbase::find.c::cmp_eq::0002::16afa3d71aab::controlled::fixture_overfit_construction_01", "sbase::find.c::cmp_lt::0003::3ff7fb5ec166::controlled::fixture_overfit_construction_00"]`
- At 5s, neither-detected candidates: `[]`

## Interpretation

- Gate outcome: `weak_comparative_support`
- Paper-claim consequence: The frozen policy is a deterministic solver-free alternative, but the evaluation does not establish superiority over coverage-guided fuzzing.

## Tests Run

- `python -m py_compile analysis/decompile_faithfulness/libfuzzer_wallclock.py`
- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze analysis.decompile_faithfulness.tests.test_submission_evidence_corrections analysis.decompile_faithfulness.tests.test_holdout_acquisition analysis.decompile_faithfulness.tests.test_holdout_evaluation analysis.decompile_faithfulness.tests.test_strong_baselines_and_mechanism analysis.decompile_faithfulness.tests.test_libfuzzer_wallclock`

The Phase 1g run reused the Phase 1f libFuzzer harness semantics, did not provide source-literal dictionaries or exact mismatch witnesses, did not install or run KLEE, did not use GPU devices, and did not invoke the frozen final auditor.
