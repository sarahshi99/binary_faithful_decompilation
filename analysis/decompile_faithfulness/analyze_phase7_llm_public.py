from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu


DEFAULT_RUN_DIRS = [
    Path("analysis_outputs/decompile_faithfulness/phase7_llm_public_cuda2_s0"),
    Path("analysis_outputs/decompile_faithfulness/phase7_llm_public_cuda3_s1"),
    Path("analysis_outputs/decompile_faithfulness/phase7_llm_public_topup_full2_cuda2_s0"),
    Path("analysis_outputs/decompile_faithfulness/phase7_llm_public_topup_full2_cuda3_s1"),
]
DEFAULT_SOURCE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_combined.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_combined.zh.md")
DEFAULT_CANDIDATE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_candidate_manifest_combined.json")


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
                "v3_auc": summary["baseline_auc"]["v3_trace_total"],
                "static_auc": summary["baseline_auc"]["static_structured_proxy"],
                "sota_delta_vs_best_baseline": summary["sota_delta_vs_best_baseline"],
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
    risk_by_case = {
        entry["case_id"]: list(entry.get("risk_families", []))
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
        generation_records.extend(read_jsonl(generation_path))
        records.extend(read_jsonl(records_path))
    records = dedupe_records(records)
    generation_records = dedupe_generation_records(generation_records)

    candidate_manifest = build_candidate_manifest(
        manifest=manifest,
        records=records,
        generation_records=generation_records,
        run_dirs=run_dirs,
    )
    write_json(candidate_manifest_json, candidate_manifest)

    eval_records = [
        record for record in records
        if record.get("compiled") and record.get("label") in {"faithful", "plausible_wrong"}
    ]
    baseline_auc = {
        "fixture_only": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("fixture_mismatch_rate", 1.0)),
        ),
        "static_structured_proxy": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("static_structured_total", 0.0)),
        ),
        "v3_trace_total": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_total", 0.0)),
        ),
    }
    best_baseline = max(baseline_auc["fixture_only"], baseline_auc["static_structured_proxy"])
    summary: dict[str, Any] = {
        "phase": "phase7_llm_public_combined",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_dirs": [str(path) for path in run_dirs],
        "missing_inputs": missing_inputs,
        "source_manifest": str(source_manifest),
        "source_function_count": manifest.get("function_count", 0),
        "generation_count": len(generation_records),
        "parsed_count": sum(1 for record in generation_records if record.get("cleaning_status") == "parsed_function"),
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record.get("compiled")),
        "behavior_label_counts": count_by(records, "label"),
        "cleaning_status_counts": count_by(generation_records, "cleaning_status"),
        "paired_case_count": paired_case_count(records),
        "fixture_passing_wrong_count": fixture_passing_wrong_count(records),
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
        "baseline_auc": baseline_auc,
        "best_non_oracle_baseline_auc": best_baseline,
        "sota_delta_vs_best_baseline": baseline_auc["v3_trace_total"] - best_baseline,
        "case_label_counts": case_label_counts(records),
        "by_prompt_id": grouped_metrics(
            records,
            lambda record: str(record.get("metadata", {}).get("prompt_id", "")),
        ),
        "by_risk_family": {
            risk: basic_metrics(
                [record for record in records if risk in risk_by_case.get(str(record.get("case_id")), [])]
            )
            for risk in sorted({risk for risks in risk_by_case.values() for risk in risks})
        },
        "candidate_manifest_verdict": candidate_manifest["verdict"],
        "gate": {},
    }
    summary["gate"] = {
        "missing_inputs_gate": not summary["missing_inputs"],
        "compile_pass_scale_gate": summary["compile_pass_count"] >= 100,
        "paired_case_gate": summary["paired_case_count"] >= 20,
        "parsed_rate_gate": (
            summary["parsed_count"] / summary["generation_count"]
            if summary["generation_count"] else 0.0
        ) >= 0.50,
        "v3_beats_fixture_gate": baseline_auc["v3_trace_total"] > baseline_auc["fixture_only"],
        "v3_beats_static_gate": baseline_auc["v3_trace_total"] > baseline_auc["static_structured_proxy"],
        "sota_delta_gate": summary["sota_delta_vs_best_baseline"] >= 0.05,
        "fixture_collapse_gate": not summary["fixture_collapse"],
    }
    summary["verdict"] = summary_verdict(summary)
    write_json(output_json, summary)
    write_markdown(output_zh, summary)
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
                "source_kind": metadata.get("source_kind", "phase7_public_local_llm"),
                "source_name": metadata.get("source_name", "Dream-Coder-v0-Instruct-7B"),
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
        "phase": "phase7_llm_public_candidate_generation_combined",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": manifest.get("benchmark", "CodeFuse-DeBench"),
        "source_manifest_function_count": manifest.get("function_count", 0),
        "generation_count": len(generation_records),
        "candidate_count": len(records),
        "compile_pass_count": compile_pass,
        "compile_pass_target_min": 100,
        "paired_function_count": paired,
        "paired_function_target_min": 20,
        "run_dirs": [str(path) for path in run_dirs],
        "candidates": [
            {"case_id": case_id, "candidates": candidates}
            for case_id, candidates in sorted(by_case.items())
        ],
        "verdict": (
            "pass-phase7-llm-public-candidate-generation"
            if compile_pass >= 100 and paired >= 20
            else "needs-more-phase7-llm-public-samples"
        ),
        "gpu_decision": "completed" if records else "not-completed",
    }


def grouped_metrics(
    records: list[dict[str, Any]],
    key_fn: Any,
) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[key_fn(record)].append(record)
    return {key: basic_metrics(group) for key, group in sorted(grouped.items())}


def basic_metrics(records: list[dict[str, Any]]) -> dict[str, Any]:
    eval_records = [
        record for record in records
        if record.get("compiled") and record.get("label") in {"faithful", "plausible_wrong"}
    ]
    return {
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record.get("compiled")),
        "label_counts": count_by(records, "label"),
        "paired_case_count": paired_case_count(records),
        "fixture_passing_wrong_count": fixture_passing_wrong_count(records),
        "fixture_only_auc": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("fixture_mismatch_rate", 1.0)),
        ),
        "static_structured_auc": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("static_structured_total", 0.0)),
        ),
        "v3_trace_total_auc": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_total", 0.0)),
        ),
    }


def summary_verdict(summary: dict[str, Any]) -> str:
    gate = summary["gate"]
    if summary["missing_inputs"]:
        return "phase7-llm-public-runs-missing"
    if gate["compile_pass_scale_gate"] and gate["paired_case_gate"]:
        if gate["v3_beats_fixture_gate"] and gate["v3_beats_static_gate"] and gate["sota_delta_gate"]:
            return "pass-phase7-llm-public-baseline"
        return "method-negative-phase7-llm-public"
    return "needs-more-phase7-llm-public-samples"


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


def case_label_counts(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    for record in records:
        counts[str(record.get("case_id"))][str(record.get("label"))] += 1
    return {case_id: dict(counter) for case_id, counter in sorted(counts.items())}


def count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(record.get(key, "")) for record in records))


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


def dedupe_generation_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for record in records:
        key = str(record.get("candidate_id"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    prompt_rows = "\n".join(
        "| `{prompt}` | `{candidate_count}` | `{compile_pass_count}` | `{paired_case_count}` | "
        "`{fixture_only_auc:.4f}` | `{static_structured_auc:.4f}` | `{v3_trace_total_auc:.4f}` |".format(
            prompt=prompt,
            **metrics,
        )
        for prompt, metrics in summary["by_prompt_id"].items()
    )
    text = f"""# Decompilation Faithfulness Phase 7E LLM Public Combined

- Verdict: `{summary['verdict']}`
- Source functions: `{summary['source_function_count']}`
- Generations: `{summary['generation_count']}`
- Parsed candidates: `{summary['parsed_count']}`
- Evaluated candidates: `{summary['candidate_count']}`
- Compile pass count: `{summary['compile_pass_count']}`
- Behavior labels: `{summary['behavior_label_counts']}`
- Cleaning status counts: `{summary['cleaning_status_counts']}`
- Paired case count: `{summary['paired_case_count']}`
- Fixture-passing wrong count: `{summary['fixture_passing_wrong_count']}`
- Fixture-only AUC: `{summary['baseline_auc']['fixture_only']:.4f}`
- Static structured proxy AUC: `{summary['baseline_auc']['static_structured_proxy']:.4f}`
- Dynamic Trace v3 AUC: `{summary['baseline_auc']['v3_trace_total']:.4f}`
- Delta vs best non-oracle baseline: `{summary['sota_delta_vs_best_baseline']:.4f}`

## Gate Check

| Gate | Passed |
|---|---:|
{gate_rows}

## By Prompt

| Prompt | Candidates | Compile Pass | Paired Cases | Fixture AUC | Static AUC | V3 AUC |
|---|---:|---:|---:|---:|---:|---:|
{prompt_rows}

## Interpretation

This combines the GPU 2/3 Phase 7E public LLM shards. It is a model-generated candidate baseline, not a decompiler-output baseline. If the scale gates fail, top-up generation should target missing paired cases and cleaning/compile failures.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
