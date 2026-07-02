# Binary-Faithful Decompilation Phase 1K Three-Route Scout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` only, or execute locally in the current session. Do not use `superpowers:subagent-driven-development`, Task/Spawn subagents, dispatching/parallel agents, reviewer subagents, `tool_search`, or multi-agent discovery. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run a CPU-only three-route scout after Phase 1J failed: dynamic trace gate, symbolic/concolic feasibility probe, and narrowed localized-bug framing audit.

**Architecture:** Route A adds a focused dynamic-trace module and runner. Route B is a read-only/local environment feasibility probe that writes a symbolic route report before any dependency install. Route C writes a claim matrix to decide whether the paper should narrow to source-known localized semantic bug auditing. A final decision document combines all three routes and decides whether GPU candidate generation or real-project transfer is justified later.

**Tech Stack:** Python standard library, `/usr/bin/gcc`, existing Phase 1H artifacts, direct `unittest`, JSON/Markdown outputs. No GPU, network, subagents, Ghidra, RetDec, angr install, z3 install, or LLM API in Phase 1K.

---

## File Structure

Route A creates:

- `analysis/decompile_faithfulness/dynamic_trace.py`
  - trace input generation, trace harness rendering, trace execution, and trace-distance computation.
- `analysis/decompile_faithfulness/run_dynamic_trace_audit.py`
  - artifact reading, trace aggregation, formula scoring, leave-one-case-out, and report writing.
- `tests/test_decompile_faithfulness_dynamic_trace.py`
  - generated inputs, harness output parsing, trace execution, and distance components.
- `tests/test_decompile_faithfulness_dynamic_trace_audit.py`
  - artifact path lookup, aggregation, LOCO formula selection, and label isolation.

Route B creates:

- `docs/paper_agent/decompile_faithfulness_phase1k_symbolic_probe.md`
- `docs/paper_agent/decompile_faithfulness_phase1k_symbolic_probe.zh.md`
- `analysis_outputs/decompile_faithfulness/phase1k_symbolic_probe/environment.json`

Route C creates:

- `docs/paper_agent/decompile_faithfulness_phase1k_claim_matrix.zh.md`

Combined decision creates:

- `docs/paper_agent/decompile_faithfulness_phase1k_three_route_decision.zh.md`
- modifies `docs/paper_agent/decompile_faithfulness_phase1_overview_and_next_steps.zh.md`

Do not modify:

- `/home/shx/projects/dllm_infilling`
- GPU or LLM runners
- existing Phase 1A-1J output files except the Phase 1 overview document

## Task 1: Route A Dynamic Trace Input Generation And Harness Tests

**Files:**

- Create: `tests/test_decompile_faithfulness_dynamic_trace.py`
- Create: `analysis/decompile_faithfulness/dynamic_trace.py`

- [x] **Step 1: Write failing input-generation and harness tests**

Create `tests/test_decompile_faithfulness_dynamic_trace.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import dynamic_trace, fixtures


class DecompileFaithfulnessDynamicTraceTest(unittest.TestCase):
    def test_generated_trace_inputs_are_deterministic_and_exclude_fixture_tests(self) -> None:
        case = fixtures.case_by_id("signum")

        first = dynamic_trace.generate_trace_inputs(case, max_inputs=32, include_fixture_tests=False)
        second = dynamic_trace.generate_trace_inputs(case, max_inputs=32, include_fixture_tests=False)
        fixture_args = {test.args for test in case.tests}

        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 32)
        self.assertTrue(first)
        self.assertTrue(all(trace_input.args not in fixture_args for trace_input in first))
        self.assertEqual(first, sorted(first, key=lambda item: item.args))

    def test_generated_trace_inputs_can_include_fixture_tests_for_diagnostics(self) -> None:
        case = fixtures.case_by_id("clamp8")

        inputs = dynamic_trace.generate_trace_inputs(case, max_inputs=64, include_fixture_tests=True)
        input_args = {trace_input.args for trace_input in inputs}

        self.assertTrue({test.args for test in case.tests}.issubset(input_args))

    def test_render_trace_harness_prints_one_output_per_input(self) -> None:
        case = fixtures.case_by_id("absdiff")
        inputs = [
            dynamic_trace.TraceInput(args=(7, 3), bucket="fixture"),
            dynamic_trace.TraceInput(args=(3, 7), bucket="fixture"),
        ]

        harness = dynamic_trace.render_trace_harness(case, case.function_source, inputs)

        self.assertIn("#include <stdio.h>", harness)
        self.assertIn("int absdiff(int a, int b)", harness)
        self.assertIn('printf("%d\\\\n", absdiff(7, 3));', harness)
        self.assertIn('printf("%d\\\\n", absdiff(3, 7));', harness)

    def test_parse_trace_stdout_rejects_wrong_output_count(self) -> None:
        with self.assertRaises(ValueError):
            dynamic_trace.parse_trace_stdout("1\\n2\\n", expected_count=3)
```

- [x] **Step 2: Run the failing test**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace.py
```

Expected: import failure for `analysis.decompile_faithfulness.dynamic_trace`.

- [x] **Step 3: Implement minimal input generation and harness rendering**

Create `analysis/decompile_faithfulness/dynamic_trace.py` with:

```python
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import fixtures


@dataclass(frozen=True, order=True)
class TraceInput:
    args: tuple[int, ...]
    bucket: str


@dataclass(frozen=True)
class TraceRun:
    case_id: str
    candidate_id: str
    compiled: bool
    exit_code: int
    outputs: tuple[int, ...]
    stdout: str
    stderr: str
    source_path: Path
    exe_path: Path


@dataclass(frozen=True)
class TraceDistance:
    components: dict[str, float]


VALUE_POOL = (-16, -8, -5, -3, -2, -1, 0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 12, 14, 16, 17, 21, 25, 31, 63, 127, 128, 170, 255, 256, 300)
COMPACT_POOL_2 = (-8, -3, -1, 0, 1, 2, 3, 5, 8, 12, 17, 25, 255)
COMPACT_POOL_3 = (-8, -1, 0, 1, 2, 3, 5, 8, 17)
BOUNDARY_VALUES = {-16, -8, -1, 0, 1, 8, 16, 127, 128, 255, 256, 300}
```

Implement:

- `generate_trace_inputs(case, max_inputs=256, include_fixture_tests=False) -> list[TraceInput]`
- `render_trace_harness(case, function_source, inputs) -> str`
- `parse_trace_stdout(stdout, expected_count) -> tuple[int, ...]`

Required behavior:

- infer arity from `case.tests[0].args`;
- generate deterministic inputs by arity;
- remove fixture-test tuples from primary generated inputs;
- include fixture tuples with bucket `fixture` when requested;
- sort by `args`;
- cap at `max_inputs`;
- raise `ValueError` on malformed trace stdout.

- [x] **Step 4: Verify Task 1 tests pass**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace.py
```

Expected: 4 tests pass.

## Task 2: Route A Trace Execution And Distance Tests

**Files:**

- Modify: `tests/test_decompile_faithfulness_dynamic_trace.py`
- Modify: `analysis/decompile_faithfulness/dynamic_trace.py`

- [x] **Step 1: Add failing trace-run and distance tests**

Append to `DecompileFaithfulnessDynamicTraceTest`:

```python
    def test_run_trace_executes_generated_harness(self) -> None:
        case = fixtures.case_by_id("absdiff")
        inputs = [
            dynamic_trace.TraceInput(args=(7, 3), bucket="fixture"),
            dynamic_trace.TraceInput(args=(3, 7), bucket="fixture"),
            dynamic_trace.TraceInput(args=(5, 5), bucket="fixture"),
        ]

        with tempfile.TemporaryDirectory() as td:
            run = dynamic_trace.run_trace(
                case=case,
                candidate_id="original",
                function_source=case.function_source,
                inputs=inputs,
                output_dir=Path(td),
                opt_level="O0",
            )

        self.assertTrue(run.compiled, run.stderr)
        self.assertEqual(run.exit_code, 0)
        self.assertEqual(run.outputs, (4, 4, 0))

    def test_trace_distance_scores_output_mismatches_without_labels(self) -> None:
        inputs = [
            dynamic_trace.TraceInput(args=(-1,), bucket="negative"),
            dynamic_trace.TraceInput(args=(0,), bucket="zero"),
            dynamic_trace.TraceInput(args=(1,), bucket="positive"),
            dynamic_trace.TraceInput(args=(128,), bucket="boundary"),
        ]

        distance = dynamic_trace.trace_distance(
            inputs=inputs,
            original_outputs=(-1, 0, 1, 1),
            candidate_outputs=(1, 0, -1, 1),
        )

        self.assertAlmostEqual(distance.components["trace_input_count"], 4.0)
        self.assertAlmostEqual(distance.components["trace_mismatch_count"], 2.0)
        self.assertAlmostEqual(distance.components["trace_mismatch_rate"], 0.5)
        self.assertGreater(distance.components["trace_sign_mismatch_rate"], 0.0)
        self.assertGreater(distance.components["trace_total"], 0.5)
```

- [x] **Step 2: Run test to verify failure**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace.py
```

Expected: failures for missing `run_trace` and `trace_distance`.

- [x] **Step 3: Implement trace execution and distance**

Add:

- `run_trace(...) -> TraceRun`
- `trace_distance(...) -> TraceDistance`
- `_safe_name(value: str) -> str`
- `_sign(value: int) -> int`
- `_squash(value: float) -> float`

Implementation constraints:

- compile generated trace harness with `/usr/bin/gcc`;
- use existing `ccompile.run_command`;
- parse exactly one output per input;
- compute:
  - `trace_input_count`
  - `trace_mismatch_count`
  - `trace_mismatch_rate`
  - `trace_abs_error_mean`
  - `trace_abs_error_max`
  - `trace_sign_mismatch_rate`
  - `trace_zero_mismatch_rate`
  - `trace_boundary_mismatch_rate`
  - `trace_total`

- [x] **Step 4: Verify Task 2 tests pass**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace.py
```

Expected: 6 tests pass.

## Task 3: Route A Dynamic Trace Audit Runner

**Files:**

- Create: `tests/test_decompile_faithfulness_dynamic_trace_audit.py`
- Create: `analysis/decompile_faithfulness/run_dynamic_trace_audit.py`

- [x] **Step 1: Write failing runner tests**

Create `tests/test_decompile_faithfulness_dynamic_trace_audit.py` with tests for:

- `_source_paths_for_record(root, record)` using Phase 1H `o0/candidates/*__O0.function.c` naming.
- `_aggregate_records([root], distance_fn=fake_distance)` adding trace features while keeping labels only for offline scoring.
- `_leave_one_case_out(records, _formulas())` selecting `trace_mismatch_rate` on synthetic training folds.

The test should use temporary artifact roots and should not call gcc.

- [x] **Step 2: Run test to verify failure**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace_audit.py
```

Expected: import failure for `run_dynamic_trace_audit`.

- [x] **Step 3: Implement runner**

Create `analysis/decompile_faithfulness/run_dynamic_trace_audit.py` with:

- `SourcePaths(original: Path, candidate: Path)` dataclass.
- `Formula(name: str, score: Callable[[dict[str, float]], float])` dataclass.
- `_source_paths_for_record(artifact_root, record) -> SourcePaths`.
- `_aggregate_records(artifact_roots, distance_fn=None) -> list[dict[str, Any]]`.
- `_dynamic_distance_for_paths(paths) -> dict[str, float]`.
- `_formulas() -> list[Formula]`.
- `_leave_one_case_out(records, formulas) -> dict[str, Any]`.
- `_pairwise_auc(records, score) -> float`.
- `run_audit(...) -> dict[str, Any]`.
- `main() -> None`.

Rules:

- read only `o0/records.jsonl` from each Phase 1H root;
- read matching original/candidate `.function.c`;
- generate primary trace inputs with `include_fixture_tests=False`;
- compute fixture diagnostics separately;
- use labels only in scoring and summary counts;
- preserve `slot_concentration` as `min_slot`.

- [x] **Step 4: Verify runner tests pass**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_dynamic_trace_audit.py
```

Expected: runner tests pass.

## Task 4: Route A Audit Run

**Files:**

- Generate: `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.json`
- Generate: `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.md`
- Generate: `docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.zh.md`
- Generate: `analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace/records.jsonl`

- [x] **Step 1: Run dynamic trace audit**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_dynamic_trace_audit \
  --artifact-roots \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1e \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1f \
    analysis_outputs/decompile_faithfulness/phase1h_bigram_repair_phase1g \
  --output-json docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.json \
  --output-md docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.md \
  --output-zh docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.zh.md \
  --output-jsonl analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace/records.jsonl
```

Expected:

- command exits `0`;
- no GPU is used;
- JSON/Markdown/JSONL outputs exist.

- [x] **Step 2: Read Route A verdict**

Run:

```bash
jq '{best_in_sample, leave_one_case_out, hard_case_auc, fixture_collapse, verdict}' docs/paper_agent/decompile_faithfulness_phase1k_dynamic_trace.json
```

Expected: `verdict` is present and hard cases are reported.

## Task 5: Route B Symbolic / Concolic Feasibility Probe

**Files:**

- Create: `analysis_outputs/decompile_faithfulness/phase1k_symbolic_probe/environment.json`
- Create: `docs/paper_agent/decompile_faithfulness_phase1k_symbolic_probe.md`
- Create: `docs/paper_agent/decompile_faithfulness_phase1k_symbolic_probe.zh.md`

- [x] **Step 1: Probe local dependencies**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -c "import importlib.util as u, json; print(json.dumps({name: u.find_spec(name) is not None for name in ['z3', 'angr', 'claripy', 'capstone', 'unicorn']}, sort_keys=True))"
```

Expected: prints JSON availability. Do not install anything in this task.

- [x] **Step 2: Write environment JSON**

Create `analysis_outputs/decompile_faithfulness/phase1k_symbolic_probe/environment.json` with:

- dependency availability from Step 1;
- Python executable path;
- decision `no_dependency_install_in_phase1k`;
- candidate hard cases: `signum`, `max3`, `gcd_positive`, `sum_to_n`.

- [x] **Step 3: Write symbolic probe reports**

Create English and Chinese reports stating:

- whether local dependencies are available;
- whether a no-new-dependency bounded fallback is plausible;
- which hard cases are suitable symbolic targets;
- whether a separate dependency plan is needed;
- verdict:
  - `symbolic-feasible-next` if a practical no-install route exists;
  - `needs-dependency-plan` if z3/angr-like tools are absent but route is still promising;
  - `defer-symbolic-route` if tooling cost dominates.

## Task 6: Route C Narrowed Localized-Bug Framing Audit

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase1k_claim_matrix.zh.md`

- [x] **Step 1: Write claim matrix**

Create a Chinese claim matrix with columns:

- Claim
- Status after Phase 1A-1J
- Evidence
- What Phase 1K A/B can still change
- Paper wording recommendation

Include at least these claims:

- raw global binary distance can rank decompilation faithfulness;
- multi-opt slot concentration is a robust verifier;
- static binary motifs are useful diagnostics;
- source-known dynamic traces can identify localized semantic bugs;
- symbolic/concolic summaries may explain hard cases;
- real-project transfer is justified now;
- GPU LLM/decompiler candidate generation is justified now.

- [x] **Step 2: Assign Route C verdict**

End the claim matrix with one of:

- `narrow-localized-bug-paper`
- `need-route-a-or-b-positive`
- `stop-current-direction`

## Task 7: Combined Phase 1K Decision

**Files:**

- Create: `docs/paper_agent/decompile_faithfulness_phase1k_three_route_decision.zh.md`
- Modify: `docs/paper_agent/decompile_faithfulness_phase1_overview_and_next_steps.zh.md`

- [x] **Step 1: Write combined decision**

Create `docs/paper_agent/decompile_faithfulness_phase1k_three_route_decision.zh.md` summarizing:

- Route A result and verdict;
- Route B feasibility verdict;
- Route C framing verdict;
- final decision:
  - `continue-dynamic-trace`
  - `continue-symbolic-probe`
  - `narrow-localized-bug-paper`
  - `stop-current-direction`
- whether GPU 2/3 should be used next.

- [x] **Step 2: Update overview**

Update `docs/paper_agent/decompile_faithfulness_phase1_overview_and_next_steps.zh.md` with a Phase 1K result paragraph and the final decision.

## Task 8: Verification

**Files:**

- All files created in Tasks 1-7.

- [x] **Step 1: Run focused tests**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest \
  tests/test_decompile_faithfulness_dynamic_trace.py \
  tests/test_decompile_faithfulness_dynamic_trace_audit.py
```

Expected: focused Phase 1K tests pass.

- [x] **Step 2: Run full test suite**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest discover -s tests
```

Expected: all repository tests pass.

- [x] **Step 3: Run py_compile**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m py_compile \
  analysis/decompile_faithfulness/dynamic_trace.py \
  analysis/decompile_faithfulness/run_dynamic_trace_audit.py
```

Expected: command exits `0`.

- [x] **Step 4: Run diff hygiene**

Run:

```bash
git diff --check
```

Expected: no whitespace errors.

- [x] **Step 5: Confirm no GPU use**

Run:

```bash
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader
```

Expected: no Phase 1K process is using GPU 2/3.

## Self-Review

- Spec coverage: covers Route A dynamic trace, Route B symbolic feasibility, Route C claim framing, and combined decision.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: Route A API names match the dynamic trace design.
- Scope: no GPU, network, dependency install, subagent, or real-project transfer is included in Phase 1K.
