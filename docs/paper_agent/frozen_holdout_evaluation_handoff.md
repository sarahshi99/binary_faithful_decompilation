# Frozen Holdout Evaluation Handoff

## Git

- Branch: `phase1e-frozen-holdout-evaluation`
- Preregistration commit: `758707882eacf905545cd3b42d7b83fc94f52bc9`
- Result-producing HEAD at run: `32e4a8651eefb9d6d2aca5f63effb802cbe1e1b5`
- Verified holdout seal: `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`
- Method freeze commit: `06dda89912103b94fc065d6f073581a7811154b1`

## Populations

- Fixture-passing wrong count: `37`
- Low-density fixture-passing wrong count: `16`
- All controlled semantic-wrong count: `60`
- No-mismatch comparison count: `34`

## Final Detection

- B=1: `15/37` = `0.405`
- B=2: `25/37` = `0.676`
- B=4: `30/37` = `0.811`
- B=8: `33/37` = `0.892`
- B=16: `34/37` = `0.919`
- B=32: `34/37` = `0.919`

## Budget-8 Baselines

- fixture_neighbor_only: `25/37` = `0.676`
- source_literal_only: `11/37` = `0.297`
- neighbor_first_concatenation: `25/37` = `0.676`
- literal_first_concatenation: `33/37` = `0.892`
- operator_char_first: `25/37` = `0.676`
- generic_fallback_only: `22/37` = `0.595`
- generic_type_boundaries: `32/37` = `0.865`
- uniform_random_domain: `23.433333333333334/37` = `0.633`
- randomized_union_order: `27.566666666666666/37` = `0.745`

## Realized Mutation Families

- argument_substitution_or_swap: attempts `1`, compile-ready `1`, semantic wrong `1`, fixture-passing wrong `0`, final Detection@8 `0.000`
- branch_condition_negation: attempts `2`, compile-ready `2`, semantic wrong `2`, fixture-passing wrong `0`, final Detection@8 `0.000`
- comparison_operator_replacement: attempts `15`, compile-ready `15`, semantic wrong `11`, fixture-passing wrong `5`, final Detection@8 `0.800`
- fixture_overfit_construction: attempts `26`, compile-ready `26`, semantic wrong `22`, fixture-passing wrong `22`, final Detection@8 `0.909`
- integer_or_character_constant_plus_1: attempts `8`, compile-ready `8`, semantic wrong `3`, fixture-passing wrong `3`, final Detection@8 `1.000`
- return_value_perturbation: attempts `26`, compile-ready `26`, semantic wrong `21`, fixture-passing wrong `7`, final Detection@8 `0.857`

## Source-Literal Strata

- has_source_char_literal / fixture_neighbor_only: `11/21` = `0.524`
- has_source_char_literal / generic_type_boundaries: `18/21` = `0.857`
- has_source_char_literal / source_literal_char_interleave: `19/21` = `0.905`
- has_source_char_literal / source_literal_only: `11/21` = `0.524`
- no_source_char_literal / fixture_neighbor_only: `14/16` = `0.875`
- no_source_char_literal / generic_type_boundaries: `14/16` = `0.875`
- no_source_char_literal / source_literal_char_interleave: `14/16` = `0.875`
- no_source_char_literal / source_literal_only: `0/16` = `0.000`

## Natural Ghidra Execution

- Natural Ghidra no-mismatch candidates executed by final policy at B=8: `16`
- Natural Ghidra in-domain unexpected mismatches: `0`

## No-Mismatch And Out-of-Domain

- No-mismatch unexpected in-domain mismatches: `0`
- Out-of-domain probe/witness rows requiring separate reporting: `846`

## Gate Outcome

- Outcome: `moderate_support_requiring_claim_narrowing`
- Claim consequence: Narrow claims to represented controlled-drift families and exact-domain holdout conditions.

## Tests Run

- `python -m py_compile analysis/decompile_faithfulness/holdout_evaluation.py`
- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze analysis.decompile_faithfulness.tests.test_submission_evidence_corrections analysis.decompile_faithfulness.tests.test_holdout_acquisition analysis.decompile_faithfulness.tests.test_holdout_evaluation`

The frozen final auditor was evaluated only after the preregistration commit and successful seal preflight. No holdout candidates, fixtures, labels, domains, mutation grammar, or sealed manifest artifacts were regenerated or modified.
