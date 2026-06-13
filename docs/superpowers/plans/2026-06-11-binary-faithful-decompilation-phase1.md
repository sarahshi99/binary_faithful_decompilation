# Binary-Faithful Decompilation Phase 1 Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` only, or execute this plan manually in the current session. Do not use `superpowers:subagent-driven-development`, `superpowers:dispatching-parallel-agents`, Task/Spawn subagents, reviewer subagents, parallel-agent dispatch, `tool_search` discovery, or multi-agent reviewer discovery. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CPU-only audit scaffold that tests whether recompiled binary feature distance can rank faithful C candidates above plausible-but-wrong candidates, then extend the same scaffold to slot-level localization and real-project transfer.

**Architecture:** Add a small `analysis/decompile_faithfulness/` package with focused modules for source-known fixtures, compile/run gates, rule-based counterfactual generation, binary feature extraction, ranking metrics, reporting, and slot localization. Keep Phase 1A model-agnostic: no GPU, no training, no Ghidra/RetDec/angr dependency, and no LLM API calls are required for the first kill gate.

**Tech Stack:** Python standard library, `/usr/bin/gcc`, `/usr/bin/objdump`, `/usr/bin/nm`, `/usr/bin/readelf`, direct `unittest` tests, compact JSON/Markdown outputs under `docs/paper_agent/` and optional larger artifacts under `analysis_outputs/decompile_faithfulness/`.

---

## Current State And Serial Execution Rules

Status as of 2026-06-13 CST:

- Branch: `phase1a-audit`.
- Completed and committed: Tasks 1-5, through commit `267c0f9` (`analysis: add binary feature ranking audit`).
- Initial Phase 1A result: `pairwise_auc=0.875`, `top1_faithful_rate=0.6667`, `verdict=inconclusive`, with a return-value operand-order blind spot.
- Current uncommitted follow-up: Task 5.1 adds operand-sensitive `instruction_signature_l1`, regenerating Phase 1A to `pairwise_auc=1.0000`, `top1_faithful_rate=1.0000`, `verdict=continue`.
- Before any new experiment, close Task 5.1: run fresh verification, do local diff review fallback, and commit only the Phase 1A.1 files.
- Next experiment after Task 5.1 closes: Task 6, Phase 1B realistic negatives input format. Do not jump directly to Task 7 localization or Task 8 real-project transfer, because current evidence is still controlled mutation-style.

Serial execution policy:

- Execute one task at a time in the current Codex session.
- Do not auto-discover or invoke subagent, reviewer, Task/Spawn, parallel-agent, or multi-agent tools.
- If a review gate is needed, record `reviewer_gate_disabled`, run local diff review plus fresh verification, and continue.
- If a future prompt manually names a Superpowers skill, run only that named skill; if it requires subagents or tool discovery, stop that path and use the local serial fallback.

---

## File Structure

Create a focused analysis package:

- `analysis/decompile_faithfulness/__init__.py`: package marker and public version string.
- `analysis/decompile_faithfulness/fixtures.py`: source-known benchmark cases, deterministic test vectors, and harness rendering.
- `analysis/decompile_faithfulness/compile.py`: compile, run, and subprocess helpers for candidate C snippets.
- `analysis/decompile_faithfulness/mutations.py`: rule-based counterfactual operators with mutation labels and expected sketch slots.
- `analysis/decompile_faithfulness/features.py`: extract normalized binary features from object files using `objdump`, `nm`, and `readelf`.
- `analysis/decompile_faithfulness/ranking.py`: feature distance, candidate ranking, AUC/top-1 metrics, and bucket summaries.
- `analysis/decompile_faithfulness/report.py`: JSON and Markdown report writers.
- `analysis/decompile_faithfulness/localization.py`: map feature deltas back to mutated sketch slots for Phase 1C.
- `analysis/decompile_faithfulness/run_candidate_ranking_audit.py`: CLI for Phase 1A/1B candidate ranking.
- `analysis/decompile_faithfulness/run_slot_localization_audit.py`: CLI for Phase 1C slot localization.

Add focused tests:

- `tests/test_decompile_faithfulness_fixtures.py`
- `tests/test_decompile_faithfulness_compile.py`
- `tests/test_decompile_faithfulness_mutations.py`
- `tests/test_decompile_faithfulness_features.py`
- `tests/test_decompile_faithfulness_ranking.py`
- `tests/test_decompile_faithfulness_localization.py`

Write compact evidence:

- `docs/paper_agent/decompile_faithfulness_phase1_audit.json`
- `docs/paper_agent/decompile_faithfulness_phase1_audit.md`
- `docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md`

Optional larger, reproducible artifacts:

- `analysis_outputs/decompile_faithfulness/phase1a/records.jsonl`
- `analysis_outputs/decompile_faithfulness/phase1a/candidates/`
- `analysis_outputs/decompile_faithfulness/phase1c/localization_records.jsonl`

Do not modify current DLLM runners in `clean_scripts/` or `expvision_dllm_clean/` during this plan.

---

### Task 1: Source-Known Fixture Schema

**Files:**
- Create: `analysis/decompile_faithfulness/__init__.py`
- Create: `analysis/decompile_faithfulness/fixtures.py`
- Test: `tests/test_decompile_faithfulness_fixtures.py`

- [ ] **Step 1: Write the failing fixture tests**

Create `tests/test_decompile_faithfulness_fixtures.py`:

```python
from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import fixtures


class DecompileFaithfulnessFixturesTest(unittest.TestCase):
    def test_builtin_cases_have_expected_shape(self) -> None:
        cases = fixtures.builtin_cases()
        self.assertGreaterEqual(len(cases), 3)
        for case in cases:
            self.assertRegex(case.case_id, r"^[a-z0-9_]+$")
            self.assertIn("int", case.function_source)
            self.assertIn(case.function_name, case.function_source)
            self.assertGreaterEqual(len(case.tests), 3)
            for test in case.tests:
                self.assertIsInstance(test.args, tuple)
                self.assertIsInstance(test.expected, int)

    def test_render_translation_unit_wraps_function_and_harness(self) -> None:
        case = fixtures.builtin_cases()[0]
        rendered = fixtures.render_translation_unit(case, case.function_source)
        self.assertIn(case.function_source.strip(), rendered)
        self.assertIn("int main(void)", rendered)
        self.assertIn("return 0;", rendered)
        self.assertIn("return 100 +", rendered)

    def test_case_by_id_is_stable(self) -> None:
        first = fixtures.case_by_id("absdiff")
        second = fixtures.case_by_id("absdiff")
        self.assertEqual(first.case_id, second.case_id)
        self.assertEqual(first.function_source, second.function_source)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_fixtures.py
```

Expected: import failure for `analysis.decompile_faithfulness`.

- [ ] **Step 3: Implement the fixture schema**

Create `analysis/decompile_faithfulness/__init__.py`:

```python
"""CPU-only audits for binary-faithful decompilation research."""

__version__ = "0.1"
```

Create `analysis/decompile_faithfulness/fixtures.py` with:

- `FunctionTest(args: tuple[int, ...], expected: int)`
- `FunctionCase(case_id: str, function_name: str, function_source: str, tests: tuple[FunctionTest, ...])`
- `builtin_cases() -> list[FunctionCase]`
- `case_by_id(case_id: str) -> FunctionCase`
- `render_translation_unit(case: FunctionCase, function_source: str) -> str`

Use these first three source-known cases:

```c
int absdiff(int a, int b) {
    if (a > b) {
        return a - b;
    }
    return b - a;
}
```

```c
int clamp8(int x) {
    if (x < 0) {
        return 0;
    }
    if (x > 255) {
        return 255;
    }
    return x;
}
```

```c
int count_bits8(int x) {
    int total = 0;
    for (int i = 0; i < 8; i++) {
        if ((x & (1 << i)) != 0) {
            total++;
        }
    }
    return total;
}
```

`render_translation_unit` must embed deterministic tests and return `100 + test_index` on the first mismatch so the compile/run gate can identify behavioral divergence.

- [ ] **Step 4: Verify the fixture tests pass**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_fixtures.py
```

Expected: `Ran 3 tests` and `OK`.

- [ ] **Step 5: Commit Task 1**

```bash
git add analysis/decompile_faithfulness/__init__.py analysis/decompile_faithfulness/fixtures.py tests/test_decompile_faithfulness_fixtures.py docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
git commit -m "analysis: add decompilation fixture schema"
```

---

### Task 2: Compile And Behavior Gates

**Files:**
- Create: `analysis/decompile_faithfulness/compile.py`
- Modify: `analysis/decompile_faithfulness/fixtures.py`
- Test: `tests/test_decompile_faithfulness_compile.py`

- [ ] **Step 1: Write failing compile-gate tests**

Create `tests/test_decompile_faithfulness_compile.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import fixtures


class DecompileFaithfulnessCompileTest(unittest.TestCase):
    def test_compile_and_run_original_case(self) -> None:
        case = fixtures.case_by_id("absdiff")
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(
                case=case,
                candidate_id="original",
                function_source=case.function_source,
                output_dir=Path(td),
                opt_level="O0",
            )
        self.assertTrue(result.compiled, result.stderr)
        self.assertTrue(result.behavior_passed, result.run_stdout + result.run_stderr)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.object_path.name.endswith(".o"))
        self.assertTrue(result.exe_path.name.endswith(".exe"))

    def test_behavior_gate_catches_wrong_predicate(self) -> None:
        case = fixtures.case_by_id("absdiff")
        wrong_source = case.function_source.replace("a > b", "a < b")
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(
                case=case,
                candidate_id="predicate_ge",
                function_source=wrong_source,
                output_dir=Path(td),
                opt_level="O0",
            )
        self.assertTrue(result.compiled, result.stderr)
        self.assertFalse(result.behavior_passed)
        self.assertGreaterEqual(result.exit_code, 100)

    def test_compile_gate_records_syntax_failure(self) -> None:
        case = fixtures.case_by_id("clamp8")
        bad_source = "int clamp8(int x) { return ; }"
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(
                case=case,
                candidate_id="syntax_bad",
                function_source=bad_source,
                output_dir=Path(td),
                opt_level="O0",
            )
        self.assertFalse(result.compiled)
        self.assertFalse(result.behavior_passed)
        self.assertIn("error", result.stderr.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_compile.py
```

Expected: import failure for `analysis.decompile_faithfulness.compile`.

- [ ] **Step 3: Implement compile helpers**

Create `analysis/decompile_faithfulness/compile.py` with:

- `CompileResult` dataclass fields: `case_id`, `candidate_id`, `opt_level`, `source_path`, `object_path`, `exe_path`, `compiled`, `behavior_passed`, `exit_code`, `stdout`, `stderr`, `run_stdout`, `run_stderr`.
- `run_command(argv: list[str], cwd: Path | None = None, timeout_s: int = 10) -> subprocess.CompletedProcess[str]`.
- `compile_candidate(case, candidate_id, function_source, output_dir, opt_level="O0") -> CompileResult`.

Implementation rules:

- Write function-only source to `<output_dir>/<case_id>__<candidate_id>__<opt_level>.function.c`.
- Write harness source from `fixtures.render_translation_unit(...)` to `<output_dir>/<case_id>__<candidate_id>__<opt_level>.harness.c`.
- Compile the object from the function-only source with `/usr/bin/gcc -std=c11 -Wall -Wextra -Werror -<opt_level> -c function.c -o function.o`.
- Compile the executable from the harness source with `/usr/bin/gcc -std=c11 -Wall -Wextra -Werror -<opt_level> harness.c -o harness.exe`.
- Run the executable only if both compile commands succeed.
- Set `CompileResult.source_path` to the function-only source path so feature extraction remains tied to the candidate function, not the test harness.
- Set `behavior_passed=True` only when executable exit code is `0`.
- Capture stdout and stderr for all commands.

- [ ] **Step 4: Verify compile tests pass**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_fixtures.py tests/test_decompile_faithfulness_compile.py
```

Expected: all tests exit `0`.

- [ ] **Step 5: Commit Task 2**

```bash
git add analysis/decompile_faithfulness/compile.py tests/test_decompile_faithfulness_compile.py analysis/decompile_faithfulness/fixtures.py docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
git commit -m "analysis: add decompilation compile gates"
```

---

### Task 3: Rule-Based Counterfactuals

**Files:**
- Create: `analysis/decompile_faithfulness/mutations.py`
- Test: `tests/test_decompile_faithfulness_mutations.py`

- [ ] **Step 1: Write failing mutation tests**

Create `tests/test_decompile_faithfulness_mutations.py`:

```python
from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import fixtures, mutations


class DecompileFaithfulnessMutationTest(unittest.TestCase):
    def test_absdiff_predicate_mutations_are_labeled(self) -> None:
        case = fixtures.case_by_id("absdiff")
        muts = mutations.generate_rule_mutations(case)
        by_id = {mut.candidate_id: mut for mut in muts}
        self.assertIn("mut_predicate_gt_to_ge", by_id)
        self.assertEqual(by_id["mut_predicate_gt_to_ge"].mutation_type, "predicate")
        self.assertEqual(by_id["mut_predicate_gt_to_ge"].expected_slot, "branch_predicate")
        self.assertIn("a >= b", by_id["mut_predicate_gt_to_ge"].function_source)

    def test_clamp_constant_mutations_are_labeled(self) -> None:
        case = fixtures.case_by_id("clamp8")
        muts = mutations.generate_rule_mutations(case)
        by_id = {mut.candidate_id: mut for mut in muts}
        self.assertIn("mut_constant_255_to_256", by_id)
        self.assertEqual(by_id["mut_constant_255_to_256"].mutation_type, "constant")
        self.assertEqual(by_id["mut_constant_255_to_256"].expected_slot, "constant")
        self.assertIn("return 256;", by_id["mut_constant_255_to_256"].function_source)

    def test_count_bits8_loop_mutation_is_labeled(self) -> None:
        case = fixtures.case_by_id("count_bits8")
        muts = mutations.generate_rule_mutations(case)
        by_id = {mut.candidate_id: mut for mut in muts}
        self.assertIn("mut_predicate_ne_to_eq", by_id)
        self.assertEqual(by_id["mut_predicate_ne_to_eq"].expected_slot, "branch_predicate")
        self.assertIn("(x & (1 << i)) == 0", by_id["mut_predicate_ne_to_eq"].function_source)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_mutations.py
```

Expected: import failure for `analysis.decompile_faithfulness.mutations`.

- [ ] **Step 3: Implement rule mutations**

Create `analysis/decompile_faithfulness/mutations.py` with:

- `MutationCandidate` dataclass fields: `candidate_id`, `function_source`, `mutation_type`, `expected_slot`, `description`.
- `replace_once(source: str, old: str, new: str) -> str` that raises `ValueError` if `old` is absent or appears more than once.
- `generate_rule_mutations(case: FunctionCase) -> list[MutationCandidate]`.

Implement only explicit, case-specific mutations for the first audit:

- `absdiff`: `a > b` -> `a >= b`, `a > b` -> `a < b`, `return a - b;` -> `return b - a;`.
- `clamp8`: `x < 0` -> `x <= 0`, `x > 255` -> `x >= 255`, `return 255;` -> `return 256;`.
- `count_bits8`: `(x & (1 << i)) != 0` -> `(x & (1 << i)) == 0`, `i < 8` -> `i <= 8`.

Keep mutation generation deterministic by sorting candidates by `candidate_id`.

- [ ] **Step 4: Verify mutation tests pass**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_mutations.py
```

Expected: `OK`.

- [ ] **Step 5: Compile and behavior-filter generated mutations**

Run a short inline check:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python - <<'PY'
from pathlib import Path
import tempfile
from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import fixtures, mutations

with tempfile.TemporaryDirectory() as td:
    out = Path(td)
    total = 0
    compiled = 0
    behavior_fail = 0
    for case in fixtures.builtin_cases():
        for mut in mutations.generate_rule_mutations(case):
            total += 1
            result = ccompile.compile_candidate(case, mut.candidate_id, mut.function_source, out, opt_level="O0")
            compiled += int(result.compiled)
            behavior_fail += int(result.compiled and not result.behavior_passed)
    print({"total": total, "compiled": compiled, "behavior_fail": behavior_fail})
PY
```

Expected: all generated mutations compile, and at least one mutation fails the behavior gate.

- [ ] **Step 6: Commit Task 3**

```bash
git add analysis/decompile_faithfulness/mutations.py tests/test_decompile_faithfulness_mutations.py docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
git commit -m "analysis: add controlled decompilation counterfactuals"
```

---

### Task 4: Binary Feature Extraction

**Files:**
- Create: `analysis/decompile_faithfulness/features.py`
- Test: `tests/test_decompile_faithfulness_features.py`

- [ ] **Step 1: Write failing feature tests**

Create `tests/test_decompile_faithfulness_features.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import features, fixtures


class DecompileFaithfulnessFeatureTest(unittest.TestCase):
    def test_extract_features_from_original_object(self) -> None:
        case = fixtures.case_by_id("clamp8")
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(case, "original", case.function_source, Path(td), opt_level="O0")
            vector = features.extract_binary_features(result.object_path)
        self.assertGreater(vector.instruction_count, 0)
        self.assertGreaterEqual(vector.branch_count, 1)
        self.assertIn("clamp8", vector.symbols)
        self.assertGreaterEqual(len(vector.opcode_counts), 1)

    def test_feature_distance_is_zero_for_same_object(self) -> None:
        case = fixtures.case_by_id("absdiff")
        with tempfile.TemporaryDirectory() as td:
            result = ccompile.compile_candidate(case, "original", case.function_source, Path(td), opt_level="O0")
            left = features.extract_binary_features(result.object_path)
            right = features.extract_binary_features(result.object_path)
        distance = features.feature_distance(left, right)
        self.assertEqual(distance.total, 0.0)
        self.assertEqual(distance.components["opcode_l1"], 0.0)

    def test_feature_distance_detects_constant_change(self) -> None:
        case = fixtures.case_by_id("clamp8")
        wrong_source = case.function_source.replace("return 255;", "return 256;")
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            original = ccompile.compile_candidate(case, "original", case.function_source, out, opt_level="O0")
            wrong = ccompile.compile_candidate(case, "constant", wrong_source, out, opt_level="O0")
            left = features.extract_binary_features(original.object_path)
            right = features.extract_binary_features(wrong.object_path)
        distance = features.feature_distance(left, right)
        self.assertGreater(distance.total, 0.0)
        self.assertGreaterEqual(distance.components["immediate_symmetric_diff"], 1.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_features.py
```

Expected: import failure for `analysis.decompile_faithfulness.features`.

- [ ] **Step 3: Implement feature extraction**

Create `analysis/decompile_faithfulness/features.py` with:

- `BinaryFeatureVector` dataclass fields: `object_path`, `instruction_count`, `branch_count`, `call_count`, `ret_count`, `opcode_counts`, `immediates`, `symbols`.
- `FeatureDistance` dataclass fields: `total`, `components`.
- `extract_binary_features(object_path: Path) -> BinaryFeatureVector`.
- `feature_distance(left: BinaryFeatureVector, right: BinaryFeatureVector) -> FeatureDistance`.

Implementation rules:

- Use `/usr/bin/objdump -d object.o` to parse instruction lines.
- Count opcodes from disassembly lines matching `^\s*[0-9a-f]+:`.
- Treat opcodes beginning with `j` as branches, opcode `call` as calls, and opcode `ret` as returns.
- Extract decimal/hex immediates with a regex from operand text.
- Use `/usr/bin/nm --defined-only object.o` to collect defined symbols.
- Distance components:
  - `instruction_count_abs`: absolute instruction-count difference.
  - `branch_count_abs`: absolute branch-count difference.
  - `call_count_abs`: absolute call-count difference.
  - `ret_count_abs`: absolute ret-count difference.
  - `opcode_l1`: L1 distance over opcode counts.
  - `immediate_symmetric_diff`: count of immediates present in only one vector.
  - `symbol_symmetric_diff`: count of symbols present in only one vector.
- `total` is the sum of all components with unit weights for Phase 1A.

- [ ] **Step 4: Verify feature tests pass**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_features.py
```

Expected: `OK`.

- [ ] **Step 5: Commit Task 4**

```bash
git add analysis/decompile_faithfulness/features.py tests/test_decompile_faithfulness_features.py docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
git commit -m "analysis: extract binary faithfulness features"
```

---

### Task 5: Phase 1A Candidate-C Ranking Audit

**Files:**
- Create: `analysis/decompile_faithfulness/ranking.py`
- Create: `analysis/decompile_faithfulness/report.py`
- Create: `analysis/decompile_faithfulness/run_candidate_ranking_audit.py`
- Test: `tests/test_decompile_faithfulness_ranking.py`
- Create generated: `docs/paper_agent/decompile_faithfulness_phase1_audit.json`
- Create generated: `docs/paper_agent/decompile_faithfulness_phase1_audit.md`
- Create generated: `docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md`

- [ ] **Step 1: Write failing ranking tests**

Create `tests/test_decompile_faithfulness_ranking.py`:

```python
from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import ranking


class DecompileFaithfulnessRankingTest(unittest.TestCase):
    def test_rank_candidates_orders_low_distance_first(self) -> None:
        rows = [
            ranking.CandidateDistance(case_id="a", candidate_id="wrong", label="plausible_wrong", distance=3.0, mutation_type="predicate"),
            ranking.CandidateDistance(case_id="a", candidate_id="faithful", label="faithful", distance=0.0, mutation_type="original"),
        ]
        ranked = ranking.rank_candidates(rows)
        self.assertEqual([row.candidate_id for row in ranked], ["faithful", "wrong"])

    def test_compute_ranking_summary_counts_top1_success(self) -> None:
        rows = [
            ranking.CandidateDistance(case_id="a", candidate_id="faithful", label="faithful", distance=0.0, mutation_type="original"),
            ranking.CandidateDistance(case_id="a", candidate_id="wrong", label="plausible_wrong", distance=2.0, mutation_type="predicate"),
            ranking.CandidateDistance(case_id="b", candidate_id="wrong", label="plausible_wrong", distance=1.0, mutation_type="constant"),
            ranking.CandidateDistance(case_id="b", candidate_id="faithful", label="faithful", distance=3.0, mutation_type="original"),
        ]
        summary = ranking.compute_ranking_summary(rows)
        self.assertEqual(summary["case_count"], 2)
        self.assertEqual(summary["top1_faithful_count"], 1)
        self.assertAlmostEqual(summary["top1_faithful_rate"], 0.5)
        self.assertEqual(summary["by_mutation_type"]["predicate"]["candidate_count"], 1)
        self.assertEqual(summary["by_mutation_type"]["constant"]["candidate_count"], 1)

    def test_pairwise_auc_handles_ties_as_half_credit(self) -> None:
        rows = [
            ranking.CandidateDistance(case_id="a", candidate_id="faithful", label="faithful", distance=1.0, mutation_type="original"),
            ranking.CandidateDistance(case_id="a", candidate_id="wrong1", label="plausible_wrong", distance=2.0, mutation_type="predicate"),
            ranking.CandidateDistance(case_id="a", candidate_id="wrong2", label="plausible_wrong", distance=1.0, mutation_type="constant"),
        ]
        self.assertAlmostEqual(ranking.pairwise_auc(rows), 0.75)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing ranking test**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_ranking.py
```

Expected: import failure for `analysis.decompile_faithfulness.ranking`.

- [ ] **Step 3: Implement ranking and reporting**

Create `analysis/decompile_faithfulness/ranking.py` with:

- `CandidateDistance(case_id, candidate_id, label, distance, mutation_type)` dataclass.
- `rank_candidates(rows: list[CandidateDistance]) -> list[CandidateDistance]`.
- `pairwise_auc(rows: list[CandidateDistance]) -> float`.
- `compute_ranking_summary(rows: list[CandidateDistance]) -> dict[str, object]`.

Create `analysis/decompile_faithfulness/report.py` with:

- `write_json(path: Path, payload: dict[str, object]) -> None`.
- `write_markdown(path: Path, payload: dict[str, object]) -> None`.

Markdown must include:

- research question,
- dataset summary,
- candidate counts,
- top-1 faithful rate,
- pairwise AUC,
- mutation-type bucket table,
- kill-criterion verdict.

- [ ] **Step 4: Implement the Phase 1A CLI**

Create `analysis/decompile_faithfulness/run_candidate_ranking_audit.py` with CLI defaults:

```bash
--output-json docs/paper_agent/decompile_faithfulness_phase1_audit.json
--output-md docs/paper_agent/decompile_faithfulness_phase1_audit.md
--artifact-dir analysis_outputs/decompile_faithfulness/phase1a
--opt-level O0
```

The CLI must:

1. Load `fixtures.builtin_cases()`.
2. Compile each original case as `label="faithful"` and `mutation_type="original"`.
3. Generate rule mutations.
4. Compile each mutation.
5. Exclude mutations that fail compilation from ranking and count them in `excluded_compile_fail`.
6. Keep behavior-passing mutations in a separate `equivalent_or_weak` bucket, not in `plausible_wrong`.
7. Rank only `faithful` versus behavior-failing, compile-passing `plausible_wrong` candidates.
8. Extract binary features from each object file.
9. Compare every candidate to the original object's feature vector for the same case.
10. Write JSON, Markdown, and `records.jsonl`.

Kill criterion in this first audit:

```text
continue = pairwise_auc >= 0.75 and top1_faithful_rate >= 0.67
kill_core_method = pairwise_auc < 0.60 or top1_faithful_rate < 0.50
inconclusive = all other outcomes
```

- [ ] **Step 5: Run tests for ranking stack**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest \
  tests/test_decompile_faithfulness_fixtures.py \
  tests/test_decompile_faithfulness_compile.py \
  tests/test_decompile_faithfulness_mutations.py \
  tests/test_decompile_faithfulness_features.py \
  tests/test_decompile_faithfulness_ranking.py
```

Expected: all tests exit `0`.

- [ ] **Step 6: Run the Phase 1A audit**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_candidate_ranking_audit
```

Expected:

- JSON is written to `docs/paper_agent/decompile_faithfulness_phase1_audit.json`.
- Markdown is written to `docs/paper_agent/decompile_faithfulness_phase1_audit.md`.
- Artifact JSONL is written to `analysis_outputs/decompile_faithfulness/phase1a/records.jsonl`.
- No GPU or network access is used.

- [ ] **Step 7: Add the Chinese audit summary**

Create `docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md` as a faithful Chinese summary of the generated English Markdown. Include the same numbers, the same kill-criterion verdict, and a short note that this is a controlled mutation-style audit rather than a full decompilation system.

- [ ] **Step 8: Commit Task 5**

```bash
git add \
  analysis/decompile_faithfulness/ranking.py \
  analysis/decompile_faithfulness/report.py \
  analysis/decompile_faithfulness/run_candidate_ranking_audit.py \
  tests/test_decompile_faithfulness_ranking.py \
  docs/paper_agent/decompile_faithfulness_phase1_audit.json \
  docs/paper_agent/decompile_faithfulness_phase1_audit.md \
  docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md \
  analysis_outputs/decompile_faithfulness/phase1a/records.jsonl \
  docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
git commit -m "analysis: add binary feature ranking audit"
```

### Task 5.1: Operand-Sensitive Feature Follow-Up

**Files:**
- Modify: `analysis/decompile_faithfulness/features.py`
- Modify: `analysis/decompile_faithfulness/report.py`
- Modify: `tests/test_decompile_faithfulness_features.py`
- Regenerate: `docs/paper_agent/decompile_faithfulness_phase1_audit.json`
- Regenerate: `docs/paper_agent/decompile_faithfulness_phase1_audit.md`
- Modify: `docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md`
- Regenerate: `analysis_outputs/decompile_faithfulness/phase1a/records.jsonl`

- [x] **Step 1: Investigate zero-distance return-value failure**

Compare `objdump -d` for `absdiff__original__O0.function.o` and `absdiff__mut_return_a_minus_b_to_b_minus_a__O0.function.o`.

Finding: opcode counts, instruction counts, and immediate sets match, but operand order differs in the first return block. The original metric dropped operand-sensitive instruction signatures, so it assigned `distance=0.0` to a behavior-changing return-value mutation.

- [x] **Step 2: Write failing regression test**

Add `test_feature_distance_detects_operand_order_return_change` to `tests/test_decompile_faithfulness_features.py`.

Expected before fix: failure with `AssertionError: 0.0 not greater than 0.0`.

- [x] **Step 3: Implement minimal feature fix**

Add `instruction_signature_counts` to `BinaryFeatureVector`, normalize disassembly operands, and add `instruction_signature_l1` to `feature_distance`.

- [x] **Step 4: Regenerate audit**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_candidate_ranking_audit
```

Expected after fix: `pairwise_auc=1.0`, `top1_faithful_rate=1.0`, `verdict=continue` on the controlled Phase 1A mutation set.

---

### Task 6: Phase 1B Realistic Negatives Input Format

**Files:**
- Modify: `analysis/decompile_faithfulness/run_candidate_ranking_audit.py`
- Modify: `analysis/decompile_faithfulness/ranking.py`
- Test: `tests/test_decompile_faithfulness_ranking.py`
- Create docs: `docs/paper_agent/decompile_faithfulness_candidate_format.md`

- [ ] **Step 1: Extend ranking tests for external candidates**

Append this test to `tests/test_decompile_faithfulness_ranking.py`:

```python
    def test_load_external_candidate_manifest(self) -> None:
        manifest = {
            "case_id": "absdiff",
            "candidates": [
                {
                    "candidate_id": "ghidra_like_wrong",
                    "label": "unknown",
                    "mutation_type": "external_decompiler",
                    "function_source": "int absdiff(int a, int b) { return a - b; }",
                }
            ],
        }
        rows = ranking.external_candidates_from_manifest(manifest)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].case_id, "absdiff")
        self.assertEqual(rows[0].candidate_id, "ghidra_like_wrong")
        self.assertEqual(rows[0].label, "unknown")
        self.assertEqual(rows[0].mutation_type, "external_decompiler")
```

- [ ] **Step 2: Run the failing test**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_ranking.py
```

Expected: failure for missing `external_candidates_from_manifest`.

- [ ] **Step 3: Implement external candidate loading**

Add to `analysis/decompile_faithfulness/ranking.py`:

- `ExternalCandidate(case_id, candidate_id, label, mutation_type, function_source)` dataclass.
- `external_candidates_from_manifest(manifest: dict[str, object]) -> list[ExternalCandidate]`.

Validation rules:

- `case_id` must match a known fixture.
- `candidate_id`, `label`, `mutation_type`, and `function_source` must be non-empty strings.
- Allowed labels: `unknown`, `faithful`, `plausible_wrong`.
- External candidates with `label="unknown"` must be compiled and behavior-gated before being used for ranking.

- [ ] **Step 4: Extend the CLI**

Add CLI option:

```bash
--external-candidates-json path/to/candidates.json
```

The JSON format:

```json
[
  {
    "case_id": "absdiff",
    "candidates": [
      {
        "candidate_id": "llm_candidate_001",
        "label": "unknown",
        "mutation_type": "llm_generated",
        "function_source": "int absdiff(int a, int b) { if (a > b) return a - b; return b - a; }"
      }
    ]
  }
]
```

When provided, the CLI must include these candidates in the same compile, behavior, feature, and ranking pipeline. Report them in separate `mutation_type` buckets so controlled mutations and realistic negatives are not merged.

- [ ] **Step 5: Document candidate format**

Create `docs/paper_agent/decompile_faithfulness_candidate_format.md` with:

- JSON schema shown above.
- Label semantics.
- Rule that `unknown` labels are assigned by compile/behavior gates.
- Instructions for adding Ghidra/RetDec/angr or LLM outputs later without changing Phase 1A code.

- [ ] **Step 6: Verify external candidate support**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_ranking.py
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_candidate_ranking_audit
```

Expected: tests pass and the default Phase 1A audit still runs without an external manifest.

- [ ] **Step 7: Commit Task 6**

```bash
git add \
  analysis/decompile_faithfulness/ranking.py \
  analysis/decompile_faithfulness/run_candidate_ranking_audit.py \
  tests/test_decompile_faithfulness_ranking.py \
  docs/paper_agent/decompile_faithfulness_candidate_format.md \
  docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
git commit -m "analysis: support realistic decompilation negatives"
```

---

### Task 7: Phase 1C Slot-Level Localization

**Files:**
- Create: `analysis/decompile_faithfulness/localization.py`
- Create: `analysis/decompile_faithfulness/run_slot_localization_audit.py`
- Test: `tests/test_decompile_faithfulness_localization.py`
- Create generated: `analysis_outputs/decompile_faithfulness/phase1c/localization_records.jsonl`

- [ ] **Step 1: Write failing localization tests**

Create `tests/test_decompile_faithfulness_localization.py`:

```python
from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import localization


class DecompileFaithfulnessLocalizationTest(unittest.TestCase):
    def test_component_to_slot_votes_maps_expected_components(self) -> None:
        components = {
            "branch_count_abs": 1.0,
            "opcode_l1": 4.0,
            "immediate_symmetric_diff": 0.0,
            "call_count_abs": 0.0,
        }
        votes = localization.component_to_slot_votes(components)
        self.assertGreater(votes["branch_predicate"], votes["constant"])
        self.assertGreater(votes["control_structure"], 0.0)

    def test_localization_hit_at_k(self) -> None:
        ranked = ["branch_predicate", "control_structure", "constant"]
        self.assertTrue(localization.hit_at_k(ranked, "branch_predicate", 1))
        self.assertFalse(localization.hit_at_k(ranked, "constant", 2))
        self.assertTrue(localization.hit_at_k(ranked, "constant", 3))

    def test_localization_summary_counts_hits(self) -> None:
        rows = [
            localization.LocalizationRecord("a", "mut1", "branch_predicate", ["branch_predicate", "constant"]),
            localization.LocalizationRecord("a", "mut2", "constant", ["branch_predicate", "constant"]),
        ]
        summary = localization.compute_localization_summary(rows)
        self.assertEqual(summary["record_count"], 2)
        self.assertAlmostEqual(summary["hit_at_1"], 0.5)
        self.assertAlmostEqual(summary["hit_at_2"], 1.0)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the failing localization test**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_localization.py
```

Expected: import failure for `analysis.decompile_faithfulness.localization`.

- [ ] **Step 3: Implement localization helpers**

Create `analysis/decompile_faithfulness/localization.py` with:

- `LocalizationRecord(case_id, candidate_id, expected_slot, ranked_slots)` dataclass.
- `component_to_slot_votes(components: dict[str, float]) -> dict[str, float]`.
- `rank_slots(votes: dict[str, float]) -> list[str]`.
- `hit_at_k(ranked_slots: list[str], expected_slot: str, k: int) -> bool`.
- `compute_localization_summary(records: list[LocalizationRecord]) -> dict[str, object]`.

Initial component-to-slot mapping:

- `branch_count_abs` and branch opcode deltas vote for `branch_predicate` and `control_structure`.
- `immediate_symmetric_diff` votes for `constant`.
- `call_count_abs` votes for `api_call`.
- `instruction_count_abs` and `opcode_l1` vote weakly for `control_structure`.
- `ret_count_abs` votes for `return_value`.

- [ ] **Step 4: Implement slot localization CLI**

Create `analysis/decompile_faithfulness/run_slot_localization_audit.py`.

The CLI must:

1. Reuse the same fixtures and rule mutations as Phase 1A.
2. Compile original and mutation candidates.
3. Extract feature distances.
4. Convert feature-distance components to ranked slots.
5. Compare ranked slots with `MutationCandidate.expected_slot`.
6. Write `analysis_outputs/decompile_faithfulness/phase1c/localization_records.jsonl`.
7. Print summary with `hit_at_1`, `hit_at_2`, and `hit_at_3`.

Phase 1C continue criterion:

```text
continue_to_sketch_localization = hit_at_3 >= 0.70
do_not_claim_localization = hit_at_3 < 0.50
```

- [ ] **Step 5: Verify localization tests and run CLI**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest tests/test_decompile_faithfulness_localization.py
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_slot_localization_audit
```

Expected: tests pass and CLI writes localization records without GPU or network access.

- [ ] **Step 6: Commit Task 7**

```bash
git add \
  analysis/decompile_faithfulness/localization.py \
  analysis/decompile_faithfulness/run_slot_localization_audit.py \
  tests/test_decompile_faithfulness_localization.py \
  analysis_outputs/decompile_faithfulness/phase1c/localization_records.jsonl \
  docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
git commit -m "analysis: add binary feature slot localization audit"
```

---

### Task 8: Phase 1D Real-Project Transfer Design Gate

**Files:**
- Create: `docs/paper_agent/decompile_faithfulness_real_project_transfer.md`
- Modify: `docs/paper_agent/decompile_faithfulness_phase1_audit.md`
- Modify: `docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md`

- [ ] **Step 1: Write the transfer design note**

Create `docs/paper_agent/decompile_faithfulness_real_project_transfer.md` with:

```markdown
# Decompilation Faithfulness Real-Project Transfer Gate

## Purpose

The source-known benchmark audit is only a signal test. Real-project transfer is required before claiming that recompiled binary feature distance helps realistic decompilation.

## Entry Criteria

- Phase 1A is not killed by the ranking criterion.
- Phase 1B includes at least one realistic negative source: LLM output, decompiler output, or manually written hard negative.
- The compile and feature extraction stack is deterministic on the current machine.

## First Real Projects

Use small, buildable C projects before large dependency-heavy systems:

1. `coreutils`-style standalone utility functions if source and build flags are easy to isolate.
2. `sqlite` small helper functions only after the standalone path works.
3. Crypto or compression libraries only after optimization-level transfer is stable.

## Required Controls

- GCC `O0` and `O2`.
- Same source compiled twice to measure feature extractor noise.
- At least one behavior-changing mutation per selected function.
- At least one behavior-preserving source rewrite per selected function.

## Kill Criteria

- Same-source recompile feature distance is not near zero under fixed compiler flags.
- Behavior-changing hard negatives are not separable from faithful rewrites.
- Function extraction or build-system complexity dominates the experiment.

## Output

Write a separate implementation plan for real-project extraction after this gate passes.
```

- [ ] **Step 2: Update Phase 1 audit docs**

In `docs/paper_agent/decompile_faithfulness_phase1_audit.md` and `.zh.md`, add a short "Next Gate" section that points to `docs/paper_agent/decompile_faithfulness_real_project_transfer.md` and states whether Phase 1A/1B results are strong enough to enter real-project transfer.

- [ ] **Step 3: Verify docs**

Run:

```bash
git diff --check -- docs/paper_agent/decompile_faithfulness_phase1_audit.md docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md docs/paper_agent/decompile_faithfulness_real_project_transfer.md
```

Expected: no whitespace errors.

- [ ] **Step 4: Commit Task 8**

```bash
git add \
  docs/paper_agent/decompile_faithfulness_real_project_transfer.md \
  docs/paper_agent/decompile_faithfulness_phase1_audit.md \
  docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md \
  docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
git commit -m "docs: define decompilation transfer gate"
```

---

### Task 9: Final Verification And Research Decision

**Files:**
- All files created in Tasks 1-8.
- Do not stage unrelated modified files already present in the worktree.

- [ ] **Step 1: Run focused tests**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m unittest \
  tests/test_decompile_faithfulness_fixtures.py \
  tests/test_decompile_faithfulness_compile.py \
  tests/test_decompile_faithfulness_mutations.py \
  tests/test_decompile_faithfulness_features.py \
  tests/test_decompile_faithfulness_ranking.py \
  tests/test_decompile_faithfulness_localization.py
```

Expected: all tests exit `0`.

- [ ] **Step 2: Run py_compile**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m py_compile \
  analysis/decompile_faithfulness/__init__.py \
  analysis/decompile_faithfulness/fixtures.py \
  analysis/decompile_faithfulness/compile.py \
  analysis/decompile_faithfulness/mutations.py \
  analysis/decompile_faithfulness/features.py \
  analysis/decompile_faithfulness/ranking.py \
  analysis/decompile_faithfulness/report.py \
  analysis/decompile_faithfulness/localization.py \
  analysis/decompile_faithfulness/run_candidate_ranking_audit.py \
  analysis/decompile_faithfulness/run_slot_localization_audit.py
```

Expected: command exits `0`.

- [ ] **Step 3: Regenerate Phase 1A and Phase 1C artifacts**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_candidate_ranking_audit
/home/shx/miniconda3/envs/dllm_env/bin/python -m analysis.decompile_faithfulness.run_slot_localization_audit
```

Expected:

- `docs/paper_agent/decompile_faithfulness_phase1_audit.json` exists.
- `docs/paper_agent/decompile_faithfulness_phase1_audit.md` exists.
- `docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md` exists.
- `analysis_outputs/decompile_faithfulness/phase1a/records.jsonl` exists.
- `analysis_outputs/decompile_faithfulness/phase1c/localization_records.jsonl` exists.

- [ ] **Step 4: Check JSON decision fields**

Run:

```bash
/home/shx/miniconda3/envs/dllm_env/bin/python - <<'PY'
import json
from pathlib import Path

path = Path("docs/paper_agent/decompile_faithfulness_phase1_audit.json")
payload = json.loads(path.read_text())
required = ["case_count", "candidate_count", "pairwise_auc", "top1_faithful_rate", "verdict"]
missing = [key for key in required if key not in payload]
if missing:
    raise SystemExit(f"missing keys: {missing}")
print({key: payload[key] for key in required})
PY
```

Expected: prints required fields and exits `0`.

- [ ] **Step 5: Run diff hygiene**

Run:

```bash
git diff --check -- \
  analysis/decompile_faithfulness \
  tests/test_decompile_faithfulness_fixtures.py \
  tests/test_decompile_faithfulness_compile.py \
  tests/test_decompile_faithfulness_mutations.py \
  tests/test_decompile_faithfulness_features.py \
  tests/test_decompile_faithfulness_ranking.py \
  tests/test_decompile_faithfulness_localization.py \
  docs/paper_agent/decompile_faithfulness_phase1_audit.json \
  docs/paper_agent/decompile_faithfulness_phase1_audit.md \
  docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md \
  docs/paper_agent/decompile_faithfulness_candidate_format.md \
  docs/paper_agent/decompile_faithfulness_real_project_transfer.md \
  docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
```

Expected: no whitespace errors.

- [ ] **Step 6: Make the research decision**

Read `docs/paper_agent/decompile_faithfulness_phase1_audit.md` and choose one of these decisions:

- `continue`: Phase 1A/1B ranking signal is strong enough to plan slot-aware sketch experiments and realistic decompiler/LLM negatives.
- `inconclusive`: Feature distance has some signal, but the candidate set is too small or too synthetic; add more cases before method claims.
- `kill-core-method`: Feature distance fails to distinguish faithful from plausible-wrong candidates; do not center Paper A on recompile-guided binary feature feedback.

Record the decision in the final section of the audit Markdown and Chinese audit Markdown.

- [ ] **Step 7: Commit final Phase 1 audit state**

Stage only the decompilation faithfulness files and this plan. Do not stage existing unrelated changes in `AGENTS.md`, DLLM runners, or prior paper-agent result docs unless they were intentionally updated by this plan.

```bash
git add \
  analysis/decompile_faithfulness \
  tests/test_decompile_faithfulness_fixtures.py \
  tests/test_decompile_faithfulness_compile.py \
  tests/test_decompile_faithfulness_mutations.py \
  tests/test_decompile_faithfulness_features.py \
  tests/test_decompile_faithfulness_ranking.py \
  tests/test_decompile_faithfulness_localization.py \
  docs/paper_agent/decompile_faithfulness_phase1_audit.json \
  docs/paper_agent/decompile_faithfulness_phase1_audit.md \
  docs/paper_agent/decompile_faithfulness_phase1_audit.zh.md \
  docs/paper_agent/decompile_faithfulness_candidate_format.md \
  docs/paper_agent/decompile_faithfulness_real_project_transfer.md \
  analysis_outputs/decompile_faithfulness/phase1a/records.jsonl \
  analysis_outputs/decompile_faithfulness/phase1c/localization_records.jsonl \
  docs/superpowers/plans/2026-06-11-binary-faithful-decompilation-phase1.md
git commit -m "analysis: audit binary-faithful decompilation signals"
```

---

## Self-Review

- Spec coverage: The plan covers Phase 1A candidate-C ranking, Phase 1B realistic negative input, Phase 1C slot-level localization, and Phase 1D real-project transfer gating.
- Contribution clarity: Paper A is not tied to DM. DM remains a later audit only if posterior sketch and binary feature guidance survive the ranking/localization gates.
- Kill criteria: The plan has explicit kill, continue, and inconclusive criteria for ranking and localization.
- Scope control: The first runnable audit is CPU-only and does not require GPU, LLM APIs, decompiler installations, or network access.
- Placeholder scan: No task depends on unspecified files or an undefined external service.
- Risk called out: Controlled mutation-style negatives are treated as a first-stage probe, not final decompilation evidence.
