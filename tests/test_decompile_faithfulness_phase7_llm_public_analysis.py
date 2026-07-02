from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import analyze_phase7_llm_public as analysis


class Phase7LlmPublicAnalysisTest(unittest.TestCase):
    def test_combine_runs_counts_pairs_and_auc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {
                "function_count": 2,
                "benchmark": "Demo",
                "functions": [
                    {"case_id": "a", "risk_families": ["branch"]},
                    {"case_id": "b", "risk_families": ["loop"]},
                ],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            run_dir = root / "run"
            run_dir.mkdir()
            write_jsonl(
                run_dir / "generation_metadata.jsonl",
                [
                    {"candidate_id": "a1", "cleaning_status": "parsed_function"},
                    {"candidate_id": "a2", "cleaning_status": "parsed_function"},
                    {"candidate_id": "b1", "cleaning_status": "parsed_function"},
                ],
            )
            write_jsonl(
                run_dir / "records.jsonl",
                [
                    record("a", "a1", "faithful", 0.0, 0.0, "strict_rewrite"),
                    record("a", "a2", "plausible_wrong", 1.0, 0.2, "strict_bug"),
                    record("b", "b1", "faithful", 0.0, 0.0, "strict_rewrite"),
                ],
            )
            summary = analysis.combine_runs(
                repo_root=root,
                run_dirs=[run_dir],
                source_manifest=manifest_path,
                output_json=root / "summary.json",
                output_zh=root / "summary.md",
                candidate_manifest_json=root / "candidates.json",
            )
        self.assertEqual(summary["generation_count"], 3)
        self.assertEqual(summary["paired_case_count"], 1)
        self.assertEqual(summary["baseline_auc"]["v3_trace_total"], 1.0)
        self.assertEqual(summary["by_prompt_id"]["strict_bug"]["candidate_count"], 1)

    def test_summary_verdict_reports_missing_runs(self) -> None:
        self.assertEqual(
            analysis.summary_verdict({"missing_inputs": ["x"], "gate": {}}),
            "phase7-llm-public-runs-missing",
        )

    def test_candidate_manifest_verdict_needs_scale(self) -> None:
        manifest = {"function_count": 2, "benchmark": "Demo"}
        payload = analysis.build_candidate_manifest(
            manifest=manifest,
            records=[record("a", "a1", "faithful", 0.0, 0.0, "strict_rewrite")],
            generation_records=[],
            run_dirs=[Path("run")],
        )
        self.assertEqual(payload["verdict"], "needs-more-phase7-llm-public-samples")


def record(
    case_id: str,
    candidate_id: str,
    label: str,
    trace_total: float,
    static_total: float,
    prompt_id: str,
) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "label": label,
        "mutation_type": f"phase7_llm_public_{prompt_id}",
        "compiled": True,
        "features": {
            "trace_total": trace_total,
            "trace_mismatch_rate": trace_total,
            "fixture_mismatch_rate": trace_total,
            "static_structured_total": static_total,
        },
        "metadata": {"prompt_id": prompt_id, "function_source": "int f(int x) { return x; }"},
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
