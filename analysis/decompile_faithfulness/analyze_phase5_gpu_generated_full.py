from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu


DEFAULT_RUN_DIRS = [
    Path("analysis_outputs/decompile_faithfulness/phase5_gpu_generated_full_cuda2_s0"),
    Path("analysis_outputs/decompile_faithfulness/phase5_gpu_generated_full_cuda3_s1"),
]
DEFAULT_SOURCE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase5_gpu_generated_full_combined.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase5_gpu_generated_full_combined.zh.md")
DEFAULT_CANDIDATE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_candidate_manifest.json")


def main() -> None:
    args = parse_args()
    summary = combine_runs(
        repo_root=args.repo_root,
        run_dirs=args.run_dir or DEFAULT_RUN_DIRS,
        source_manifest=args.source_manifest,
        output_json=args.output_json,
        output_zh=args.output_zh,
        candidate_manifest_json=args.candidate_manifest_json,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "generation_count": summary["generation_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "paired_case_count": summary["paired_case_count"],
                "trace_pairwise_auc": summary["trace_pairwise_auc"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--run-dir", type=Path, action="append", default=None)
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--candidate-manifest-json", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    return parser.parse_args()


def combine_runs(
    repo_root: Path,
    run_dirs: list[Path],
    source_manifest: Path,
    output_json: Path,
    output_zh: Path,
    candidate_manifest_json: Path,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    run_dirs = [_resolve(repo_root, path) for path in run_dirs]
    source_manifest = _resolve(repo_root, source_manifest)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    candidate_manifest_json = _resolve(repo_root, candidate_manifest_json)

    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    case_to_project = {
        entry["case_id"]: entry["project"]
        for entry in manifest.get("functions", [])
    }
    generation_records: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    missing_inputs: list[str] = []
    for run_dir in run_dirs:
        generation_path = run_dir / "generation_metadata.jsonl"
        records_path = run_dir / "records.jsonl"
        if not generation_path.exists() or not records_path.exists():
            missing_inputs.append(str(run_dir))
            continue
        generation_records.extend(_read_jsonl(generation_path))
        records.extend(_read_jsonl(records_path))

    candidate_manifest = build_candidate_manifest(
        manifest=manifest,
        records=records,
        generation_records=generation_records,
        run_dirs=run_dirs,
    )
    _write_json(candidate_manifest_json, candidate_manifest)

    eval_records = [
        record for record in records
        if record.get("label") in {"faithful", "plausible_wrong"}
    ]
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dirs": [str(path) for path in run_dirs],
        "missing_inputs": missing_inputs,
        "source_manifest": str(source_manifest),
        "source_function_count": manifest.get("function_count", 0),
        "source_projects": manifest.get("source_projects", []),
        "generation_count": len(generation_records),
        "parsed_count": sum(
            1 for record in generation_records
            if record.get("cleaning_status") == "parsed_function"
        ),
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record.get("compiled")),
        "behavior_label_counts": _count_by(records, "label"),
        "cleaning_status_counts": _count_by(generation_records, "cleaning_status"),
        "paired_case_count": _paired_case_count(records),
        "fixture_passing_wrong_count": _fixture_passing_wrong_count(records),
        "trace_pairwise_auc": phase3_cpu._pairwise_auc(eval_records, phase3_cpu._trace_score),
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
        "case_label_counts": _case_label_counts(records),
        "project_label_counts": _project_label_counts(records, case_to_project),
        "candidate_manifest_verdict": candidate_manifest["verdict"],
    }
    summary["verdict"] = _summary_verdict(summary)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def build_candidate_manifest(
    manifest: dict[str, Any],
    records: list[dict[str, Any]],
    generation_records: list[dict[str, Any]],
    run_dirs: list[Path],
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
                "mutation_type": record["mutation_type"],
                "function_source": metadata.get("function_source", ""),
                "source_kind": metadata.get("source_kind", "local_llm"),
                "source_name": metadata.get("source_name", "Dream-Coder-v0-Instruct-7B"),
                "prompt_id": metadata.get("prompt_id", ""),
                "raw_output_path": metadata.get("raw_output_path", ""),
                "cleaning_status": metadata.get("cleaning_status", "parsed_function"),
                "generation_index": metadata.get("generation_index", 0),
                "sampling": metadata.get("sampling", {}),
            }
        )
    compile_pass_count = sum(1 for record in records if record.get("compiled"))
    paired_case_count = _paired_case_count(records)
    return {
        "phase": "phase5_candidate_generation_or_import",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_manifest_function_count": manifest.get("function_count", 0),
        "candidate_layers": ["llm_strict_rewrite", "llm_strict_bug"],
        "generation_count": len(generation_records),
        "candidate_count": len(records),
        "compile_pass_count": compile_pass_count,
        "compile_pass_target_min": 100,
        "compile_pass_target_range": [100, 200],
        "paired_function_count": paired_case_count,
        "paired_function_target_min": 20,
        "run_dirs": [str(path) for path in run_dirs],
        "candidates": [
            {"case_id": case_id, "candidates": candidates}
            for case_id, candidates in sorted(by_case.items())
        ],
        "verdict": _candidate_manifest_verdict(compile_pass_count, paired_case_count),
        "gpu_decision": "completed" if records else "not-completed",
    }


def _candidate_manifest_verdict(compile_pass_count: int, paired_case_count: int) -> str:
    if compile_pass_count >= 100 and paired_case_count >= 20:
        return "pass-phase5-full-candidate-generation"
    return "needs-full-candidate-generation"


def _summary_verdict(summary: dict[str, Any]) -> str:
    if summary["missing_inputs"]:
        return "phase5-gpu-runs-still-running-or-missing"
    if summary["candidate_manifest_verdict"] != "pass-phase5-full-candidate-generation":
        return "needs-more-phase5-gpu-generated-samples"
    return "pass-phase5-gpu-generated-full-ready-for-result-analysis"


def _paired_case_count(records: list[dict[str, Any]]) -> int:
    total = 0
    for case_id in sorted({record["case_id"] for record in records}):
        labels = {record["label"] for record in records if record["case_id"] == case_id}
        if "faithful" in labels and "plausible_wrong" in labels:
            total += 1
    return total


def _fixture_passing_wrong_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1 for record in records
        if record.get("label") == "plausible_wrong"
        and record.get("features", {}).get("fixture_mismatch_rate") == 0.0
    )


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(record.get(key, "")) for record in records))


def _case_label_counts(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        counts[record["case_id"]][record["label"]] += 1
    return {case_id: dict(counter) for case_id, counter in sorted(counts.items())}


def _project_label_counts(
    records: list[dict[str, Any]],
    case_to_project: dict[str, str],
) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        project = case_to_project.get(record["case_id"], "unknown")
        counts[project][record["label"]] += 1
    return {project: dict(counter) for project, counter in sorted(counts.items())}


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
    project_rows = "\n".join(
        f"| `{project}` | `{counts}` |"
        for project, counts in summary["project_label_counts"].items()
    )
    text = f"""# Decompilation Faithfulness Phase 5 GPU Generated Combined

- Verdict: `{summary['verdict']}`
- Source functions: `{summary['source_function_count']}`
- Source projects: `{summary['source_projects']}`
- Generations: `{summary['generation_count']}`
- Parsed candidates: `{summary['parsed_count']}`
- Evaluated candidates: `{summary['candidate_count']}`
- Compile pass count: `{summary['compile_pass_count']}`
- Behavior labels: `{summary['behavior_label_counts']}`
- Paired case count: `{summary['paired_case_count']}`
- Fixture-passing wrong count: `{summary['fixture_passing_wrong_count']}`
- Trace pairwise AUC: `{summary['trace_pairwise_auc']:.4f}`
- Fixture collapse: `{summary['fixture_collapse']}`
- Candidate manifest verdict: `{summary['candidate_manifest_verdict']}`

## By Project

| Project | Label Counts |
|---|---|
{project_rows}

## CCF-A 风险自查

1. Full-scale 风险：只有当 compile-pass candidates `>=100` 且 paired functions `>=20` 时，本 combined report 才会给出 `pass-phase5-full-candidate-generation`。
2. SOTA 进步风险：本文件只说明 candidate generation 和 bounded trace audit 是否达到规模。最终是否达到 CCF-A/SOTA 贡献，还必须继续跑 Phase 5 result analysis，对比 fixture-only、static/binary motif、Dynamic Trace v1/v2/v3，并检查 `v3 - best non-oracle baseline >= 0.05`。
"""
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
