from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import structured_features


@dataclass(frozen=True)
class ObjectPaths:
    original: Path
    candidate: Path


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
        output_zh=args.output_zh,
        output_jsonl=args.output_jsonl,
    )
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-roots", nargs="+", type=Path, required=True)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.md"),
    )
    parser.add_argument(
        "--output-zh",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1j_structural_binding.zh.md"),
    )
    parser.add_argument(
        "--output-jsonl",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1j_structural_binding/records.jsonl"),
    )
    return parser.parse_args()


def run_audit(
    artifact_roots: list[Path],
    output_json: Path,
    output_md: Path,
    output_zh: Path,
    output_jsonl: Path,
) -> dict[str, Any]:
    records = _aggregate_records(artifact_roots)
    formulas = _formulas()
    formula_scores = _formula_scores(records, formulas)
    loco = _leave_one_case_out(records, formulas)
    hard_cases = ["signum", "gcd_positive", "max3", "sum_to_n"]
    hard_case_auc = {
        case_id: loco["case_pairwise_auc"].get(case_id, 0.0)
        for case_id in hard_cases
    }
    summary = {
        "artifact_roots": [str(path) for path in artifact_roots],
        "case_count": len({record["case_id"] for record in records}),
        "candidate_count": len(records),
        "faithful_count": sum(1 for record in records if record["label"] == "faithful"),
        "plausible_wrong_count": sum(1 for record in records if record["label"] == "plausible_wrong"),
        "baselines": {
            "phase1g_multi_opt_min_slot_auc": 0.7552,
            "phase1i_best_in_sample_auc": 0.7604,
            "phase1i_leave_one_case_out_auc": 0.6719,
        },
        "best_in_sample": formula_scores[0] if formula_scores else {"formula": "", "pairwise_auc": 0.0},
        "formula_scores": formula_scores,
        "leave_one_case_out": loco,
        "hard_case_auc": hard_case_auc,
        "records_path": str(output_jsonl),
        "verdict": _verdict(loco["pairwise_auc"], hard_case_auc),
    }
    _write_json(output_json, summary)
    _write_markdown(output_md, summary)
    _write_markdown_zh(output_zh, summary)
    _write_jsonl(output_jsonl, records)
    return summary


def _object_paths_for_record(
    artifact_root: Path,
    opt_level: str,
    record: dict[str, Any],
) -> ObjectPaths:
    opt_dir = artifact_root / opt_level.lower()
    candidates_dir = opt_dir / "candidates"
    case_id = str(record["case_id"])
    candidate_id = str(record["candidate_id"])
    return ObjectPaths(
        original=candidates_dir / f"{case_id}__original__{opt_level}.function.o",
        candidate=candidates_dir / f"{case_id}__{candidate_id}__{opt_level}.function.o",
    )


def _aggregate_records(
    artifact_roots: list[Path],
    distance_fn: Callable[[ObjectPaths], dict[str, float]] | None = None,
) -> list[dict[str, Any]]:
    distance = distance_fn or _structured_distance_for_paths
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for artifact_root in artifact_roots:
        for opt_level in ["O0", "O1", "O2", "O3"]:
            records_path = artifact_root / opt_level.lower() / "records.jsonl"
            if not records_path.exists():
                continue
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
                paths = _object_paths_for_record(artifact_root, opt_level, record)
                components = {
                    str(component): float(value)
                    for component, value in distance(paths).items()
                }
                item["by_opt"][opt_level] = {
                    "artifact_root": str(artifact_root),
                    "original_object": str(paths.original),
                    "candidate_object": str(paths.candidate),
                    "slot_concentration": float(record["slot_concentration"]),
                    "global_distance": float(record.get("global_distance", 0.0)),
                    "existing_components": {
                        str(component): float(value)
                        for component, value in record.get("components", {}).items()
                    },
                    "structured_components": components,
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
                "by_opt": item["by_opt"],
            }
        )
    return sorted(rows, key=lambda row: (row["case_id"], row["candidate_id"]))


def _structured_distance_for_paths(paths: ObjectPaths) -> dict[str, float]:
    original = _extract_structured_features_cached(paths.original)
    candidate = _extract_structured_features_cached(paths.candidate)
    return structured_features.structured_feature_distance(original, candidate)


@lru_cache(maxsize=None)
def _extract_structured_features_cached(path: Path) -> structured_features.StructuredFeatureVector:
    return structured_features.extract_structured_features(path)


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
            for component in opt["structured_components"]
        }
    )
    for component in component_names:
        values = [float(opt["structured_components"].get(component, 0.0)) for opt in by_opt.values()]
        features[f"min_{component}"] = min(values)
        features[f"mean_{component}"] = _mean(values)
        features[f"max_{component}"] = max(values)
        features[f"mean_squashed_{component}"] = _mean([_squash(value) for value in values])
        features[f"max_squashed_{component}"] = max(_squash(value) for value in values)
    features["structured_only"] = features.get("max_squashed_structured_binding_total", 0.0)
    return features


def _formulas() -> list[Formula]:
    return [
        Formula("structured_only", lambda f: f.get("structured_only", 0.0)),
        Formula("structured_binding_total", lambda f: f.get("max_squashed_structured_binding_total", 0.0)),
        Formula("min_slot", lambda f: f["min_slot"]),
        Formula("mean_slot", lambda f: f["mean_slot"]),
        Formula(
            "mean_slot_plus_structured_0.10",
            lambda f: f["mean_slot"] + 0.10 * f.get("max_squashed_structured_binding_total", 0.0),
        ),
        Formula(
            "mean_slot_plus_structured_0.25",
            lambda f: f["mean_slot"] + 0.25 * f.get("max_squashed_structured_binding_total", 0.0),
        ),
        Formula(
            "min_slot_plus_branch_return_0.10",
            lambda f: f["min_slot"] + 0.10 * f.get("max_squashed_branch_return_binding_l1", 0.0),
        ),
        Formula(
            "min_slot_plus_cfg_edge_0.10",
            lambda f: f["min_slot"] + 0.10 * f.get("max_squashed_cfg_edge_motif_l1", 0.0),
        ),
    ]


def _formula_scores(records: list[dict[str, Any]], formulas: list[Formula]) -> list[dict[str, Any]]:
    scores = [
        {
            "formula": formula.name,
            "pairwise_auc": _pairwise_auc(records, lambda record, formula=formula: formula.score(record["features"])),
        }
        for formula in formulas
    ]
    formula_order = {formula.name: index for index, formula in enumerate(formulas)}
    return sorted(scores, key=lambda row: (-row["pairwise_auc"], formula_order[row["formula"]]))


def _leave_one_case_out(records: list[dict[str, Any]], formulas: list[Formula]) -> dict[str, Any]:
    case_ids = sorted({record["case_id"] for record in records})
    formula_order = {formula.name: index for index, formula in enumerate(formulas)}
    folds: list[dict[str, Any]] = []
    heldout_scores: dict[tuple[str, str], float] = {}
    case_pairwise_auc: dict[str, float] = {}
    for case_id in case_ids:
        train = [record for record in records if record["case_id"] != case_id]
        heldout = [record for record in records if record["case_id"] == case_id]
        ranked = sorted(
            (
                (
                    _pairwise_auc(train, lambda record, formula=formula: formula.score(record["features"])),
                    formula_order[formula.name],
                    formula,
                )
                for formula in formulas
            ),
            key=lambda row: (-row[0], row[1]),
        )
        train_auc, _order, formula = ranked[0]
        heldout_auc = _pairwise_auc(heldout, lambda record, formula=formula: formula.score(record["features"]))
        folds.append(
            {
                "heldout_case": case_id,
                "selected_formula": formula.name,
                "train_pairwise_auc": train_auc,
                "heldout_pairwise_auc": heldout_auc,
            }
        )
        case_pairwise_auc[str(case_id)] = heldout_auc
        for record in heldout:
            heldout_scores[(record["case_id"], record["candidate_id"])] = formula.score(record["features"])

    auc = _pairwise_auc(
        records,
        lambda record: heldout_scores[(record["case_id"], record["candidate_id"])],
    )
    return {
        "pairwise_auc": auc,
        "folds": folds,
        "case_pairwise_auc": case_pairwise_auc,
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


def _verdict(loco_auc: float, hard_case_auc: dict[str, float]) -> str:
    hard_cases_pass = all(value >= 0.667 for value in hard_case_auc.values())
    hard_cases_below_kill = sum(1 for value in hard_case_auc.values() if value < 0.60)
    if loco_auc >= 0.80 and hard_cases_pass:
        return "continue-structured-binding"
    if loco_auc < 0.75 or hard_cases_below_kill >= 2:
        return "do-not-transfer-yet"
    return "borderline-structured-binding"


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
        "# Decompilation Faithfulness Phase 1J Structural Binding Audit",
        "",
        "## Dataset",
        "",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Faithful candidates: `{payload['faithful_count']}`",
        f"- Plausible-wrong candidates: `{payload['plausible_wrong_count']}`",
        "",
        "## Baselines",
        "",
        f"- Phase 1G multi-opt min slot AUC: `{payload['baselines']['phase1g_multi_opt_min_slot_auc']:.4f}`",
        f"- Phase 1I best in-sample AUC: `{payload['baselines']['phase1i_best_in_sample_auc']:.4f}`",
        f"- Phase 1I leave-one-case-out AUC: `{payload['baselines']['phase1i_leave_one_case_out_auc']:.4f}`",
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
            "## Hard Cases",
            "",
            "| Case | Held-out AUC |",
            "|---|---:|",
        ]
    )
    for case_id, auc in payload["hard_case_auc"].items():
        lines.append(f"| `{case_id}` | `{auc:.4f}` |")
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
                "This is a CPU-only source-known kill-gate. Labels are used for offline "
                "evaluation and formula selection only; structured feature extraction reads "
                "object-code paths without using candidate labels."
            ),
            "",
            "## Next Route",
            "",
            _next_route_en(payload),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown_zh(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 1J 结构绑定审计",
        "",
        "## 数据集",
        "",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Faithful candidates: `{payload['faithful_count']}`",
        f"- Plausible-wrong candidates: `{payload['plausible_wrong_count']}`",
        "",
        "## 基线",
        "",
        f"- Phase 1G multi-opt min slot AUC: `{payload['baselines']['phase1g_multi_opt_min_slot_auc']:.4f}`",
        f"- Phase 1I best in-sample AUC: `{payload['baselines']['phase1i_best_in_sample_auc']:.4f}`",
        f"- Phase 1I leave-one-case-out AUC: `{payload['baselines']['phase1i_leave_one_case_out_auc']:.4f}`",
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
            "## Hard Cases",
            "",
            "| Case | Held-out AUC |",
            "|---|---:|",
        ]
    )
    for case_id, auc in payload["hard_case_auc"].items():
        lines.append(f"| `{case_id}` | `{auc:.4f}` |")
    lines.extend(
        [
            "",
            "## 解释",
            "",
            (
                "这是 source-known kill-gate，不是 real-project transfer。"
                "标签只用于离线评估和 LOCO 公式选择；结构特征抽取只读取 object 文件路径。"
            ),
            "",
            "## 后续路线",
            "",
            _next_route_zh(payload),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _next_route_en(payload: dict[str, Any]) -> str:
    if payload["verdict"] == "continue-structured-binding":
        return (
            "The structured binding gate passed. The next step is a small transfer design "
            "that keeps the scope source-known/localized and tests whether these motifs "
            "survive on real decompiler candidates."
        )
    return (
        "The structured binding gate did not pass. Record Phase 1J as negative evidence "
        "for lightweight static binary motifs and pivot before real-project transfer: "
        "dynamic traces, symbolic traces, or a narrower localized-bug problem framing are "
        "better next candidates."
    )


def _next_route_zh(payload: dict[str, Any]) -> str:
    if payload["verdict"] == "continue-structured-binding":
        return (
            "结构绑定 gate 通过。下一步应设计一个小规模 transfer，仍然保持 source-known/localized "
            "范围，验证这些 motifs 在真实 decompiler candidates 上是否稳定。"
        )
    return (
        "结构绑定 gate 未通过。Phase 1J 应记录为 lightweight static binary motifs 的负结果；"
        "在 real-project transfer 前应先转向 dynamic trace、symbolic trace，或重新收窄为更明确的 "
        "localized-bug 问题。"
    )


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(record, sort_keys=True) for record in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
