# Decompilation Faithfulness Phase 1E Expanded Slot-Calibration Audit

## Question

Does slot-vote concentration still separate behavior-preserving rewrites from localized semantic bugs after expanding the realistic candidate set and sweeping compiler optimization levels?

## Dataset

- Cases: `3`
- Candidates: `21`
- Faithful candidates: `9`
- Plausible-wrong candidates: `12`
- Candidate source: expanded manual realistic rewrites and hard negatives
- Optimization levels: `O0`, `O1`, `O2`, `O3`

## Results

| Opt | Slot-concentration AUC | Raw global-distance AUC | Faithful mean | Wrong mean | Verdict |
|---|---:|---:|---:|---:|---|
| `O0` | `0.9028` | `0.1111` | `0.5036` | `0.7481` | `continue-slot-calibration` |
| `O1` | `0.7361` | `0.5000` | `0.3429` | `0.6606` | `weak-signal` |
| `O2` | `0.6944` | `0.5000` | `0.3435` | `0.6589` | `weak-signal` |
| `O3` | `0.7500` | `0.5833` | `0.3621` | `0.6483` | `continue-slot-calibration` |

## Per-Case AUC

| Opt | `absdiff` | `clamp8` | `count_bits8` |
|---|---:|---:|---:|
| `O0` | `0.7500` | `1.0000` | `0.9583` |
| `O1` | `0.6667` | `0.6667` | `0.8750` |
| `O2` | `0.6667` | `0.6667` | `0.7500` |
| `O3` | `0.6667` | `0.6667` | `0.9167` |

## Multi-Opt Aggregation

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.8472` |
| mean slot concentration | `0.8056` |
| max slot concentration | `0.7639` |
| range slot concentration | `0.4306` |

## Interpretation

The expanded audit confirms the Phase 1D direction: raw global binary distance is not a faithful ranking score for arbitrary C rewrites, but slot-local concentration retains useful signal.

The weakness is optimization sensitivity. Single-level `O1/O2` runs fall below the strong gate, mainly because some faithful rewrites look locally concentrated under optimized codegen. A conservative multi-opt score, using the minimum slot concentration observed across `O0/O1/O2/O3`, recovers a stronger AUC of `0.8472`.

## Verdict

Continue with multi-opt slot-local calibration. The next method should treat single optimization-level scores as diagnostic only, and use multi-opt conservative scoring as the primary suspicion signal before any real-project transfer.
