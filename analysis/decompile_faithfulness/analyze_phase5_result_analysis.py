from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu


DEFAULT_SOURCE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json")
DEFAULT_RECORD_PATHS = [
    Path("analysis_outputs/decompile_faithfulness/phase5_deterministic_candidates/records.jsonl"),
    Path("analysis_outputs/decompile_faithfulness/phase5_gpu_generated_full_cuda2_s0/records.jsonl"),
    Path("analysis_outputs/decompile_faithfulness/phase5_gpu_generated_full_cuda3_s1/records.jsonl"),
    Path("analysis_outputs/decompile_faithfulness/phase5_gpu_generated_full_cuda2_v2_full/records.jsonl"),
]
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase5_result_analysis.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase5_result_analysis.zh.md")
DEFAULT_CANDIDATE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_candidate_manifest.json")


def main() -> None:
    args = parse_args()
    summary = run_analysis(
        repo_root=args.repo_root,
        source_manifest=args.source_manifest,
        record_paths=args.records_jsonl or DEFAULT_RECORD_PATHS,
        output_json=args.output_json,
        output_zh=args.output_zh,
        candidate_manifest_json=args.candidate_manifest_json,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "candidate_count": summary["candidate_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "paired_case_count": summary["paired_case_count"],
                "v3_trace_total_auc": summary["baseline_auc"]["v3_trace_total"],
                "fixture_only_auc": summary["baseline_auc"]["fixture_only"],
                "sota_delta": summary["sota_delta_vs_best_non_oracle_baseline"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--records-jsonl", type=Path, action="append", default=None)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--candidate-manifest-json", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    return parser.parse_args()


def run_analysis(
    repo_root: Path,
    source_manifest: Path,
    record_paths: list[Path],
    output_json: Path,
    output_zh: Path,
    candidate_manifest_json: Path,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    source_manifest = _resolve(repo_root, source_manifest)
    record_paths = [_resolve(repo_root, path) for path in record_paths]
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    candidate_manifest_json = _resolve(repo_root, candidate_manifest_json)

    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    case_to_project = {
        entry["case_id"]: entry["project"]
        for entry in manifest.get("functions", [])
    }
    records: list[dict[str, Any]] = []
    missing_record_paths: list[str] = []
    for path in record_paths:
        if not path.exists():
            missing_record_paths.append(str(path))
            continue
        records.extend(_read_jsonl(path))
    records = dedupe_records(records)

    candidate_manifest = build_candidate_manifest(
        manifest=manifest,
        records=records,
        record_paths=record_paths,
    )
    _write_json(candidate_manifest_json, candidate_manifest)

    eval_records = [
        record for record in records
        if record.get("label") in {"faithful", "plausible_wrong"}
        and record.get("compiled")
        and "features" in record
    ]
    baseline_auc = {
        "fixture_only": pairwise_auc(eval_records, lambda r: float(r["features"].get("fixture_mismatch_rate", 1.0))),
        "v3_trace_mismatch_rate": pairwise_auc(eval_records, lambda r: float(r["features"].get("trace_mismatch_rate", 0.0))),
        "v3_trace_total": pairwise_auc(eval_records, lambda r: float(r["features"].get("trace_total", 0.0))),
    }
    best_non_oracle_baseline = baseline_auc["fixture_only"]
    sota_delta = baseline_auc["v3_trace_total"] - best_non_oracle_baseline
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest": str(source_manifest),
        "record_paths": [str(path) for path in record_paths],
        "missing_record_paths": missing_record_paths,
        "source_function_count": manifest.get("function_count", 0),
        "source_projects": manifest.get("source_projects", []),
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record.get("compiled")),
        "behavior_label_counts": _count_by(records, "label"),
        "paired_case_count": paired_case_count(records),
        "fixture_passing_wrong_count": fixture_passing_wrong_count(records),
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
        "baseline_auc": baseline_auc,
        "best_non_oracle_baseline": "fixture_only",
        "sota_delta_vs_best_non_oracle_baseline": sota_delta,
        "by_source_kind": grouped_metrics(records, lambda r: str(r.get("metadata", {}).get("source_kind", "unknown"))),
        "by_mutation_type": grouped_metrics(records, lambda r: str(r.get("mutation_type", "unknown"))),
        "by_project": grouped_metrics(records, lambda r: case_to_project.get(str(r.get("case_id")), "unknown")),
        "candidate_manifest_verdict": candidate_manifest["verdict"],
        "phase5_pass_gates": {
            "scale_gate": candidate_manifest["verdict"] == "pass-phase5-full-candidate-generation",
            "auc_gate": baseline_auc["v3_trace_total"] >= 0.85,
            "sota_delta_gate": sota_delta >= 0.05,
            "fixture_collapse_gate": not phase3_cpu.v1._fixture_collapse(eval_records),
            "fixture_passing_wrong_gate": fixture_passing_wrong_count(records) >= 5,
        },
    }
    summary["verdict"] = verdict(summary)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for record in records:
        key = (str(record.get("case_id")), str(record.get("candidate_id")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def build_candidate_manifest(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    record_paths: list[Path],
) -> dict[str, Any]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        if not record.get("compiled"):
            continue
        metadata = record.get("metadata", {})
        by_case[record["case_id"]].append(
            {
                "case_id": record["case_id"],
                "candidate_id": record["candidate_id"],
                "label": record["label"],
                "mutation_type": record.get("mutation_type", ""),
                "function_source": metadata.get("function_source", ""),
                "source_kind": metadata.get("source_kind", "unknown"),
                "source_name": metadata.get("source_name", ""),
                "prompt_id": metadata.get("prompt_id", ""),
                "raw_output_path": metadata.get("raw_output_path", ""),
                "cleaning_status": metadata.get("cleaning_status", "parsed_function"),
                "generation_index": metadata.get("generation_index", 0),
                "sampling": metadata.get("sampling", {}),
            }
        )
    compile_pass = sum(1 for record in records if record.get("compiled"))
    paired = paired_case_count(records)
    return {
        "phase": "phase5_candidate_generation_or_import",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest_function_count": manifest.get("function_count", 0),
        "candidate_layers": sorted({
            str(record.get("metadata", {}).get("source_kind", "unknown"))
            for record in records
        }),
        "candidate_count": len(records),
        "compile_pass_count": compile_pass,
        "compile_pass_target_min": 100,
        "compile_pass_target_range": [100, 200],
        "paired_function_count": paired,
        "paired_function_target_min": 20,
        "record_paths": [str(path) for path in record_paths],
        "candidates": [
            {"case_id": case_id, "candidates": candidates}
            for case_id, candidates in sorted(by_case.items())
        ],
        "verdict": (
            "pass-phase5-full-candidate-generation"
            if compile_pass >= 100 and paired >= 20
            else "needs-full-candidate-generation"
        ),
    }


def grouped_metrics(
    records: list[dict[str, Any]],
    key_fn: Callable[[dict[str, Any]], str],
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[key_fn(record)].append(record)
    return {
        key: basic_metrics(group_records)
        for key, group_records in sorted(grouped.items())
    }


def basic_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    eval_records = [
        record for record in records
        if record.get("label") in {"faithful", "plausible_wrong"}
        and record.get("compiled")
        and "features" in record
    ]
    return {
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record.get("compiled")),
        "label_counts": _count_by(records, "label"),
        "paired_case_count": paired_case_count(records),
        "fixture_passing_wrong_count": fixture_passing_wrong_count(records),
        "fixture_only_auc": pairwise_auc(eval_records, lambda r: float(r["features"].get("fixture_mismatch_rate", 1.0))),
        "v3_trace_total_auc": pairwise_auc(eval_records, lambda r: float(r["features"].get("trace_total", 0.0))),
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
    }


def pairwise_auc(
    records: list[dict[str, Any]],
    score: Callable[[dict[str, Any]], float],
) -> float:
    return phase3_cpu._pairwise_auc(records, score)


def paired_case_count(records: list[dict[str, Any]]) -> int:
    total = 0
    for case_id in sorted({record.get("case_id") for record in records}):
        labels = {
            record.get("label")
            for record in records
            if record.get("case_id") == case_id and record.get("compiled")
        }
        if "faithful" in labels and "plausible_wrong" in labels:
            total += 1
    return total


def fixture_passing_wrong_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1 for record in records
        if record.get("label") == "plausible_wrong"
        and record.get("compiled")
        and record.get("features", {}).get("fixture_mismatch_rate") == 0.0
    )


def verdict(summary: dict[str, Any]) -> str:
    gates = summary["phase5_pass_gates"]
    if summary["missing_record_paths"]:
        return "phase5-analysis-partial-waiting-for-records"
    if all(gates.values()):
        return "pass-phase5-start-phase6-planning"
    if gates["scale_gate"] and gates["auc_gate"] and not gates["sota_delta_gate"]:
        return "scale-positive-sota-delta-not-established"
    if gates["scale_gate"]:
        return "scale-positive-needs-hardcase-sota-analysis"
    return "needs-full-candidate-generation"


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(record.get(key, "")) for record in records))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown_zh(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gate_rows = "\n".join(
        f"| `{key}` | `{value}` |"
        for key, value in summary["phase5_pass_gates"].items()
    )
    source_rows = "\n".join(
        "| `{name}` | `{candidate_count}` | `{compile_pass_count}` | `{paired_case_count}` | `{fixture_passing_wrong_count}` | `{fixture_only_auc:.4f}` | `{v3_trace_total_auc:.4f}` |".format(
            name=name,
            **metrics,
        )
        for name, metrics in summary["by_source_kind"].items()
    )
    text = f"""# Decompilation Faithfulness Phase 5 Result Analysis

- Verdict: `{summary['verdict']}`
- Source functions: `{summary['source_function_count']}`
- Source projects: `{summary['source_projects']}`
- Candidates: `{summary['candidate_count']}`
- Compile pass count: `{summary['compile_pass_count']}`
- Behavior labels: `{summary['behavior_label_counts']}`
- Paired case count: `{summary['paired_case_count']}`
- Fixture-passing wrong count: `{summary['fixture_passing_wrong_count']}`
- Fixture-only AUC: `{summary['baseline_auc']['fixture_only']:.4f}`
- V3 trace total AUC: `{summary['baseline_auc']['v3_trace_total']:.4f}`
- SOTA delta vs best non-oracle baseline: `{summary['sota_delta_vs_best_non_oracle_baseline']:.4f}`
- Fixture collapse: `{summary['fixture_collapse']}`
- Candidate manifest verdict: `{summary['candidate_manifest_verdict']}`

## Gate Check

| Gate | Passed |
|---|---:|
{gate_rows}

## By Candidate Source

| Source Kind | Candidates | Compile Pass | Paired Cases | Fixture-passing Wrong | Fixture-only AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|---:|
{source_rows}

## Interpretation

Phase 5 的规模门槛可以由 deterministic candidate layer 支撑，但这不自动等价于 CCF-A/SOTA 贡献。当前最严格的问题是：如果 fixture-only baseline 已经能分开大部分 deterministic/manual stress wrong candidates，那么 V3 的机制优势还没有被充分证明。

因此后续应把注意力放在 fixture-passing wrong / subtle semantic drift 的候选分布上：LLM/decompiler candidates、targeted boundary bugs、以及 Phase 6 decompiler-output。只有当 V3 在这些更难候选上比 fixture-only 和其他 non-oracle baseline 至少高 `0.05` AUC，才可以写成强 SOTA contribution。
"""
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
