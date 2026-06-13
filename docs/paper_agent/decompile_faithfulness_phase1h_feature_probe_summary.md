# Decompilation Faithfulness Phase 1H Feature Probe Summary

## Question

Can operand/order-sensitive binary features repair the Phase 1G blind spot without hurting behavior-preserving rewrites?

## Change

Two diagnostic feature components were added:

- `instruction_bigram_l1`: adjacent normalized instruction-signature order distance.
- `branch_return_immediate_pair_l1`: conditional-jump to nearby return-immediate pairing distance.

These components are recorded in `FeatureDistance.components`, but they are not used in the primary slot-vote concentration score.

## Diagnostic Result

The new features detect the clearest Phase 1G blind spot. For `signum/manual_signum_reversed_signs` at `O0`, the old bag-style components were zero:

| Component | Value |
|---|---:|
| `opcode_l1` | `0.0` |
| `instruction_signature_l1` | `0.0` |
| `immediate_symmetric_diff` | `0.0` |
| `instruction_bigram_l1` | `4.0` |
| `branch_return_immediate_pair_l1` | `4.0` |

## Combined Primary Score

Because the new components are diagnostic-only, the 8-case primary score remains the Phase 1G baseline:

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.7552` |
| mean slot concentration | `0.7500` |
| max slot concentration | `0.6979` |
| range slot concentration | `0.4271` |

## Interpretation

The probe confirms the root cause: some semantic bugs are invisible to bag-of-instruction features because the same instruction signatures appear in a different control-flow/order context.

However, directly folding order-sensitive components into slot-vote concentration is not safe enough as a hand-written rule, because behavior-preserving rewrites can also change instruction order. The next step should be a calibrated component-combination experiment over source-known cases, not another single handcrafted vote.

## Verdict

Keep the new components as diagnostic evidence. Do not claim Phase 1H fixed the primary score yet.
