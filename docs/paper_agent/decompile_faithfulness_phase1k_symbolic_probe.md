# Decompilation Faithfulness Phase 1K Symbolic Probe

## Dependency Snapshot

Local probe in `/home/shx/miniconda3/envs/dllm_env/bin/python` found no usable symbolic/concolic stack:

| Dependency | Available |
|---|---:|
| `z3` | false |
| `angr` | false |
| `claripy` | false |
| `capstone` | false |
| `unicorn` | false |

Phase 1K intentionally does not install dependencies or use the network, so Route B cannot run a proper symbolic or concolic experiment in this pass.

## No-Install Fallback

A no-new-dependency bounded fallback is possible only as finite input enumeration over source-level harnesses. That is already covered more directly by Route A dynamic traces. Without `z3`-style constraint solving or `angr`/`claripy` binary lifting, a "symbolic" fallback would mostly be another hand-coded heuristic and would not add enough independent evidence.

## Candidate Targets

The most useful future symbolic targets are:

| Case | Why it matters |
|---|---|
| `gcd_positive` | Route A still fails to separate faithful and plausible-wrong candidates reliably. |
| `signum` | Branch-boundary behavior is compact enough for path constraints and still partially weak. |
| `max3` | Good sanity target for branch-order equivalence once tooling exists. |
| `sum_to_n` | Loop summaries can test whether symbolic/concolic tooling adds value beyond traces. |

## Verdict

`needs-dependency-plan`

Route B remains scientifically promising, especially for explaining hard cases, but it should be scheduled as a separate dependency-controlled experiment. It should not block Phase 1K, and it does not justify GPU candidate generation by itself.
