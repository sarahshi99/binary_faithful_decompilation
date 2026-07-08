from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import phase3a_candidates as p3a
from analysis.decompile_faithfulness import phase3a_corpus as corpus


PHASE3AR_BRANCH = "phase3ar-producer-recovery-census"
STARTING_PHASE3A_HEAD = "db5a9fc78e43d2702f9490184d0ae690a6a57c4d"
RECOVERY_PREREG = Path("docs/paper_agent/phase3ar_producer_recovery_preregistration.md")
CANONICAL_FUNCTION_FIXTURE_SEAL = p3a.CANONICAL_FUNCTION_FIXTURE_SEAL
CANONICAL_CANDIDATE_SEAL = "e34f3c7532a8a2b399ef5be4c7a931b3f4d5e7c982c6f5d29adb14a89c8971f4"

CLANG_ENV = Path("/home/shx/.conda/envs/phase3ar-clang")
CLANG = CLANG_ENV / "bin/clang"
LLVM_NM = CLANG_ENV / "bin/llvm-nm"
LLVM_OBJDUMP = CLANG_ENV / "bin/llvm-objdump"

WORK_DIR = Path("analysis_outputs/decompile_faithfulness/phase3ar_recovery_run2")
RESULT_DIR = Path("results/decompile_faithfulness")
ANALYSIS_DIR = Path("analysis/decompile_faithfulness")
MANIFEST_PATH = RESULT_DIR / "phase3ar_candidate_manifest.jsonl"
PROVENANCE_PATH = RESULT_DIR / "phase3ar_candidate_provenance.csv"
COMMAND_LOG = RESULT_DIR / "phase3ar_candidate_generation_log.jsonl"
LABEL_LOG = RESULT_DIR / "phase3ar_label_execution_log.jsonl"
RECOVERY_MATRIX_PATH = RESULT_DIR / "phase3ar_recovery_matrix.csv"
CLANG_RECOVERY_PATH = RESULT_DIR / "phase3ar_clang_recovery.json"
LLM_RECOVERY_PATH = RESULT_DIR / "phase3ar_llm4decompile_recovery.json"
CANDIDATE_SEAL_PATH = ANALYSIS_DIR / "phase3ar_candidate_seal.json"
CANDIDATE_SEAL_SHA_PATH = ANALYSIS_DIR / "phase3ar_candidate_seal.sha256"
LABELS_PATH = RESULT_DIR / "phase3ar_exact_labels.jsonl"
LABEL_SUMMARY_PATH = RESULT_DIR / "phase3ar_label_summary.csv"
FIXTURE_REPLAY_PATH = RESULT_DIR / "phase3ar_fixture_replay.jsonl"
DESCRIPTORS_PATH = RESULT_DIR / "phase3ar_natural_error_descriptors.csv"
TAXONOMY_PACKET_PATH = RESULT_DIR / "phase3ar_taxonomy_review_packet.jsonl"

COMBINED_MANIFEST_PATH = RESULT_DIR / "phase3ar_combined_candidate_manifest.jsonl"
COMBINED_LABELS_PATH = RESULT_DIR / "phase3ar_combined_exact_labels.jsonl"
COMBINED_LABEL_SUMMARY_PATH = RESULT_DIR / "phase3ar_combined_label_summary.csv"
COMBINED_FIXTURE_REPLAY_PATH = RESULT_DIR / "phase3ar_combined_fixture_replay.jsonl"
COMBINED_DESCRIPTORS_PATH = RESULT_DIR / "phase3ar_combined_natural_error_descriptors.csv"
COMBINED_TAXONOMY_PACKET_PATH = RESULT_DIR / "phase3ar_combined_taxonomy_review_packet.jsonl"

CANDIDATE_YIELD_TABLE = Path("paper/tables/phase3ar_candidate_yield.tex")
NATURAL_ERROR_TABLE = Path("paper/tables/phase3ar_natural_error_census.tex")
FLOW_DATA = Path("figures/data/phase3ar_candidate_flow.json")
ERROR_DENSITY_DATA = Path("figures/data/phase3ar_error_density.csv")
ERROR_PRODUCER_DATA = Path("figures/data/phase3ar_error_producer_distribution.csv")
HANDOFF_PATH = Path("docs/paper_agent/phase3ar_producer_recovery_handoff.md")

ORIGINAL_ARTIFACTS = [
    RESULT_DIR / "phase3a_candidate_manifest.jsonl",
    RESULT_DIR / "phase3a_candidate_provenance.csv",
    RESULT_DIR / "phase3a_exact_labels.jsonl",
    RESULT_DIR / "phase3a_label_summary.csv",
    RESULT_DIR / "phase3a_fixture_replay.jsonl",
    RESULT_DIR / "phase3a_natural_error_descriptors.csv",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 3a-R producer recovery census.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument(
        "--stage",
        choices=["record-llm-blocker", "matrix", "generate", "label", "combine", "tables", "handoff"],
        required=True,
    )
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    if args.stage == "record-llm-blocker":
        summary = write_llm_blocker_record(repo_root)
    elif args.stage == "matrix":
        summary = write_recovery_matrix(repo_root)
    elif args.stage == "generate":
        summary = generate_recovered_candidates(repo_root)
    elif args.stage == "label":
        summary = label_recovered_candidates(repo_root)
    elif args.stage == "combine":
        summary = write_combined_census(repo_root)
    elif args.stage == "tables":
        summary = write_tables(repo_root)
    elif args.stage == "handoff":
        summary = write_handoff(repo_root)
    else:
        raise ValueError(args.stage)
    print(json.dumps(summary, sort_keys=True))


def configure_phase3a_module(repo_root: Path) -> None:
    p3a.WORK_DIR = WORK_DIR
    p3a.MANIFEST_PATH = MANIFEST_PATH
    p3a.PROVENANCE_PATH = PROVENANCE_PATH
    p3a.CANDIDATE_SEAL_PATH = CANDIDATE_SEAL_PATH
    p3a.CANDIDATE_SEAL_SHA_PATH = CANDIDATE_SEAL_SHA_PATH
    p3a.LABELS_PATH = LABELS_PATH
    p3a.LABEL_SUMMARY_PATH = LABEL_SUMMARY_PATH
    p3a.FIXTURE_REPLAY_PATH = FIXTURE_REPLAY_PATH
    p3a.DESCRIPTORS_PATH = DESCRIPTORS_PATH
    p3a.TAXONOMY_PACKET_PATH = TAXONOMY_PACKET_PATH
    p3a.COMMAND_LOG = COMMAND_LOG
    p3a.BUILD_VIEWS["clang_O2"]["compiler"] = str(CLANG)
    p3a.candidate_id_for = phase3ar_candidate_id_for  # type: ignore[method-assign]
    p3a.render_build_source = render_recovery_build_source  # type: ignore[method-assign]
    os.environ["PATH"] = str(CLANG_ENV / "bin") + os.pathsep + os.environ.get("PATH", "")
    (repo_root / WORK_DIR).mkdir(parents=True, exist_ok=True)


def verify_recovery_preflight(repo_root: Path) -> None:
    if git_at(repo_root, ["branch", "--show-current"]) != PHASE3AR_BRANCH:
        raise RuntimeError("not on Phase 3a-R branch")
    if not (repo_root / RECOVERY_PREREG).exists():
        raise RuntimeError("missing Phase 3a-R preregistration")
    function_sha = (repo_root / ANALYSIS_DIR / "phase3a_function_fixture_seal.sha256").read_text(encoding="utf-8").split()[0]
    if function_sha != CANONICAL_FUNCTION_FIXTURE_SEAL:
        raise RuntimeError(f"function/fixture seal mismatch: {function_sha}")
    if p3a.sha256_path(repo_root / ANALYSIS_DIR / "phase3a_function_fixture_seal.json") != CANONICAL_FUNCTION_FIXTURE_SEAL:
        raise RuntimeError("function/fixture seal recomputation mismatch")
    candidate_sha = (repo_root / ANALYSIS_DIR / "phase3a_candidate_seal.sha256").read_text(encoding="utf-8").split()[0]
    if candidate_sha != CANONICAL_CANDIDATE_SEAL:
        raise RuntimeError(f"original candidate seal mismatch: {candidate_sha}")
    if p3a.sha256_path(repo_root / ANALYSIS_DIR / "phase3a_candidate_seal.json") != CANONICAL_CANDIDATE_SEAL:
        raise RuntimeError("original candidate seal recomputation mismatch")
    missing = [str(path) for path in ORIGINAL_ARTIFACTS if not (repo_root / path).exists()]
    if missing:
        raise RuntimeError(f"missing original Phase 3a artifacts: {missing}")


def write_llm_blocker_record(repo_root: Path) -> dict[str, Any]:
    verify_recovery_preflight(repo_root)
    helper_source = p3a.llm_helper_source()
    adapter_change = "Filtered tokenizer output with inputs.pop(\"token_type_ids\", None) before model.generate."
    record = {
        "created_at_utc": now_utc(),
        "producer": "llm4decompile",
        "model_identifier": p3a.LLM_MODEL_IDENTIFIER,
        "model_snapshot": p3a.LLM_MODEL_SNAPSHOT,
        "model_path": str(p3a.LLM_MODEL_PATH),
        "tokenizer_identity": str(p3a.LLM_MODEL_PATH / "tokenizer.json"),
        "tokenizer_sha256": p3a.sha256_path(p3a.LLM_MODEL_PATH / "tokenizer.json")
        if (p3a.LLM_MODEL_PATH / "tokenizer.json").exists()
        else "",
        "precision": p3a.LLM_DECODING["precision"],
        "decoding_parameters": p3a.LLM_DECODING,
        "adapter_change": adapter_change,
        "interface_only_change": True,
        "prompt_template_changed": False,
        "decoding_parameters_changed": False,
        "dream_coder_used": False,
        "smoke_prompt_sha256": "fe2c2eb88c7450400fb25c78d94d5729c745fe6c646f8b862b3318ec06ce4229",
        "smoke_status": "blocked",
        "blocker": "gpu_smoke_escalation_rejected_by_auto_review_model_unavailable",
        "blocker_detail": "The attempted H200 smoke command was rejected before execution by the escalation reviewer: model not found: codex-auto-review.",
        "gpu_model": gpu_name(),
        "batch_size": p3a.LLM_DECODING["batch_size"],
        "max_batch_size_tested": 0,
        "peak_memory_mib": 0,
        "helper_source_sha256": p3a.sha256_text(helper_source),
        "token_type_ids_filter_present": 'inputs.pop("token_type_ids", None)' in helper_source,
        "producer_status": "blocked",
    }
    p3a.write_json(repo_root / LLM_RECOVERY_PATH, record)
    return {"stage": "record-llm-blocker", "producer_status": record["producer_status"], "blocker": record["blocker"]}


def write_recovery_matrix(repo_root: Path) -> dict[str, Any]:
    verify_recovery_preflight(repo_root)
    clang_record = load_json(repo_root / CLANG_RECOVERY_PATH)
    llm_record = load_json(repo_root / LLM_RECOVERY_PATH)
    clang_available = clang_record.get("producer_status") == "available" or clang_record.get("status") == "available"
    llm_available = llm_record.get("producer_status") == "available" or llm_record.get("status") == "available"
    rows = []
    for row in p3a.read_jsonl(repo_root / RESULT_DIR / "phase3a_candidate_manifest.jsonl"):
        reason = row.get("non_evaluable_reason", "")
        clang_required = reason == "compiler_unavailable:clang"
        llm_interface_required = row["producer"] == "llm4decompile" and (
            reason == "llm4decompile_exception" or clang_required
        )
        if not clang_required and not (row["producer"] == "llm4decompile" and reason == "llm4decompile_exception"):
            continue
        eligible = True
        recovery_reasons = []
        if clang_required:
            eligible = eligible and clang_available
            recovery_reasons.append("clang_O2_compiler_recovery")
        if llm_interface_required:
            eligible = eligible and llm_available
            recovery_reasons.append("llm4decompile_token_type_ids_interface_recovery")
        rows.append(
            {
                "original_candidate_id": row["candidate_id"],
                "recovery_candidate_id": phase3ar_candidate_id_for(row["selected_function_id"], row["producer"], row["build_view"]),
                "selected_function_id": row["selected_function_id"],
                "project": row["project"],
                "function_name": row["function_name"],
                "producer": row["producer"],
                "build_view": row["build_view"],
                "original_failure_reason": reason,
                "recovery_eligibility": "eligible" if eligible else "blocked",
                "recovery_reason": ";".join(recovery_reasons),
                "clang_fix_required": int(clang_required),
                "llm4decompile_fix_required": int(llm_interface_required),
                "clang_recovery_status": "available" if clang_available else "blocked",
                "llm4decompile_recovery_status": "available" if llm_available else "blocked",
            }
        )
    fields = [
        "original_candidate_id",
        "recovery_candidate_id",
        "selected_function_id",
        "project",
        "function_name",
        "producer",
        "build_view",
        "original_failure_reason",
        "recovery_eligibility",
        "recovery_reason",
        "clang_fix_required",
        "llm4decompile_fix_required",
        "clang_recovery_status",
        "llm4decompile_recovery_status",
    ]
    p3a.write_csv(repo_root / RECOVERY_MATRIX_PATH, rows, fields)
    return {
        "stage": "matrix",
        "matrix_rows": len(rows),
        "eligible_rows": sum(1 for row in rows if row["recovery_eligibility"] == "eligible"),
        "blocked_rows": sum(1 for row in rows if row["recovery_eligibility"] == "blocked"),
    }


def generate_recovered_candidates(repo_root: Path) -> dict[str, Any]:
    verify_recovery_preflight(repo_root)
    if not matrix_committed(repo_root):
        raise RuntimeError("recovery matrix must be committed before candidate generation")
    configure_phase3a_module(repo_root)
    selected = p3a.load_selected_functions(repo_root)
    selected_by_id = {item.record.function_id: item for item in selected}
    availability = json.loads((repo_root / RESULT_DIR / "phase3a_producer_availability.json").read_text(encoding="utf-8"))
    for sub in ["build", "raw", "parsed", "normalized", "compile", "prompts", "logs", "ghidra_projects"]:
        (repo_root / WORK_DIR / sub).mkdir(parents=True, exist_ok=True)
    (repo_root / COMMAND_LOG).write_text("", encoding="utf-8")
    matrix_rows = [row for row in p3a.read_csv_rows(repo_root / RECOVERY_MATRIX_PATH) if row["recovery_eligibility"] == "eligible"]
    needed_functions = sorted({row["selected_function_id"] for row in matrix_rows})
    needed_builds = sorted({(row["selected_function_id"], row["build_view"]) for row in matrix_rows})
    builds: dict[tuple[str, str], p3a.BuildArtifact] = {}
    for function_id, build_view in needed_builds:
        function = selected_by_id[function_id]
        builds[(function_id, build_view)] = p3a.build_binary(
            repo_root, function.record, build_view, p3a.BUILD_VIEWS[build_view], repo_root / COMMAND_LOG
        )
    rows: list[dict[str, Any]] = []
    for matrix_row in matrix_rows:
        function = selected_by_id[matrix_row["selected_function_id"]]
        artifact = builds[(function.record.function_id, matrix_row["build_view"])]
        row = p3a.process_attempt(repo_root, function, artifact, matrix_row["producer"], availability, repo_root / COMMAND_LOG)
        row.update(
            {
                "phase3ar_recovery": True,
                "original_candidate_id": matrix_row["original_candidate_id"],
                "recovery_reason": matrix_row["recovery_reason"],
                "clang_fix_required": int(matrix_row["clang_fix_required"]),
                "llm4decompile_fix_required": int(matrix_row["llm4decompile_fix_required"]),
            }
        )
        rows.append(row)
    rows = p3a.run_llm4decompile_batch(repo_root, rows)
    rows = run_api_requests_for_recovery(repo_root, rows)
    rows = p3a.finalize_manifest_rows(repo_root, rows)
    p3a.write_jsonl(repo_root / MANIFEST_PATH, rows)
    p3a.write_candidate_provenance(repo_root / PROVENANCE_PATH, rows)
    seal = build_recovery_candidate_seal(repo_root, rows)
    p3a.write_json(repo_root / CANDIDATE_SEAL_PATH, seal)
    seal_hash = p3a.sha256_path(repo_root / CANDIDATE_SEAL_PATH)
    (repo_root / CANDIDATE_SEAL_SHA_PATH).write_text(f"{seal_hash}  phase3ar_candidate_seal.json\n", encoding="utf-8")
    return {
        "stage": "generate",
        "needed_functions": len(needed_functions),
        "attempts": len(rows),
        "candidate_seal_sha256": seal_hash,
        "compile_ready": sum(1 for row in rows if row["compile_status"] == "compile_ready"),
        "by_status": dict(Counter(row["final_candidate_status"] for row in rows)),
    }


def run_api_requests_for_recovery(repo_root: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    updated = []
    for row in rows:
        if row.get("final_candidate_status") != "pending_api":
            updated.append(row)
            continue
        raw_path = Path(row["raw_output_path"])
        response_json_path = raw_path.with_name("response.json")
        metadata_path = raw_path.with_name("api_metadata.json")
        if not api_key:
            metadata_path.write_text(json.dumps({"status": "blocked", "reason": "api_key_unavailable"}, sort_keys=True) + "\n")
            updated.append(p3a.mark_generation_failure(row, "decompilation_failure", "api_key_unavailable"))
            continue
        payload = json.loads(Path(row["prompt_payload_path"]).read_text(encoding="utf-8"))
        try:
            raw_payload, metadata = p3a.call_api(payload["request_payload"], api_key)
        except Exception as exc:
            metadata_path.write_text(
                json.dumps({"status": "exception", "error": repr(exc)}, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )
            updated.append(p3a.mark_generation_failure(row, "decompilation_failure", "api_exception"))
            continue
        response_json_path.write_text(json.dumps(raw_payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        metadata_path.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        returned_model = raw_payload.get("model", "")
        if returned_model and returned_model != p3a.API_MODEL:
            updated.append(p3a.mark_generation_failure(row, "decompilation_failure", "api_model_mismatch"))
            continue
        raw_path.write_text(p3a.extract_api_text(raw_payload), encoding="utf-8")
        row = p3a.process_generated_raw(repo_root, row, "raw_candidate", "")
        row["api_returned_model"] = returned_model
        row["api_request_id"] = raw_payload.get("id", "")
        row["api_finish_reason"] = p3a.response_finish_reason(raw_payload)
        row["api_usage"] = raw_payload.get("usage", {})
        updated.append(row)
    return updated


def build_recovery_candidate_seal(repo_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    paths = [
        RECOVERY_PREREG,
        RESULT_DIR / "phase3a_producer_availability.json",
        Path("docs/paper_agent/phase3a_producer_setup_log.md"),
        ANALYSIS_DIR / "phase3a_function_fixture_seal.json",
        ANALYSIS_DIR / "phase3a_function_fixture_seal.sha256",
        ANALYSIS_DIR / "phase3a_candidate_seal.json",
        ANALYSIS_DIR / "phase3a_candidate_seal.sha256",
        CLANG_RECOVERY_PATH,
        LLM_RECOVERY_PATH,
        RECOVERY_MATRIX_PATH,
        RESULT_DIR / "phase3a_selected_functions.csv",
        RESULT_DIR / "phase3a_fixtures.jsonl",
        MANIFEST_PATH,
        PROVENANCE_PATH,
        COMMAND_LOG,
        Path("analysis/decompile_faithfulness/phase3a_candidates.py"),
        Path("analysis/decompile_faithfulness/phase3ar_recovery.py"),
    ]
    artifact_paths = set()
    for row in rows:
        for key in [
            "binary_path",
            "symbol_metadata_path",
            "disassembly_path",
            "raw_output_path",
            "parsed_function_path",
            "normalized_candidate_path",
            "transformation_log_path",
            "compile_log_path",
            "prompt_payload_path",
        ]:
            if row.get(key):
                artifact_paths.add(row[key])
    return {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "branch": git_at(repo_root, ["branch", "--show-current"]),
        "head_before_labeling": git_at(repo_root, ["rev-parse", "HEAD"]),
        "starting_phase3a_head": STARTING_PHASE3A_HEAD,
        "function_fixture_seal_sha256": CANONICAL_FUNCTION_FIXTURE_SEAL,
        "original_phase3a_candidate_seal_sha256": CANONICAL_CANDIDATE_SEAL,
        "recovery_candidate_attempt_count": len(rows),
        "recovered_original_candidate_ids": [row["original_candidate_id"] for row in rows],
        "candidate_manifest_sha256": p3a.sha256_path(repo_root / MANIFEST_PATH),
        "candidate_provenance_sha256": p3a.sha256_path(repo_root / PROVENANCE_PATH),
        "artifact_hashes": p3a.artifact_hashes(repo_root, [str(path) for path in paths]),
        "candidate_artifact_hashes": p3a.artifact_hashes_absolute(repo_root, sorted(artifact_paths)),
        "prompt_templates": {
            "phase3a_llm4decompile_disassembly_v1": "unchanged Phase 3a LLM4Decompile disassembly plus sealed signature prompt",
            "phase3a_mycodex_disassembly_v1": "unchanged Phase 3a mycodex disassembly plus sealed signature prompt",
        },
        "normalization_forbidden_operations": {
            "source_aware_constant_repair": False,
            "source_aware_branch_repair": False,
            "fixture_guided_repair": False,
            "execution_feedback_repair": False,
            "model_retry_after_compile_failure": False,
            "candidate_variant_selection": False,
            "semantic_patching": False,
        },
        "semantic_labeling": "not_run_at_candidate_seal_creation",
        "auditor_execution": "not_run",
        "libfuzzer_execution": "not_run",
    }


def label_recovered_candidates(repo_root: Path) -> dict[str, Any]:
    verify_recovery_preflight(repo_root)
    configure_phase3a_module(repo_root)
    if not recovery_candidate_seal_committed(repo_root):
        raise RuntimeError("Phase 3a-R candidate seal must be committed before labeling")
    rows = p3a.read_jsonl(repo_root / MANIFEST_PATH)
    selected = {item.record.function_id: item for item in p3a.load_selected_functions(repo_root)}
    fixtures_by_function = p3a.load_fixtures_by_function(repo_root)
    labels: list[dict[str, Any]] = []
    fixture_replay: list[dict[str, Any]] = []
    descriptors: list[dict[str, Any]] = []
    taxonomy_packet: list[dict[str, Any]] = []
    (repo_root / LABEL_LOG).write_text("", encoding="utf-8")
    for row in rows:
        function = selected[row["selected_function_id"]].record
        if row["compile_status"] != "compile_ready":
            label = p3a.non_evaluable_label(row, function)
        else:
            label = p3a.execute_label(repo_root, row, function, repo_root / LABEL_LOG)
        label.update({"phase3ar_recovery": True, "original_candidate_id": row.get("original_candidate_id", "")})
        labels.append(label)
        if label["label"] == "semantic_wrong":
            replay = p3a.replay_fixtures(repo_root, row, function, fixtures_by_function[function.function_id], repo_root / LABEL_LOG)
            replay.update({"phase3ar_recovery": True, "original_candidate_id": row.get("original_candidate_id", "")})
            fixture_replay.append(replay)
            descriptor = descriptor_for_any_semantic_wrong(row, function, label, replay, "recovery")
            descriptors.append(descriptor)
            taxonomy_packet.append(taxonomy_packet_for_recovery(repo_root, row, function, label, descriptor))
    p3a.write_jsonl(repo_root / LABELS_PATH, labels)
    write_label_summary(repo_root / LABEL_SUMMARY_PATH, labels, fixture_replay)
    p3a.write_jsonl(repo_root / FIXTURE_REPLAY_PATH, fixture_replay)
    write_descriptors(repo_root / DESCRIPTORS_PATH, descriptors)
    p3a.write_jsonl(repo_root / TAXONOMY_PACKET_PATH, taxonomy_packet)
    return {
        "stage": "label",
        "labels": len(labels),
        "semantic_wrong": sum(1 for item in labels if item["label"] == "semantic_wrong"),
        "fixture_passing_semantic_wrong": sum(
            1 for item in fixture_replay if item["fixture_replay_label"] == "fixture_passing_semantic_wrong"
        ),
        "fixture_failing_semantic_wrong": sum(
            1 for item in fixture_replay if item["fixture_replay_label"] == "fixture_failing_semantic_wrong"
        ),
    }


def write_combined_census(repo_root: Path) -> dict[str, Any]:
    verify_recovery_preflight(repo_root)
    configure_phase3a_module(repo_root)
    original_manifest = p3a.read_jsonl(repo_root / RESULT_DIR / "phase3a_candidate_manifest.jsonl")
    original_labels = p3a.read_jsonl(repo_root / RESULT_DIR / "phase3a_exact_labels.jsonl")
    original_replay = p3a.read_jsonl(repo_root / RESULT_DIR / "phase3a_fixture_replay.jsonl")
    recovered_manifest = p3a.read_jsonl(repo_root / MANIFEST_PATH)
    recovered_labels = p3a.read_jsonl(repo_root / LABELS_PATH)
    recovered_replay = p3a.read_jsonl(repo_root / FIXTURE_REPLAY_PATH)
    recovered_by_original = {row["original_candidate_id"]: row for row in recovered_manifest}
    original_labels_by_id = {row["candidate_id"]: row for row in original_labels}
    recovered_labels_by_original = {row.get("original_candidate_id", ""): row for row in recovered_labels}
    combined_manifest = []
    combined_labels = []
    for row in original_manifest:
        replacement = recovered_by_original.get(row["candidate_id"])
        if replacement:
            combined_manifest.append(combined_manifest_row(row, replacement))
            combined_labels.append(combined_label_row(original_labels_by_id[row["candidate_id"]], recovered_labels_by_original[row["candidate_id"]]))
        else:
            original = dict(row)
            original.update({"census_phase": "original_phase3a", "recovered_clang_O2_cell": 0, "recovered_llm4decompile_interface_cell": 0})
            combined_manifest.append(original)
            label = dict(original_labels_by_id[row["candidate_id"]])
            label.update({"census_phase": "original_phase3a"})
            combined_labels.append(label)
    combined_replay = []
    replaced_original_ids = set(recovered_by_original)
    for row in original_replay:
        if row["candidate_id"] not in replaced_original_ids:
            item = dict(row)
            item.update({"census_phase": "original_phase3a"})
            combined_replay.append(item)
    for row in recovered_replay:
        item = dict(row)
        item.update({"census_phase": "recovery_phase3ar"})
        combined_replay.append(item)
    descriptors, taxonomy_packet = combined_descriptors(repo_root, combined_manifest, combined_labels, combined_replay)
    p3a.write_jsonl(repo_root / COMBINED_MANIFEST_PATH, combined_manifest)
    p3a.write_jsonl(repo_root / COMBINED_LABELS_PATH, combined_labels)
    write_label_summary(repo_root / COMBINED_LABEL_SUMMARY_PATH, combined_labels, combined_replay)
    p3a.write_jsonl(repo_root / COMBINED_FIXTURE_REPLAY_PATH, combined_replay)
    write_descriptors(repo_root / COMBINED_DESCRIPTORS_PATH, descriptors)
    p3a.write_jsonl(repo_root / COMBINED_TAXONOMY_PACKET_PATH, taxonomy_packet)
    gate = p3a.census_gate(gate_descriptors(descriptors))
    return {
        "stage": "combine",
        "combined_candidates": len(combined_manifest),
        "combined_labels": len(combined_labels),
        "semantic_wrong": sum(1 for row in combined_labels if row["label"] == "semantic_wrong"),
        "fixture_passing_semantic_wrong": sum(
            1 for row in combined_replay if row["fixture_replay_label"] == "fixture_passing_semantic_wrong"
        ),
        "minimum_gate": gate["minimum_gate_status"],
    }


def combined_manifest_row(original: dict[str, Any], recovered: dict[str, Any]) -> dict[str, Any]:
    out = dict(recovered)
    out.update(
        {
            "census_phase": "recovery_phase3ar",
            "original_candidate_id": original["candidate_id"],
            "original_final_candidate_status": original["final_candidate_status"],
            "original_compile_status": original["compile_status"],
            "original_non_evaluable_reason": original.get("non_evaluable_reason", ""),
            "recovered_clang_O2_cell": int(out.get("clang_fix_required", 0)),
            "recovered_llm4decompile_interface_cell": int(out.get("llm4decompile_fix_required", 0)),
        }
    )
    return out


def combined_label_row(original: dict[str, Any], recovered: dict[str, Any]) -> dict[str, Any]:
    out = dict(recovered)
    out.update(
        {
            "census_phase": "recovery_phase3ar",
            "original_candidate_id": original["candidate_id"],
            "original_label": original["label"],
            "original_label_reason": original.get("label_reason", ""),
        }
    )
    return out


def combined_descriptors(
    repo_root: Path,
    combined_manifest: list[dict[str, Any]],
    combined_labels: list[dict[str, Any]],
    combined_replay: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    selected = {item.record.function_id: item for item in p3a.load_selected_functions(repo_root)}
    rows_by_id = {row["candidate_id"]: row for row in combined_manifest}
    replay_by_id = {row["candidate_id"]: row for row in combined_replay}
    descriptors = []
    taxonomy_packet = []
    for label in combined_labels:
        if label["label"] != "semantic_wrong":
            continue
        row = rows_by_id[label["candidate_id"]]
        function = selected[label["selected_function_id"]].record
        replay = replay_by_id.get(label["candidate_id"], {"fixture_replay_label": "", "fixture_domain_indices": []})
        descriptor = descriptor_for_any_semantic_wrong(row, function, label, replay, row.get("census_phase", ""))
        descriptors.append(descriptor)
        taxonomy_packet.append(taxonomy_packet_for_recovery(repo_root, row, function, label, descriptor))
    return descriptors, taxonomy_packet


def descriptor_for_any_semantic_wrong(
    row: dict[str, Any],
    function: corpus.FunctionRecord,
    label: dict[str, Any],
    replay: dict[str, Any],
    census_phase: str,
) -> dict[str, Any]:
    descriptor = p3a.build_descriptor(row, function, label, replay)
    descriptor.update(
        {
            "census_phase": census_phase,
            "original_candidate_id": row.get("original_candidate_id", ""),
            "fixture_replay_label": replay.get("fixture_replay_label", ""),
            "counts_for_gate": int(replay.get("fixture_replay_label") == "fixture_passing_semantic_wrong"),
            "recovered_clang_O2_cell": int(row.get("clang_fix_required", row.get("recovered_clang_O2_cell", 0)) or 0),
            "recovered_llm4decompile_interface_cell": int(
                row.get("llm4decompile_fix_required", row.get("recovered_llm4decompile_interface_cell", 0)) or 0
            ),
        }
    )
    return descriptor


def taxonomy_packet_for_recovery(
    repo_root: Path,
    row: dict[str, Any],
    function: corpus.FunctionRecord,
    label: dict[str, Any],
    descriptor: dict[str, Any],
) -> dict[str, Any]:
    packet = p3a.build_taxonomy_packet(repo_root, row, function, label, descriptor)
    packet.update(
        {
            "census_phase": descriptor.get("census_phase", ""),
            "original_candidate_id": descriptor.get("original_candidate_id", ""),
            "fixture_replay_label": descriptor.get("fixture_replay_label", ""),
            "counts_for_gate": descriptor.get("counts_for_gate", 0),
            "recovered_clang_O2_cell": descriptor.get("recovered_clang_O2_cell", 0),
            "recovered_llm4decompile_interface_cell": descriptor.get("recovered_llm4decompile_interface_cell", 0),
        }
    )
    return packet


def write_tables(repo_root: Path) -> dict[str, Any]:
    combined_manifest = p3a.read_jsonl(repo_root / COMBINED_MANIFEST_PATH)
    combined_labels = p3a.read_jsonl(repo_root / COMBINED_LABELS_PATH)
    combined_replay = p3a.read_jsonl(repo_root / COMBINED_FIXTURE_REPLAY_PATH)
    descriptors = p3a.read_csv_rows(repo_root / COMBINED_DESCRIPTORS_PATH)
    gate = p3a.census_gate(gate_descriptors(descriptors))
    counts = Counter((row["producer"], row["build_view"], row["final_candidate_status"]) for row in combined_manifest)
    p3a.write_simple_tex_table(
        repo_root / CANDIDATE_YIELD_TABLE,
        ["Producer", "Build", "Status", "Count"],
        [(producer, build, status, count) for (producer, build, status), count in sorted(counts.items())],
    )
    p3a.write_simple_tex_table(
        repo_root / NATURAL_ERROR_TABLE,
        ["Metric", "Value"],
        [
            ("Fixture-passing natural wrong", gate["natural_wrong_count"]),
            ("Distinct functions", gate["distinct_function_count"]),
            ("Projects", len(gate["project_counts"])),
            ("Producers", len(gate["producer_counts"])),
            ("Low-density", gate["low_density_count"]),
            ("Multi-arg/loop/lookup", gate["multi_argument_loop_lookup_count"]),
            ("Minimum gate", gate["minimum_gate_status"]),
            ("Strong gate", gate["strong_gate_status"]),
        ],
    )
    flow = {
        "candidate_attempts": len(combined_manifest),
        "recovered_candidate_attempts": len(p3a.read_jsonl(repo_root / MANIFEST_PATH)),
        "compile_ready": sum(1 for row in combined_manifest if row["compile_status"] == "compile_ready"),
        "semantic_wrong": sum(1 for row in combined_labels if row["label"] == "semantic_wrong"),
        "fixture_passing_semantic_wrong": gate["natural_wrong_count"],
        "fixture_failing_semantic_wrong": sum(
            1 for row in combined_replay if row["fixture_replay_label"] == "fixture_failing_semantic_wrong"
        ),
        "no_mismatch": sum(1 for row in combined_labels if row["label"] == "no_mismatch_under_exact_audit_domain"),
        "non_evaluable": sum(1 for row in combined_labels if row["label"] == "non_evaluable"),
        "minimum_gate": gate["minimum_gate_status"],
    }
    p3a.write_json(repo_root / FLOW_DATA, flow)
    p3a.write_csv(
        repo_root / ERROR_DENSITY_DATA,
        descriptors,
        [
            "candidate_id",
            "census_phase",
            "project",
            "producer",
            "build_view",
            "mismatch_density",
            "mismatch_count",
            "domain_size",
            "primary_taxonomy_tag",
            "fixture_replay_label",
            "counts_for_gate",
        ],
    )
    producer_distribution = [
        {"producer": producer, "natural_wrong_count": count}
        for producer, count in Counter(row["producer"] for row in descriptors if str(row.get("counts_for_gate", "")) == "1").items()
    ]
    p3a.write_csv(repo_root / ERROR_PRODUCER_DATA, producer_distribution, ["producer", "natural_wrong_count"])
    return {"stage": "tables", "minimum_gate": gate["minimum_gate_status"]}


def write_handoff(repo_root: Path) -> dict[str, Any]:
    configure_phase3a_module(repo_root)
    recovered_rows = p3a.read_jsonl(repo_root / MANIFEST_PATH)
    recovered_labels = p3a.read_jsonl(repo_root / LABELS_PATH)
    recovered_replay = p3a.read_jsonl(repo_root / FIXTURE_REPLAY_PATH)
    combined_manifest = p3a.read_jsonl(repo_root / COMBINED_MANIFEST_PATH)
    combined_labels = p3a.read_jsonl(repo_root / COMBINED_LABELS_PATH)
    combined_replay = p3a.read_jsonl(repo_root / COMBINED_FIXTURE_REPLAY_PATH)
    descriptors = p3a.read_csv_rows(repo_root / COMBINED_DESCRIPTORS_PATH)
    gate = p3a.census_gate(gate_descriptors(descriptors))
    clang = load_json(repo_root / CLANG_RECOVERY_PATH)
    llm = load_json(repo_root / LLM_RECOVERY_PATH)
    seal_hash = (repo_root / CANDIDATE_SEAL_SHA_PATH).read_text(encoding="utf-8").split()[0] if (repo_root / CANDIDATE_SEAL_SHA_PATH).exists() else ""
    tests_path = repo_root / RESULT_DIR / "phase3ar_test_results.json"
    tests = load_json(tests_path) if tests_path.exists() else {"status": "pending"}
    rec_label_counts = Counter(row["label"] for row in recovered_labels)
    combo_label_counts = Counter(row["label"] for row in combined_labels)
    combo_non_eval = Counter(row["label_reason"] for row in combined_labels if row["label"] == "non_evaluable")
    recommendation = "authorize Phase 3b" if gate["phase3b_authorized_for_review"] else "report remaining infrastructure blocker"
    if not gate["phase3b_authorized_for_review"] and llm.get("producer_status") != "available":
        recommendation = "report remaining infrastructure blocker"
    elif not gate["phase3b_authorized_for_review"]:
        recommendation = "stop CCF-A empirical route"
    text = f"""# Phase 3a-R Producer Recovery Handoff

Updated: {now_utc()}

- Branch: `{git_at(repo_root, ["branch", "--show-current"])}`
- Starting Phase 3a HEAD: `{STARTING_PHASE3A_HEAD}`
- Recovery preregistration commit: `{git_at(repo_root, ["log", "--format=%H", "--", str(RECOVERY_PREREG)]).splitlines()[0] if git_at(repo_root, ["log", "--format=%H", "--", str(RECOVERY_PREREG)]) else ""}`
- Clang recovery status: `{clang.get("producer_status", clang.get("status", ""))}`
- LLM4Decompile recovery status: `{llm.get("producer_status", llm.get("status", ""))}`; blocker `{llm.get("blocker", "")}`
- Recovery matrix size: `{len(p3a.read_csv_rows(repo_root / RECOVERY_MATRIX_PATH))}`
- Recovered candidate seal commit and hash: `{git_at(repo_root, ["log", "-1", "--format=%H", "--", str(CANDIDATE_SEAL_PATH)])}` / `{seal_hash}`
- Recovered labeling result commit and final HEAD: pending final commit / `{git_at(repo_root, ["rev-parse", "HEAD"])}`
- Original Phase 3a candidate seal hash: `{CANONICAL_CANDIDATE_SEAL}`
- Verified function/fixture seal: `{CANONICAL_FUNCTION_FIXTURE_SEAL}`
- Recovered attempts by producer/build view: `{json.dumps(counts_by(recovered_rows, "producer", "build_view"), sort_keys=True)}`
- Recovered parse-ready count: `{sum(1 for row in recovered_rows if row.get("parse_status") == "parsed_function")}`
- Recovered compile-ready count: `{sum(1 for row in recovered_rows if row.get("compile_status") == "compile_ready")}`
- Recovered semantic_wrong count: `{rec_label_counts.get("semantic_wrong", 0)}`
- Recovered fixture-passing semantic_wrong count: `{sum(1 for row in recovered_replay if row.get("fixture_replay_label") == "fixture_passing_semantic_wrong")}`
- Recovered fixture-failing semantic_wrong count: `{sum(1 for row in recovered_replay if row.get("fixture_replay_label") == "fixture_failing_semantic_wrong")}`
- Combined candidate count: `{len(combined_manifest)}`
- Combined compile-ready count: `{sum(1 for row in combined_manifest if row.get("compile_status") == "compile_ready")}`
- Combined semantic_wrong count: `{combo_label_counts.get("semantic_wrong", 0)}`
- Combined fixture-passing semantic_wrong count: `{gate["natural_wrong_count"]}`
- Combined no_mismatch count: `{combo_label_counts.get("no_mismatch_under_exact_audit_domain", 0)}`
- Combined non_evaluable count and reasons: `{json.dumps(dict(combo_non_eval.most_common()), sort_keys=True)}`
- Natural wrong counts by project: `{json.dumps(dict(Counter(row["project"] for row in descriptors if str(row.get("counts_for_gate")) == "1")), sort_keys=True)}`
- Natural wrong counts by function: `{json.dumps(dict(Counter(row["selected_function_id"] for row in descriptors if str(row.get("counts_for_gate")) == "1")), sort_keys=True)}`
- Natural wrong counts by producer: `{json.dumps(dict(Counter(row["producer"] for row in descriptors if str(row.get("counts_for_gate")) == "1")), sort_keys=True)}`
- Natural wrong counts by build view: `{json.dumps(dict(Counter(row["build_view"] for row in descriptors if str(row.get("counts_for_gate")) == "1")), sort_keys=True)}`
- Preliminary error-category counts: `{json.dumps(gate["category_counts"], sort_keys=True)}`
- Low-density count: `{gate["low_density_count"]}`
- Multi-argument/loop/lookup error count: `{gate["multi_argument_loop_lookup_count"]}`
- mycodex API usage and cost: `{sum(1 for row in recovered_rows if row.get("producer") == "mycodex_api" and row.get("non_evaluable_reason") == "api_exception")}` attempted mycodex Clang-O2 recovery requests were blocked locally by sandbox network permissions (`URLError(PermissionError(1, 'Operation not permitted'))`); no provider response IDs or usage were returned, and no post-label retry was performed.
- LLM4Decompile GPU time, batch size, precision, peak memory: GPU smoke/generation blocked by escalation infrastructure; batch size `{p3a.LLM_DECODING["batch_size"]}`, precision `{p3a.LLM_DECODING["precision"]}`, peak memory `0`.
- Exact census-gate outcome: minimum `{gate["minimum_gate_status"]}`, strong `{gate["strong_gate_status"]}`.
- Phase 3b auditor evaluation authorized: `{gate["phase3b_authorized_for_review"]}`
- Tests run: `{json.dumps(tests, sort_keys=True)}`
- Confirmation: no auditing policy was run.
- Confirmation: libFuzzer was not run.
- Confirmation: no budget curves or auditor tables were generated.
- Exact recommendation: `{recommendation}`.
"""
    (repo_root / HANDOFF_PATH).write_text(text, encoding="utf-8")
    return {"stage": "handoff", "recommendation": recommendation, "minimum_gate": gate["minimum_gate_status"]}


def phase3ar_candidate_id_for(function_id: str, producer: str, build_view: str) -> str:
    digest = hashlib.sha256(f"phase3ar|{function_id}|{producer}|{build_view}".encode("utf-8")).hexdigest()[:12]
    return f"phase3ar::{corpus.safe_name(function_id)}::{producer}::{build_view}::{digest}"


def render_recovery_build_source(function: corpus.FunctionRecord) -> str:
    arg_rows = "\n".join(f"volatile long long phase3ar_input_{index};" for index, _ in enumerate(function.params))
    call_args = ", ".join(f"({param.type_text})phase3ar_input_{index}" for index, param in enumerate(function.params))
    return "\n".join(
        [
            "#include <stdbool.h>",
            "#include <stddef.h>",
            "#include <stdint.h>",
            "",
            function.support_source.strip(),
            "",
            function.source.rstrip(),
            "",
            "volatile long long phase3a_sink;",
            arg_rows,
            "int main(void) {",
            f"    phase3a_sink = (long long){function.function_name}({call_args});",
            "    return (int)(phase3a_sink & 0);",
            "}",
            "",
        ]
    )


def matrix_committed(repo_root: Path) -> bool:
    if not (repo_root / RECOVERY_MATRIX_PATH).exists():
        return False
    commit = git_at(repo_root, ["log", "-1", "--format=%H", "--", str(RECOVERY_MATRIX_PATH)])
    diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(RECOVERY_MATRIX_PATH)], cwd=repo_root)
    return bool(commit) and diff.returncode == 0


def recovery_candidate_seal_committed(repo_root: Path) -> bool:
    if not (repo_root / CANDIDATE_SEAL_PATH).exists() or not (repo_root / CANDIDATE_SEAL_SHA_PATH).exists():
        return False
    commit = git_at(repo_root, ["log", "-1", "--format=%H", "--", str(CANDIDATE_SEAL_PATH)])
    diff = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", str(CANDIDATE_SEAL_PATH), str(CANDIDATE_SEAL_SHA_PATH)],
        cwd=repo_root,
    )
    return bool(commit) and diff.returncode == 0


def write_label_summary(path: Path, labels: list[dict[str, Any]], fixture_replay: list[dict[str, Any]]) -> None:
    label_counts = Counter(row["label"] for row in labels)
    reason_counts = Counter(row["label_reason"] for row in labels if row["label"] == "non_evaluable")
    replay_counts = Counter(row["fixture_replay_label"] for row in fixture_replay)
    rows = []
    for key, value in sorted(label_counts.items()):
        rows.append({"metric": "label:" + key, "count": value})
    for key, value in sorted(replay_counts.items()):
        rows.append({"metric": "fixture_replay:" + key, "count": value})
    for key, value in reason_counts.most_common():
        rows.append({"metric": "non_evaluable_reason:" + key, "count": value})
    p3a.write_csv(path, rows, ["metric", "count"])


def write_descriptors(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "candidate_id",
        "census_phase",
        "original_candidate_id",
        "project",
        "producer",
        "build_view",
        "function",
        "selected_function_id",
        "argument_count",
        "ast_node_count",
        "cyclomatic_complexity",
        "branch_count",
        "loop_count",
        "switch_presence",
        "lookup_table_access",
        "bitwise_operation_count",
        "comparison_count",
        "character_literal_count",
        "integer_literal_count",
        "domain_size",
        "mismatch_count",
        "mismatch_density",
        "connected_mismatch_intervals_1d",
        "boundary_distance",
        "fixture_distance",
        "categorical_value_concentration",
        "argument_interaction_dependent",
        "compile_normalization_extent",
        "taxonomy_tags",
        "primary_taxonomy_tag",
        "fixture_replay_label",
        "counts_for_gate",
        "recovered_clang_O2_cell",
        "recovered_llm4decompile_interface_cell",
    ]
    p3a.write_csv(path, rows, fields)


def gate_descriptors(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for row in rows:
        if str(row.get("counts_for_gate", "")) != "1":
            continue
        item = dict(row)
        for key in ["mismatch_density"]:
            item[key] = float(item[key])
        for key in ["argument_count", "loop_count", "lookup_table_access"]:
            item[key] = int(item[key])
        out.append(item)
    return out


def guard_against_auditor_imports() -> dict[str, bool]:
    imports_ok = True
    calls_ok = True
    for path in [Path(__file__), Path(p3a.__file__)]:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in p3a.FORBIDDEN_AUDITOR_IMPORTS:
                imports_ok = False
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in p3a.FORBIDDEN_AUDITOR_IMPORTS:
                        imports_ok = False
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in p3a.FORBIDDEN_AUDITOR_CALLS:
                    calls_ok = False
                if isinstance(node.func, ast.Attribute) and node.func.attr in p3a.FORBIDDEN_AUDITOR_CALLS:
                    calls_ok = False
    return {"imports_ok": imports_ok, "calls_ok": calls_ok}


def counts_by(rows: list[dict[str, Any]], a: str, b: str) -> dict[str, int]:
    return {f"{ka}/{kb}": value for (ka, kb), value in Counter((row[a], row[b]) for row in rows).items()}


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.read_text(encoding="utf-8", errors="ignore").strip():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def git_at(path: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=path, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def gpu_name() -> str:
    nvidia_smi = shutil.which("nvidia-smi")
    if not nvidia_smi:
        return ""
    result = subprocess.run([nvidia_smi, "-L"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.stdout.strip()


if __name__ == "__main__":
    main()
