from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from analysis.decompile_faithfulness import run_phase5_source_preflight as phase5


class Phase5SourcePreflightTest(unittest.TestCase):
    def test_extract_function_skips_prototype(self) -> None:
        source = """
int target(int x);

int helper(int x) { return x + 1; }

int target(int x)
{
    return helper(x) * 2;
}
"""
        extracted = phase5.extract_function(source, "target")
        self.assertIn("return helper(x) * 2;", extracted)
        self.assertNotIn("int target(int x);", extracted)

    def test_spec_pool_has_full_scale_shape(self) -> None:
        specs = phase5.phase5_specs()
        self.assertGreaterEqual(len(specs), 30)
        self.assertGreaterEqual(len({spec.project for spec in specs}), 2)
        self.assertTrue(any(spec.extraction_kind == "scalar_adapter" for spec in specs))

    def test_build_manifest_from_real_sources(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            manifest = phase5.build_manifest(
                repo_root=repo_root,
                source_dir=Path(tmp) / "sources",
            )
        self.assertEqual(manifest["verdict"], "pass-phase5-source-gate")
        self.assertGreaterEqual(manifest["phase5_real_project_eligible_function_count"], 30)
        self.assertGreaterEqual(len(manifest["source_projects"]), 2)
        self.assertFalse(manifest["extraction_errors"])


if __name__ == "__main__":
    unittest.main()
