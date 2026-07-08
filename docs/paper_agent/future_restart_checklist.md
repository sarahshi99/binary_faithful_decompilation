# Future Restart Checklist

Updated: 2026-07-08

Use this checklist before restarting any CCF-A-level decompilation-faithfulness
project from this repository.

## Required Decisions Before Work Starts

- [ ] Choose a new research question.
- [ ] Define whether the goal is a method paper, a benchmark paper, or an
  empirical measurement/characterization paper.
- [ ] State the primary denominator before candidate generation. If the study is
  about auditors, define the fixture-passing natural semantic-wrong population
  before results exist.
- [ ] Define the minimum viable natural-error population gate before generating
  candidates.
- [ ] Decide which prior artifacts are development-only and which, if any, can
  be treated as held-out.

## Candidate Producers First

- [ ] Build and verify candidate producers before auditor design.
- [ ] Pin every producer version, model snapshot, compiler, prompt template, and
  decoding parameter.
- [ ] Require at least `3` working independent candidate producers before a
  natural-error census.
- [ ] Require at least one traditional decompiler and at least one neural/API
  producer if the research question concerns decompiler/LLM generalization.
- [ ] Verify natural-error yield before designing or modifying an auditor.
- [ ] Do not substitute a different neural model after labels are observed.

## Corpus And Candidate Sealing

- [ ] Preregister a new corpus. Do not post-hoc extend Phase 3a.
- [ ] Avoid Phase 1, Phase 2, and Phase 3 projects unless the new study is
  explicitly development-only.
- [ ] Pin source repositories and source-file hashes before extraction.
- [ ] Seal selected functions, domains, fixtures, and trusted fixture outputs
  before candidate generation.
- [ ] Seal raw and normalized candidates before semantic labeling.
- [ ] Seal the candidate population before any auditor execution.
- [ ] Do not run any auditor, libFuzzer, budget curve, or policy probe before
  the candidate population is sealed.

## Labeling And Population Rules

- [ ] Label compile-ready candidates by complete exact-domain enumeration under
  the declared domain.
- [ ] Treat compile failures, parse failures, harness failures, and runtime
  failures as non-evaluable, not semantic wrong.
- [ ] Report no-mismatch candidates as no mismatch under the bounded audit
  domain, not as fully equivalent.
- [ ] Report fixture-failing semantic-wrong candidates separately.
- [ ] Count fixture-passing semantic-wrong candidates as the primary natural
  auditor-evaluation denominator only if the gate is preregistered.
- [ ] Require at least `25` fixture-passing natural semantic-wrong candidates
  across at least `15` functions and `8` projects before a CCF-A-style auditor
  evaluation.
- [ ] Require at least two producers each contributing at least `5` primary wrong
  candidates.
- [ ] Require a taxonomy broad enough to avoid a single mechanism or project
  dominating the result.

## Baselines And Claims

- [ ] Compare any proposed auditor to libFuzzer wall-clock and execution-count
  baselines.
- [ ] Compare deterministic concrete-input policies to literal-first and generic
  boundary baselines.
- [ ] Do not claim controlled mutations establish natural-error
  generalization.
- [ ] Do not claim a policy is superior to libFuzzer unless the wall-clock
  baseline supports it.
- [ ] Do not claim interleaving is uniquely superior to literal-first unless a
  new independent population supports that claim.
- [ ] Do not reuse Phase 1/2/3 misses or witnesses to design a supposedly
  prospective auditor.

## Stop Conditions

- [ ] Stop before auditor evaluation if fewer than `25` fixture-passing natural
  semantic-wrong candidates are found.
- [ ] Stop if fewer than `3` producers are available.
- [ ] Stop if one project or one producer dominates the primary wrong
  population beyond the preregistered cap.
- [ ] Stop if infrastructure failures prevent a fair producer matrix and cannot
  be fixed before labels.
- [ ] Stop and document the blocker rather than lowering gates after seeing
  labels.
