# Holdout Feasibility Amendment

Date: 2026-07-03

This amendment is applied before Phase 1d fixture generation, candidate generation, semantic labeling, witness inspection, or final-auditor evaluation.

## Phase 1c Scope

Phase 1c observed only source eligibility and sanitizer feasibility. It did not generate fixtures, decompiler candidates, semantic labels, labeling witnesses, or final-auditor results.

## Census Result

The preregistered project pool yielded:

- 86 eligible functions;
- 10 projects with at least one eligible function;
- project-cap-constrained capacity of 42 under `PROJECT_CAP=8`.

## Feasibility Finding

The original 48-function target is infeasible without either:

- increasing project concentration; or
- adding projects after the census.

## Amended Target

To preserve project diversity and avoid an open-ended project search, the holdout target is revised to exactly the maximum capped census capacity: 42 functions from all 10 eligible projects.

`PROJECT_CAP=8` is retained.

The prior requirement that a selected project must provide at least four functions is removed. Every project with at least one eligible function is part of the sampling frame.

This is a pre-label feasibility amendment, not a result-driven change.

## Fixed Expected Distribution

Under the Phase 1c census and `PROJECT_CAP=8`, the expected selected-function distribution is:

- musl: 8
- sqlite: 8
- TinyCC: 8
- sbase: 8
- mbedtls: 2
- libb64: 2
- libtomcrypt: 2
- BearSSL: 2
- xxHash: 1
- chibicc: 1

Total: 42 functions across 10 projects.
