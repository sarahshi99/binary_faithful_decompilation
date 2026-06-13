from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


@dataclass(frozen=True)
class Formula:
    name: str
    score: Callable[[dict[str, float]], float]


def main() -> None:
    args = parse_args()
    summary = run_audit(
        artifact_roots=args.artifact_roots,
        output_json=args.output_json,
        output_md=args.output_md,
        output_jsonl=args.output_jsonl,
    )
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-roots", nargs="+", type=Path, required=True)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1i_component_combination.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1i_component_combination.md"),
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1i_component_combination/records.jsonl"),
    )
    return parser.parse_args()


def run_audit(
    artifact_roots: list[Path],
    output_json: Path,
    output_md: Path,
    output_jsonl: Path,
) -> dict[str, Any]:
    records = _aggregate_records(artifact_roots)
    formulas = _formulas()
    formula_scores = [
        {
            "formula": formula.name,
            "pairwise_auc": _pairwise_auc(records, lambda record, formula=formula: formula.score(record["features"])),
        }
        for formula in formulas
    ]
    formula_scores.sort(key=lambda row: (-row["pairwise_auc"], row["formula"]))
    loco = _leave_one_case_out(records, formulas)
    summary = {
        "artifact_roots": [str(path) for path in artifact_roots],
        "case_count": len({record["case_id"] for record in records}),
        "candidate_count": len(records),
        "faithful_count": sum(1 for record in records if record["label"] == "faithful"),
        "plausible_wrong_count": sum(1 for record in records if record["label"] == "plausible_wrong"),
        "best_in_sample": formula_scores[0],
        "formula_scores": formula_scores,
        "leave_one_case_out": loco,
        "records_path": str(output_jsonl),
        "verdict": _verdict(loco["pairwise_auc"]),
    }
    _write_json(output_json, summary)
    _write_markdown(output_md, summary)
    _write_jsonl(output_jsonl, records)
    return summary


def _aggregate_records(artifact_roots: list[Path]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for artifact_root in artifact_roots:
        for opt_level in ["O0", "O1", "O2", "O3"]:
            records_path = artifact_root / opt_level.lower() / "records.jsonl"
            for record in _read_jsonl(records_path):
                key = (str(record["case_id"]), str(record["candidate_id"]))
                item = grouped.setdefault(
                    key,
                    {
                        "case_id": record["case_id"],
                        "candidate_id": record["candidate_id"],
                        "label": record["label"],
                        "mutation_type": record["mutation_type"],
                        "by_opt": {},
                    },
                )
                if item["label"] != record["label"]:
                    raise ValueError(f"inconsistent label across opt levels for {key}")
                item["by_opt"][opt_level] = {
                    "slot_concentration": float(record["slot_concentration"]),
                    "global_distance": float(record["global_distance"]),
                    "components": {
                        str(component): float(value)
                        for component, value in record["components"].items()
                    },
                }

    rows = []
    for item in grouped.values():
        features = _features_from_by_opt(item["by_opt"])
        rows.append(
            {
                "case_id": item["case_id"],
                "candidate_id": item["candidate_id"],
                "label": item["label"],
                "mutation_type": item["mutation_type"],
                "features": features,
            }
        )
    return sorted(rows, key=lambda row: (row["case_id"], row["candidate_id"]))


def _features_from_by_opt(by_opt: dict[str, dict[str, Any]]) -> dict[str, float]:
    slot_scores = [opt["slot_concentration"] for opt in by_opt.values()]
    global_scores = [_squash(opt["global_distance"]) for opt in by_opt.values()]
    features = {
        "min_slot": min(slot_scores),
        "mean_slot": _mean(slot_scores),
        "max_slot": max(slot_scores),
        "range_slot": max(slot_scores) - min(slot_scores),
        "mean_global": _mean(global_scores),
        "max_global": max(global_scores),
    }
    component_names = sorted(
        {
            component
            for opt in by_opt.values()
            for component in opt["components"]
        }
    )
    for component in component_names:
        values = [_squash(opt["components"].get(component, 0.0)) for opt in by_opt.values()]
        features[f"mean_{component}"] = _mean(values)
        features[f"max_{component}"] = max(values)
    return features


def _formulas() -> list[Formula]:
    formulas = [
        Formula("min_slot", lambda f: f["min_slot"]),
        Formula("mean_slot", lambda f: f["mean_slot"]),
        Formula("max_slot", lambda f: f["max_slot"]),
        Formula("mean_slot_plus_range_0.10", lambda f: f["mean_slot"] + 0.10 * f["range_slot"]),
        Formula("mean_slot_plus_range_0.25", lambda f: f["mean_slot"] + 0.25 * f["range_slot"]),
        Formula(
            "mean_slot_plus_branch_return_0.10",
            lambda f: f["mean_slot"] + 0.10 * f.get("max_branch_return_immediate_pair_l1", 0.0),
        ),
        Formula(
            "mean_slot_plus_branch_return_0.25",
            lambda f: f["mean_slot"] + 0.25 * f.get("max_branch_return_immediate_pair_l1", 0.0),
        ),
        Formula(
            "mean_slot_plus_bigram_0.10",
            lambda f: f["mean_slot"] + 0.10 * f.get("max_instruction_bigram_l1", 0.0),
        ),
        Formula(
            "mean_slot_plus_bigram_0.25",
            lambda f: f["mean_slot"] + 0.25 * f.get("max_instruction_bigram_l1", 0.0),
        ),
        Formula(
            "mean_slot_plus_global_0.10",
            lambda f: f["mean_slot"] + 0.10 * f["max_global"],
        ),
        Formula(
            "mean_slot_plus_global_0.25",
            lambda f: f["mean_slot"] + 0.25 * f["max_global"],
        ),
    ]
    return formulas


def _leave_one_case_out(records: list[dict[str, Any]], formulas: list[Formula]) -> dict[str, Any]:
    case_ids = sorted({record["case_id"] for record in records})
    selected: list[dict[str, Any]] = []
    heldout_scores: dict[tuple[str, str], float] = {}
    for case_id in case_ids:
        train = [record for record in records if record["case_id"] != case_id]
        heldout = [record for record in records if record["case_id"] == case_id]
        ranked = sorted(
            (
                (
                    _pairwise_auc(train, lambda record, formula=formula: formula.score(record["features"])),
                    formula.name,
                    formula,
                )
                for formula in formulas
            ),
            key=lambda row: (-row[0], row[1]),
        )
        train_auc, _formula_name, formula = ranked[0]
        heldout_auc = _pairwise_auc(heldout, lambda record, formula=formula: formula.score(record["features"]))
        selected.append(
            {
                "heldout_case": case_id,
                "selected_formula": formula.name,
                "train_pairwise_auc": train_auc,
                "heldout_pairwise_auc": heldout_auc,
            }
        )
        for record in heldout:
            heldout_scores[(record["case_id"], record["candidate_id"])] = formula.score(record["features"])

    auc = _pairwise_auc(
        records,
        lambda record: heldout_scores[(record["case_id"], record["candidate_id"])],
    )
    return {
        "pairwise_auc": auc,
        "folds": selected,
    }


def _pairwise_auc(records: list[dict[str, Any]], score: Callable[[dict[str, Any]], float]) -> float:
    credit = 0.0
    pairs = 0
    for case_id in sorted({record["case_id"] for record in records}):
        case_records = [record for record in records if record["case_id"] == case_id]
        faithful = [record for record in case_records if record["label"] == "faithful"]
        wrong = [record for record in case_records if record["label"] == "plausible_wrong"]
        for faithful_record in faithful:
            for wrong_record in wrong:
                pairs += 1
                wrong_score = score(wrong_record)
                faithful_score = score(faithful_record)
                if wrong_score > faithful_score:
                    credit += 1.0
                elif wrong_score == faithful_score:
                    credit += 0.5
    return credit / pairs if pairs else 0.0


def _verdict(loco_auc: float) -> str:
    if loco_auc >= 0.80:
        return "continue-calibrated-combination"
    if loco_auc >= 0.75:
        return "borderline-calibrated-combination"
    return "do-not-transfer-yet"


def _squash(value: float) -> float:
    return value / (1.0 + value) if value > 0.0 else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 1I Component Combination Audit",
        "",
        "## Dataset",
        "",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Faithful candidates: `{payload['faithful_count']}`",
        f"- Plausible-wrong candidates: `{payload['plausible_wrong_count']}`",
        "",
        "## Best In-Sample Formula",
        "",
        f"- Formula: `{payload['best_in_sample']['formula']}`",
        f"- Pairwise AUC: `{payload['best_in_sample']['pairwise_auc']:.4f}`",
        "",
        "## Leave-One-Case-Out",
        "",
        f"- Pairwise AUC: `{payload['leave_one_case_out']['pairwise_auc']:.4f}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "| Held-out case | Selected formula | Train AUC | Held-out AUC |",
        "|---|---|---:|---:|",
    ]
    for fold in payload["leave_one_case_out"]["folds"]:
        lines.append(
            "| `{}` | `{}` | `{:.4f}` | `{:.4f}` |".format(
                fold["heldout_case"],
                fold["selected_formula"],
                fold["train_pairwise_auc"],
                fold["heldout_pairwise_auc"],
            )
        )
    lines.extend(
        [
            "",
            "## Formula Scores",
            "",
            "| Formula | Pairwise AUC |",
            "|---|---:|",
        ]
    )
    for row in payload["formula_scores"]:
        lines.append(f"| `{row['formula']}` | `{row['pairwise_auc']:.4f}` |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            (
                "This is a calibration audit over source-known cases, not a training claim. "
                "The leave-one-case-out result is the main guard against selecting a formula "
                "that only wins in-sample."
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
