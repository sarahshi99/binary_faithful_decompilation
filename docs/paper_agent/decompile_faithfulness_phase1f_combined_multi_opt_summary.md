# Decompilation Faithfulness Phase 1F Combined Multi-Opt Summary

## Dataset

- Cases: `5`
- Candidates: `35`
- Faithful candidates: `15`
- Plausible-wrong candidates: `20`
- Sources: Phase 1E expanded realistic candidates plus Phase 1F `max3` and `sum_to_n` candidates

## Single-Opt Results

| Opt | Slot-concentration AUC | Raw global-distance AUC |
|---|---:|---:|
| `O0` | `0.9083` | `0.1750` |
| `O1` | `0.6583` | `0.5917` |
| `O2` | `0.6417` | `0.5583` |
| `O3` | `0.5667` | `0.6417` |

## Multi-Opt Results

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.8250` |
| mean slot concentration | `0.7667` |
| max slot concentration | `0.6917` |
| range slot concentration | `0.4250` |

## Interpretation

Across all five source-known cases, no single optimization level is reliable enough to be the primary score. `O0` is strong for slot concentration but raw global distance fails badly; optimized levels make slot concentration weaker and sometimes make raw global distance look better.

The stable signal is multi-opt conservative slot concentration. Taking the minimum slot concentration across `O0/O1/O2/O3` reaches `0.8250`, above the continue gate, and should be the default suspicion score for the next experiment.

## Verdict

Continue with multi-opt slot-local calibration, but broaden source-known coverage before real-project transfer.
