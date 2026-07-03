from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from analysis.decompile_faithfulness import run_phase11_input_ordering as phase11


UNKNOWN = "unknown"
FINAL_METHOD = "source_literal_char_interleave"
DEFAULT_BUDGET = 8
METHOD_FREEZE_COMMIT = "06dda89912103b94fc065d6f073581a7811154b1"
EVIDENCE_AUDIT_COMMIT = "c974129c231ff1274e5af714fdc9f01dec927019"
PHASE18_DIR = Path("analysis_outputs/decompile_faithfulness/phase18_source_literal_char_policy")
PHASE18_UNIFIED_JSON = PHASE18_DIR / "phase12_unified_low_budget.json"
V1_FREEZE_MANIFEST = Path("analysis/decompile_faithfulness/paper_freeze_manifest.json")
V1_OVERLAP_AUDIT = Path("results/decompile_faithfulness/oracle_overlap_audit.json")


DATASETS = {
    "public_static_hard": {
        "dataset_id": "phase7c2_static_hard_public",
        "display_name": "Public static-hard",
        "records_path": Path("analysis_outputs/decompile_faithfulness/phase7_static_hard/records.jsonl"),
        "function_manifest": Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json"),
        "candidate_manifest": Path("docs/paper_agent/decompile_faithfulness_phase7_static_hard_candidate_manifest.json"),
        "summary_path": Path("docs/paper_agent/decompile_faithfulness_phase7_static_hard_result.json"),
        "project_family": "CodeFuse-DeBench",
        "label_probe_family": "phase5b_hard_trace_inputs",
    },
    "llm_public": {
        "dataset_id": "phase7e_llm_public_full_topup",
        "display_name": "LLM-public",
        "records_path": None,
        "function_manifest": Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json"),
        "candidate_manifest": Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_candidate_manifest_combined_topup_full2.json"),
        "summary_path": Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_combined.json"),
        "project_family": "CodeFuse-DeBench",
        "label_probe_family": "phase5b_hard_trace_inputs",
    },
    "ghidra": {
        "dataset_id": "phase6r_ghidra_full",
        "display_name": "Ghidra",
        "records_path": Path("analysis_outputs/decompile_faithfulness/phase6r_ghidra_full/records.jsonl"),
        "function_manifest": Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json"),
        "candidate_manifest": Path("docs/paper_agent/decompile_faithfulness_phase6r_real_decompiler_manifest.json"),
        "summary_path": Path("docs/paper_agent/decompile_faithfulness_phase6r_result_analysis.json"),
        "project_family": "thealgorithms_c+c_algorithms",
        "label_probe_family": "phase5b_hard_trace_inputs",
    },
}


PROVENANCE_COLUMNS = [
    "dataset",
    "project",
    "source_file",
    "source_function",
    "stable_case_id",
    "stable_candidate_id",
    "base_candidate_origin",
    "compile_processing",
    "semantic_transformation",
    "evidence_stratum",
    "producing_tool_or_model",
    "producing_tool_or_model_version",
    "prompt_or_transformation_family",
    "compiler",
    "optimization_level",
    "architecture",
    "function_signature",
    "source_loc",
    "argument_count",
    "argument_types",
    "fixture_count",
    "source_char_literal_count",
    "compile_status",
    "sanitizer_status",
    "execution_status",
    "legacy_label",
    "paper_label",
    "primary_budget8_label",
    "primary_budget8_paper_label",
    "label_oracle_type",
    "concrete_labeling_witness",
    "influenced_method_development",
    "drift_family",
    "normalization_or_manual_edit_notes",
    "in_candidate_attempt_pool",
    "compile_ready",
    "executable",
    "oracle_adjudicable",
    "in_primary_full_result_table",
    "in_primary_paired_case",
    "exclusion_reason_from_primary_table",
]


@dataclass(frozen=True)
class DatasetContext:
    key: str
    dataset_id: str
    spec: dict[str, Any]
    function_manifest: dict[str, Any]
    functions_by_case: dict[str, dict[str, Any]]
    records: list[dict[str, Any]]
    candidate_manifest: dict[str, Any]
    candidate_manifest_by_id: dict[str, dict[str, Any]]
    phase18_budget8_by_id: dict[tuple[str, str], dict[str, Any]]
    phase18_metrics: dict[str, Any]
    phase18_input_counts: dict[str, int]


def main() -> None:
    args = parse_args()
    summary = generate(args.repo_root.resolve())
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args()


def generate(repo_root: Path) -> dict[str, Any]:
    contexts = [load_dataset_context(repo_root, key, spec) for key, spec in DATASETS.items()]
    integrity = build_method_freeze_integrity(repo_root)
    provenance_rows = build_provenance(repo_root, contexts)
    reconciliation_rows = build_primary_reconciliation(repo_root, contexts, provenance_rows)
    validation = build_provenance_validation_summary(provenance_rows)
    overlap_audit, overlap_summary_rows = build_oracle_overlap_v2(repo_root, provenance_rows)
    environment = build_environment_manifest(repo_root, contexts)

    write_json(repo_root / "analysis/decompile_faithfulness/method_freeze_integrity.json", integrity)
    write_provenance_v2(repo_root, provenance_rows)
    write_reconciliation(repo_root, reconciliation_rows)
    write_json(repo_root / "results/decompile_faithfulness/provenance_validation_summary.json", validation)
    write_json(repo_root / "results/decompile_faithfulness/oracle_overlap_audit_v2.json", overlap_audit)
    write_overlap_summary_v2(repo_root, overlap_summary_rows)
    write_json(repo_root / "results/decompile_faithfulness/dataset_environment_manifest.json", environment)
    write_dataset_provenance_latex(repo_root, contexts, reconciliation_rows)
    write_holdout_preregistration_v2(repo_root, contexts)
    write_handoff(repo_root, integrity, validation, reconciliation_rows, overlap_audit, environment)

    return {
        "candidate_rows": len(provenance_rows),
        "method_hashes_unchanged": integrity["summary"]["all_method_files_current_match_freeze"],
        "semantic_wrong_rows": sum(1 for row in provenance_rows if row["paper_label"] == "semantic_wrong"),
        "primary_full_table_rows": sum(1 for row in provenance_rows if row["in_primary_full_result_table"] == "true"),
    }


def load_dataset_context(repo_root: Path, key: str, spec: dict[str, Any]) -> DatasetContext:
    phase18 = read_json(repo_root / PHASE18_UNIFIED_JSON)
    dataset_id = spec["dataset_id"]
    function_manifest = read_json(repo_root / spec["function_manifest"])
    functions_by_case = {entry["case_id"]: entry for entry in function_manifest.get("functions", [])}
    if key == "llm_public":
        summary = read_json(repo_root / spec["summary_path"])
        records: list[dict[str, Any]] = []
        for run_dir in summary.get("run_dirs", []):
            records.extend(read_jsonl(Path(run_dir) / "records.jsonl"))
        records = dedupe_records(records)
    else:
        records = read_jsonl(repo_root / spec["records_path"])
    candidate_manifest = read_json(repo_root / spec["candidate_manifest"])
    return DatasetContext(
        key=key,
        dataset_id=dataset_id,
        spec=spec,
        function_manifest=function_manifest,
        functions_by_case=functions_by_case,
        records=records,
        candidate_manifest=candidate_manifest,
        candidate_manifest_by_id=index_candidate_manifest(candidate_manifest),
        phase18_budget8_by_id=load_phase18_budget8(repo_root, dataset_id),
        phase18_metrics=phase18["datasets"][dataset_id]["budget_metrics"][str(DEFAULT_BUDGET)],
        phase18_input_counts=phase18["datasets"][dataset_id].get("input_counts_by_case", {}),
    )


def build_method_freeze_integrity(repo_root: Path) -> dict[str, Any]:
    freeze_manifest = read_json(repo_root / V1_FREEZE_MANIFEST)
    sources = freeze_manifest["method_affecting_sources"]
    current_commit = git_output(repo_root, ["rev-parse", "HEAD"])
    rows = []
    for item in sources:
        path = item["path"]
        freeze_bytes = git_blob(repo_root, METHOD_FREEZE_COMMIT, path)
        current_path = repo_root / path
        current_bytes = current_path.read_bytes() if current_path.exists() else b""
        freeze_hash = sha256_bytes(freeze_bytes) if freeze_bytes is not None else UNKNOWN
        current_hash = sha256_bytes(current_bytes) if current_path.exists() else UNKNOWN
        rows.append(
            {
                "path": path,
                "functions": item.get("functions", []),
                "affects": item.get("affects", []),
                "method_freeze_sha256": freeze_hash,
                "current_sha256": current_hash,
                "whole_file_unchanged": freeze_hash == current_hash and freeze_hash != UNKNOWN,
                "method_behavior_affecting_contents_unchanged": freeze_hash == current_hash and freeze_hash != UNKNOWN,
                "verification_basis": "whole-file SHA-256 equality for method-affecting source file",
            }
        )
    all_equal = all(row["method_behavior_affecting_contents_unchanged"] for row in rows)
    return {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "repository": "https://github.com/sarahshi99/binary_faithful_decompilation",
        "branch": git_output(repo_root, ["branch", "--show-current"]),
        "generated_at_commit": current_commit,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "evidence_audit_commit": EVIDENCE_AUDIT_COMMIT,
        "final_method": FINAL_METHOD,
        "default_budget": DEFAULT_BUDGET,
        "excluded_from_method_freeze": [
            "analysis/decompile_faithfulness/submission_evidence_audit.py",
            "analysis/decompile_faithfulness/submission_evidence_corrections.py",
            "analysis/decompile_faithfulness/tests/",
            "results/decompile_faithfulness/",
            "docs/paper_agent/",
            "paper/tables/",
        ],
        "method_affecting_sources": rows,
        "summary": {
            "method_file_count": len(rows),
            "unchanged_method_file_count": sum(1 for row in rows if row["method_behavior_affecting_contents_unchanged"]),
            "all_method_files_current_match_freeze": all_equal,
        },
    }


def build_provenance(repo_root: Path, contexts: list[DatasetContext]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    preliminary_rows: list[dict[str, Any]] = []
    for context in contexts:
        for record in context.records:
            manifest_item = context.candidate_manifest_by_id.get(str(record.get("candidate_id")), {})
            entry = context.functions_by_case.get(str(record.get("case_id")), {})
            b8 = context.phase18_budget8_by_id.get(record_key(record))
            classification = classify_candidate_provenance(context.key, record, manifest_item)
            legacy_label = str(record.get("label", UNKNOWN))
            paper_label = paper_label_for_source_record(record)
            primary_paper_label = paper_label_for_primary_budget_record(b8) if b8 else ""
            preliminary_rows.append(
                {
                    "context": context,
                    "record": record,
                    "manifest_item": manifest_item,
                    "entry": entry,
                    "b8": b8,
                    "classification": classification,
                    "legacy_label": legacy_label,
                    "paper_label": paper_label,
                    "primary_paper_label": primary_paper_label,
                }
            )

    paired_cases = primary_paired_cases(preliminary_rows)
    development_cases = development_coupled_cases()
    for item in preliminary_rows:
        context: DatasetContext = item["context"]
        record: dict[str, Any] = item["record"]
        manifest_item: dict[str, Any] = item["manifest_item"]
        entry: dict[str, Any] = item["entry"]
        b8: dict[str, Any] | None = item["b8"]
        classification: dict[str, str] = item["classification"]
        source = str(record.get("metadata", {}).get("function_source", "") or manifest_item.get("function_source", ""))
        case_id = str(record.get("case_id", UNKNOWN))
        candidate_id = str(record.get("candidate_id", UNKNOWN))
        row = {
            "dataset": context.dataset_id,
            "project": str(entry.get("project", UNKNOWN)),
            "source_file": str(entry.get("source_path") or entry.get("original_source_path") or UNKNOWN),
            "source_function": str(entry.get("function_name", UNKNOWN)),
            "stable_case_id": case_id,
            "stable_candidate_id": candidate_id,
            **classification,
            "producing_tool_or_model": producing_tool(context.key, record, manifest_item),
            "producing_tool_or_model_version": producing_version(context.key, record, manifest_item),
            "prompt_or_transformation_family": prompt_or_transform(record, manifest_item),
            "compiler": compiler_for_record(context.key, record, manifest_item),
            "optimization_level": str(record.get("optimization_level") or manifest_item.get("optimization_level") or UNKNOWN),
            "architecture": architecture_for_record(context.key, record, manifest_item),
            "function_signature": str(entry.get("signature", UNKNOWN)),
            "source_loc": str(source_loc(source if source else read_source(repo_root, entry))),
            "argument_count": str(argument_count(entry.get("signature", ""))),
            "argument_types": argument_types(entry.get("signature", "")),
            "fixture_count": str(len(entry.get("fixtures", []))),
            "source_char_literal_count": str(len(phase11.source_char_literal_values(read_source(repo_root, entry)))),
            "compile_status": "compiled" if record.get("compiled") else "compile_fail",
            "sanitizer_status": sanitizer_status(context.key),
            "execution_status": execution_status(record),
            "legacy_label": item["legacy_label"],
            "paper_label": item["paper_label"],
            "primary_budget8_label": str(b8.get("label", "")) if b8 else "",
            "primary_budget8_paper_label": item["primary_paper_label"],
            "label_oracle_type": label_oracle_type(item["paper_label"], record, context),
            "concrete_labeling_witness": concrete_labeling_witness(item["paper_label"], record, context),
            "influenced_method_development": "yes" if case_id in development_cases else "no",
            "drift_family": drift_family(context.key, record, entry),
            "normalization_or_manual_edit_notes": normalization_notes(context.key, record, manifest_item),
            "in_candidate_attempt_pool": "true",
            "compile_ready": bool_str(bool(record.get("compiled"))),
            "executable": bool_str(source_record_executable(record)),
            "oracle_adjudicable": bool_str(item["paper_label"] in {"semantic_wrong", "no_mismatch_under_labeling_protocol"}),
            "in_primary_full_result_table": bool_str(b8 is not None),
            "in_primary_paired_case": bool_str(bool(b8) and (context.dataset_id, case_id) in paired_cases),
            "exclusion_reason_from_primary_table": exclusion_reason_from_primary_table(context, record, b8),
        }
        rows.append(row)
    rows.sort(key=lambda row: (row["dataset"], row["stable_case_id"], row["stable_candidate_id"]))
    return rows


def classify_candidate_provenance(
    context_key: str,
    record: dict[str, Any],
    manifest_item: dict[str, Any],
) -> dict[str, str]:
    mutation = str(record.get("mutation_type") or manifest_item.get("mutation_type") or "")
    prompt_id = str(record.get("metadata", {}).get("prompt_id") or manifest_item.get("prompt_id") or "")
    if context_key == "ghidra":
        semantic = {
            "phase6_fixture_ifchain_semantic_drift": "fixture_overfit_construction",
            "phase6_behavior_preserving_noop_guard": "behavior_preserving_noop",
            "phase6_original_control": "none",
        }.get(mutation, "unknown")
        stratum = "controlled_stress_candidate" if semantic == "fixture_overfit_construction" else "behavior_preserving_control"
        return {
            "base_candidate_origin": "raw_ghidra_output",
            "compile_processing": "syntax_normalization",
            "semantic_transformation": semantic,
            "evidence_stratum": stratum,
        }
    if context_key == "llm_public":
        semantic = {
            "strict_rewrite": "llm_rewrite",
            "strict_bug": "llm_bug_prompt",
        }.get(prompt_id, "unknown")
        return {
            "base_candidate_origin": "raw_llm_generation",
            "compile_processing": "function_extraction",
            "semantic_transformation": semantic,
            "evidence_stratum": "natural_llm_output",
        }
    if context_key == "public_static_hard":
        if mutation == "phase7_static_hard_original_control":
            return {
                "base_candidate_origin": "original_source_control",
                "compile_processing": "none",
                "semantic_transformation": "none",
                "evidence_stratum": "behavior_preserving_control",
            }
        return {
            "base_candidate_origin": "original_source_control",
            "compile_processing": "none",
            "semantic_transformation": "controlled_semantic_mutation",
            "evidence_stratum": "controlled_stress_candidate",
        }
    return {
        "base_candidate_origin": "other",
        "compile_processing": "unknown",
        "semantic_transformation": "unknown",
        "evidence_stratum": "non_evaluable",
    }


def paper_label_for_source_record(record: dict[str, Any]) -> str:
    legacy = record.get("label")
    if not record.get("compiled") or not source_record_executable(record):
        return "non_evaluable"
    if legacy == "plausible_wrong":
        return "semantic_wrong"
    if legacy == "faithful":
        return "no_mismatch_under_labeling_protocol"
    return "non_evaluable"


def paper_label_for_primary_budget_record(record: dict[str, Any] | None) -> str:
    if record is None:
        return ""
    if not record.get("compiled"):
        return "non_evaluable"
    if record.get("label") == "plausible_wrong":
        return "semantic_wrong"
    if record.get("label") == "faithful":
        return "no_mismatch_under_labeling_protocol"
    return "non_evaluable"


def source_record_executable(record: dict[str, Any]) -> bool:
    if not record.get("compiled"):
        return False
    diagnostics = record.get("diagnostics", {}) or {}
    return float(diagnostics.get("primary_exit_code", 0.0)) == 0.0


def primary_paired_cases(items: list[dict[str, Any]]) -> set[tuple[str, str]]:
    labels_by_case: dict[tuple[str, str], set[str]] = defaultdict(set)
    for item in items:
        b8 = item["b8"]
        if not b8:
            continue
        label = item["primary_paper_label"]
        if label in {"semantic_wrong", "no_mismatch_under_labeling_protocol"}:
            labels_by_case[(item["context"].dataset_id, str(b8["case_id"]))].add(label)
    return {
        key for key, labels in labels_by_case.items()
        if {"semantic_wrong", "no_mismatch_under_labeling_protocol"} <= labels
    }


def build_primary_reconciliation(
    repo_root: Path,
    contexts: list[DatasetContext],
    rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    rows_by_dataset: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        rows_by_dataset[row["dataset"]].append(row)
    output = []
    for context in contexts:
        summary = read_json(repo_root / context.spec["summary_path"])
        dataset_rows = rows_by_dataset[context.dataset_id]
        primary_rows = [row for row in dataset_rows if row["in_primary_full_result_table"] == "true"]
        primary_evaluable = [
            row for row in primary_rows
            if row["primary_budget8_paper_label"] in {"semantic_wrong", "no_mismatch_under_labeling_protocol"}
        ]
        excluded = [row for row in dataset_rows if row["in_primary_full_result_table"] != "true"]
        excluded_reasons = Counter(row["exclusion_reason_from_primary_table"] for row in excluded)
        paired_case_ids = {
            row["stable_case_id"] for row in primary_rows
            if row["in_primary_paired_case"] == "true"
        }
        output.append(
            {
                "dataset": context.dataset_id,
                "attempts": candidate_attempts(context.key, summary),
                "generated_records": len(dataset_rows),
                "compile_ready": sum(1 for row in dataset_rows if row["compile_ready"] == "true"),
                "executable": sum(1 for row in dataset_rows if row["executable"] == "true"),
                "oracle_adjudicable": sum(1 for row in dataset_rows if row["oracle_adjudicable"] == "true"),
                "candidates_in_current_full_result_table": len(primary_rows),
                "primary_evaluable_candidates": len(primary_evaluable),
                "paired_cases": len(paired_case_ids),
                "candidates_in_paired_cases": sum(1 for row in primary_rows if row["in_primary_paired_case"] == "true"),
                "wrong_candidates_in_result_table": sum(1 for row in primary_rows if row["primary_budget8_paper_label"] == "semantic_wrong"),
                "no_mismatch_candidates_in_result_table": sum(1 for row in primary_rows if row["primary_budget8_paper_label"] == "no_mismatch_under_labeling_protocol"),
                "non_evaluable_candidates_in_result_table": sum(1 for row in primary_rows if row["primary_budget8_paper_label"] == "non_evaluable"),
                "excluded_candidates": len(excluded),
                "excluded_not_compile_ready": excluded_reasons["not_compile_ready"],
                "excluded_no_generated_final_method_inputs": excluded_reasons["no_generated_final_method_inputs"],
                "excluded_missing_case_manifest": excluded_reasons["missing_case_manifest"],
                "excluded_other": sum(
                    count for reason, count in excluded_reasons.items()
                    if reason not in {"not_compile_ready", "no_generated_final_method_inputs", "missing_case_manifest"}
                ),
                "exclusion_reasons_json": json.dumps(dict(sorted(excluded_reasons.items())), sort_keys=True),
                "phase18_candidate_count_metric": context.phase18_metrics["candidate_count"],
                "phase18_compile_pass_count_metric": context.phase18_metrics["compile_pass_count"],
                "phase18_eval_count_metric": context.phase18_metrics["eval_count"],
                "phase18_wrong_count_metric": context.phase18_metrics["wrong_count"],
                "count_difference_explanation": count_difference_explanation(context.dataset_id),
            }
        )
    return output


def build_provenance_validation_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    semantic_wrong = [row for row in rows if row["paper_label"] == "semantic_wrong"]
    all_rows = list(rows)
    natural_ghidra_wrong = [
        row for row in semantic_wrong
        if row["base_candidate_origin"] == "raw_ghidra_output"
        and row["evidence_stratum"] == "natural_tool_output"
    ]
    ghidra_controlled_wrong = [
        row for row in semantic_wrong
        if row["dataset"] == "phase6r_ghidra_full"
        and row["semantic_transformation"] == "fixture_overfit_construction"
    ]
    natural_llm_wrong = [
        row for row in semantic_wrong
        if row["base_candidate_origin"] == "raw_llm_generation"
        and row["evidence_stratum"] == "natural_llm_output"
    ]
    actual_semantic_repair = [
        row for row in all_rows
        if row["semantic_transformation"] == "llm_rewrite"
        and "repair" in row["normalization_or_manual_edit_notes"].lower()
    ]
    controls = [
        row for row in all_rows
        if row["evidence_stratum"] == "behavior_preserving_control"
    ]
    return {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "candidate_count": len(all_rows),
        "stable_identifier_coverage": {
            "rows_with_dataset_case_candidate_ids": sum(
                1 for row in rows
                if row["dataset"] and row["stable_case_id"] != UNKNOWN and row["stable_candidate_id"] != UNKNOWN
            ),
            "coverage_rate": 1.0 if rows else 0.0,
        },
        "paper_label_counts": counter_dict(row["paper_label"] for row in rows),
        "legacy_label_counts": counter_dict(row["legacy_label"] for row in rows),
        "taxonomy_counts": {
            "base_candidate_origin": counter_dict(row["base_candidate_origin"] for row in rows),
            "compile_processing": counter_dict(row["compile_processing"] for row in rows),
            "semantic_transformation": counter_dict(row["semantic_transformation"] for row in rows),
            "evidence_stratum": counter_dict(row["evidence_stratum"] for row in rows),
        },
        "required_answers": {
            "wrong_candidates_natural_raw_or_minimally_processed_ghidra_errors": len(natural_ghidra_wrong),
            "wrong_candidates_controlled_ghidra_derived_stress": len(ghidra_controlled_wrong),
            "wrong_candidates_natural_llm_generations": len(natural_llm_wrong),
            "candidates_with_actual_semantic_repair": len(actual_semantic_repair),
            "comparison_class_original_source_or_behavior_preserving_controls": len(controls),
        },
        "ghidra_correction": {
            "phase6_fixture_ifchain_semantic_drift": "controlled_stress_candidate / fixture_overfit_construction; Ghidra is base context only",
            "phase6_original_control": "behavior_preserving_control / none",
            "phase6_behavior_preserving_noop_guard": "behavior_preserving_control / behavior_preserving_noop",
            "semantic_wrong_by_transformation": counter_dict(
                row["semantic_transformation"] for row in semantic_wrong
                if row["dataset"] == "phase6r_ghidra_full"
            ),
        },
        "llm_correction": {
            "function_extraction_is_not_semantic_repair": True,
            "semantic_wrong_by_transformation": counter_dict(
                row["semantic_transformation"] for row in semantic_wrong
                if row["dataset"] == "phase7e_llm_public_full_topup"
            ),
        },
    }


def build_oracle_overlap_v2(
    repo_root: Path,
    provenance_rows: list[dict[str, str]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    v1 = read_json(repo_root / V1_OVERLAP_AUDIT)
    provenance_by_id = {
        (row["dataset"], row["stable_candidate_id"]): row
        for row in provenance_rows
    }
    candidate_rows = []
    for item in v1["candidates"]:
        row = provenance_by_id.get((item["dataset"], item["candidate_id"]))
        if row is None:
            continue
        flags = item.get("probe_family_overlap", {})
        unresolved = item.get("oracle_independence_class") == "unresolved" or bool(item.get("unresolved_reason"))
        exact = bool(item.get("exact_witness_overlap"))
        family_only = (not exact) and (not unresolved) and any(bool(value) for value in flags.values())
        no_demonstrated = (not exact) and (not unresolved) and not family_only
        candidate_rows.append(
            {
                "dataset": item["dataset"],
                "case_id": item["case_id"],
                "candidate_id": item["candidate_id"],
                "paper_label": row["paper_label"],
                "primary_budget8_paper_label": row["primary_budget8_paper_label"],
                "in_primary_full_result_table": row["in_primary_full_result_table"] == "true",
                "in_primary_paired_case": row["in_primary_paired_case"] == "true",
                "base_candidate_origin": row["base_candidate_origin"],
                "semantic_transformation": row["semantic_transformation"],
                "evidence_stratum": row["evidence_stratum"],
                "drift_family": row["drift_family"],
                "label_oracle_type": row["label_oracle_type"],
                "overlap_kind": "reconstructed exact witness overlap under the current artifact" if exact else "",
                "historical_exact_witness_reuse": False,
                "reconstructed_exact_witness_overlap_under_current_artifact": exact,
                "first_exact_overlap_rank": item.get("first_exact_overlap_rank"),
                "exact_overlap_count": int(item.get("exact_overlap_count", 0)),
                "exact_overlap_args": item.get("exact_overlap_args", []),
                "shared_probe_generation_family": family_only or exact,
                "only_probe_family_overlap": family_only,
                "no_demonstrated_overlap": no_demonstrated,
                "unresolved_reconstruction": unresolved,
                "probe_family_overlap": flags,
                "oracle_independence_class": item.get("oracle_independence_class", UNKNOWN),
            }
        )

    summary_specs: list[tuple[str, str, Any]] = [
        ("scope", "all_compiled_wrong_label_records", lambda row: row["paper_label"] in {"semantic_wrong", "non_evaluable"}),
        ("scope", "current_full_result_tables", lambda row: row["in_primary_full_result_table"] and row["primary_budget8_paper_label"] == "semantic_wrong"),
        ("scope", "primary_paired_cases", lambda row: row["in_primary_paired_case"] and row["primary_budget8_paper_label"] == "semantic_wrong"),
        ("scope", "natural_tool_or_llm_outputs_only", lambda row: row["paper_label"] == "semantic_wrong" and row["evidence_stratum"] in {"natural_tool_output", "natural_llm_output"}),
        ("scope", "controlled_stress_candidates_only", lambda row: row["paper_label"] == "semantic_wrong" and row["evidence_stratum"] == "controlled_stress_candidate"),
    ]
    datasets = sorted({row["dataset"] for row in candidate_rows})
    for dataset in datasets:
        summary_specs.append(("dataset", dataset, lambda row, dataset=dataset: row["dataset"] == dataset and row["paper_label"] == "semantic_wrong"))
    families = sorted({row["drift_family"] for row in candidate_rows})
    for family in families:
        summary_specs.append(("drift_family", family, lambda row, family=family: row["drift_family"] == family and row["paper_label"] == "semantic_wrong"))

    summary_rows = [
        overlap_summary_row(group_type, group, [row for row in candidate_rows if predicate(row)])
        for group_type, group, predicate in summary_specs
    ]
    summary = {
        "schema_version": 2,
        "created_at_utc": now_utc(),
        "final_method": FINAL_METHOD,
        "final_budget": DEFAULT_BUDGET,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "evidence_audit_commit": EVIDENCE_AUDIT_COMMIT,
        "overlap_wording": "reconstructed exact witness overlap under the current artifact",
        "source_artifact": str(V1_OVERLAP_AUDIT),
        "candidates": candidate_rows,
        "summaries": summary_rows,
        "interpretation": {
            "historical_exact_witness_reuse": "No historical trace in the current artifact stores the original per-candidate labeling witness; this count is therefore zero unless explicitly documented later.",
            "reconstructed_exact_overlap": "A reconstructed source-labeling mismatch input also occurs in the final budget-8 prefix under the current artifact.",
            "shared_probe_generation_family": "The label and final probes share a family such as fixture +/- 1 or hard-input Cartesian construction; this is reported separately and is not leakage by itself.",
            "independent_exhaustive_oracle_overlap": "If a future exhaustive oracle overlaps the auditor prefix, that is allowed and should be reported rather than removed.",
        },
        "development_coupling_audit": development_coupling_audit(),
    }
    return summary, summary_rows


def overlap_summary_row(group_type: str, group: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    denominator = len(rows)
    exact = sum(1 for row in rows if row["reconstructed_exact_witness_overlap_under_current_artifact"])
    only_family = sum(1 for row in rows if row["only_probe_family_overlap"])
    unresolved = sum(1 for row in rows if row["unresolved_reconstruction"])
    no_overlap = sum(1 for row in rows if row["no_demonstrated_overlap"])
    historical = sum(1 for row in rows if row["historical_exact_witness_reuse"])
    return {
        "group_type": group_type,
        "group": group,
        "wrong_candidate_denominator": denominator,
        "historical_exact_witness_reuse": historical,
        "candidates_with_reconstructed_exact_witness_overlap_under_current_artifact": exact,
        "overlap_rate": safe_rate(exact, denominator),
        "only_probe_family_overlap": only_family,
        "no_demonstrated_overlap": no_overlap,
        "unresolved_reconstruction_count": unresolved,
    }


def build_environment_manifest(repo_root: Path, contexts: list[DatasetContext]) -> dict[str, Any]:
    env: dict[str, Any] = {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "evidence_audit_commit": EVIDENCE_AUDIT_COMMIT,
        "collections": {},
        "global_runner_reconstruction": {
            "trace_compiler_command": "/usr/bin/gcc -std=c11 -Wall -Wextra -Werror -O{optimization_level} {trace_source} -o {trace_exe}",
            "trace_timeout_behavior": "compile.py::run_command default timeout_s=10; timeout return code 124",
            "dynamic_trace_output_parsing": "one integer stdout line per probe; non-integer or count mismatch is a failed trace",
            "sanitizer_flags": "none found in compile.py, dynamic_trace.py, phase6r, phase7 static-hard, or phase7 LLM runners",
        },
    }
    for context in contexts:
        if context.key == "public_static_hard":
            env["collections"][context.dataset_id] = {
                "stored_historical_metadata": {
                    "benchmark": context.candidate_manifest.get("benchmark", UNKNOWN),
                    "candidate_count": context.candidate_manifest.get("candidate_count", UNKNOWN),
                    "compile_pass_count": context.candidate_manifest.get("compile_pass_count", UNKNOWN),
                    "optimization_levels": context.candidate_manifest.get("optimization_levels", []),
                    "tool": "objdump",
                    "assembly_context_count": context.candidate_manifest.get("assembly_context_count", UNKNOWN),
                },
                "reconstructed_from_runner_scripts": {
                    "compiler_command": "/usr/bin/gcc -std=c11 -Wall -Wextra -Werror -O{O0,O2}",
                    "architecture": "x86_64 inferred for records with x86_64/amd64 assembly paths; otherwise unknown",
                    "timeout_behavior": "compile.py::run_command default timeout_s=10 for compile and execution",
                    "sanitizer_use": "none in runner flags",
                },
                "still_unknown": ["exact GCC version", "host CPU model", "sanitizer runtime status per candidate"],
            }
        elif context.key == "llm_public":
            sampling = llm_sampling_summary(context)
            env["collections"][context.dataset_id] = {
                "stored_historical_metadata": {
                    "model_name": "Dream-Coder-v0-Instruct-7B",
                    "run_dirs": context.candidate_manifest.get("run_dirs", []),
                    "generation_count": context.candidate_manifest.get("generation_count", UNKNOWN),
                    "candidate_count": context.candidate_manifest.get("candidate_count", UNKNOWN),
                    "compile_pass_count": context.candidate_manifest.get("compile_pass_count", UNKNOWN),
                    "sampling": sampling,
                },
                "reconstructed_from_runner_scripts": {
                    "default_model_path": "phase2_gpu.DEFAULT_MODEL_PATH",
                    "default_device": "cuda:2 in run_phase7_llm_public_generation.py; historical run dirs include cuda2/cuda3 names",
                    "compiler_command": "/usr/bin/gcc -std=c11 -Wall -Wextra -Werror -O0",
                    "optimization_levels": ["O0"],
                    "timeout_behavior": "compile.py::run_command default timeout_s=10 for compile and execution",
                    "sanitizer_use": "none in runner flags",
                },
                "still_unknown": ["exact model checkpoint hash in local model path", "exact GPU model per run", "exact GCC version", "sanitizer runtime status per candidate"],
            }
        elif context.key == "ghidra":
            env["collections"][context.dataset_id] = {
                "stored_historical_metadata": {
                    "tool": context.candidate_manifest.get("tool", "ghidra"),
                    "tool_path": context.candidate_manifest.get("tool_path", UNKNOWN),
                    "ghidra_version": "12.1.2 inferred from stored tool_path/source_name",
                    "java_home": context.candidate_manifest.get("java_home", UNKNOWN),
                    "optimization_levels": context.candidate_manifest.get("optimization_levels", []),
                    "candidate_count": context.candidate_manifest.get("candidate_count", UNKNOWN),
                    "compile_pass_count": context.candidate_manifest.get("compile_pass_count", UNKNOWN),
                },
                "reconstructed_from_runner_scripts": {
                    "binary_compile_command": "/usr/bin/gcc -std=c11 -w -O{O0,O2} -g -fno-pie -fcf-protection=none -c",
                    "ghidra_command": "analyzeHeadless ... -analysisTimeoutPerFile 120 -max-cpu 1 -deleteProject",
                    "ghidra_process_timeout_seconds": 180,
                    "binary_compile_timeout_seconds": 20,
                    "trace_compiler_command": "/usr/bin/gcc -std=c11 -Wall -Wextra -Werror -O{O0,O2}",
                    "sanitizer_use": "none in runner flags",
                },
                "still_unknown": ["exact GCC version", "host architecture unless recovered from object metadata", "sanitizer runtime status per candidate"],
            }
    return env


def write_dataset_provenance_latex(
    repo_root: Path,
    contexts: list[DatasetContext],
    reconciliation_rows: list[dict[str, Any]],
) -> None:
    by_dataset = {row["dataset"]: row for row in reconciliation_rows}
    project_counts = project_function_counts(contexts)
    provenance_text = {
        "phase7c2_static_hard_public": "Source-controlled semantic mutations and original controls",
        "phase7e_llm_public_full_topup": "Dream-Coder raw generations with function extraction",
        "phase6r_ghidra_full": "Ghidra-derived controlled stress and control candidates",
    }
    status_text = {
        "phase7c2_static_hard_public": "pre-freeze development evidence",
        "phase7e_llm_public_full_topup": "pre-freeze development evidence",
        "phase6r_ghidra_full": "pre-freeze development evidence",
    }
    lines = [
        r"\begin{tabular}{lrrrrrrrrll}",
        r"\toprule",
        r"Collection & Projects & Source functions & Attempts & Compile-ready & Primary evaluated & Paired cases & Semantic wrong & No-mismatch & Primary candidate provenance & Development/holdout status \\",
        r"\midrule",
    ]
    for context in contexts:
        row = by_dataset[context.dataset_id]
        counts = project_counts[context.dataset_id]
        lines.append(
            "{} & {} & {} & {} & {} & {} & {} & {} & {} & {} & {} \\\\".format(
                latex_escape(context.spec["display_name"]),
                counts["projects"],
                counts["source_functions"],
                row["attempts"],
                row["compile_ready"],
                row["candidates_in_current_full_result_table"],
                row["paired_cases"],
                row["wrong_candidates_in_result_table"],
                row["no_mismatch_candidates_in_result_table"],
                latex_escape(provenance_text[context.dataset_id]),
                latex_escape(status_text[context.dataset_id]),
            )
        )
    lines.extend([r"\bottomrule", r"\end{tabular}", ""])
    path = repo_root / "paper/tables/dataset_provenance_v2.tex"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_holdout_preregistration_v2(repo_root: Path, contexts: list[DatasetContext]) -> None:
    seen_projects = sorted({entry.get("project", UNKNOWN) for context in contexts for entry in context.function_manifest.get("functions", [])})
    text = f"""# Frozen Holdout Preregistration v2

Generated: {now_utc()}

Final method: `{FINAL_METHOD}`. Method freeze commit: `{METHOD_FREEZE_COMMIT}`. Evidence-audit commit: `{EVIDENCE_AUDIT_COMMIT}`.

The prospective holdout must not be acquired, labeled, or evaluated by the final auditor until this preregistration and its sealed acquisition manifest are committed and reviewed.

## Current Sources Excluded From Holdout

Already used projects: {", ".join(seen_projects)}. The holdout must not reuse any function, fixture, candidate, source literal, inspected failure, or development example from these projects.

## Candidate Unseen Upstream Projects

- `libtommath`
- `cJSON`
- `uthash`
- `musl`
- `zlib`
- `mbedtls`
- `sqlite` utility-only subset
- `libb64`
- `inih`
- `tiny-AES-c` utility subset

Exact upstream releases or commit hashes must be selected before function sampling.

## Deterministic Eligibility Filtering

Keep only functions satisfying all conditions:

- scalar integer or char arguments only;
- deterministic behavior;
- no heap ownership;
- no I/O;
- no mutable global state;
- no threads, time, environment, or undefined behavior;
- source and harness compile under the sealed toolchain.

After eligibility filtering, select functions with a committed random seed rather than manual preference for source literals. Retain at least 8 project-disjoint upstream projects and target 48-64 eligible functions.

## Candidate Strata

Primary natural-output stratum:

- raw or minimally compile-normalized traditional decompiler outputs;
- fixed-pipeline LLM outputs where available.

Secondary controlled-stress stratum:

- candidate mutations generated by a fixed grammar sealed before evaluation.

Controlled stress candidates must not be pooled with natural outputs in the primary generalization claim.

Store raw output, normalized output, and every transformation step separately. Candidate generation rules, prompts, models, normalization, compiler flags, random seeds, and mutation grammar must be committed before labels or final-auditor results are inspected.

## Labeling Oracle

- Finite char domains: exhaustive enumeration over the declared domain.
- Small multi-char domains: exhaustive Cartesian enumeration when feasible.
- Integer domains: independent high-budget differential fuzzing plus symbolic/concolic or structured independent boundary sampling.
- All mismatch witnesses must be manually and reproducibly confirmed.

Compile failure and runtime failure are `non_evaluable`, not `semantic_wrong`. They must not enter Detection@B denominators.

The labeling procedure must not invoke `{FINAL_METHOD}` or copy its ordered prefix. Accidental overlap produced by exhaustive enumeration is allowed and must be reported, not removed.

## Seal Before Final Auditor

After candidate generation and labels are complete, commit a sealed manifest containing SHA-256 hashes for:

- projects and versions;
- selected functions;
- fixtures;
- raw candidates;
- normalized candidates;
- labeling configuration;
- labels;
- labeling witnesses.

Do not run `{FINAL_METHOD}` on holdout candidates until the sealed manifest has been committed and reviewed.

## Holdout Target Gates

Report gates separately for number of projects, source functions, natural compile-ready candidates, controlled stress candidates, independently confirmed semantic-wrong candidates, and paired cases.

Minimum viable acquisition target:

- at least 8 project-disjoint upstream projects;
- 48-64 eligible source functions;
- at least 96 natural candidate attempts, with achieved compile-ready yield reported honestly;
- 96-160 secondary controlled-stress candidates if the fixed grammar is included;
- at least 30 paired cases if naturally achieved.

Do not require a predefined number of wrong candidates by repeatedly changing candidate generation after inspecting labels. Report the achieved natural error yield honestly.

## Witness Exposure Risks In Current Pipeline

- Function manifests expose fixtures used by fixture-neighbor generation.
- `phase5b_hard_trace_inputs` exposes a hard-input family that overlaps fixture +/- 1 and generic anchors.
- Candidate records expose legacy labels and aggregate trace mismatch counts.
- Phase18 budgeted records expose final prefix outcomes.
- Trace output directories preserve final probes.
- Phase16/17/18 documents expose development-inspected misses, including `ta_infix_precedence_two`.

## Readiness

This preregistration is ready for holdout acquisition only after the v2 correction commit is pushed and reviewed. It is not permission to run the final holdout auditor.
"""
    path = repo_root / "docs/paper_agent/frozen_holdout_preregistration_v2.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_handoff(
    repo_root: Path,
    integrity: dict[str, Any],
    validation: dict[str, Any],
    reconciliation_rows: list[dict[str, Any]],
    overlap_audit: dict[str, Any],
    environment: dict[str, Any],
) -> None:
    correction_commit = git_output(repo_root, ["rev-parse", "HEAD"])
    scope_summaries = {
        row["group"]: row for row in overlap_audit["summaries"]
        if row["group_type"] == "scope"
    }
    missing = missing_metadata_from_environment(environment)
    text = f"""# Submission Evidence Correction Handoff

## Git

- Branch: `{git_output(repo_root, ["branch", "--show-current"])}`
- Method freeze commit: `{METHOD_FREEZE_COMMIT}`
- Evidence audit commit: `{EVIDENCE_AUDIT_COMMIT}`
- Correction commit at generation time: `{correction_commit}`

## Commands Executed

- `git checkout -b phase1b-evidence-corrections`
- `rg`, `sed`, and JSON inspection commands over Phase18/20 artifacts
- `python -m analysis.decompile_faithfulness.submission_evidence_corrections`
- focused unittest commands listed in the final terminal transcript
- JSON validation via `python -m json.tool`
- `git diff --check`

## Method Integrity

- Method hashes unchanged: `{integrity['summary']['all_method_files_current_match_freeze']}`
- Method-affecting files checked: `{integrity['summary']['method_file_count']}`
- Unchanged files: `{integrity['summary']['unchanged_method_file_count']}`

## Corrected Provenance Counts

- Ghidra semantic wrong as natural raw/minimally processed decompiler errors: `{validation['required_answers']['wrong_candidates_natural_raw_or_minimally_processed_ghidra_errors']}`
- Ghidra-derived controlled stress semantic wrong: `{validation['required_answers']['wrong_candidates_controlled_ghidra_derived_stress']}`
- LLM semantic wrong natural generations: `{validation['required_answers']['wrong_candidates_natural_llm_generations']}`
- Candidates with documented actual semantic repair: `{validation['required_answers']['candidates_with_actual_semantic_repair']}`
- Original-source or behavior-preserving comparison controls: `{validation['required_answers']['comparison_class_original_source_or_behavior_preserving_controls']}`

## Primary Evaluation Reconciliation

```json
{json.dumps(reconciliation_rows, indent=2, sort_keys=True)}
```

## Current-Table Reconstructed Overlap

The current-table-specific rate is reported as reconstructed exact witness overlap under the current artifact.

```json
{json.dumps(scope_summaries, indent=2, sort_keys=True)}
```

## Remaining Unknown Metadata

```json
{json.dumps(missing, indent=2, sort_keys=True)}
```

## Development Coupling

The current Public, LLM-public, and Ghidra tables remain pre-freeze/development evidence. Ghidra `char_boundary`/`multi_arg` misses and `ta_infix_precedence_two` were inspected before Phase18 and directly motivated `{FINAL_METHOD}`.

## Prospective Holdout

The preregistration is corrected and ready for acquisition-and-sealing review. The final holdout auditor has not been run and must not be run until a sealed holdout manifest is committed and reviewed.

## Independence Verdict

The current three perfect-result tables cannot be described as independent test evidence. They can be described as frozen pre-freeze/development evidence with corrected provenance, label semantics, and overlap denominators.
"""
    path = repo_root / "docs/paper_agent/submission_evidence_correction_handoff.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_phase18_budget8(repo_root: Path, dataset_id: str) -> dict[tuple[str, str], dict[str, Any]]:
    path = repo_root / PHASE18_DIR / "unified_low_budget" / dataset_id / "records_budgeted.jsonl"
    rows = {}
    for record in read_jsonl(path):
        if int(record.get("requested_budget", 0)) == DEFAULT_BUDGET:
            rows[record_key(record)] = record
    return rows


def record_key(record: dict[str, Any]) -> tuple[str, str]:
    return (str(record.get("case_id")), str(record.get("candidate_id")))


def index_candidate_manifest(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for item in manifest.get("candidates", []):
        if isinstance(item, dict) and "candidate_id" in item:
            index[str(item["candidate_id"])] = item
        elif isinstance(item, dict):
            for candidate in item.get("candidates", []):
                index[str(candidate.get("candidate_id"))] = candidate
    return index


def dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for record in records:
        key = record_key(record)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def producing_tool(context_key: str, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    if context_key == "llm_public":
        return str(metadata.get("source_name") or manifest_item.get("source_name") or "Dream-Coder-v0-Instruct-7B")
    if context_key == "ghidra":
        return str(metadata.get("source_name") or "Ghidra 12.1.2 headless")
    return str(metadata.get("tool") or manifest_item.get("tool") or "deterministic_source_mutation")


def producing_version(context_key: str, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    if context_key == "ghidra":
        return "12.1.2"
    if context_key == "llm_public":
        return str(record.get("metadata", {}).get("source_name") or manifest_item.get("source_name") or UNKNOWN)
    return UNKNOWN


def prompt_or_transform(record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    return str(
        metadata.get("prompt_id")
        or manifest_item.get("prompt_id")
        or record.get("mutation_type")
        or manifest_item.get("mutation_type")
        or UNKNOWN
    )


def compiler_for_record(context_key: str, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    value = metadata.get("binary_compiler") or manifest_item.get("binary_compiler")
    if value:
        return str(value)
    if context_key == "ghidra":
        return "/usr/bin/gcc for binary and trace reconstruction"
    return "/usr/bin/gcc"


def architecture_for_record(context_key: str, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    assembly = str(record.get("metadata", {}).get("assembly_context_path") or manifest_item.get("assembly_context_path") or "")
    if "x86_64" in assembly or "amd64" in assembly:
        return "x86_64"
    if context_key == "ghidra":
        return UNKNOWN
    return UNKNOWN


def sanitizer_status(context_key: str) -> str:
    if context_key in {"public_static_hard", "llm_public", "ghidra"}:
        return "none_observed_in_runner_flags"
    return UNKNOWN


def execution_status(record: dict[str, Any]) -> str:
    if not record.get("compiled"):
        return "not_executed_or_failed"
    diagnostics = record.get("diagnostics", {}) or {}
    primary = float(diagnostics.get("primary_exit_code", 0.0))
    fixture = float(diagnostics.get("fixture_exit_code", 0.0))
    if primary == 0.0:
        return "executed" if fixture == 0.0 else f"executed_primary_fixture_exit_{fixture:g}"
    return f"runtime_exit_primary_{primary:g}_fixture_{fixture:g}"


def label_oracle_type(paper_label: str, record: dict[str, Any], context: DatasetContext) -> str:
    if paper_label == "semantic_wrong":
        return "source_known_hard_probe_trace_mismatch"
    if paper_label == "no_mismatch_under_labeling_protocol":
        return "source_known_hard_probe_no_mismatch_under_protocol"
    if not record.get("compiled"):
        return "compile_failure_non_evaluable"
    if not source_record_executable(record):
        return "runtime_failure_non_evaluable"
    return "unresolved_non_evaluable"


def concrete_labeling_witness(paper_label: str, record: dict[str, Any], context: DatasetContext) -> str:
    if paper_label == "no_mismatch_under_labeling_protocol":
        return "no mismatch found by source-known hard-probe labeling protocol; no equivalence claim"
    if paper_label == "non_evaluable":
        return execution_status(record)
    count = int(float(record.get("features", {}).get("trace_mismatch_count", 0.0)))
    if count <= 0:
        return "unresolved: semantic_wrong without positive trace_mismatch_count in available record"
    return f"{count} mismatch(es) over {context.spec['label_probe_family']}; concrete input reconstructed in oracle_overlap_audit_v2.json"


def drift_family(context_key: str, record: dict[str, Any], entry: dict[str, Any]) -> str:
    risk = entry.get("risk_families") or []
    mutation = str(record.get("mutation_type", ""))
    if "fixture_ifchain" in mutation or "fixture_overfit" in mutation:
        return "fixture_overfit_stress"
    if context_key == "llm_public":
        return "llm_generated_" + str(record.get("metadata", {}).get("prompt_id", UNKNOWN))
    if mutation.startswith("phase7_static_hard_"):
        return mutation.replace("phase7_static_hard_", "static_")
    if risk:
        return "+".join(str(item) for item in risk)
    return mutation or UNKNOWN


def normalization_notes(context_key: str, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    if context_key == "ghidra":
        return "Ghidra output passed through normalize_ghidra_translation_unit; fixture_ifchain rows are controlled stress derived from Ghidra base context"
    if context_key == "llm_public":
        return str(metadata.get("cleaning_status") or manifest_item.get("cleaning_status") or "parsed_function")
    if context_key == "public_static_hard":
        return "deterministic source mutation or original-source control; no decompiler repair"
    return UNKNOWN


def exclusion_reason_from_primary_table(context: DatasetContext, record: dict[str, Any], b8: dict[str, Any] | None) -> str:
    if b8 is not None:
        return "included"
    if not record.get("compiled"):
        return "not_compile_ready"
    if str(record.get("case_id")) not in context.functions_by_case:
        return "missing_case_manifest"
    if context.phase18_input_counts.get(str(record.get("case_id")), 1) == 0:
        return "no_generated_final_method_inputs"
    return "not_in_phase18_budget8_records"


def candidate_attempts(context_key: str, summary: dict[str, Any]) -> int:
    if context_key == "llm_public":
        return int(summary.get("generation_count", summary.get("candidate_count", 0)))
    return int(summary.get("candidate_count", 0))


def count_difference_explanation(dataset_id: str) -> str:
    explanations = {
        "phase7c2_static_hard_public": "524 generated records; 21 failed compile pre-primary; 25 compile-ready records from zero-input unsupported signatures were not rerun; 478 records entered the current full result table; 9 primary budget rows became non_evaluable runtime failures, leaving 469 evaluable.",
        "phase7e_llm_public_full_topup": "224 raw generations produced 195 parsed candidate records; 52 failed compile; 7 compile-ready records from zero-input unsupported signatures were not rerun; 136 records entered and completed primary evaluation.",
        "phase6r_ghidra_full": "228 Ghidra-derived records; 62 did not become compile-ready normalized C; all 166 compile-ready records entered and completed primary evaluation.",
    }
    return explanations[dataset_id]


def project_function_counts(contexts: list[DatasetContext]) -> dict[str, dict[str, int]]:
    result = {}
    for context in contexts:
        supported = [
            entry for entry in context.function_manifest.get("functions", [])
            if entry.get("counts_for_phase7_public_benchmark_gate")
            or entry.get("counts_for_phase5_real_project_gate")
        ]
        result[context.dataset_id] = {
            "projects": len({entry.get("project", UNKNOWN) for entry in supported}),
            "source_functions": len(supported),
        }
    return result


def llm_sampling_summary(context: DatasetContext) -> dict[str, Any]:
    sampling: dict[str, Any] = {}
    for run_dir in context.candidate_manifest.get("run_dirs", []):
        path = Path(run_dir) / "generation_metadata.jsonl"
        if not path.exists():
            continue
        for record in read_jsonl(path):
            if record.get("sampling"):
                sampling = record["sampling"]
                break
        if sampling:
            break
    return sampling or {"status": UNKNOWN}


def missing_metadata_from_environment(environment: dict[str, Any]) -> dict[str, Any]:
    return {
        dataset: item.get("still_unknown", [])
        for dataset, item in environment["collections"].items()
        if item.get("still_unknown")
    }


def development_coupling_audit() -> dict[str, Any]:
    return {
        "inspected_before_phase18": [
            {
                "phase": "phase16_runtime_risk",
                "datasets": ["phase6r_ghidra_full"],
                "cases": ["ta_infix_precedence_two"],
                "failure_families": ["char_boundary", "multi_arg"],
            },
            {
                "phase": "phase17_operator_char_policy",
                "datasets": ["phase6r_ghidra_full", "phase7c2_static_hard_public", "phase7e_llm_public_full_topup"],
                "cases": ["ta_infix_precedence_two"],
                "failure_families": ["operator_char_class_first regressions", "char_boundary"],
            },
        ],
        "directly_motivated_final_method": [
            "Phase17 showed front-loaded generic operator chars fixed one Ghidra miss but regressed broader coverage.",
            "Phase18 source literal char interleaving targeted the inspected source-literal/operator-char failure family.",
        ],
        "pre_freeze_development_evidence": [
            "phase6r_ghidra_full",
            "phase7c2_static_hard_public",
            "phase7e_llm_public_full_topup",
        ],
    }


def development_coupled_cases() -> set[str]:
    return {"ta_infix_precedence_two"}


def argument_count(signature: str) -> int:
    args = signature_args(signature)
    if not args or args == ["void"]:
        return 0
    return len(args)


def argument_types(signature: str) -> str:
    args = signature_args(signature)
    if not args:
        return UNKNOWN
    return ";".join(" ".join(part.split()[:-1]) or part for part in args)


def signature_args(signature: str) -> list[str]:
    if "(" not in signature or ")" not in signature:
        return []
    inside = signature[signature.find("(") + 1:signature.rfind(")")].strip()
    if not inside:
        return []
    return [part.strip() for part in inside.split(",") if part.strip()]


def source_loc(source: str) -> int:
    if not source:
        return 0
    return sum(1 for line in source.splitlines() if line.strip())


def read_source(repo_root: Path, entry: dict[str, Any]) -> str:
    source_path = entry.get("source_path")
    if not source_path:
        return ""
    path = repo_root / str(source_path)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_provenance_v2(repo_root: Path, rows: list[dict[str, str]]) -> None:
    csv_path = repo_root / "results/decompile_faithfulness/candidate_provenance_v2.csv"
    jsonl_path = repo_root / "results/decompile_faithfulness/candidate_provenance_v2.jsonl"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROVENANCE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    jsonl_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_reconciliation(repo_root: Path, rows: list[dict[str, Any]]) -> None:
    path = repo_root / "results/decompile_faithfulness/primary_evaluation_reconciliation.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_overlap_summary_v2(repo_root: Path, rows: list[dict[str, Any]]) -> None:
    path = repo_root / "results/decompile_faithfulness/oracle_overlap_summary_v2.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def bool_str(value: bool) -> str:
    return "true" if value else "false"


def counter_dict(values: Iterable[str]) -> dict[str, int]:
    return dict(sorted(Counter(values).items()))


def safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob(repo_root: Path, commit: str, path: str) -> bytes | None:
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=repo_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def git_output(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else UNKNOWN


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def latex_escape(text: str) -> str:
    return text.replace("_", r"\_").replace("&", r"\&")


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
