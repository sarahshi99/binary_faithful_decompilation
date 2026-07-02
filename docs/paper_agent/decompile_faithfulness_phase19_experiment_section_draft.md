# Experiment Section Draft: Source-Literal-Aware Low-Budget Dynamic Re-Execution

We evaluate source-literal-aware fixture-neighbor low-budget dynamic re-execution in a source-known localized semantic drift auditing setting. The auditor compares the original source and a candidate C function on a deterministic generated-input prefix, using budget 8 as the default. The input policy interleaves fixture-neighbor probes with character literals extracted from the original source for `char` parameters.

Across the current public static-hard, LLM-public, and Ghidra datasets, the method passes the budget-8 gates. The main evidence is summarized below:

- `phase6r_ghidra_full`: AUC `1.0000` with CI95 `[1.0000, 1.0000]`, wrong-detection rate `1.0000` with CI95 `[1.0000, 1.0000]`, average inputs `6.97`.
- `phase7c2_static_hard_public`: AUC `1.0000` with CI95 `[1.0000, 1.0000]`, wrong-detection rate `1.0000` with CI95 `[1.0000, 1.0000]`, average inputs `6.64`.
- `phase7e_llm_public_full_topup`: AUC `1.0000` with CI95 `[1.0000, 1.0000]`, wrong-detection rate `1.0000` with CI95 `[1.0000, 1.0000]`, average inputs `6.69`.

These results support a low-budget semantic auditing claim, not a general decompiler-generation SOTA claim. The method assumes source-known oracle access and bounded deterministic inputs. The final Phase 19 miss taxonomy has zero missed wrong candidates on the current full datasets.
