from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import analyze_phase5_gpu_generated_full as analysis


class Phase5GpuGeneratedAnalysisTest(unittest.TestCase):
    def test_combine_runs_counts_pairs_and_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = {
                "function_count": 2,
                "source_projects": ["p"],
                "functions": [
                    {"case_id": "a", "project": "p"},
                    {"case_id": "b", "project": "p"},
                ],
            }
            manifest_path = root / "manifest.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            run_dir = root / "run"
            run_dir.mkdir()
            _write_jsonl(
                run_dir / "generation_metadata.jsonl",
                [
                    {"candidate_id": "a1", "cleaning_status": "parsed_function"},
                    {"candidate_id": "a2", "cleaning_status": "parsed_function"},
                    {"candidate_id": "b1", "cleaning_status": "parsed_function"},
                ],
            )
            _write_jsonl(
                run_dir / "records.jsonl",
                [
                    _record("a", "a1", "faithful", 0.0),
                    _record("a", "a2", "plausible_wrong", 1.0),
                    _record("b", "b1", "faithful", 0.0),
                ],
            )

            summary = analysis.combine_runs(
                repo_root=root,
                run_dirs=[run_dir],
                source_manifest=manifest_path,
                output_json=root / "summary.json",
                output_zh=root / "summary.zh.md",
                candidate_manifest_json=root / "candidates.json",
            )

        self.assertEqual(summary["generation_count"], 3)
        self.assertEqual(summary["compile_pass_count"], 3)
        self.assertEqual(summary["paired_case_count"], 1)
        self.assertEqual(summary["trace_pairwise_auc"], 1.0)
        self.assertEqual(summary["candidate_manifest_verdict"], "needs-full-candidate-generation")


def _record(case_id: str, candidate_id: str, label: str, trace_total: float) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "label": label,
        "mutation_type": "test",
        "compiled": True,
        "features": {
            "trace_total": trace_total,
            "trace_mismatch_rate": trace_total,
            "fixture_mismatch_rate": 0.0,
        },
        "metadata": {"function_source": "int f(int x) { return x; }"},
    }


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
