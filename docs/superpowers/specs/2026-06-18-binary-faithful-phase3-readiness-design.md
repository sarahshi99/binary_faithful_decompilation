# Binary-Faithful Decompilation Phase 3 Readiness Design

> **Superpowers mode:** Use `superpowers:brainstorming` and `superpowers:writing-plans` style reasoning only. Execute locally and serially. Do not use `superpowers:subagent-driven-development`, Task/Spawn subagents, reviewer subagents, `tool_search`, multi-agent discovery, network, dependency installation, or GPU jobs while writing this design. Work only under `/home/shx/projects/binary_faithful_decompilation`.

## Design Decision

Phase 3 should start as a readiness check, not a full real-project transfer.

Phase 2 v3 passed the narrowed gate:

- generated-candidate pairwise AUC: `1.0000`;
- 8/8 case AUC: `1.0000`;
- `fixture_collapse=False`;
- trace-zero blind spot wrong count: `0`;
- no fixture mismatch is used as the primary score.

That is enough to plan transfer to new source-known small functions. It is not enough to claim a general decompilation faithfulness verifier.

## Research Question

Can the v3 boundary-preserving dynamic trace policy remain useful when the source-known function set changes, while preserving bounded-input oracle semantics and avoiding fixture collapse across multiple independently chosen function subsets?

## Scope

In scope:

- source-known C functions;
- small isolated functions;
- bounded input domains;
- original source as oracle over generated trace inputs;
- deterministic compile and runtime gates;
- CPU-only readiness and first audit;
- optional later GPU generation only after CPU gates pass.

Out of scope:

- binary-only equivalence;
- arbitrary real-project transfer;
- dependency installation;
- symbolic/concolic route;
- subagents or multi-agent work;
- using fixture mismatch as the primary method score.

## Source Selection Criteria

Phase 3 should not rely on one fixed hand-picked set of 5 functions. It should first build a pool of 10-12 eligible functions and then enumerate multiple 5-10 function subsets.

Each pool function must have:

- exact source path;
- exact target function name;
- complete standalone or extractable C function source;
- integer-only arguments and return value for the first pass;
- bounded input domain;
- fixtures that cover ordinary and boundary behavior;
- oracle policy: run original source over generated inputs;
- no global state, I/O, malloc, undefined behavior, callbacks, or external dependencies.

Preferred diversity:

- branch-heavy;
- loop-heavy;
- arithmetic boundary;
- bitwise boundary;
- sign/zero behavior;
- small state-machine-like control flow if still deterministic.

## Combinatorial Selection Policy

The source-selection stage should:

- validate every pool function by compiling the original source and running fixtures;
- enumerate all 5-10 function subsets from the eligible pool;
- score subsets by critical tag coverage and risk-family coverage;
- report the best subset for each size from 5 through 10;
- recommend a tiered set of subsets: minimal 5, balanced 7, broad 10, plus low-overlap alternatives.

Failure interpretation:

- one function failing compile/fixture is a source-manifest issue;
- one subset failing is a subset-specific result;
- repeated failures in one risk family trigger targeted hard-case analysis;
- only repeated failures across diverse high-coverage subsets should count as a Phase 3 method-level failure.

## Manifest Shape

Source pool:

```json
{
  "selection_policy": {
    "minimum_subset_size": 5,
    "maximum_subset_size": 10
  },
  "functions": [
    {
      "case_id": "phase3_example_abs",
      "source_path": "third_party_or_selected/example.c",
      "function_name": "example_abs",
      "signature": "int example_abs(int x)",
      "domain": {
        "arity": 1,
        "values": [-16, -8, -1, 0, 1, 2, 8, 16]
      },
      "fixtures": [
        {"args": [-1], "expected": 1},
        {"args": [0], "expected": 0}
      ],
      "oracle": "compile_original_and_execute_generated_inputs"
    }
  ]
}
```

## Readiness Gates

Gate 1: Method gate from Phase 2 v3.

- `verdict=pass-v3-boundary-trace`;
- pairwise AUC at least `0.9623`;
- `fixture_collapse=False`;
- trace-zero blind spot wrong count `0`.

Gate 2: Source manifest gate.

- at least 10 candidate pool functions preferred;
- at least 5 eligible functions required;
- every function has source path and exact target name;
- every function has bounded domain;
- every function has fixtures and oracle policy.

Gate 2b: Combinatorial subset-selection gate.

- all pool functions compile and pass fixtures, or failures are excluded with reasons;
- at least one valid subset exists for each size 5-10 when possible;
- recommended subsets include minimal, balanced, broad, and low-overlap variants.

Gate 3: CPU audit gate.

- all original functions compile;
- all fixtures pass on original source;
- generated v3 boundary inputs execute without timeout;
- no fixture collapse;
- initial manual or generated candidate pairs produce meaningful score spread.

GPU is not part of readiness. GPU can only be considered after Gate 3.

## Expected Output

- `docs/paper_agent/decompile_faithfulness_phase3_readiness_preflight.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase3_readiness_preflight.json`
- `docs/paper_agent/decompile_faithfulness_phase3_source_pool.json`
- `docs/paper_agent/decompile_faithfulness_phase3_source_selection.zh.md`
- `docs/paper_agent/decompile_faithfulness_phase3_source_selection.json`
- later:
  - `docs/paper_agent/decompile_faithfulness_phase3_cpu_audit.zh.md`

## Claim Boundary

If Phase 3 readiness passes, the paper claim can expand from "same benchmark generated candidates" to "new source-known small-function transfer readiness." It still cannot claim arbitrary real-project transfer or binary-only semantic equivalence.
