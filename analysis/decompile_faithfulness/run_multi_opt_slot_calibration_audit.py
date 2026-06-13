from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_slot_calibration_audit


def main() -> None:
    args = parse_args()
    summary = run_audit(
        external_candidates_json=args.external_candidates_json,
        opt_levels=args.opt_levels,
        output_json=args.output_json,
        output_md=args.output_md,
        output_jsonl=args.output_jsonl,
        artifact_root=args.artifact_root,
    )
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-candidates-json", type=Path, required=True)
    parser.add_argument("--opt-levels", nargs="+", default=["O0", "O1", "O2", "O3"])
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1e_multi_opt_slot_calibration.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1e_multi_opt_slot_calibration.md"),
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1e_multi_opt_slot_calibration/records.jsonl"),
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1e_multi_opt_slot_calibration"),
    )
    return parser.parse_args()


def run_audit(
    external_candidates_json: Path,
    opt_levels: list[str],
    output_json: Path,
    output_md: Path,
    output_jsonl: Path,
    artifact_root: Path,
) -> dict[str, Any]:
    per_opt: dict[str, dict[str, Any]] = {}
    records_by_opt: dict[str, list[dict[str, Any]]] = {}

    for opt_level in opt_levels:
        opt_key = opt_level.lower()
        opt_dir = artifact_root / opt_key
        summary = run_slot_calibration_audit.run_audit(
            external_candidates_json=external_candidates_json,
            output_json=opt_dir / "summary.json",
            output_md=opt_dir / "summary.md",
            output_jsonl=opt_dir / "records.jsonl",
            artifact_dir=opt_dir / "candidates",
            opt_level=opt_level,
        )
        per_opt[opt_level] = summary
        records_by_opt[opt_level] = _read_jsonl(opt_dir / "records.jsonl")

    aggregate_records = _aggregate_records(records_by_opt)
    multi_opt = {
        "min_slot_concentration_auc": _pairwise_auc(aggregate_records, "min_slot_concentration"),
        "mean_slot_concentration_auc": _pairwise_auc(aggregate_records, "mean_slot_concentration"),
        "max_slot_concentration_auc": _pairwise_auc(aggregate_records, "max_slot_concentration"),
        "range_slot_concentration_auc": _pairwise_auc(aggregate_records, "range_slot_concentration"),
    }
    summary = {
        "candidate_manifest": str(external_candidates_json),
        "opt_levels": opt_levels,
        "case_count": len({record["case_id"] for record in aggregate_records}),
        "candidate_count": len(aggregate_records),
        "faithful_count": sum(1 for record in aggregate_records if record["label"] == "faithful"),
        "plausible_wrong_count": sum(1 for record in aggregate_records if record["label"] == "plausible_wrong"),
        "per_opt": per_opt,
        "multi_opt": multi_opt,
        "primary_score": "min_slot_concentration",
        "primary_pairwise_auc": multi_opt["min_slot_concentration_auc"],
        "verdict": _verdict(multi_opt["min_slot_concentration_auc"]),
        "records_path": str(output_jsonl),
    }
    _write_json(output_json, summary)
    _write_markdown(output_md, summary)
    _write_jsonl(output_jsonl, aggregate_records)
    return summary


def _aggregate_records(records_by_opt: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for opt_level, records in records_by_opt.items():
        for record in records:
            key = (str(record["case_id"]), str(record["candidate_id"]))
            slot_concentration = float(record["slot_concentration"])
            item = grouped.setdefault(
                key,
                {
                    "case_id": record["case_id"],
                    "candidate_id": record["candidate_id"],
                    "label": record["label"],
                    "mutation_type": record["mutation_type"],
                    "slot_concentration_by_opt": {},
                },
            )
            if item["label"] != record["label"]:
                raise ValueError(f"inconsistent label across opt levels for {key}")
            item["slot_concentration_by_opt"][opt_level] = slot_concentration

    aggregate_records = []
    for item in grouped.values():
        scores = list(item["slot_concentration_by_opt"].values())
        if not scores:
            continue
        item["min_slot_concentration"] = min(scores)
        item["mean_slot_concentration"] = sum(scores) / len(scores)
        item["max_slot_concentration"] = max(scores)
        item["range_slot_concentration"] = max(scores) - min(scores)
        aggregate_records.append(item)
    return sorted(aggregate_records, key=lambda row: (row["case_id"], row["candidate_id"]))


def _pairwise_auc(records: list[dict[str, Any]], score_key: str) -> float:
    credit = 0.0
    pairs = 0
    for case_id in sorted({record["case_id"] for record in records}):
        case_records = [record for record in records if record["case_id"] == case_id]
        faithful = [record for record in case_records if record["label"] == "faithful"]
        wrong = [record for record in case_records if record["label"] == "plausible_wrong"]
        for faithful_record in faithful:
            for wrong_record in wrong:
                pairs += 1
                wrong_score = float(wrong_record[score_key])
                faithful_score = float(faithful_record[score_key])
                if wrong_score > faithful_score:
                    credit += 1.0
                elif wrong_score == faithful_score:
                    credit += 0.5
    return credit / pairs if pairs else 0.0


def _verdict(primary_auc: float) -> str:
    if primary_auc >= 0.75:
        return "continue-with-multi-opt-calibration"
    if primary_auc < 0.60:
        return "redesign-multi-opt-calibration"
    return "weak-multi-opt-signal"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 1E Multi-Opt Slot Calibration",
        "",
        "## Metrics",
        "",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Faithful candidates: `{payload['faithful_count']}`",
        f"- Plausible-wrong candidates: `{payload['plausible_wrong_count']}`",
        f"- Opt levels: `{', '.join(payload['opt_levels'])}`",
        f"- Primary score: `{payload['primary_score']}`",
        f"- Primary pairwise AUC: `{payload['primary_pairwise_auc']:.4f}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "## Per-Opt Slot AUC",
        "",
        "| Opt | Slot AUC | Faithful mean | Wrong mean | Verdict |",
        "|---|---:|---:|---:|---|",
    ]
    for opt_level, summary in payload["per_opt"].items():
        lines.append(
            "| `{}` | `{:.4f}` | `{:.4f}` | `{:.4f}` | `{}` |".format(
                opt_level,
                summary["pairwise_slot_concentration_auc"],
                summary["mean_faithful_slot_concentration"],
                summary["mean_wrong_slot_concentration"],
                summary["verdict"],
            )
        )
    lines.extend(
        [
            "",
            "## Multi-Opt AUC",
            "",
            "| Aggregation | Pairwise AUC |",
            "|---|---:|",
        ]
    )
    for key, value in payload["multi_opt"].items():
        lines.append(f"| `{key}` | `{value:.4f}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "Use single optimization-level scores as diagnostics and use the minimum "
                "slot concentration across optimization levels as the primary suspicion score. "
                "This makes behavior-preserving rewrites less likely to be punished when one "
                "optimization level happens to produce locally concentrated binary drift."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
