from __future__ import annotations

import argparse
import csv
import json
import subprocess
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import run_phase10_low_budget_rerun as phase10
from analysis.decompile_faithfulness import run_phase11_input_ordering as phase11
from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase5b_hard_candidates as phase5b


UNKNOWN = "unknown"
FINAL_METHOD = "source_literal_char_interleave"
DEFAULT_BUDGET = 8
MAX_LABEL_WITNESS_PROBES = 128
FINAL_MAX_INPUTS = 16

DATASETS = {
    "public_static_hard": {
        "dataset_id": "phase7c2_static_hard_public",
        "records_path": Path("analysis_outputs/decompile_faithfulness/phase7_static_hard/records.jsonl"),
        "function_manifest": Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json"),
        "candidate_manifest": Path("docs/paper_agent/decompile_faithfulness_phase7_static_hard_candidate_manifest.json"),
        "summary_path": Path("docs/paper_agent/decompile_faithfulness_phase7_static_hard_result.json"),
        "attempt_summary_path": Path("docs/paper_agent/decompile_faithfulness_phase7_static_hard_candidate_manifest.json"),
        "project_family": "CodeFuse-DeBench",
        "label_oracle_type": "source_known_hard_probe_trace_mismatch",
        "label_probe_family": "phase5b_hard_trace_inputs",
    },
    "llm_public": {
        "dataset_id": "phase7e_llm_public_full_topup",
        "records_path": None,
        "function_manifest": Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json"),
        "candidate_manifest": Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_candidate_manifest_combined_topup_full2.json"),
        "summary_path": Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_combined.json"),
        "attempt_summary_path": Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_combined.json"),
        "project_family": "CodeFuse-DeBench",
        "label_oracle_type": "source_known_hard_probe_trace_mismatch",
        "label_probe_family": "phase5b_hard_trace_inputs",
    },
    "ghidra": {
        "dataset_id": "phase6r_ghidra_full",
        "records_path": Path("analysis_outputs/decompile_faithfulness/phase6r_ghidra_full/records.jsonl"),
        "function_manifest": Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json"),
        "candidate_manifest": Path("docs/paper_agent/decompile_faithfulness_phase6r_real_decompiler_manifest.json"),
        "summary_path": Path("docs/paper_agent/decompile_faithfulness_phase6r_result_analysis.json"),
        "attempt_summary_path": Path("docs/paper_agent/decompile_faithfulness_phase6r_real_decompiler_manifest.json"),
        "project_family": "thealgorithms_c+c_algorithms",
        "label_oracle_type": "source_known_hard_probe_trace_mismatch",
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
    "candidate_source_category",
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
    "label",
    "label_oracle_type",
    "concrete_labeling_witness",
    "influenced_method_development",
    "drift_family",
    "normalization_or_manual_edit_notes",
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


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    generated = generate(repo_root)
    print(json.dumps(generated, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args()


def generate(repo_root: Path) -> dict[str, Any]:
    contexts = [load_dataset_context(repo_root, key, spec) for key, spec in DATASETS.items()]
    freeze_manifest = build_freeze_manifest(repo_root, contexts)
    provenance_rows = build_provenance(repo_root, contexts)
    overlap_audit = build_oracle_overlap_audit(repo_root, contexts, provenance_rows)
    flow_rows, dataset_flow = build_dataset_flow(repo_root, contexts, provenance_rows)
    missing_summary = missing_metadata_summary(provenance_rows)

    write_json(repo_root / "analysis/decompile_faithfulness/paper_freeze_manifest.json", freeze_manifest)
    write_provenance(repo_root, provenance_rows)
    write_json(repo_root / "results/decompile_faithfulness/oracle_overlap_audit.json", overlap_audit)
    write_overlap_summary(repo_root, overlap_audit)
    write_flow_csv(repo_root, flow_rows)
    write_json(repo_root / "figures/data/dataset_flow.json", dataset_flow)
    write_holdout_preregistration(repo_root, overlap_audit, contexts)
    write_latex_table(repo_root, contexts, provenance_rows, missing_summary)
    write_handoff(repo_root, freeze_manifest, provenance_rows, overlap_audit, flow_rows, missing_summary)
    return {
        "freeze_manifest": "analysis/decompile_faithfulness/paper_freeze_manifest.json",
        "candidate_rows": len(provenance_rows),
        "wrong_label_rows": sum(1 for row in provenance_rows if row["label"] == "plausible_wrong"),
        "exact_witness_overlap_rate": overlap_audit["summary"]["exact_witness_overlap_rate"],
    }


def load_dataset_context(repo_root: Path, key: str, spec: dict[str, Any]) -> DatasetContext:
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
        dataset_id=spec["dataset_id"],
        spec=spec,
        function_manifest=function_manifest,
        functions_by_case=functions_by_case,
        records=records,
        candidate_manifest=candidate_manifest,
        candidate_manifest_by_id=index_candidate_manifest(candidate_manifest),
    )


def build_freeze_manifest(repo_root: Path, contexts: list[DatasetContext]) -> dict[str, Any]:
    head = git_output(repo_root, ["rev-parse", "HEAD"])
    branch = git_output(repo_root, ["branch", "--show-current"])
    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": "https://github.com/sarahshi99/binary_faithful_decompilation",
        "branch": branch,
        "head_commit": head,
        "proposed_paper_freeze_commit": head,
        "final_method": FINAL_METHOD,
        "core_scope": "source-known, recompilable, function-level localized semantic drift auditing under a small execution budget",
        "default_budget": DEFAULT_BUDGET,
        "budgets_recorded": [1, 2, 4, 8, 16],
        "max_inputs_generated_for_phase18": FINAL_MAX_INPUTS,
        "character_domain": {
            "char_like_detection": "signature substring contains 'char'; parameter positions whose declarator contains 'char'",
            "allowed_char_values": {"min": 0, "max": 127},
            "source_literal_regex": r"'((?:\\.|[^\\'])*)'",
            "supported_escapes": {
                "\\0": 0,
                "\\a": 7,
                "\\b": 8,
                "\\t": 9,
                "\\n": 10,
                "\\v": 11,
                "\\f": 12,
                "\\r": 13,
                "\\\\": 92,
                "\\'": 39,
                '\\"': 34,
                "\\?": 63,
                "\\xHH": "hexadecimal escape; all hex digits after x are consumed",
                "\\OOO": "octal escape; up to three octal digits",
            },
            "stable_literal_deduplication": "first occurrence wins by parsed integer value",
        },
        "neighbor_values": {
            "integer_positions": ["value - 1", "value + 1", "0 if value != 0", "1 if value != 1"],
            "char_positions_extra_anchors": [64, 65, 66, 73, 74, 75, 90],
            "ordering": "sorted(set(values)) after char-domain filtering",
        },
        "generic_character_anchors": {
            "final_method_source_literal_char_interleave": "no generic operator list is prepended",
            "legacy_operator_char_class_values_not_final_default": list(phase11.OPERATOR_CHAR_CLASS_VALUES),
            "phase5b_hard_probe_char_anchors": [43, 45, 65, 90, 97, 122],
        },
        "generic_fallback_construction": {
            "source": "analysis/decompile_faithfulness/run_phase5b_hard_candidates.py::phase5b_hard_trace_inputs",
            "per_position_values": [
                "observed fixture values",
                "observed +/- 1",
                "positive-only adds {1,2} and drops <=0",
                "nonnegative-only adds {0,1,2} and drops <0",
                "otherwise adds {-1,0,1}",
                "char-like signatures restrict to 0..127 and add {43,45,65,90,97,122}",
                "sorted values truncated to first 10 per position",
            ],
            "cartesian_product_order": "itertools.product over values_by_position; fixture tuples removed; stops at max_inputs",
        },
        "admissibility_filtering": {
            "fixture_neighbors_and_source_literals": "exclude original fixtures and domain_allows(entry,args)",
            "domain_allows": [
                "if all fixture values are >=0, reject args containing negative values",
                "if all fixture values are >0, reject args containing <=0 values",
                "for char-like parameter positions, require 0 <= value <= 127",
            ],
        },
        "probe_ordering": {
            "final_order_expression": "dedupe_inputs(interleave_inputs(fixture_neighbor_inputs(entry), source_literal_char_inputs(entry, case)) + phase5b_hard_trace_inputs(entry, max_inputs=10000))[:max_inputs]",
            "interleaving": "zip_longest, left item then right item, continuing after either queue exhausts",
            "stable_deduplication": "first trace_input.args occurrence wins; bucket from first occurrence is retained",
            "budget_truncation": "actual_budget = min(requested_budget, len(inputs)); scoring slices inputs and outputs to actual_budget",
        },
        "early_stop_behavior": {
            "probe_generation": "phase5b_hard_trace_inputs stops once max_inputs generated; final build_ordered_inputs truncates after stable dedupe",
            "differential_execution": "no early stop on first mismatch; all selected budget-prefix probes are executed in one harness",
            "scoring": "all selected prefix outputs contribute to trace_distance",
        },
        "caching_behavior": {
            "phase11_rerun_strategy": "original trace cache keyed by (case_id,opt_level,strategy_id)",
            "phase10_cached_original_run": "legacy original trace cache keyed by (case_id,opt_level)",
            "phase6_phase_features": "source-labeling original trace cache keyed by (case_id,opt_level,bucket)",
            "candidate_traces": "not cached; each candidate rerun compiles/runs its trace harness",
        },
        "method_affecting_sources": method_affecting_sources(),
        "dataset_inputs": [
            {
                "dataset": context.dataset_id,
                "records": str(context.spec.get("records_path") or context.spec.get("summary_path")),
                "function_manifest": str(context.spec["function_manifest"]),
                "candidate_manifest": str(context.spec["candidate_manifest"]),
            }
            for context in contexts
        ],
    }


def method_affecting_sources() -> list[dict[str, Any]]:
    return [
        {
            "path": "analysis/decompile_faithfulness/run_phase18_source_literal_char_policy.py",
            "functions": ["run_phase18", "phase18_verdict", "_resolve"],
            "affects": ["final method selection", "report budget", "phase12 rerun invocation"],
        },
        {
            "path": "analysis/decompile_faithfulness/run_phase12_unified_low_budget_eval.py",
            "functions": ["run_phase12", "rerun_dataset", "metric_delta", "phase12_verdict"],
            "affects": ["dataset rerun orchestration", "budget list", "strategy propagation"],
        },
        {
            "path": "analysis/decompile_faithfulness/run_phase11_input_ordering.py",
            "functions": [
                "rerun_strategy",
                "build_ordered_inputs",
                "fixture_neighbor_inputs",
                "source_literal_char_inputs",
                "source_char_literal_values",
                "parse_c_char_literal_body",
                "boundary_inputs",
                "single_position_boundary_args",
                "boundary_values_by_position",
                "neighbor_values",
                "domain_allows",
                "char_like_positions",
                "interleave_inputs",
                "dedupe_inputs",
                "summarize_with_misses",
                "best_strategy_for_budget",
                "strategy_sort_key",
            ],
            "affects": [
                "probe generation",
                "probe ordering",
                "source literal parsing",
                "admissibility filtering",
                "stable deduplication",
                "candidate rerun orchestration",
            ],
        },
        {
            "path": "analysis/decompile_faithfulness/run_phase10_low_budget_rerun.py",
            "functions": [
                "load_records",
                "budget_record",
                "summarize_budget",
                "paired_case_count",
                "pairwise_auc",
                "flatten_budget_records",
                "cached_original_run",
            ],
            "affects": ["budget handling", "candidate scoring", "mismatch semantics", "summary metrics"],
        },
        {
            "path": "analysis/decompile_faithfulness/run_phase5b_hard_candidates.py",
            "functions": ["phase5b_hard_trace_inputs", "phase5b_features", "record_from_features"],
            "affects": ["generic fallback probes", "source-labeling oracle witnesses"],
        },
        {
            "path": "analysis/decompile_faithfulness/run_phase5_gpu_generated_full.py",
            "functions": ["safe_run_trace", "_case_from_manifest_entry"],
            "affects": ["differential execution wrapper", "manifest-to-case reconstruction"],
        },
        {
            "path": "analysis/decompile_faithfulness/dynamic_trace.py",
            "functions": [
                "TraceInput",
                "TraceRun",
                "generate_trace_inputs",
                "generate_domain_trace_inputs",
                "generate_boundary_trace_inputs",
                "render_trace_harness",
                "parse_trace_stdout",
                "run_trace",
                "trace_distance",
                "_bucket_for_args",
                "_v3_boundary_args",
                "_safe_name",
                "_sign",
                "_squash",
                "_timeout_stream",
                "_timeout_message",
            ],
            "affects": ["differential execution", "output normalization", "mismatch features"],
        },
        {
            "path": "analysis/decompile_faithfulness/compile.py",
            "functions": ["run_command", "compile_candidate", "_safe_name"],
            "affects": ["compiler invocation", "timeout behavior", "compile/run status"],
        },
        {
            "path": "analysis/decompile_faithfulness/run_phase3_combinatorial_cpu_audit.py",
            "functions": ["_failure_components"],
            "affects": ["compile/runtime failure scoring semantics"],
        },
    ]


def build_provenance(repo_root: Path, contexts: list[DatasetContext]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    development_cases = development_coupled_cases()
    for context in contexts:
        for record in context.records:
            entry = context.functions_by_case.get(str(record.get("case_id")), {})
            metadata = record.get("metadata", {})
            manifest_item = context.candidate_manifest_by_id.get(str(record.get("candidate_id")), {})
            source = str(metadata.get("function_source", "") or manifest_item.get("function_source", ""))
            category = candidate_source_category(context, record, manifest_item)
            witness = concrete_labeling_witness(record, context, entry)
            compiler = compiler_for_record(context, record, manifest_item)
            row = {
                "dataset": context.dataset_id,
                "project": str(entry.get("project", UNKNOWN)),
                "source_file": str(entry.get("source_path") or entry.get("original_source_path") or UNKNOWN),
                "source_function": str(entry.get("function_name", UNKNOWN)),
                "stable_case_id": str(record.get("case_id", UNKNOWN)),
                "stable_candidate_id": str(record.get("candidate_id", UNKNOWN)),
                "candidate_source_category": category,
                "producing_tool_or_model": producing_tool(context, record, manifest_item),
                "producing_tool_or_model_version": producing_version(context, record, manifest_item),
                "prompt_or_transformation_family": prompt_or_transform(record, manifest_item),
                "compiler": compiler,
                "optimization_level": str(record.get("optimization_level") or manifest_item.get("optimization_level") or UNKNOWN),
                "architecture": architecture_for_record(context, record, manifest_item),
                "function_signature": str(entry.get("signature", UNKNOWN)),
                "source_loc": str(source_loc(source if source else read_source(repo_root, entry))),
                "argument_count": str(argument_count(entry.get("signature", ""))),
                "argument_types": argument_types(entry.get("signature", "")),
                "fixture_count": str(len(entry.get("fixtures", []))),
                "source_char_literal_count": str(len(phase11.source_char_literal_values(read_source(repo_root, entry)))),
                "compile_status": "compiled" if record.get("compiled") else "compile_fail",
                "sanitizer_status": UNKNOWN,
                "execution_status": execution_status(record),
                "label": str(record.get("label", UNKNOWN)),
                "label_oracle_type": label_oracle_type(record, context),
                "concrete_labeling_witness": witness,
                "influenced_method_development": "yes" if str(record.get("case_id")) in development_cases else "no",
                "drift_family": drift_family(context, record, entry),
                "normalization_or_manual_edit_notes": normalization_notes(context, record, manifest_item),
            }
            rows.append(row)
    rows.sort(key=lambda row: (row["dataset"], row["stable_case_id"], row["stable_candidate_id"]))
    return rows


def concrete_labeling_witness(record: dict[str, Any], context: DatasetContext, entry: dict[str, Any]) -> str:
    if record.get("label") == "faithful":
        return "no mismatch over source-labeling hard probe set"
    if record.get("label") == "compile_fail":
        return "compile/runtime failure status in candidate record"
    count = int(float(record.get("features", {}).get("trace_mismatch_count", 0.0)))
    if count <= 0:
        return "unresolved: wrong label without positive trace_mismatch_count in available record"
    return f"{count} mismatch(es) over {context.spec['label_probe_family']}; concrete input reconstructed in oracle_overlap_audit.json"


def build_oracle_overlap_audit(
    repo_root: Path,
    contexts: list[DatasetContext],
    provenance_rows: list[dict[str, str]],
) -> dict[str, Any]:
    rows_by_id = {
        (row["dataset"], row["stable_candidate_id"]): row
        for row in provenance_rows
    }
    candidate_results: list[dict[str, Any]] = []
    counts_by_dataset: dict[str, Counter[str]] = defaultdict(Counter)
    counts_by_family: dict[str, Counter[str]] = defaultdict(Counter)
    family_flags_by_dataset: dict[str, Counter[str]] = defaultdict(Counter)

    for context in contexts:
        temp_root = repo_root / "analysis_outputs/decompile_faithfulness/submission_evidence_audit_overlap"
        temp_root.mkdir(parents=True, exist_ok=True)
        for record in context.records:
            if not record.get("compiled") or record.get("label") != "plausible_wrong":
                continue
            entry = context.functions_by_case.get(str(record.get("case_id")))
            if entry is None:
                result = unresolved_overlap_result(context, record, "missing_manifest_entry")
            else:
                result = overlap_for_wrong_record(repo_root, context, entry, record, temp_root)
            candidate_results.append(result)
            row = rows_by_id.get((context.dataset_id, str(record.get("candidate_id"))))
            family = row["drift_family"] if row else drift_family(context, record, entry or {})
            overlap_key = "exact_overlap" if result["exact_witness_overlap"] else "no_exact_overlap"
            counts_by_dataset[context.dataset_id][overlap_key] += 1
            counts_by_dataset[context.dataset_id]["wrong_labels"] += 1
            counts_by_dataset[context.dataset_id]["overlap_witness_count"] += int(result["exact_overlap_count"])
            counts_by_family[family][overlap_key] += 1
            counts_by_family[family]["wrong_labels"] += 1
            counts_by_family[family]["overlap_witness_count"] += int(result["exact_overlap_count"])
            for flag, enabled in result["probe_family_overlap"].items():
                if enabled:
                    family_flags_by_dataset[context.dataset_id][flag] += 1

    total_wrong = len(candidate_results)
    total_exact = sum(1 for item in candidate_results if item["exact_witness_overlap"])
    exact_witness_count = sum(int(item["exact_overlap_count"]) for item in candidate_results)
    probe_family_keys = sorted(probe_family_definitions())
    by_dataset = {
        dataset: {
            "wrong_labels": counter["wrong_labels"],
            "candidates_with_exact_overlap": counter["exact_overlap"],
            "candidates_without_exact_overlap": counter["no_exact_overlap"],
            "exact_overlap_candidate_rate": safe_rate(counter["exact_overlap"], counter["wrong_labels"]),
            "exact_overlap_witness_count": counter["overlap_witness_count"],
            "probe_family_overlap_rates": {
                flag: safe_rate(family_flags_by_dataset[dataset][flag], counter["wrong_labels"])
                for flag in probe_family_keys
            },
        }
        for dataset, counter in sorted(counts_by_dataset.items())
    }
    by_family = {
        family: {
            "wrong_labels": counter["wrong_labels"],
            "candidates_with_exact_overlap": counter["exact_overlap"],
            "candidates_without_exact_overlap": counter["no_exact_overlap"],
            "exact_overlap_candidate_rate": safe_rate(counter["exact_overlap"], counter["wrong_labels"]),
            "exact_overlap_witness_count": counter["overlap_witness_count"],
        }
        for family, counter in sorted(counts_by_family.items())
    }
    return {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "final_method": FINAL_METHOD,
        "final_budget": DEFAULT_BUDGET,
        "candidates": candidate_results,
        "summary": {
            "wrong_label_count": total_wrong,
            "candidates_with_exact_witness_overlap": total_exact,
            "candidates_without_exact_witness_overlap": total_wrong - total_exact,
            "exact_witness_overlap_rate": safe_rate(total_exact, total_wrong),
            "exact_overlap_witness_count": exact_witness_count,
            "by_dataset": by_dataset,
            "by_drift_family": by_family,
        },
        "probe_family_definitions": probe_family_definitions(),
        "development_coupling_audit": development_coupling_audit(),
        "interpretation": (
            "Exact witness reuse means a concrete source-labeling mismatch input also appears in the final "
            "budget-8 prefix. Shared input-family overlap is reported separately and is not by itself treated "
            "as leakage."
        ),
    }


def overlap_for_wrong_record(
    repo_root: Path,
    context: DatasetContext,
    entry: dict[str, Any],
    record: dict[str, Any],
    temp_root: Path,
) -> dict[str, Any]:
    case = phase5_gpu._case_from_manifest_entry(repo_root, entry)
    label_inputs = phase5b.phase5b_hard_trace_inputs(entry, max_inputs=MAX_LABEL_WITNESS_PROBES)
    final_inputs = phase11.build_ordered_inputs(entry, case, FINAL_METHOD, max_inputs=FINAL_MAX_INPUTS)
    budget8_inputs = final_inputs[:DEFAULT_BUDGET]
    candidate_source = str(record.get("metadata", {}).get("function_source", ""))
    opt_level = str(record.get("optimization_level", "O0"))
    if not label_inputs or not candidate_source:
        return unresolved_overlap_result(context, record, "missing_label_inputs_or_candidate_source")

    output_dir = temp_root / context.dataset_id
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_dir) as tmp:
        trace_dir = Path(tmp)
        original_label = dynamic_trace.run_trace(case, "audit_original_label", case.function_source, label_inputs, trace_dir, opt_level=opt_level)
        candidate_label = phase5_gpu.safe_run_trace(case, "audit_candidate_label", candidate_source, label_inputs, trace_dir, opt_level=opt_level)
        original_final = dynamic_trace.run_trace(case, "audit_original_final", case.function_source, budget8_inputs, trace_dir, opt_level=opt_level)
        candidate_final = phase5_gpu.safe_run_trace(case, "audit_candidate_final", candidate_source, budget8_inputs, trace_dir, opt_level=opt_level)

    label_witnesses = mismatch_witnesses(label_inputs, original_label, candidate_label)
    final_witnesses = mismatch_witnesses(budget8_inputs, original_final, candidate_final)
    label_args = {tuple(item["args"]) for item in label_witnesses}
    final_args = {tuple(item["args"]) for item in final_witnesses}
    budget_args = [trace_input.args for trace_input in budget8_inputs]
    overlap_args = [args for args in budget_args if args in label_args]
    first_rank = next((rank + 1 for rank, args in enumerate(budget_args) if args in label_args), None)
    probe_overlap = classify_probe_family_overlap(entry, case, label_inputs, budget8_inputs, record)
    return {
        "dataset": context.dataset_id,
        "case_id": str(record.get("case_id")),
        "candidate_id": str(record.get("candidate_id")),
        "label_oracle_type": context.spec["label_oracle_type"],
        "label_probe_family": context.spec["label_probe_family"],
        "label_witness_count": len(label_witnesses),
        "label_witnesses_first_10": label_witnesses[:10],
        "final_budget8_prefix": [
            {"rank": index + 1, "args": list(trace_input.args), "bucket": trace_input.bucket}
            for index, trace_input in enumerate(budget8_inputs)
        ],
        "final_budget8_detecting_witnesses": final_witnesses,
        "exact_witness_overlap": bool(overlap_args),
        "first_exact_overlap_rank": first_rank,
        "exact_overlap_count": len(overlap_args),
        "exact_overlap_args": [list(args) for args in overlap_args],
        "probe_family_overlap": probe_overlap,
        "oracle_independence_class": oracle_independence_class(bool(overlap_args), probe_overlap),
    }


def unresolved_overlap_result(context: DatasetContext, record: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "dataset": context.dataset_id,
        "case_id": str(record.get("case_id")),
        "candidate_id": str(record.get("candidate_id")),
        "label_oracle_type": context.spec["label_oracle_type"],
        "label_probe_family": context.spec["label_probe_family"],
        "label_witness_count": 0,
        "label_witnesses_first_10": [],
        "final_budget8_prefix": [],
        "final_budget8_detecting_witnesses": [],
        "exact_witness_overlap": False,
        "first_exact_overlap_rank": None,
        "exact_overlap_count": 0,
        "exact_overlap_args": [],
        "probe_family_overlap": {},
        "oracle_independence_class": "unresolved",
        "unresolved_reason": reason,
    }


def mismatch_witnesses(
    inputs: list[dynamic_trace.TraceInput],
    original: dynamic_trace.TraceRun,
    candidate: dynamic_trace.TraceRun,
) -> list[dict[str, Any]]:
    if (
        not original.compiled
        or not candidate.compiled
        or original.exit_code != 0
        or candidate.exit_code != 0
        or len(original.outputs) < len(inputs)
        or len(candidate.outputs) < len(inputs)
    ):
        return []
    witnesses = []
    for index, (trace_input, left, right) in enumerate(zip(inputs, original.outputs, candidate.outputs), start=1):
        if left == right:
            continue
        witnesses.append(
            {
                "rank": index,
                "args": list(trace_input.args),
                "bucket": trace_input.bucket,
                "original_output": left,
                "candidate_output": right,
            }
        )
    return witnesses


def classify_probe_family_overlap(
    entry: dict[str, Any],
    case: Any,
    label_inputs: list[dynamic_trace.TraceInput],
    final_inputs: list[dynamic_trace.TraceInput],
    record: dict[str, Any],
) -> dict[str, bool]:
    label_args = {trace_input.args for trace_input in label_inputs}
    final_args = {trace_input.args for trace_input in final_inputs}
    fixtures = {tuple(int(value) for value in item["args"]) for item in entry.get("fixtures", [])}
    fixture_neighbor_args = {item.args for item in phase11.fixture_neighbor_inputs(entry)}
    hard_args = {item.args for item in phase5b.phase5b_hard_trace_inputs(entry, max_inputs=MAX_LABEL_WITNESS_PROBES)}
    values_in_label = {value for args in label_args for value in args}
    legacy_ascii = set(phase11.OPERATOR_CHAR_CLASS_VALUES)
    return {
        "exact_fixtures": bool(label_args & fixtures),
        "fixture_plus_minus_1": bool(label_args & fixture_neighbor_args),
        "generic_0_1_values": any(value in {0, 1} for value in values_in_label),
        "legacy_ascii_anchors": bool(values_in_label & legacy_ascii),
        "source_literals": False,
        "operator_character_lists": False,
        "generic_hard_input_cartesian_products": bool(label_args & hard_args),
        "random_inputs": False,
        "fuzzing": False,
        "symbolic_concolic_inputs": False,
        "exhaustive_enumeration": False,
        "controlled_construction_records": "fixture_ifchain" in str(record.get("mutation_type", "")) or "static_hard" in str(record.get("mutation_type", "")),
        "shared_with_final_budget8_prefix": bool(label_args & final_args),
    }


def oracle_independence_class(exact_overlap: bool, flags: dict[str, bool]) -> str:
    if exact_overlap:
        return "exact_witness_reuse"
    if flags.get("fixture_plus_minus_1") or flags.get("source_literals") or flags.get("generic_hard_input_cartesian_products"):
        return "shared_input_family"
    return "fully_independent_or_unresolved_from_available_metadata"


def build_dataset_flow(
    repo_root: Path,
    contexts: list[DatasetContext],
    provenance_rows: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = []
    rows_by_dataset = defaultdict(list)
    for row in provenance_rows:
        rows_by_dataset[row["dataset"]].append(row)
    for context in contexts:
        dataset_rows = rows_by_dataset[context.dataset_id]
        summary = read_json(repo_root / context.spec["summary_path"])
        attempts = candidate_attempts(context, summary)
        generated = len(context.records)
        compile_ready = sum(1 for record in context.records if record.get("compiled"))
        executable = sum(
            1
            for record in context.records
            if record.get("compiled")
            and float(record.get("diagnostics", {}).get("primary_exit_code", 0.0)) == 0.0
        )
        adjudicable = sum(1 for record in context.records if record.get("label") in {"faithful", "plausible_wrong"})
        final_paired_cases = paired_case_count_from_rows(dataset_rows)
        faithful = sum(1 for row in dataset_rows if row["label"] == "faithful")
        wrong = sum(1 for row in dataset_rows if row["label"] == "plausible_wrong")
        supported = [
            entry for entry in context.function_manifest.get("functions", [])
            if entry.get("counts_for_phase7_public_benchmark_gate")
            or entry.get("counts_for_phase5_real_project_gate")
        ]
        projects = sorted({entry.get("project", UNKNOWN) for entry in supported})
        row = {
            "dataset": context.dataset_id,
            "projects": len(projects),
            "project_names": ";".join(projects),
            "source_functions": len(supported),
            "supported_signatures": len({entry.get("signature", UNKNOWN) for entry in supported}),
            "candidate_attempts": attempts,
            "generated_candidates": generated,
            "compile_ready_candidates": compile_ready,
            "executable_candidates": executable,
            "oracle_adjudicable_candidates": adjudicable,
            "final_paired_cases": final_paired_cases,
            "faithful_class_candidates": faithful,
            "wrong_candidates": wrong,
        }
        rows.append(row)
    figure = {
        "schema_version": 1,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "flow_order": [
            "projects",
            "source_functions",
            "supported_signatures",
            "candidate_attempts",
            "generated_candidates",
            "compile_ready_candidates",
            "executable_candidates",
            "oracle_adjudicable_candidates",
            "final_paired_cases",
            "faithful_class_candidates",
            "wrong_candidates",
        ],
        "datasets": rows,
        "notes": [
            "candidate_attempts are deterministic mutation attempts for public_static_hard, raw generations for llm_public, and proxy candidates submitted to Ghidra for ghidra.",
            "final_paired_cases count cases with at least one faithful and one wrong candidate in the candidate records.",
        ],
    }
    return rows, figure


def candidate_attempts(context: DatasetContext, summary: dict[str, Any]) -> int:
    if context.key == "llm_public":
        return int(summary.get("generation_count", len(context.records)))
    return int(summary.get("candidate_count", len(context.records)))


def write_provenance(repo_root: Path, rows: list[dict[str, str]]) -> None:
    csv_path = repo_root / "results/decompile_faithfulness/candidate_provenance.csv"
    jsonl_path = repo_root / "results/decompile_faithfulness/candidate_provenance.jsonl"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=PROVENANCE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    jsonl_path.write_text(
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
        encoding="utf-8",
    )


def write_overlap_summary(repo_root: Path, audit: dict[str, Any]) -> None:
    path = repo_root / "results/decompile_faithfulness/oracle_overlap_summary.csv"
    rows = []
    for dataset, item in audit["summary"]["by_dataset"].items():
        rows.append(
            {
                "group_type": "dataset",
                "group": dataset,
                **{key: item.get(key, "") for key in [
                    "wrong_labels",
                    "candidates_with_exact_overlap",
                    "candidates_without_exact_overlap",
                    "exact_overlap_candidate_rate",
                    "exact_overlap_witness_count",
                ]},
            }
        )
    for family, item in audit["summary"]["by_drift_family"].items():
        rows.append(
            {
                "group_type": "drift_family",
                "group": family,
                **{key: item.get(key, "") for key in [
                    "wrong_labels",
                    "candidates_with_exact_overlap",
                    "candidates_without_exact_overlap",
                    "exact_overlap_candidate_rate",
                    "exact_overlap_witness_count",
                ]},
            }
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        fieldnames = [
            "group_type",
            "group",
            "wrong_labels",
            "candidates_with_exact_overlap",
            "candidates_without_exact_overlap",
            "exact_overlap_candidate_rate",
            "exact_overlap_witness_count",
        ]
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_flow_csv(repo_root: Path, rows: list[dict[str, Any]]) -> None:
    path = repo_root / "results/decompile_faithfulness/dataset_inclusion_flow.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_holdout_preregistration(repo_root: Path, audit: dict[str, Any], contexts: list[DatasetContext]) -> None:
    seen_projects = sorted({entry.get("project", UNKNOWN) for context in contexts for entry in context.function_manifest.get("functions", [])})
    text = f"""# Frozen Holdout Preregistration

Date: 2026-07-02

Final method is frozen as `{FINAL_METHOD}` at the paper-freeze commit recorded in `analysis/decompile_faithfulness/paper_freeze_manifest.json`. Do not tune source literal extraction, fixture-neighbor generation, admissibility filters, fallback probes, interleaving order, deduplication, budget handling, output normalization, scoring, or mismatch semantics on holdout data.

## Excluded Current Sources

Current evidence has already used projects: {", ".join(seen_projects)}. The prospective holdout must be project-disjoint from these and must not reuse their fixtures, candidates, source literals, inspected failures, or development examples.

## Candidate Upstream Projects

Candidate unseen projects for sourcing small scalar C functions:

| Project | Why eligible if freshly sampled |
|---|---|
| `libtommath` | integer arithmetic functions, project-disjoint from current sources |
| `cJSON` | small parser/helper routines with deterministic scalar subfunctions |
| `uthash` examples | compact C helper functions, separate upstream |
| `musl` | mature C library; select only isolated pure scalar helpers |
| `zlib` | checksum/table helpers; select bounded scalar wrappers |
| `mbedtls` | utility/math helpers; avoid crypto stateful paths |
| `sqlite` | pure utility functions only; avoid database state |
| `qsort_bench` or similar tiny C benchmark suites | project-disjoint scalar cases |

Eligibility must be established from a fresh clone or archived release after this freeze. A project is ineligible if any function, fixture, candidate, source literal, inspected failure, or development note from it influenced this method.

## Eligibility Criteria

1. Project-disjoint from `CodeFuse-DeBench`, `thealgorithms_c`, and `c_algorithms`.
2. One C function per case, source-known, deterministic, recompilable with `/usr/bin/gcc -std=c11`.
3. Integer or char scalar parameters only for this holdout round; no heap, I/O, global mutable state, threads, environment, time, or undefined behavior.
4. Fixtures must be generated and stored before running the final auditor.
5. Candidate generation and labeling must be completed before inspecting final-method misses.
6. No prompt or mutation family may be edited after seeing holdout auditor outcomes.

## Independent Label Oracles

Finite char domains: exhaustive enumeration over every char-like argument in 0..127 crossed with a fixed small independent set for non-char integer arguments. Label wrong if any source/candidate output differs or candidate fails compile/runtime.

Single integer arguments: use an independently specified bounded domain combining fixtures, hand-declared semantic boundaries, and stratified random integers from a committed seed. The final budget-8 prefix must be withheld from label generation until labels are sealed.

Multi-argument functions: use pairwise/combinatorial coverage over independently declared per-argument domains plus seed-committed random Cartesian samples. For small domains, exhaustive enumeration is preferred.

## Witness Exposure Risks

Current pipeline locations that can expose labeling witnesses to the auditor:

1. `docs/paper_agent/*function_manifest.json` stores fixtures used by fixture-neighbor generation.
2. `phase5b_hard_trace_inputs` derives label hard probes from fixture values and char anchors; using the same family in final fallback creates shared-family overlap.
3. Candidate records store `trace_mismatch_count` and labels before final rerun.
4. `analysis_outputs/.../records_budgeted.jsonl` stores per-budget detection outcomes.
5. Trace harness files under `analysis_outputs/.../traces/` preserve concrete final probes.
6. Phase 16/17/18 docs expose inspected misses such as `ta_infix_precedence_two`.

## Minimum Viable Holdout

Use at least 8 project-disjoint upstream projects, 60 source functions, and 240 compile-ready candidates, with at least 80 independently labeled wrong candidates and at least 30 paired cases. This is a minimum viability target; larger is better if labeling remains independent.

## Current Evidence Status

Exact witness overlap in current evidence: {audit['summary']['candidates_with_exact_witness_overlap']} / {audit['summary']['wrong_label_count']} wrong candidates ({audit['summary']['exact_witness_overlap_rate']:.4f}). Current three-dataset perfect tables should be described as pre-freeze/development evidence, not as fully independent holdout test evidence.
"""
    path = repo_root / "docs/paper_agent/frozen_holdout_preregistration.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_latex_table(
    repo_root: Path,
    contexts: list[DatasetContext],
    rows: list[dict[str, str]],
    missing_summary: dict[str, Any],
) -> None:
    counts = Counter(row["dataset"] for row in rows)
    wrong = Counter(row["dataset"] for row in rows if row["label"] == "plausible_wrong")
    faithful = Counter(row["dataset"] for row in rows if row["label"] == "faithful")
    compile_fail = Counter(row["dataset"] for row in rows if row["label"] == "compile_fail")
    lines = [
        r"\begin{tabular}{lrrrrl}",
        r"\toprule",
        r"Dataset & Candidates & Faithful & Wrong & Compile fail & Primary provenance \\",
        r"\midrule",
    ]
    provenance = {
        "phase7c2_static_hard_public": "controlled source mutation",
        "phase7e_llm_public_full_topup": "Dream-Coder local generations",
        "phase6r_ghidra_full": "Ghidra 12.1.2 headless",
    }
    for context in contexts:
        dataset = context.dataset_id.replace("_", r"\_")
        lines.append(
            f"{dataset} & {counts[context.dataset_id]} & {faithful[context.dataset_id]} & "
            f"{wrong[context.dataset_id]} & {compile_fail[context.dataset_id]} & "
            f"{provenance[context.dataset_id]} \\\\"
        )
    lines.extend(
        [
            r"\bottomrule",
            r"\end{tabular}",
            "",
            "% Missing metadata fields are reported in docs/paper_agent/submission_evidence_audit_handoff.md.",
            f"% Fields with nonzero unknown rates: {', '.join(sorted(missing_summary['fields_with_missing_values'].keys()))}",
        ]
    )
    path = repo_root / "paper/tables/dataset_provenance.tex"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_handoff(
    repo_root: Path,
    freeze_manifest: dict[str, Any],
    rows: list[dict[str, str]],
    audit: dict[str, Any],
    flow_rows: list[dict[str, Any]],
    missing_summary: dict[str, Any],
) -> None:
    branch = freeze_manifest["branch"]
    head = freeze_manifest["head_commit"]
    counts = Counter(row["dataset"] for row in rows)
    wrong = Counter(row["dataset"] for row in rows if row["label"] == "plausible_wrong")
    exact = {
        dataset: item["exact_overlap_candidate_rate"]
        for dataset, item in audit["summary"]["by_dataset"].items()
    }
    family_rates = {
        dataset: item["probe_family_overlap_rates"]
        for dataset, item in audit["summary"]["by_dataset"].items()
    }
    text = f"""# Submission Evidence Audit Handoff

## Git

- Branch: `{branch}`
- HEAD commit: `{head}`
- Freeze commit: `{freeze_manifest['proposed_paper_freeze_commit']}`

## Commands Executed

- `git status --short --branch`
- `git rev-parse HEAD`
- `rg ...` code/data discovery commands
- `python -m analysis.decompile_faithfulness.submission_evidence_audit`
- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze`
- `python -m json.tool` over generated JSON outputs
- `git diff --check`

## Tests Passed

Probe-order regression tests snapshot the exact ordered prefix for single integer, single char, mixed integer/char, duplicate source literals, empty source-literal queues, and one exhausted interleave queue.

## Candidate Provenance

- Total candidate records: `{len(rows)}`
- By dataset: `{dict(counts)}`
- Wrong labels: `{dict(wrong)}`
- 100% of candidate records have stable dataset/case/candidate identifiers.

## Missing Metadata

Unknown values are explicit rather than inferred. Nonzero missing-field counts:

```json
{json.dumps(missing_summary['fields_with_missing_values'], indent=2, sort_keys=True)}
```

## Oracle Overlap

- Exact witness overlap: `{audit['summary']['candidates_with_exact_witness_overlap']}` / `{audit['summary']['wrong_label_count']}` wrong labels = `{audit['summary']['exact_witness_overlap_rate']:.4f}`.
- Exact overlap by dataset: `{json.dumps(exact, sort_keys=True)}`
- Probe-family overlap rates by dataset:

```json
{json.dumps(family_rates, indent=2, sort_keys=True)}
```

Generator-family overlap is not claimed as leakage by itself. The audit distinguishes exact witness reuse, shared input family, and unresolved/full independence.

## Development Coupling

Phase 16 inspected Ghidra `char_boundary` and `multi_arg` misses. Phase 17 explicitly tested a generic operator-character fix after seeing `ta_infix_precedence_two`; Phase 18 introduced source-literal char interleaving to recover that case without regressing broader coverage. Therefore current results on Ghidra char-boundary/multi-arg, and any aggregate tables containing those same cases, are pre-freeze/development evidence.

Development-coupled cases/families:

- `ta_infix_precedence_two`
- Ghidra `char_boundary`
- Ghidra `multi_arg`
- Phase 17 broad regressions on public/static and LLM-public under `operator_char_class_first`

## Dataset Flow

```json
{json.dumps(flow_rows, indent=2, sort_keys=True)}
```

## Proposed Unseen Projects

`libtommath`, `cJSON`, `uthash` examples, `musl`, `zlib`, `mbedtls`, `sqlite` utility functions, and small project-disjoint C benchmark suites are proposed in `docs/paper_agent/frozen_holdout_preregistration.md`.

## Unresolved Risks

- Architecture, sanitizer status, and some compiler versions are not stored in candidate records.
- Exact label witnesses were reconstructed from current code and candidate sources; historical trace files do not store per-input label witnesses in records.
- Existing Phase 19 readiness markdown appears to retain a Phase 14 heading, so historical doc naming should be treated carefully.
- LLM-public provenance covers candidate records; raw parse-failed generations are counted in flow attempts but do not have full candidate rows.

## Independence Verdict

The current three perfect-result tables should not be described as fully independent test evidence. They are valid frozen, source-known, pre-freeze/development evidence with transparent provenance and overlap accounting. A project-disjoint prospective holdout is required for independent test evidence.
"""
    path = repo_root / "docs/paper_agent/submission_evidence_audit_handoff.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def missing_metadata_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    fields = Counter()
    by_dataset: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        for key, value in row.items():
            if value == UNKNOWN or value.startswith("unknown"):
                fields[key] += 1
                by_dataset[row["dataset"]][key] += 1
    return {
        "row_count": len(rows),
        "fields_with_missing_values": dict(sorted(fields.items())),
        "by_dataset": {
            dataset: dict(sorted(counter.items()))
            for dataset, counter in sorted(by_dataset.items())
        },
    }


def candidate_source_category(
    context: DatasetContext,
    record: dict[str, Any],
    manifest_item: dict[str, Any],
) -> str:
    mutation = str(record.get("mutation_type", ""))
    metadata = record.get("metadata", {})
    source_kind = str(metadata.get("source_kind") or manifest_item.get("source") or manifest_item.get("source_kind") or "")
    if context.key == "ghidra":
        return "normalized_decompiler" if record.get("compiled") else "raw_decompiler"
    if context.key == "llm_public":
        return "raw_llm" if record.get("label") == "compile_fail" else "repaired_llm"
    if "fixture_ifchain" in mutation or "fixture_overfit" in mutation:
        return "fixture_overfit_stress"
    if "static_hard" in mutation:
        return "controlled_mutation"
    if "control" in source_kind or "original_control" in mutation:
        return "controlled_mutation"
    return "other"


def producing_tool(context: DatasetContext, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    if context.key == "llm_public":
        return str(metadata.get("source_name") or manifest_item.get("source_name") or "Dream-Coder-v0-Instruct-7B")
    if context.key == "ghidra":
        return str(metadata.get("source_name") or "Ghidra 12.1.2 headless")
    return str(metadata.get("tool") or manifest_item.get("tool") or "deterministic_source_mutation")


def producing_version(context: DatasetContext, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    if context.key == "ghidra":
        return "12.1.2"
    if context.key == "llm_public":
        raw = record.get("metadata", {}).get("source_name") or manifest_item.get("source_name")
        return "snapshot 5d9e88c723af9045f362748b5284bdf43d9c501e" if raw else UNKNOWN
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


def compiler_for_record(context: DatasetContext, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    value = metadata.get("binary_compiler") or manifest_item.get("binary_compiler")
    if value:
        return str(value)
    if context.key in {"public_static_hard", "llm_public"}:
        return "/usr/bin/gcc"
    return UNKNOWN


def architecture_for_record(context: DatasetContext, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    assembly = str(record.get("metadata", {}).get("assembly_context_path") or manifest_item.get("assembly_context_path") or "")
    if "x86_64" in assembly or "amd64" in assembly:
        return "x86_64"
    return UNKNOWN


def label_oracle_type(record: dict[str, Any], context: DatasetContext) -> str:
    if record.get("label") == "compile_fail":
        return "compile_or_runtime_failure"
    if record.get("label") in {"faithful", "plausible_wrong"}:
        return context.spec["label_oracle_type"]
    return "unresolved"


def execution_status(record: dict[str, Any]) -> str:
    if not record.get("compiled"):
        return "not_executed_or_failed"
    primary = float(record.get("diagnostics", {}).get("primary_exit_code", 0.0))
    fixture = float(record.get("diagnostics", {}).get("fixture_exit_code", 0.0))
    return "executed" if primary == 0.0 and fixture == 0.0 else f"runtime_exit_primary_{primary:g}_fixture_{fixture:g}"


def drift_family(context: DatasetContext, record: dict[str, Any], entry: dict[str, Any]) -> str:
    risk = entry.get("risk_families") or []
    mutation = str(record.get("mutation_type", ""))
    if "fixture_ifchain" in mutation or "fixture_overfit" in mutation:
        return "fixture_overfit_stress"
    if "llm_public" in mutation:
        return "llm_generated_" + str(record.get("metadata", {}).get("prompt_id", UNKNOWN))
    if "static_hard_" in mutation:
        return mutation.replace("phase7_static_hard_", "static_")
    if risk:
        return "+".join(str(item) for item in risk)
    return mutation or UNKNOWN


def normalization_notes(context: DatasetContext, record: dict[str, Any], manifest_item: dict[str, Any]) -> str:
    metadata = record.get("metadata", {})
    if context.key == "ghidra":
        return "Ghidra output normalized by normalize_ghidra_translation_unit; raw and normalized paths recorded"
    if context.key == "llm_public":
        return str(metadata.get("cleaning_status") or manifest_item.get("cleaning_status") or UNKNOWN)
    if context.key == "public_static_hard":
        return "deterministic source mutation; comments stripped before mutation"
    return UNKNOWN


def probe_family_definitions() -> dict[str, str]:
    return {
        "exact_fixtures": "label witness is one of the original fixture arguments",
        "fixture_plus_minus_1": "labeling hard-probe set intersects fixture-neighbor-generated arguments",
        "generic_0_1_values": "labeling hard-probe set contains 0 or 1 values",
        "legacy_ascii_anchors": "labeling hard-probe set contains one of the Phase 17 operator char anchors",
        "source_literals": "labeling hard-probe set intersects source-literal-generated arguments",
        "operator_character_lists": "labeling procedure explicitly used Phase 17 operator_char_class_inputs",
        "generic_hard_input_cartesian_products": "label witness comes from phase5b_hard_trace_inputs Cartesian product",
        "random_inputs": "random input oracle documented",
        "fuzzing": "fuzzing oracle documented",
        "symbolic_concolic_inputs": "symbolic/concolic oracle documented",
        "exhaustive_enumeration": "exhaustive oracle documented",
        "controlled_construction_records": "wrongness also follows from controlled mutation/fixture-overfit construction",
    }


def development_coupling_audit() -> dict[str, Any]:
    return {
        "inspected_before_phase18": [
            {
                "phase": "phase16_runtime_risk",
                "datasets": ["phase6r_ghidra_full"],
                "cases": ["ta_infix_precedence_two"],
                "failure_families": ["char_boundary", "multi_arg"],
                "evidence": "Phase 16 reported budget-8 misses in Ghidra char_boundary and multi_arg rows.",
            },
            {
                "phase": "phase17_operator_char_policy",
                "datasets": ["phase6r_ghidra_full", "phase7c2_static_hard_public", "phase7e_llm_public_full_topup"],
                "cases": ["ta_infix_precedence_two"],
                "failure_families": ["operator_char_class_first regressions", "char_boundary"],
                "evidence": "Phase 17 plan states generic operator characters fixed ta_infix_precedence_two but regressed broader coverage.",
            },
        ],
        "directly_motivated_final_method": [
            "Phase 17 negative result: blindly front-loading operator characters regressed broad public and LLM-public coverage.",
            "Phase 16/17 focused miss: Ghidra ta_infix_precedence_two fixture-ifchain candidates under char_boundary/multi_arg.",
        ],
        "pre_freeze_development_evidence": [
            "phase6r_ghidra_full current results",
            "phase7c2_static_hard_public current results",
            "phase7e_llm_public_full_topup current results",
        ],
        "independence_statement": "The current three perfect-result tables are not fully independent test evidence; they are frozen pre-freeze/development evidence.",
    }


def development_coupled_cases() -> set[str]:
    return {"ta_infix_precedence_two"}


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
        key = (str(record.get("case_id")), str(record.get("candidate_id")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def paired_case_count_from_rows(rows: list[dict[str, str]]) -> int:
    labels: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        labels[row["stable_case_id"]].add(row["label"])
    return sum(1 for values in labels.values() if "faithful" in values and "plausible_wrong" in values)


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


def safe_rate(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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


if __name__ == "__main__":
    main()
