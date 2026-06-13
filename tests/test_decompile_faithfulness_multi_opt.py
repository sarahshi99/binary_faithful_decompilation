from __future__ import annotations

import unittest

from analysis.decompile_faithfulness import run_multi_opt_slot_calibration_audit as multi_opt


class DecompileFaithfulnessMultiOptTest(unittest.TestCase):
    def test_aggregate_records_tracks_min_mean_max_and_range(self) -> None:
        records = multi_opt._aggregate_records(
            {
                "O0": [
                    _record("absdiff", "faithful", "faithful", 0.2),
                    _record("absdiff", "wrong", "plausible_wrong", 0.8),
                ],
                "O2": [
                    _record("absdiff", "faithful", "faithful", 0.4),
                    _record("absdiff", "wrong", "plausible_wrong", 0.6),
                ],
            }
        )
        by_id = {record["candidate_id"]: record for record in records}

        self.assertAlmostEqual(by_id["faithful"]["min_slot_concentration"], 0.2)
        self.assertAlmostEqual(by_id["faithful"]["mean_slot_concentration"], 0.3)
        self.assertAlmostEqual(by_id["faithful"]["max_slot_concentration"], 0.4)
        self.assertAlmostEqual(by_id["faithful"]["range_slot_concentration"], 0.2)
        self.assertAlmostEqual(
            multi_opt._pairwise_auc(records, "min_slot_concentration"),
            1.0,
        )


def _record(case_id: str, candidate_id: str, label: str, score: float) -> dict[str, object]:
    return {
        "case_id": case_id,
        "candidate_id": candidate_id,
        "label": label,
        "mutation_type": "manual",
        "slot_concentration": score,
    }


if __name__ == "__main__":
    unittest.main()
