# Artifact Index

Updated: 2026-07-08

This index lists the committed artifacts that are worth preserving after the
Phase 3a-R stop decision.

| Phase | Path | Description | Sealed Or Derived | Safe To Reuse | Caveats |
|---|---|---|---|---|---|
| Phase 1b | `analysis/decompile_faithfulness/method_freeze_integrity.json` | Frozen-method integrity manifest and method-affecting source hashes. | Sealed/integrity record. | Yes. | Use only to document the historical frozen policy; it does not validate current claims. |
| Phase 1b | `results/decompile_faithfulness/provenance_validation_summary.json` | Corrected provenance counts, evidence strata, and semantic-transformation taxonomy. | Derived summary. | Yes. | Development/provenance evidence; not an independent evaluation result. |
| Phase 1b | `docs/paper_agent/submission_evidence_correction_handoff.md` | Narrative handoff for evidence correction and overlap accounting. | Derived handoff. | Yes. | It explicitly downgrades early perfect tables to development evidence. |
| Phase 1c | `docs/paper_agent/holdout_acquisition_seal_handoff.md` | Project acquisition, source pinning, seeds, and census handoff for holdout acquisition. | Handoff for sealed acquisition. | Yes. | Long project metadata should be cross-checked against seal files before reuse. |
| Phase 1d | `docs/paper_agent/holdout_generation_seal_handoff.md` | Holdout generation, selected functions, candidate/label counts, and final holdout seal. | Handoff for sealed holdout generation. | Yes. | Controlled holdout only; not natural-error evidence. |
| Phase 1d | `analysis/decompile_faithfulness/holdout_sealed_manifest_v2.json` | Final sealed holdout manifest. | Sealed. | Yes. | Use with matching `.sha256`; do not regenerate in place. |
| Phase 1d | `analysis/decompile_faithfulness/holdout_sealed_manifest_v2.sha256` | Hash for final sealed holdout manifest. | Seal hash. | Yes. | Must match before using holdout artifacts. |
| Phase 1e | `docs/paper_agent/frozen_holdout_evaluation_handoff.md` | Frozen controlled holdout evaluation summary. | Derived handoff. | Yes. | Supports only narrow controlled-drift claims. |
| Phase 1e | `results/decompile_faithfulness/holdout_exact_labels.jsonl` | Exact-domain labels for holdout candidates. | Sealed input-derived labels. | Yes. | Bounded-domain labels are not full semantic equivalence proofs. |
| Phase 1e | `results/decompile_faithfulness/holdout_policy_traces.jsonl` | Frozen-policy traces on the sealed holdout. | Derived evaluation traces. | Yes. | Auditor traces are for controlled holdout only. |
| Phase 1e | `results/decompile_faithfulness/holdout_policy_summary.csv` | Detection summaries for holdout policies and budgets. | Derived summary. | Yes. | Do not cite as natural generalization. |
| Phase 1f | `docs/paper_agent/strong_baselines_and_mechanism_handoff.md` | Strong baseline and mechanism comparison handoff. | Derived handoff. | Yes. | It records that literal-first matched or beat the final policy at key budgets. |
| Phase 1f | `results/decompile_faithfulness/holdout_paired_policy_analysis.csv` | Paired final-policy versus comparator analysis. | Derived summary. | Yes. | Controlled population only. |
| Phase 1f | `results/decompile_faithfulness/holdout_stratified_results.csv` | Stratified holdout results by family/density/literal strata. | Derived summary. | Yes. | Controlled mutation strata are not natural error strata. |
| Phase 1g | `docs/paper_agent/libfuzzer_wallclock_handoff.md` | libFuzzer wall-clock baseline handoff. | Derived handoff. | Yes. | Essential negative baseline against superiority claims. |
| Phase 1g | `results/decompile_faithfulness/libfuzzer_wallclock_summary.csv` | libFuzzer wall-clock detection and cost summary. | Derived summary. | Yes. | Controlled holdout baseline; compare hardware/time settings carefully. |
| Phase 1g | `results/decompile_faithfulness/libfuzzer_wallclock_runs.jsonl` | Per-run libFuzzer wall-clock records. | Derived run log. | Yes. | Large run-level evidence; preserve with environment notes. |
| Phase 1h | `docs/paper_agent/prospective_natural_llm_handoff.md` | Prospective natural LLM handoff. | Derived handoff. | Yes. | Natural-yield evidence is negative: only two primary wrong candidates. |
| Phase 1h | `analysis/decompile_faithfulness/natural_llm_candidate_seal.json` | Candidate seal for natural LLM candidates. | Sealed. | Yes. | Use with `.sha256`; do not alter prompts or responses. |
| Phase 1h | `analysis/decompile_faithfulness/natural_llm_evaluation_population.json` | Sealed evaluation population for natural LLM candidates. | Sealed. | Yes. | Very small primary population; not enough for CCF-A evaluation. |
| Phase 1h | `results/decompile_faithfulness/natural_llm_exact_labels.jsonl` | Exact labels for natural LLM candidates. | Sealed input-derived labels. | Yes. | Only two semantic wrong candidates. |
| Phase 1h | `results/decompile_faithfulness/natural_llm_label_summary.csv` | Natural LLM label summary. | Derived summary. | Yes. | Report as feasibility/negative evidence. |
| Phase 2a | `docs/paper_agent/source_behavioral_diversity_handoff.md` | SBDW result and stop handoff. | Derived handoff. | Yes. | Development evidence only; SBDW did not solve natural errors. |
| Phase 2a | `results/decompile_faithfulness/sbdw_budget_curves.csv` | SBDW budget curves for controlled and natural sets. | Derived summary. | Limited. | Do not use to tune a new method without preregistered separation. |
| Phase 2a | `results/decompile_faithfulness/sbdw_cost_summary.csv` | SBDW source-side cost summary. | Derived summary. | Yes. | Useful as negative cost evidence. |
| Phase 2a | `results/decompile_faithfulness/sbdw_candidate_mechanisms.jsonl` | Mechanism and category summaries for SBDW. | Derived analysis. | Limited. | Development evidence from prior collections. |
| Phase 3a | `docs/paper_agent/phase3a_natural_error_census_handoff.md` | Phase 3a corpus, candidate generation, labeling, and gate handoff. | Derived handoff. | Yes. | Final census failed minimum gate. |
| Phase 3a | `docs/paper_agent/phase3a_natural_error_census_preregistration.md` | Preregistered natural-error census protocol. | Preregistration. | Yes. | Future work should create a new preregistration, not amend this post hoc. |
| Phase 3a | `results/decompile_faithfulness/phase3a_project_manifest.json` | Project acquisition, pins, licenses, scanned files, and hashes. | Sealed/manifest. | Yes. | Only for Phase 3a corpus provenance. |
| Phase 3a | `results/decompile_faithfulness/phase3a_eligibility_census.csv` | Function eligibility census and structural features. | Derived census. | Yes. | Corpus has scalar-only limits and reduced target size. |
| Phase 3a | `results/decompile_faithfulness/phase3a_selected_functions.csv` | Canonical 80 selected functions. | Sealed corpus input. | Yes. | Do not expand after labels; new work needs a new corpus. |
| Phase 3a | `results/decompile_faithfulness/phase3a_fixtures.jsonl` | Four source-agnostic fixtures per selected function. | Sealed corpus input. | Yes. | Fixtures define primary denominator context but are not auditors. |
| Phase 3a | `analysis/decompile_faithfulness/phase3a_function_fixture_seal.json` | Function/fixture seal. | Sealed. | Yes. | Canonical hash: `2bba63e1a191050f2ec0e15a8f58ed7eff9a5c9bf1f21b672b7ab9bfc64c1494`. |
| Phase 3a | `analysis/decompile_faithfulness/phase3a_function_fixture_seal.sha256` | Function/fixture seal hash. | Seal hash. | Yes. | Must match before using corpus. |
| Phase 3a | `analysis/decompile_faithfulness/phase3a_candidate_seal.json` | Original Phase 3a candidate seal before labeling. | Sealed. | Yes. | Original census failed the gate. |
| Phase 3a | `analysis/decompile_faithfulness/phase3a_candidate_seal.sha256` | Original Phase 3a candidate seal hash. | Seal hash. | Yes. | Canonical hash: `e34f3c7532a8a2b399ef5be4c7a931b3f4d5e7c982c6f5d29adb14a89c8971f4`. |
| Phase 3a | `results/decompile_faithfulness/phase3a_label_summary.csv` | Original Phase 3a label counts. | Derived summary. | Yes. | `10` semantic wrong, `0` fixture-passing semantic wrong. |
| Phase 3a-R | `docs/paper_agent/phase3ar_producer_recovery_handoff.md` | Producer recovery and combined census handoff. | Derived handoff. | Yes. | Final recommendation is to report a remaining infrastructure blocker and stop. |
| Phase 3a-R | `docs/paper_agent/phase3ar_producer_recovery_preregistration.md` | Recovery-only preregistration. | Preregistration. | Yes. | Recovery was not Phase 3b and did not authorize auditor evaluation. |
| Phase 3a-R | `results/decompile_faithfulness/phase3ar_recovery_matrix.csv` | Eligible and blocked recovery cells. | Sealed recovery matrix. | Yes. | Includes only infrastructure-blocked cells from original Phase 3a. |
| Phase 3a-R | `analysis/decompile_faithfulness/phase3ar_candidate_seal.json` | Recovered candidate seal before labeling. | Sealed. | Yes. | Canonical hash: `42249cfb4a9e47d2001efc0d5e58f69bfbe96568567b779a44aaedd2752a6c6a`. |
| Phase 3a-R | `results/decompile_faithfulness/phase3ar_exact_labels.jsonl` | Exact labels for recovered candidates. | Derived labels from sealed candidates. | Yes. | Recovered census found only one fixture-passing semantic wrong. |
| Phase 3a-R | `results/decompile_faithfulness/phase3ar_combined_label_summary.csv` | Combined original plus recovered label summary. | Derived summary. | Yes. | Minimum gate failed. |
| Phase 3a-R | `results/decompile_faithfulness/phase3ar_combined_natural_error_descriptors.csv` | Combined semantic-error descriptors and fixture-pass flags. | Derived descriptor table. | Yes. | Only rows with `counts_for_gate=1` are primary natural wrong; count is `1`. |
| Phase 3a-R | `results/decompile_faithfulness/phase3ar_combined_taxonomy_review_packet.jsonl` | Review packet for combined semantic-wrong candidates. | Derived review packet. | Limited. | Contains candidate/source context for taxonomy review, not auditor results. |
| Producer setup | `docs/paper_agent/phase3a_producer_setup_log.md` | Producer setup attempts, commands, versions, and blockers. | Infrastructure log. | Yes. | RetDec remained blocked in Phase 3a. |
| Producer setup | `results/decompile_faithfulness/phase3a_producer_availability.json` | Producer availability status. | Infrastructure summary. | Yes. | Phase 3a setup status; Phase 3a-R later recorded additional blockers. |
| Producer recovery | `results/decompile_faithfulness/phase3ar_clang_recovery.json` | Clang-O2 recovery record and smoke results. | Infrastructure evidence. | Yes. | Explains recovered Clang-O2 build view. |
| Producer recovery | `results/decompile_faithfulness/phase3ar_llm4decompile_recovery.json` | LLM4Decompile adapter/blocker record. | Infrastructure evidence. | Yes. | LLM4Decompile recovery remained blocked by GPU smoke/generation approval infrastructure. |

## Global Caveats

- Controlled evidence should not be used as proof of natural-error
  generalization.
- Fixture-failing wrong candidates are secondary characterization material, not
  the primary auditing denominator.
- Non-evaluable candidates and compile failures are not semantic wrong.
- Bounded-domain no-mismatch means no mismatch under the declared audit domain,
  not full semantic equivalence.
- Any future auditor evaluation needs a new sealed primary natural-error
  population before the auditor is run.
