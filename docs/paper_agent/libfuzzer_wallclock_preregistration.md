# libFuzzer Wall-Clock Baseline Preregistration

Generated: 2026-07-04

This document preregisters Phase 1g before running the missing CPU-only
libFuzzer wall-clock matrix. Phase 1g starts from
`phase1f-strong-baselines-and-mechanism` at
`b626b38dd9f1398945a7c604b3213f589b936b8a`.

Frozen method commit:
`06dda89912103b94fc065d6f073581a7811154b1`.

Verified holdout seal:
`cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`.

Phase 1e result:
`f302bb51eb9371c0dad51bce92be53f58fc1a341`.

Phase 1f result artifact commit:
`66b60c7a1ec0981c1ff5b307e0ee85efcf7d9589`.

No GPU experiments will be started. KLEE will not be installed or run. No
decompiler integration, candidate generation, label generation, sealed holdout
modification, Phase 1e trace modification, or final-method modification is
permitted.

## Populations

Use the immutable Phase 1e/1f populations:

- Primary fixture-passing semantic-wrong: 37 candidates.
- Low-density fixture-passing semantic-wrong: 16 candidates with `rho <= 0.10`.
- Non-fixture-overfit fixture-passing semantic-wrong: 15 candidates.
- Exact-domain no-mismatch comparison: 34 candidates.
- Natural Ghidra no-mismatch: 16 candidates, reported as a separate stratum.

These populations are reconstructed only from the sealed Phase 1e/1f artifacts
and must not be changed.

## Toolchain

- Clang/libFuzzer: `/usr/lib/llvm-11/bin/clang`, Ubuntu clang version
  `11.0.0-2~ubuntu20.04.1`.
- Compiler flags for wall-clock harnesses:
  `-std=c11 -O1 -g -fsanitize=fuzzer,address,undefined -fno-sanitize-recover=all`.
- Validation harness flags:
  `-std=c11 -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all`.
- Source-literal dictionary: not used.
- Exact mismatch witnesses: not provided to libFuzzer.
- Seed corpus: exactly the four sealed fixtures for each function.

The Phase 1f byte-to-domain mapping, differential mismatch condition,
normalized scalar output comparison, candidate compilation pipeline, validation
harness semantics check, and fixed seed list are reused.

## Environment

Observed preregistration environment:

- OS: Linux `5.15.0-67-generic` on x86_64 Ubuntu 20.04 family.
- CPU: AMD EPYC 9334 32-Core Processor.
- Logical CPUs visible: 64.
- Threads per core reported by `lscpu`: 1.
- Default worker count: 4 concurrent workers.
- CPU affinity: no explicit pinning unless the runtime environment requires it;
  worker count is kept below physical core count and recorded in the environment
  manifest.

If fewer than four suitable CPU cores are available at runtime, reduce workers
and record the value. Do not use GPU devices.

## Seeds And Budgets

Use the fixed Phase 1f seed list:

`101, 202, 303, 404, 505, 606, 707, 808, 909, 1001, 1102, 1203, 1304, 1405, 1506, 1607, 1708, 1809, 1910, 2011, 2112, 2213, 2314, 2415, 2516, 2617, 2718, 2819, 2920, 3021`.

Wall-clock budgets:

- 0.1 seconds;
- 1 second;
- 5 seconds.

Each candidate/seed/budget run uses an isolated work directory and mutable
corpus. No mutable corpus is shared between candidates, seeds, or budgets.

## Timing Protocol

Two timing views are recorded:

- End-to-end time: measured by the Python runner with a monotonic high-resolution
  clock around process creation, corpus loading, fuzzer initialization,
  harness execution, witness handling, and process teardown. This is the
  primary wall-clock comparison.
- In-process analysis time: measured by the harness after initialization, from
  the first ready-to-process point until witness or timeout. This is a secondary
  amortized view.

Process-startup time is estimated as the difference between runner
end-to-end elapsed time and the first in-process timestamp emitted by the
harness. Harness initialization time is recorded from harness self-reporting
when available; otherwise it is marked unknown rather than inferred silently.

Each run is terminated at the declared budget plus a documented process
termination tolerance. The initial tolerance is 0.75 seconds for process
startup/teardown noise. Runs exceeding this are marked timeout or infrastructure
failure according to the observed return mode.

## Crash And Timeout Handling

A libFuzzer mismatch signal on a semantic-wrong candidate is a potential
finding only if the logged first witness is in the sealed exact domain and is
confirmed against the sealed exact labels or repeated source/candidate
execution path. A harness crash without a logged semantic mismatch is not a
semantic finding.

For no-mismatch candidates, any source/candidate mismatch finding is a
false-alarm candidate and must be counted separately. Harness crashes,
timeouts, and infrastructure failures are not semantic findings.

Candidates whose Phase 1f libFuzzer harness validation does not reproduce the
sealed exact label are unsupported for this baseline and excluded from
supported-candidate denominators while still being reported.

## Preflight

Before every batch, verify:

- sealed manifest hash equals
  `cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42`;
- all sealed artifact hashes match the manifest;
- method-affecting source hashes are unchanged;
- Phase 1f evaluation-count artifacts are unchanged;
- current commit, command, worker count, OS, CPU, and tool versions are recorded.

Fail immediately if a protected artifact changed.

## Metrics

Primary metrics for the 37-candidate primary population at each budget:

- mean Detection across seeds;
- median Detection across seeds;
- standard deviation;
- 2.5th and 97.5th seed percentiles;
- minimum and maximum seed values as descriptive statistics;
- median completed evaluations;
- median unique-domain coverage;
- median end-to-end time to witness;
- median in-process time to witness;
- candidates never detected in any seed;
- candidates detected in all seeds;
- no-mismatch false alarms.

The same detection summaries are reported for low-density and
non-fixture-overfit subsets. No-mismatch populations report total runs,
source/candidate mismatch findings, confirmed in-domain mismatch findings,
crashes, timeouts, and infrastructure failures.

## Comparison To Frozen Policy

Use immutable Phase 1e/1f artifacts for frozen-policy results whenever
possible. At B=8 compare:

- frozen final Detection: 33/37 = 0.892;
- libFuzzer wall-clock Detection at 0.1, 1, and 5 seconds;
- frozen final complete-prefix and simulated early-stop time when available;
- libFuzzer end-to-end and in-process time;
- evaluations to first witness;
- candidate-level sets: both, final-only, libFuzzer-only, neither.

Eight concrete evaluations and one wall-clock duration are complementary cost
views, not the same resource.

## Interpretation Gates

Strong early-yield support is supported if:

- libFuzzer remains materially below 0.892 Detection at 0.1 seconds
  end-to-end;
- the frozen policy reaches witnesses with materially lower median
  end-to-end cost or completed evaluations;
- no confirmed false alarm occurs on no-mismatch candidates.

Permitted wording if supported:

“The frozen source-conditioned policy provides higher early witness yield than
coverage-guided fuzzing in the evaluated startup-dominated, low-budget regime.”

Cost-regime differentiation applies if libFuzzer reaches or exceeds 0.892 at
1 or 5 seconds, but not at 0.1 seconds or eight evaluations:

“Coverage-guided fuzzing catches up with additional time or executions, whereas
the frozen policy targets deterministic early witness discovery.”

Weak comparative support applies if libFuzzer matches or exceeds the frozen
policy at 0.1 seconds end-to-end and does not require materially more
evaluations:

“The frozen policy is a deterministic solver-free alternative, but the
evaluation does not establish superiority over coverage-guided fuzzing.”

These gates must not alter the experiment.
