# Decompilation Faithfulness Phase 1D Slot-Calibration Audit

## Question

Can slot-vote concentration distinguish localized semantic bugs from broader behavior-preserving rewrite drift better than raw global feature distance?

## Metrics

- Compiler optimization: `O0`
- Records: `6`
- Faithful candidates: `3`
- Plausible-wrong candidates: `3`
- Pairwise slot-concentration AUC: `1.0000`
- Mean faithful slot concentration: `0.6263`
- Mean wrong slot concentration: `0.7559`
- Verdict: `continue-slot-calibration`

## Interpretation

This audit uses the same realistic manual candidates as Phase 1B, but scores candidate suspiciousness by concentration of slot-local votes instead of total binary feature distance. Higher concentration means the mismatch looks more like a localized source slot error; lower concentration means broader implementation drift.

## Next Route

Expand optimization-aware slot-local calibration before real-project transfer. Add more realistic hard negatives, behavior-preserving rewrites, and compiler optimization settings, then test whether slot concentration remains calibrated.
