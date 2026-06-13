# Decompilation Faithfulness Phase 1G Combined Multi-Opt Summary

## Dataset

- Cases: `8`
- Candidates: `56`
- Faithful candidates: `24`
- Plausible-wrong candidates: `32`
- Sources: Phase 1E expanded candidates, Phase 1F new cases, and Phase 1G `signum` / `is_power_of_two` / `gcd_positive`

## Single-Opt Results

| Opt | Slot-concentration AUC | Raw global-distance AUC |
|---|---:|---:|
| `O0` | `0.8021` | `0.1615` |
| `O1` | `0.6979` | `0.5260` |
| `O2` | `0.6354` | `0.5365` |
| `O3` | `0.5885` | `0.5938` |

## Multi-Opt Results

| Aggregation over `O0/O1/O2/O3` | Pairwise AUC |
|---|---:|
| min slot concentration | `0.7552` |
| mean slot concentration | `0.7500` |
| max slot concentration | `0.6979` |
| range slot concentration | `0.4271` |

## Interpretation

The 8-case combined result is borderline. Multi-opt min slot concentration still clears the continue threshold, but only narrowly. Phase 1G shows that the current feature mapping misses some constant-return and sign-direction mistakes.

Raw global distance remains unsuitable as the primary ranker. It fails badly at `O0` and does not become consistently strong at optimized levels.

## Verdict

Do not start real-project transfer. Run a Phase 1H feature-blind-spot repair focused on operand/constant-sensitive signatures before adding more transfer complexity.
