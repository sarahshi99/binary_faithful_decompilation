# Decompilation Faithfulness Phase 16 Runtime And Risk Breakdown

- Verdict: `pass-phase16-runtime-risk-breakdown`
- Strategy: `source_literal_char_interleave`
- Budget: `8`

## Runtime

| Dataset | Candidates | Skipped no-input | Total seconds | Mean sec/candidate | Median sec/candidate | P95 sec/candidate | Input evals | Input evals/sec |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `phase7c2_static_hard_public` | `478` | `25` | `85.60` | `0.1782` | `0.0446` | `0.0923` | `3172` | `37.05` |
| `phase7e_llm_public_full_topup` | `136` | `7` | `7.94` | `0.0573` | `0.0455` | `0.0874` | `910` | `114.65` |
| `phase6r_ghidra_full` | `166` | `0` | `11.21` | `0.0660` | `0.0517` | `0.1031` | `1157` | `103.25` |

Timing includes trace harness compilation and execution inside the current Python
runner. Original traces are cached per case/optimization level, so the timing
matches the deployed auditor's amortized behavior rather than compiling the
original for every candidate.

## Risk-Family Breakdown

### `phase7c2_static_hard_public`

| Risk family | Cases | Candidates | Paired cases | AUC | Detection | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|
| `public_benchmark` | `53` | `469` | `50` | `1.0000` | `1.0000` | `0` |
| `operator_boundary` | `37` | `361` | `34` | `1.0000` | `1.0000` | `0` |
| `branch` | `19` | `205` | `18` | `1.0000` | `1.0000` | `0` |
| `multi_arg` | `19` | `140` | `18` | `1.0000` | `1.0000` | `0` |
| `loop` | `11` | `111` | `11` | `1.0000` | `1.0000` | `0` |
### `phase7e_llm_public_full_topup`

| Risk family | Cases | Candidates | Paired cases | AUC | Detection | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|
| `public_benchmark` | `52` | `136` | `24` | `1.0000` | `1.0000` | `0` |
| `operator_boundary` | `36` | `89` | `16` | `1.0000` | `1.0000` | `0` |
| `branch` | `19` | `42` | `8` | `1.0000` | `1.0000` | `0` |
| `multi_arg` | `19` | `44` | `7` | `1.0000` | `1.0000` | `0` |
| `loop` | `11` | `25` | `4` | `1.0000` | `1.0000` | `0` |
### `phase6r_ghidra_full`

| Risk family | Cases | Candidates | Paired cases | AUC | Detection | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|
| `loop` | `11` | `52` | `9` | `1.0000` | `1.0000` | `0` |
| `boundary` | `10` | `47` | `7` | `1.0000` | `1.0000` | `0` |
| `branch` | `9` | `41` | `6` | `1.0000` | `1.0000` | `0` |
| `nonnegative_domain` | `6` | `29` | `5` | `1.0000` | `1.0000` | `0` |
| `positive_domain` | `6` | `28` | `5` | `1.0000` | `1.0000` | `0` |
| `digits` | `5` | `20` | `4` | `1.0000` | `1.0000` | `0` |
| `division` | `4` | `20` | `4` | `1.0000` | `1.0000` | `0` |
| `multi_arg` | `5` | `24` | `4` | `1.0000` | `1.0000` | `0` |
| `recursion` | `4` | `24` | `4` | `1.0000` | `1.0000` | `0` |
| `sign_zero` | `7` | `28` | `4` | `1.0000` | `1.0000` | `0` |
| `char_boundary` | `5` | `19` | `3` | `1.0000` | `1.0000` | `0` |
| `comparison` | `5` | `22` | `3` | `1.0000` | `1.0000` | `0` |

## Gate

| Gate | Passed |
|---|---:|
| `phase7c2_static_hard_public_runtime_present` | `True` |
| `phase7e_llm_public_full_topup_runtime_present` | `True` |
| `phase6r_ghidra_full_runtime_present` | `True` |
| `phase7c2_static_hard_public_risk_rows_present` | `True` |
| `phase7e_llm_public_full_topup_risk_rows_present` | `True` |
| `phase6r_ghidra_full_risk_rows_present` | `True` |
| `phase7c2_static_hard_public_large_risk_family_auc_gate` | `True` |
| `phase7c2_static_hard_public_large_risk_family_detection_gate` | `True` |
| `phase7e_llm_public_full_topup_large_risk_family_auc_gate` | `True` |
| `phase7e_llm_public_full_topup_large_risk_family_detection_gate` | `True` |
| `phase6r_ghidra_full_large_risk_family_auc_gate` | `True` |
| `phase6r_ghidra_full_large_risk_family_detection_gate` | `True` |

## Interpretation

This phase fills the paper's runtime and risk-family table gaps. Risk-family
rows with at least three paired cases are used for the gate; smaller rows are
reported descriptively but should not be overinterpreted.
