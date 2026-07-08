# Project Stop Report

Updated: 2026-07-08

Branch at report creation: `phase3ar-producer-recovery-census`

Recovery census HEAD before documentation cleanup:
`645bcba8e5198dd38031e8ad4634f074380dc49d`

## 1. Executive Decision

The original method-paper route is stopped.

The source-behavioral-diversity witness redesign route is stopped.

The Phase 3 empirical CCF-A route is not authorized to continue under the
current evidence.

No Phase 3b auditor evaluation should be run. The natural-error primary
population is insufficient: Phase 3a-R produced only `1` combined
fixture-passing natural semantic-wrong candidate, far below the preregistered
minimum gate of `25`.

## 2. Why The Current CCF-A Route Stops

The decisive blockers are:

- Phase 1e controlled holdout evaluation produced `33/37` Detection@8 for the
  frozen policy, but literal-first also produced `33/37`, and generic type
  boundaries produced `32/37`.
- Phase 1g libFuzzer wall-clock detected the full primary controlled population
  at 0.1 seconds: mean Detection `1.000` on `37/37`, weakening any low-cost
  superiority claim for the frozen deterministic policy.
- Phase 1h prospective LLM natural candidates produced only `2` semantic-wrong
  candidates, both from `libb64`, and deterministic policies missed both at
  B=8.
- Phase 2a SBDW failed to detect the two natural LLM errors at B=8 and had high
  source-side cost: `144.962561` seconds amortized end-to-end per source at one
  candidate/source.
- Phase 3a natural census produced `10` semantic-wrong candidates but `0`
  fixture-passing semantic-wrong candidates.
- Phase 3a-R recovery produced `20` combined semantic-wrong candidates but only
  `1` combined fixture-passing semantic-wrong candidate.
- The minimum CCF-A empirical gate failed.
- Phase 3b was not authorized.

## 3. Key Quantitative Timeline

| Phase | Branch | Final HEAD | Purpose | Key Numbers | Conclusion |
|---|---|---|---|---|---|
| Phase 1b evidence correction | `phase1b-evidence-corrections` | `a784d1c8195ae88a8b3233f8eef5cfd2c27d7b14` | Correct provenance, labels, and overlap accounting for the original development evidence. | Natural raw/minimally processed Ghidra semantic wrong `0`; natural LLM semantic wrong `36`; Ghidra-derived controlled stress wrong `74`; current-table reconstructed exact witness overlap `354/368 = 0.962`. | Prior perfect tables are development evidence, not independent test evidence. |
| Phase 1c/1d holdout construction | `phase1d-holdout-generation-and-seal` | `ef2d721202d19f8aed55ac10db6e96b6770a722c` | Acquire, sample, label, and seal controlled holdout material before frozen evaluation. | `42` selected functions; `84` natural candidate attempts; `84` controlled candidate attempts; `60` controlled semantic wrong; final holdout seal `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`. | Sealed controlled holdout was valid for frozen auditor evaluation. |
| Phase 1e frozen controlled holdout evaluation | `phase1e-frozen-holdout-evaluation` | `f302bb51eb9371c0dad51bce92be53f58fc1a341` | Evaluate the frozen final policy after the holdout seal. | Primary fixture-passing wrong `37`; final Detection@8 `33/37 = 0.892`; literal-first Detection@8 `33/37 = 0.892`; generic type boundaries Detection@8 `32/37 = 0.865`. | Moderate controlled support only; claims must be narrow. |
| Phase 1f strong baselines | `phase1f-strong-baselines-and-mechanism` | `b626b38dd9f1398945a7c604b3213f589b936b8a` | Compare the frozen policy to stronger deterministic baselines and mechanism variants. | Final versus literal-first: B=1 `15/37` vs `18/37`, B=2 `25/37` vs `27/37`, B=8 `33/37` vs `33/37`; strong low-budget execution claim supported `False`. | Do not claim interleaving superiority or a strong Pareto gate. |
| Phase 1g libFuzzer wall-clock | `phase1g-libfuzzer-wallclock` | `f9fdca2a001a9c07d2fecd507692a2d383105b91` | Evaluate coverage-guided fuzzing under wall-clock budgets on the controlled holdout. | 0.1s primary Detection mean `1.000`; low-density `1.000`; non-fixture-overfit `1.000`; no-mismatch false alarms `0`; frozen final B=8 Detection `33/37`. | Frozen policy superiority over libFuzzer is not established. |
| Phase 1h prospective natural LLM candidates | `phase1h-prospective-natural-llm-candidates` | `3bdb9f26621d2af4aea87aaa3923457532e549b0` | Generate and seal prospective natural LLM candidates before evaluation. | Attempts `168`; compile-ready `168`; semantic wrong `2`; fixture-passing semantic wrong `2`; project span `1` (`libb64`); final policy B=8 `0/2`. | Natural evidence gate failed; only a small feasibility/characterization result. |
| Phase 2a SBDW prototype | `phase2a-source-behavioral-diversity-prototype` | `a2c975609aed5975431ec1a770c9cd92c37c2b1f` | Test source-behavioral diversity witness selection as a redesign. | Natural LLM Detection@1/2/4/8 all `0/2`; controlled B=8 `33/37`; source-only execution `90.749791` s/source; amortized end-to-end at one candidate/source `144.962561` s. | Stop method redesign. |
| Phase 3a natural-error census | `phase3a-prospective-natural-error-census` | `db5a9fc78e43d2702f9490184d0ae690a6a57c4d` | Build a prospective natural candidate and semantic-error census without running auditors. | `80` sealed functions; candidate attempts `640`; compile-ready `215`; semantic wrong `10`; fixture-passing semantic wrong `0`; no-mismatch `194`; non-evaluable `436`; candidate seal `e34f3c7532a8a2b399ef5be4c7a931b3f4d5e7c982c6f5d29adb14a89c8971f4`. | Minimum empirical population gate failed. |
| Phase 3a-R producer recovery census | `phase3ar-producer-recovery-census` | `645bcba8e5198dd38031e8ad4634f074380dc49d` | Recover infrastructure-blocked producer/build-view cells without running auditors. | Recovery matrix `400`; recovered attempts `240`; recovered compile-ready `99`; recovered semantic wrong `10`; combined semantic wrong `20`; combined fixture-passing semantic wrong `1`; minimum gate `failed`. | Phase 3b remains unauthorized; remaining infrastructure blocker is reported. |

## 4. Artifacts Worth Preserving

| Artifact | Path | Contains | Evidence Type | Use In Future Papers |
|---|---|---|---|---|
| Method-freeze integrity records | `analysis/decompile_faithfulness/method_freeze_integrity.json` | Frozen-method source hashes and method-affecting file checks. | Infrastructure evidence. | Yes, as provenance for historical method-freeze accounting only. |
| Candidate provenance v2 | `results/decompile_faithfulness/candidate_provenance_v2.csv`; `results/decompile_faithfulness/candidate_provenance_v2.jsonl` | Corrected candidate provenance and evidence-stratum taxonomy. | Development evidence. | Yes, for retrospective provenance discussion; not as independent method validation. |
| Phase 1 controlled holdout labels and traces | `analysis/decompile_faithfulness/holdout_sealed_manifest_v2.json`; `results/decompile_faithfulness/holdout_exact_labels.jsonl`; `results/decompile_faithfulness/holdout_policy_traces.jsonl` | Sealed controlled holdout, exact labels, and frozen-policy traces. | Controlled evidence. | Yes, as controlled benchmark evidence with clear non-natural limits. |
| Phase 1 libFuzzer baselines | `results/decompile_faithfulness/libfuzzer_wallclock_summary.csv`; `figures/data/libfuzzer_wallclock_detection.csv`; `paper/tables/libfuzzer_wallclock.tex` | Wall-clock libFuzzer comparison on the controlled holdout. | Controlled baseline evidence. | Yes, as a necessary baseline in any future methods paper. |
| Phase 1h natural LLM candidate seal and labels | `analysis/decompile_faithfulness/natural_llm_candidate_seal.json`; `analysis/decompile_faithfulness/natural_llm_evaluation_population.json`; `results/decompile_faithfulness/natural_llm_exact_labels.jsonl` | Sealed prospective LLM natural candidates and exact labels. | Natural census evidence. | Yes, as negative natural-yield evidence. |
| Phase 2a SBDW prototype results | `results/decompile_faithfulness/sbdw_budget_curves.csv`; `results/decompile_faithfulness/sbdw_cost_summary.csv`; `docs/paper_agent/source_behavioral_diversity_handoff.md` | SBDW detection and cost results. | Development evidence. | Yes, as negative evidence against this redesign. |
| Phase 3a 80-function corpus | `results/decompile_faithfulness/phase3a_selected_functions.csv`; `results/decompile_faithfulness/phase3a_project_manifest.json`; `results/decompile_faithfulness/phase3a_eligibility_census.csv` | Prospective selected functions, project metadata, and eligibility census. | Natural census evidence. | Yes, as corpus-construction evidence; not enough for CCF-A evaluation. |
| Phase 3a function/fixture seal | `analysis/decompile_faithfulness/phase3a_function_fixture_seal.json`; `analysis/decompile_faithfulness/phase3a_function_fixture_seal.sha256` | Hash seal for selected functions, domains, fixtures, outputs, and generation code. | Natural census evidence. | Yes, as the canonical Phase 3a corpus seal. |
| Phase 3a candidate seal | `analysis/decompile_faithfulness/phase3a_candidate_seal.json`; `analysis/decompile_faithfulness/phase3a_candidate_seal.sha256` | Hash seal for original Phase 3a candidate attempts before labeling. | Natural census evidence. | Yes, as the original failed census seal. |
| Phase 3a-R recovery matrix, labels, descriptors | `results/decompile_faithfulness/phase3ar_recovery_matrix.csv`; `results/decompile_faithfulness/phase3ar_exact_labels.jsonl`; `results/decompile_faithfulness/phase3ar_combined_natural_error_descriptors.csv` | Recovery eligibility, recovered labels, and combined semantic-error descriptors. | Natural census and infrastructure evidence. | Yes, as recovery/stop evidence; not as an auditor-evaluation population. |
| Producer setup logs | `docs/paper_agent/phase3a_producer_setup_log.md`; `results/decompile_faithfulness/phase3a_producer_availability.json`; `results/decompile_faithfulness/phase3ar_clang_recovery.json`; `results/decompile_faithfulness/phase3ar_llm4decompile_recovery.json` | Producer availability, setup commands, Clang recovery, and LLM4Decompile blocker. | Infrastructure evidence. | Yes, as reproducibility and blocker documentation. |

## 5. What Should Not Be Claimed

Future writing must not claim:

- the frozen policy is superior to libFuzzer;
- interleaving is uniquely superior to literal-first;
- SBDW solves the natural-error failure;
- Phase 3 has a sufficient natural-error evaluation population;
- fixture-failing wrong candidates are primary auditing targets;
- controlled mutations establish natural-error generalization;
- no mismatch under a bounded domain means full semantic equivalence;
- compile failures are semantic wrong.

## 6. Possible Future Restart Conditions

A CCF-A-level project can only restart later with a new preregistered study that
has, before any auditor execution:

- a broader function setting, potentially including controlled pointer/array
  subsets or richer harnesses;
- a candidate-generation setup that yields at least `25` fixture-passing natural
  semantic-wrong candidates across at least `15` functions and `8` projects;
- at least `3` working candidate producers;
- at least two producers each contributing at least `5` primary wrong
  candidates;
- a larger natural-error taxonomy;
- a new preregistered corpus, not a post-hoc extension of Phase 3a;
- a sealed candidate population before auditor execution.

## 7. Recommended Near-Term Use

Recommended near-term uses are limited to:

- internal report;
- workshop or negative-result note;
- methods appendix for future work;
- artifact archive;
- benchmark-construction lessons.

Do not prepare an immediate CCF-A submission from the current evidence.
