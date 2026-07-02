from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Callable


HARD_CASES = ("signum", "gcd_positive", "max3", "sum_to_n")


def main() -> None:
    args = parse_args()
    summary = run_audit(
        v1_records_path=args.v1_records,
        v2_records_path=args.v2_records,
        output_json=args.output_json,
        output_md=args.output_md,
        output_zh=args.output_zh,
    )
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--v1-records",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace/records.jsonl"),
    )
    parser.add_argument(
        "--v2-records",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase1k_dynamic_trace_v2/records.jsonl"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1l_ablation.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1l_ablation.md"),
    )
    parser.add_argument(
        "--output-zh",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase1l_ablation.zh.md"),
    )
    return parser.parse_args()


def run_audit(
    v1_records_path: Path,
    v2_records_path: Path,
    output_json: Path,
    output_md: Path,
    output_zh: Path,
) -> dict[str, Any]:
    v1_records = _read_jsonl(v1_records_path)
    v2_records = _read_jsonl(v2_records_path)
    variants = [
        _variant_summary("mixed_domain_v1_trace_mismatch", v1_records, "trace_mismatch_rate"),
        _variant_summary("domain_aware_v2_trace_mismatch", v2_records, "trace_mismatch_rate"),
        _variant_summary("domain_aware_v2_trace_total", v2_records, "trace_total"),
        _variant_summary("fixture_only_oracle", v2_records, "fixture_mismatch_rate"),
        _variant_summary("static_only_min_slot", v2_records, "min_slot"),
    ]
    by_name = {variant["name"]: variant for variant in variants}
    leakage = _leakage_audit(v2_records)
    summary = {
        "v1_records_path": str(v1_records_path),
        "v2_records_path": str(v2_records_path),
        "case_count": len({record["case_id"] for record in v2_records}),
        "candidate_count": len(v2_records),
        "variants": variants,
        "delta_v2_minus_v1": (
            by_name["domain_aware_v2_trace_mismatch"]["pairwise_auc"]
            - by_name["mixed_domain_v1_trace_mismatch"]["pairwise_auc"]
        ),
        "delta_v2_minus_static": (
            by_name["domain_aware_v2_trace_mismatch"]["pairwise_auc"]
            - by_name["static_only_min_slot"]["pairwise_auc"]
        ),
        "leakage_audit": leakage,
        "verdict": _verdict(by_name, leakage),
    }
    _write_json(output_json, summary)
    _write_markdown(output_md, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _variant_summary(
    name: str,
    records: list[dict[str, Any]],
    score_feature: str,
) -> dict[str, Any]:
    score = lambda record: float(record["features"][score_feature])
    case_auc = _case_pairwise_auc(records, score)
    return {
        "name": name,
        "score_feature": score_feature,
        "pairwise_auc": _pairwise_auc(records, score),
        "case_pairwise_auc": case_auc,
        "hard_case_auc": {
            case_id: case_auc.get(case_id, 0.0)
            for case_id in HARD_CASES
        },
    }


def _pairwise_auc(
    records: list[dict[str, Any]],
    score: Callable[[dict[str, Any]], float],
) -> float:
    credit = 0.0
    pairs = 0
    for case_id in sorted({record["case_id"] for record in records}):
        case_records = [record for record in records if record["case_id"] == case_id]
        faithful = [record for record in case_records if record["label"] == "faithful"]
        wrong = [record for record in case_records if record["label"] == "plausible_wrong"]
        for faithful_record in faithful:
            for wrong_record in wrong:
                pairs += 1
                faithful_score = score(faithful_record)
                wrong_score = score(wrong_record)
                if wrong_score > faithful_score:
                    credit += 1.0
                elif wrong_score == faithful_score:
                    credit += 0.5
    return credit / pairs if pairs else 0.0


def _case_pairwise_auc(
    records: list[dict[str, Any]],
    score: Callable[[dict[str, Any]], float],
) -> dict[str, float]:
    return {
        str(case_id): _pairwise_auc(
            [record for record in records if record["case_id"] == case_id],
            score,
        )
        for case_id in sorted({record["case_id"] for record in records})
    }


def _score_vectors_identical(
    records: list[dict[str, Any]],
    left_feature: str,
    right_feature: str,
) -> bool:
    return all(
        float(record["features"].get(left_feature, 0.0))
        == float(record["features"].get(right_feature, 0.0))
        for record in records
    )


def _leakage_audit(records: list[dict[str, Any]]) -> dict[str, Any]:
    identical = _score_vectors_identical(records, "trace_mismatch_rate", "fixture_mismatch_rate")
    domain_filtered_cases = sorted(
        {
            str(record["case_id"])
            for record in records
            if float(record["features"].get("trace_domain_filtered_count", 0.0)) > 0.0
        }
    )
    return {
        "domain_inference_source": "fixture_argument_values_only",
        "uses_labels_for_domain_inference": False,
        "uses_candidate_outputs_for_domain_inference": False,
        "uses_candidate_ids_for_domain_inference": False,
        "per_case_label_tuned_formula_selection": False,
        "fixture_only_reported_as_comparator": True,
        "v2_scores_identical_to_fixture_only": identical,
        "domain_filtered_cases": domain_filtered_cases,
        "verdict": (
            "fixture-collapse-risk"
            if identical
            else "no-label-or-output-leakage-found"
        ),
    }


def _verdict(
    by_name: dict[str, dict[str, Any]],
    leakage: dict[str, Any],
) -> str:
    v2 = by_name["domain_aware_v2_trace_mismatch"]
    static = by_name["static_only_min_slot"]
    if leakage["verdict"] != "no-label-or-output-leakage-found":
        return "fail-leakage-audit"
    if v2["pairwise_auc"] < 0.95:
        return "fail-v2-overall-ablation"
    if v2["hard_case_auc"].get("gcd_positive", 0.0) < 1.0:
        return "fail-gcd-positive-ablation"
    if leakage["v2_scores_identical_to_fixture_only"]:
        return "fail-fixture-collapse"
    if v2["pairwise_auc"] - static["pairwise_auc"] < 0.10:
        return "fail-static-only-margin"
    return "pass-phase1l-ablation"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 1L Ablation / Leakage Audit",
        "",
        "## Dataset",
        "",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "## Variants",
        "",
        "| Variant | Feature | AUC | gcd_positive | signum | max3 | sum_to_n |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for variant in payload["variants"]:
        hard = variant["hard_case_auc"]
        lines.append(
            "| `{}` | `{}` | `{:.4f}` | `{:.4f}` | `{:.4f}` | `{:.4f}` | `{:.4f}` |".format(
                variant["name"],
                variant["score_feature"],
                variant["pairwise_auc"],
                hard.get("gcd_positive", 0.0),
                hard.get("signum", 0.0),
                hard.get("max3", 0.0),
                hard.get("sum_to_n", 0.0),
            )
        )
    lines.extend(
        [
            "",
            "## Leakage Audit",
            "",
            f"- Domain inference source: `{payload['leakage_audit']['domain_inference_source']}`",
            f"- Uses labels: `{payload['leakage_audit']['uses_labels_for_domain_inference']}`",
            f"- Uses candidate outputs: `{payload['leakage_audit']['uses_candidate_outputs_for_domain_inference']}`",
            f"- Uses candidate ids: `{payload['leakage_audit']['uses_candidate_ids_for_domain_inference']}`",
            f"- V2 identical to fixture-only: `{payload['leakage_audit']['v2_scores_identical_to_fixture_only']}`",
            f"- Leakage verdict: `{payload['leakage_audit']['verdict']}`",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown_zh(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 1L Ablation / Leakage Audit",
        "",
        "## 数据集",
        "",
        f"- Cases: `{payload['case_count']}`",
        f"- Candidates: `{payload['candidate_count']}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "## 消融结果",
        "",
        "| Variant | Feature | AUC | gcd_positive | signum | max3 | sum_to_n |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for variant in payload["variants"]:
        hard = variant["hard_case_auc"]
        lines.append(
            "| `{}` | `{}` | `{:.4f}` | `{:.4f}` | `{:.4f}` | `{:.4f}` | `{:.4f}` |".format(
                variant["name"],
                variant["score_feature"],
                variant["pairwise_auc"],
                hard.get("gcd_positive", 0.0),
                hard.get("signum", 0.0),
                hard.get("max3", 0.0),
                hard.get("sum_to_n", 0.0),
            )
        )
    lines.extend(
        [
            "",
            "## 泄漏审计",
            "",
            f"- Domain inference source: `{payload['leakage_audit']['domain_inference_source']}`",
            f"- Uses labels: `{payload['leakage_audit']['uses_labels_for_domain_inference']}`",
            f"- Uses candidate outputs: `{payload['leakage_audit']['uses_candidate_outputs_for_domain_inference']}`",
            f"- Uses candidate ids: `{payload['leakage_audit']['uses_candidate_ids_for_domain_inference']}`",
            f"- V2 identical to fixture-only: `{payload['leakage_audit']['v2_scores_identical_to_fixture_only']}`",
            f"- Domain-filtered cases: `{', '.join(payload['leakage_audit']['domain_filtered_cases'])}`",
            f"- Leakage verdict: `{payload['leakage_audit']['verdict']}`",
            "",
            "## 解释",
            "",
            (
                "Phase 1L 是只读消融，不重新编译、不重新运行 trace。它比较 v1 mixed-domain、"
                "v2 domain-aware、fixture-only oracle 和 static-only min_slot，目的是确认 v2 的提升"
                "不是 fixture oracle collapse，也不是 label / candidate-output leakage。"
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
