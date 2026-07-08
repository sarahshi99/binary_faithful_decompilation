from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import tempfile
import unittest
from collections import Counter
from pathlib import Path

from analysis.decompile_faithfulness import phase3a_candidates as p3a
from analysis.decompile_faithfulness import phase3a_corpus as corpus
from analysis.decompile_faithfulness import phase3ar_recovery as p3ar


REPO_ROOT = Path(__file__).resolve().parents[3]


class Phase3arRecoveryTest(unittest.TestCase):
    def test_recovery_preregistration_precedes_matrix_and_candidate_seal(self) -> None:
        prereg = _commit_time("docs/paper_agent/phase3ar_producer_recovery_preregistration.md")
        matrix = _commit_time("results/decompile_faithfulness/phase3ar_recovery_matrix.csv")
        seal = _commit_time("analysis/decompile_faithfulness/phase3ar_candidate_seal.json")
        self.assertLessEqual(prereg, matrix)
        self.assertLessEqual(matrix, seal)

    def test_clang_recovery_record(self) -> None:
        record = _json("results/decompile_faithfulness/phase3ar_clang_recovery.json")
        self.assertEqual(record["producer_status"], "available")
        self.assertTrue(record["compile_ok"])
        self.assertTrue(record["symbol_found"])
        self.assertTrue(record["disassembly_found"])
        self.assertTrue(record["ghidra_consumed_binary"])
        self.assertTrue(record["angr_consumed_binary"])
        self.assertIn("clang version 17.0.6", record["clang_version"]["stdout_tail"])

    def test_llm4decompile_adapter_filters_token_type_ids(self) -> None:
        helper = p3a.llm_helper_source()
        self.assertIn('inputs.pop("token_type_ids", None)', helper)
        record = _json("results/decompile_faithfulness/phase3ar_llm4decompile_recovery.json")
        self.assertTrue(record["interface_only_change"])
        self.assertTrue(record["token_type_ids_filter_present"])
        self.assertFalse(record["prompt_template_changed"])
        self.assertFalse(record["decoding_parameters_changed"])
        self.assertFalse(record["dream_coder_used"])
        self.assertIn(record["producer_status"], {"available", "blocked"})

    def test_recovery_matrix_reconciliation(self) -> None:
        rows = _csv("results/decompile_faithfulness/phase3ar_recovery_matrix.csv")
        self.assertEqual(len(rows), 400)
        self.assertEqual(Counter(row["recovery_eligibility"] for row in rows), {"eligible": 240, "blocked": 160})
        self.assertEqual(Counter((row["producer"], row["build_view"], row["recovery_eligibility"]) for row in rows)[("llm4decompile", "gcc_O0", "blocked")], 80)
        self.assertEqual(Counter((row["producer"], row["build_view"], row["recovery_eligibility"]) for row in rows)[("llm4decompile", "clang_O2", "blocked")], 80)
        self.assertTrue(
            all(
                row["original_failure_reason"] in {"compiler_unavailable:clang", "llm4decompile_exception"}
                for row in rows
            )
        )

    def test_no_regeneration_of_successful_non_recovery_cells(self) -> None:
        matrix = {row["recovery_candidate_id"]: row for row in _csv("results/decompile_faithfulness/phase3ar_recovery_matrix.csv")}
        manifest = _jsonl("results/decompile_faithfulness/phase3ar_candidate_manifest.jsonl")
        self.assertEqual(len(manifest), 240)
        original_ids = {row["candidate_id"] for row in _jsonl("results/decompile_faithfulness/phase3a_candidate_manifest.jsonl")}
        for row in manifest:
            self.assertTrue(row["candidate_id"].startswith("phase3ar::"))
            self.assertNotIn(row["candidate_id"], original_ids)
            self.assertEqual(matrix[row["candidate_id"]]["recovery_eligibility"], "eligible")
            self.assertEqual(row["build_view"], "clang_O2")
            self.assertNotEqual(row["producer"], "llm4decompile")

    def test_recovered_neural_and_api_prompt_template_has_no_source_fixture_or_witness_leakage(self) -> None:
        function = _function(source="int f(int x) { return x + 777; }")
        with tempfile.TemporaryDirectory() as tmp:
            disassembly = Path(tmp) / "d.s"
            disassembly.write_text("0000 <f>:\n  add $0x1,%eax\n", encoding="utf-8")
            artifact = p3a.BuildArtifact(
                function_id=function.function_id,
                build_view="clang_O2",
                ok=True,
                source_path=Path(tmp) / "wrapper.c",
                binary_path=Path(tmp) / "f.exe",
                compiler_command=["clang"],
                compile_log_path=Path(tmp) / "compile.json",
                symbol_metadata_path=Path(tmp) / "symbols.json",
                disassembly_path=disassembly,
                binary_hash="abc",
            )
            prompts = [p3a.llm_prompt_payload(function, artifact)["prompt"], p3a.api_prompt_payload(function, artifact)["prompt"]]
        for prompt in prompts:
            self.assertIn("Required signature: int f(int x)", prompt)
            self.assertIn("Build view: clang_O2", prompt)
            self.assertNotIn("777", prompt)
            self.assertNotIn("fixture", prompt.lower())
            self.assertNotIn("witness", prompt.lower())
            self.assertNotIn("source_output", prompt)

    def test_candidate_seal_reproducibility(self) -> None:
        seal_path = REPO_ROOT / "analysis/decompile_faithfulness/phase3ar_candidate_seal.json"
        recorded = (REPO_ROOT / "analysis/decompile_faithfulness/phase3ar_candidate_seal.sha256").read_text(encoding="utf-8").split()[0]
        self.assertEqual(hashlib.sha256(seal_path.read_bytes()).hexdigest(), recorded)
        seal = json.loads(seal_path.read_text(encoding="utf-8"))
        self.assertEqual(seal["recovery_candidate_attempt_count"], 240)
        self.assertEqual(seal["semantic_labeling"], "not_run_at_candidate_seal_creation")

    def test_recovered_label_and_fixture_reconstruction(self) -> None:
        labels = _jsonl("results/decompile_faithfulness/phase3ar_exact_labels.jsonl")
        replay = _jsonl("results/decompile_faithfulness/phase3ar_fixture_replay.jsonl")
        self.assertEqual(len(labels), 240)
        self.assertEqual(Counter(row["label"] for row in labels)["semantic_wrong"], len(replay))
        self.assertEqual(Counter(row["fixture_replay_label"] for row in replay)["fixture_passing_semantic_wrong"], 1)
        for row in labels:
            if row["label"] == "semantic_wrong":
                self.assertTrue(row["first_mismatch_reproducible"])
                self.assertTrue(row["mismatch_trace_sha256"])

    def test_combined_census_reconciliation_and_gate_failure(self) -> None:
        manifest = _jsonl("results/decompile_faithfulness/phase3ar_combined_candidate_manifest.jsonl")
        labels = _jsonl("results/decompile_faithfulness/phase3ar_combined_exact_labels.jsonl")
        descriptors = _csv("results/decompile_faithfulness/phase3ar_combined_natural_error_descriptors.csv")
        self.assertEqual(len(manifest), 640)
        self.assertEqual(len(labels), 640)
        self.assertEqual(Counter(row["label"] for row in labels)["semantic_wrong"], 20)
        self.assertEqual(sum(1 for row in descriptors if row["counts_for_gate"] == "1"), 1)
        gate = p3a.census_gate(p3ar.gate_descriptors(descriptors))
        self.assertEqual(gate["minimum_gate_status"], "failed")
        self.assertFalse(gate["phase3b_authorized_for_review"])

    def test_guard_preventing_auditor_imports_or_execution(self) -> None:
        self.assertEqual(p3ar.guard_against_auditor_imports(), {"imports_ok": True, "calls_ok": True})


def _commit_time(path: str) -> int:
    result = subprocess.run(
        ["git", "log", "-1", "--format=%ct", "--", path],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        raise AssertionError(f"no commit found for {path}: {result.stderr}")
    return int(result.stdout.strip())


def _json(path: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))


def _jsonl(path: str) -> list[dict[str, object]]:
    return [json.loads(line) for line in (REPO_ROOT / path).read_text(encoding="utf-8").splitlines() if line.strip()]


def _csv(path: str) -> list[dict[str, str]]:
    with (REPO_ROOT / path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _function(*, source: str = "int f(int x) { return x; }") -> corpus.FunctionRecord:
    params = (corpus.Param("int", "x"),)
    return corpus.FunctionRecord(
        project="p",
        pool="primary",
        project_order=1,
        source_file="f.c",
        function_name="f",
        ordinal=1,
        return_type="int",
        params=params,
        source=source,
        support_source="",
        source_sha256=corpus.sha256_text(source),
        source_file_sha256=corpus.sha256_text(source),
        function_id="p::f",
        domain_values=(tuple(range(8)),),
        domain=tuple((x,) for x in range(8)),
        domain_size=8,
        features=corpus.structural_features(source, list(params)),
    )


if __name__ == "__main__":
    unittest.main()
