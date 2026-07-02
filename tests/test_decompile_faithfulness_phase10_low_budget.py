from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import run_phase10_low_budget_rerun as phase10


class Phase10LowBudgetTest(unittest.TestCase):
    def test_budget_record_uses_prefix_outputs(self) -> None:
        source = {
            "case_id": "toy",
            "candidate_id": "cand",
            "label": "plausible_wrong",
            "compiled": True,
            "features": {"fixture_mismatch_rate": 0.0, "static_structured_total": 0.0},
        }
        inputs = [dynamic_trace.TraceInput((i,), "probe") for i in range(4)]
        original = trace_run("toy", "orig", (1, 2, 3, 4))
        candidate = trace_run("toy", "cand", (1, 2, 9, 9))
        k2 = phase10.budget_record(source, inputs, original, candidate, 2)
        k4 = phase10.budget_record(source, inputs, original, candidate, 4)
        self.assertEqual(k2["features"]["trace_mismatch_count"], 0.0)
        self.assertEqual(k4["features"]["trace_mismatch_count"], 2.0)

    def test_summarize_budget_reports_wrong_detection_rate(self) -> None:
        rows = [
            budgeted("a", "faithful", 0.0),
            budgeted("a", "plausible_wrong", 1.0),
            budgeted("b", "faithful", 0.0),
            budgeted("b", "plausible_wrong", 0.0),
        ]
        summary = phase10.summarize_budget(rows)
        self.assertEqual(summary["paired_case_count"], 2)
        self.assertEqual(summary["wrong_detection_rate"], 0.5)
        self.assertEqual(summary["mismatch_auc"], 0.75)

    def test_phase10_verdict_requires_auc_and_detection_gates(self) -> None:
        gate = {
            "phase7c2_budget8_auc_gate": True,
            "phase7c2_budget8_detection_gate": True,
            "phase6r_budget8_auc_gate": True,
            "phase6r_budget8_detection_gate": True,
        }
        self.assertEqual(phase10.phase10_verdict(gate), "pass-phase10-low-budget-rerun")
        gate["phase6r_budget8_detection_gate"] = False
        self.assertEqual(phase10.phase10_verdict(gate), "low-budget-rerun-partial")
        gate["phase6r_budget8_auc_gate"] = False
        self.assertEqual(phase10.phase10_verdict(gate), "low-budget-proxy-overestimated")


def trace_run(case_id: str, candidate_id: str, outputs: tuple[int, ...]) -> dynamic_trace.TraceRun:
    return dynamic_trace.TraceRun(
        case_id=case_id,
        candidate_id=candidate_id,
        compiled=True,
        exit_code=0,
        outputs=outputs,
        stdout="",
        stderr="",
        source_path=None,  # type: ignore[arg-type]
        exe_path=None,  # type: ignore[arg-type]
    )


def budgeted(case_id: str, label: str, mismatch_count: float) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": f"{case_id}_{label}",
        "label": label,
        "compiled": True,
        "requested_budget": 8,
        "actual_budget": 8,
        "features": {
            "trace_mismatch_count": mismatch_count,
            "trace_mismatch_rate": mismatch_count,
            "trace_total": mismatch_count,
            "fixture_mismatch_rate": mismatch_count,
            "static_structured_total": 0.0,
        },
    }


if __name__ == "__main__":
    unittest.main()
