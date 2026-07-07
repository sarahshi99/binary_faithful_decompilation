from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import itertools
import json
import os
import re
import shutil
import subprocess
import textwrap
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from analysis.decompile_faithfulness import phase3a_corpus as corpus


PHASE3A_BRANCH = "phase3a-prospective-natural-error-census"
CANONICAL_FUNCTION_FIXTURE_SEAL = "2bba63e1a191050f2ec0e15a8f58ed7eff9a5c9bf1f21b672b7ab9bfc64c1494"
BUILD_VIEWS = {
    "gcc_O0": {
        "compiler": "/usr/bin/gcc",
        "compiler_label": "gcc",
        "flags": ["-std=c11", "-Wall", "-Wextra", "-Wno-unused-const-variable", "-O0", "-g", "-fno-inline"],
    },
    "clang_O2": {
        "compiler": "clang",
        "compiler_label": "clang",
        "flags": ["-std=c11", "-Wall", "-Wextra", "-Wno-unused-const-variable", "-O2", "-g", "-fno-inline"],
    },
}
PRODUCERS = ("ghidra", "angr", "llm4decompile", "mycodex_api")
GHIDRA_JAVA_HOME = Path(
    "analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/root/usr/lib/jvm/java-21-openjdk-amd64"
)
GHIDRA_HEADLESS = Path(
    "analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/ghidra_12.1.2_PUBLIC/support/analyzeHeadless"
)
ANGR_PYTHON = Path("/home/shx/.venvs/phase3a-angr/bin/python")
LLM_PYTHON = Path("/home/shx/miniconda3/envs/dllm_env/bin/python")
LLM_MODEL_PATH = Path(
    "/home/shx/.cache/huggingface/hub/models--LLM4Binary--llm4decompile-22b-v2/snapshots/be2ac0bbb3bfa508d9f8a4790329250f1cb13ddc"
)
LLM_MODEL_IDENTIFIER = "LLM4Binary/llm4decompile-22b-v2"
LLM_MODEL_SNAPSHOT = "be2ac0bbb3bfa508d9f8a4790329250f1cb13ddc"
LLM_DECODING = {"do_sample": False, "temperature": 0, "max_new_tokens": 768, "batch_size": 1, "precision": "bfloat16"}
API_PROVIDER = "mycodex"
API_ENDPOINT = "https://wokeme.dpdns.org/v1/responses"
API_MODEL = "gpt-5.5"
API_PARAMETERS = {"temperature": 0, "max_output_tokens": 2048, "stream": False}
WORK_DIR = Path("analysis_outputs/decompile_faithfulness/phase3a_candidates")
RESULT_DIR = Path("results/decompile_faithfulness")
ANALYSIS_DIR = Path("analysis/decompile_faithfulness")
MANIFEST_PATH = RESULT_DIR / "phase3a_candidate_manifest.jsonl"
PROVENANCE_PATH = RESULT_DIR / "phase3a_candidate_provenance.csv"
CANDIDATE_SEAL_PATH = ANALYSIS_DIR / "phase3a_candidate_seal.json"
CANDIDATE_SEAL_SHA_PATH = ANALYSIS_DIR / "phase3a_candidate_seal.sha256"
LABELS_PATH = RESULT_DIR / "phase3a_exact_labels.jsonl"
LABEL_SUMMARY_PATH = RESULT_DIR / "phase3a_label_summary.csv"
FIXTURE_REPLAY_PATH = RESULT_DIR / "phase3a_fixture_replay.jsonl"
DESCRIPTORS_PATH = RESULT_DIR / "phase3a_natural_error_descriptors.csv"
TAXONOMY_PACKET_PATH = RESULT_DIR / "phase3a_taxonomy_review_packet.jsonl"
FUNCTION_CORPUS_TABLE = Path("paper/tables/phase3a_function_corpus.tex")
CANDIDATE_YIELD_TABLE = Path("paper/tables/phase3a_candidate_yield.tex")
NATURAL_ERROR_TABLE = Path("paper/tables/phase3a_natural_error_census.tex")
FLOW_DATA = Path("figures/data/phase3a_candidate_flow.json")
ERROR_DENSITY_DATA = Path("figures/data/phase3a_error_density.csv")
ERROR_PRODUCER_DATA = Path("figures/data/phase3a_error_producer_distribution.csv")
COMMAND_LOG = RESULT_DIR / "phase3a_candidate_generation_log.jsonl"

FORBIDDEN_AUDITOR_IMPORTS = {
    "analysis.decompile_faithfulness.holdout_evaluation",
    "analysis.decompile_faithfulness.libfuzzer_wallclock",
    "analysis.decompile_faithfulness.source_behavioral_diversity",
    "analysis.decompile_faithfulness.strong_baselines_and_mechanism",
    "analysis.decompile_faithfulness.run_phase18_source_literal_char_policy",
    "analysis.decompile_faithfulness.run_phase11_input_ordering",
    "analysis.decompile_faithfulness.dynamic_trace",
    "analysis.decompile_faithfulness.ranking",
}
FORBIDDEN_AUDITOR_CALLS = {
    "build_ordered_inputs",
    "source_literal_char_inputs",
    "fixture_neighbor_inputs",
    "interleave_inputs",
    "run_policy",
    "run_trace",
    "build_libfuzzer_harness",
}


@dataclass(frozen=True)
class SelectedFunction:
    record: corpus.FunctionRecord
    row: dict[str, str]
    rank: int


@dataclass(frozen=True)
class BuildArtifact:
    function_id: str
    build_view: str
    ok: bool
    source_path: Path
    binary_path: Path
    compiler_command: list[str]
    compile_log_path: Path
    symbol_metadata_path: Path
    disassembly_path: Path
    binary_hash: str
    reason: str = ""


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    if args.stage == "generate":
        summary = generate_candidates(repo_root)
    elif args.stage == "label":
        summary = label_candidates(repo_root)
    elif args.stage == "tables":
        summary = write_tables_and_handoff(repo_root)
    else:
        raise ValueError(args.stage)
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 3a candidate generation and natural-error census.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--stage", choices=["generate", "label", "tables"], required=True)
    return parser.parse_args()


def generate_candidates(repo_root: Path) -> dict[str, Any]:
    verify_preflight(repo_root)
    selected = load_selected_functions(repo_root)
    availability = json.loads((repo_root / RESULT_DIR / "phase3a_producer_availability.json").read_text(encoding="utf-8"))
    available = tuple(
        producer for producer in PRODUCERS
        if availability.get("producers", {}).get(producer, {}).get("producer_status") == "available"
    )
    if set(available) != set(PRODUCERS):
        raise RuntimeError(f"Phase 3a expected producers {PRODUCERS}, available={available}")

    command_log = repo_root / COMMAND_LOG
    command_log.parent.mkdir(parents=True, exist_ok=True)
    command_log.write_text("", encoding="utf-8")
    work = repo_root / WORK_DIR
    for sub in ["build", "raw", "parsed", "normalized", "compile", "prompts", "logs", "ghidra_projects"]:
        (work / sub).mkdir(parents=True, exist_ok=True)

    builds = build_all_binaries(repo_root, selected, command_log)
    rows: list[dict[str, Any]] = []
    for function in selected:
        for build_view in BUILD_VIEWS:
            artifact = builds[(function.record.function_id, build_view)]
            for producer in PRODUCERS:
                rows.append(process_attempt(repo_root, function, artifact, producer, availability, command_log))

    rows = run_llm4decompile_batch(repo_root, rows)
    rows = run_api_requests(repo_root, rows)
    rows = finalize_manifest_rows(repo_root, rows)
    write_jsonl(repo_root / MANIFEST_PATH, rows)
    write_candidate_provenance(repo_root / PROVENANCE_PATH, rows)
    seal = build_candidate_seal(repo_root, rows)
    write_json(repo_root / CANDIDATE_SEAL_PATH, seal)
    seal_hash = sha256_path(repo_root / CANDIDATE_SEAL_PATH)
    (repo_root / CANDIDATE_SEAL_SHA_PATH).write_text(f"{seal_hash}  phase3a_candidate_seal.json\n", encoding="utf-8")
    update_handoff_after_candidate_seal(repo_root, rows, seal_hash)
    return {
        "stage": "generate",
        "attempts": len(rows),
        "candidate_seal_sha256": seal_hash,
        "parse_ready": sum(1 for row in rows if row["parse_status"] == "parsed_function"),
        "compile_ready": sum(1 for row in rows if row["compile_status"] == "compile_ready"),
        "by_status": dict(Counter(row["final_candidate_status"] for row in rows)),
    }


def verify_preflight(repo_root: Path) -> None:
    if git_at(repo_root, ["branch", "--show-current"]) != PHASE3A_BRANCH:
        raise RuntimeError("not on Phase 3a branch")
    sha_path = repo_root / ANALYSIS_DIR / "phase3a_function_fixture_seal.sha256"
    seal_path = repo_root / ANALYSIS_DIR / "phase3a_function_fixture_seal.json"
    recorded = sha_path.read_text(encoding="utf-8").split()[0]
    recomputed = sha256_path(seal_path)
    if recorded != CANONICAL_FUNCTION_FIXTURE_SEAL or recomputed != CANONICAL_FUNCTION_FIXTURE_SEAL:
        raise RuntimeError(f"function/fixture seal mismatch: recorded={recorded} recomputed={recomputed}")
    selected_rows = read_csv_rows(repo_root / RESULT_DIR / "phase3a_selected_functions.csv")
    if len(selected_rows) != 80:
        raise RuntimeError(f"canonical v1 corpus must contain 80 functions, found {len(selected_rows)}")
    fixtures = read_jsonl(repo_root / RESULT_DIR / "phase3a_fixtures.jsonl")
    if len(fixtures) != 320:
        raise RuntimeError(f"canonical v1 fixtures must contain 320 rows, found {len(fixtures)}")


def load_selected_functions(repo_root: Path) -> list[SelectedFunction]:
    selected_rows = read_csv_rows(repo_root / RESULT_DIR / "phase3a_selected_functions.csv")
    manifest = json.loads((repo_root / RESULT_DIR / "phase3a_project_manifest.json").read_text(encoding="utf-8"))
    project_records = {record["project"]: record for record in manifest["projects"]}
    needed = {row["function_id"]: row for row in selected_rows}
    found: dict[str, corpus.FunctionRecord] = {}
    for row in selected_rows:
        project = row["project"]
        record = project_records[project]
        source_file = Path(record["local_path"]) / row["source_file"]
        text = corpus.read_text_lossy(source_file)
        enum_values = corpus.extract_enum_values(text)
        support_source = corpus.extract_support_source(text)
        for ordinal, parsed in enumerate(corpus.extract_functions(text, enum_values), start=1):
            signature = corpus.parse_signature(parsed["header"], enum_values)
            if signature is None:
                continue
            return_type, params = signature
            function_id = corpus.stable_function_id(project, row["source_file"], parsed["name"], ordinal, parsed["source"])
            if function_id != row["function_id"]:
                continue
            domains = tuple(tuple(item["values"]) for item in json.loads(row["declared_audit_domain"]))
            domain = tuple(itertools.product(*domains))
            found[function_id] = corpus.FunctionRecord(
                project=project,
                pool=row["pool"],
                project_order=int(row["project_order"]),
                source_file=row["source_file"],
                function_name=parsed["name"],
                ordinal=ordinal,
                return_type=return_type,
                params=tuple(params),
                source=parsed["source"],
                support_source=support_source,
                source_sha256=corpus.sha256_text(parsed["source"]),
                source_file_sha256=row["source_file_sha256"],
                function_id=function_id,
                domain_values=domains,
                domain=domain,
                domain_size=len(domain),
                features=features_from_selected_row(row),
            )
            break
    missing = sorted(set(needed) - set(found))
    if missing:
        raise RuntimeError(f"could not reconstruct selected functions: {missing[:5]}")
    return [SelectedFunction(found[row["function_id"]], row, int(row["selection_rank"])) for row in selected_rows]


def features_from_selected_row(row: dict[str, str]) -> dict[str, Any]:
    ints = [
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
        "multiple_interacting_arguments",
        "switch_like_categorical_behavior",
    ]
    features = {name: int(row[name]) for name in ints}
    features["argument_types"] = row["argument_types"]
    return features


def build_all_binaries(repo_root: Path, selected: list[SelectedFunction], command_log: Path) -> dict[tuple[str, str], BuildArtifact]:
    builds: dict[tuple[str, str], BuildArtifact] = {}
    for function in selected:
        for build_view, spec in BUILD_VIEWS.items():
            builds[(function.record.function_id, build_view)] = build_binary(repo_root, function.record, build_view, spec, command_log)
    return builds


def build_binary(repo_root: Path, function: corpus.FunctionRecord, build_view: str, spec: dict[str, Any], command_log: Path) -> BuildArtifact:
    safe_id = corpus.safe_name(function.function_id)
    out_dir = repo_root / WORK_DIR / "build" / safe_id / build_view
    out_dir.mkdir(parents=True, exist_ok=True)
    source_path = out_dir / "wrapper.c"
    binary_path = out_dir / "function.exe"
    compile_log_path = out_dir / "compile_log.json"
    symbol_metadata_path = out_dir / "symbols.json"
    disassembly_path = out_dir / "target_disassembly.s"
    source_path.write_text(render_build_source(function), encoding="utf-8")
    compiler_path = shutil.which(spec["compiler"]) if spec["compiler"] != "/usr/bin/gcc" else spec["compiler"]
    command = [spec["compiler"], *spec["flags"], str(source_path), "-o", str(binary_path)]
    if not compiler_path:
        reason = f"compiler_unavailable:{spec['compiler']}"
        compile_log_path.write_text(json.dumps({"ok": False, "reason": reason, "command": command}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        symbol_metadata_path.write_text(json.dumps({"ok": False, "reason": reason}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        disassembly_path.write_text("", encoding="utf-8")
        return BuildArtifact(function.function_id, build_view, False, source_path, binary_path, command, compile_log_path, symbol_metadata_path, disassembly_path, "", reason)
    command[0] = compiler_path
    result = run_command(command, out_dir, command_log, timeout_s=60)
    compile_log_path.write_text(
        json.dumps({"ok": result.returncode == 0, "command": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    if result.returncode != 0:
        reason = "build_failure"
        symbol_metadata_path.write_text(json.dumps({"ok": False, "reason": reason}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        disassembly_path.write_text("", encoding="utf-8")
        return BuildArtifact(function.function_id, build_view, False, source_path, binary_path, command, compile_log_path, symbol_metadata_path, disassembly_path, "", reason)
    symbols = symbol_metadata(binary_path, function.function_name, out_dir, command_log)
    symbol_metadata_path.write_text(json.dumps(symbols, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    disasm = disassemble_target(binary_path, function.function_name, out_dir, command_log)
    disassembly_path.write_text(disasm, encoding="utf-8")
    binary_hash = sha256_path(binary_path) if binary_path.exists() else ""
    ok = bool(symbols.get("target_symbol_found")) and bool(disasm.strip())
    return BuildArtifact(function.function_id, build_view, ok, source_path, binary_path, command, compile_log_path, symbol_metadata_path, disassembly_path, binary_hash, "" if ok else "target_symbol_or_disassembly_missing")


def render_build_source(function: corpus.FunctionRecord) -> str:
    zero_args = ", ".join(f"({param.type_text})0" for param in function.params)
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
            "int main(void) {",
            f"    phase3a_sink = (long long){function.function_name}({zero_args});",
            "    return (int)(phase3a_sink & 0);",
            "}",
            "",
        ]
    )


def symbol_metadata(binary_path: Path, function_name: str, cwd: Path, command_log: Path) -> dict[str, Any]:
    result = run_command(["/usr/bin/nm", "-an", str(binary_path)], cwd, command_log, timeout_s=30)
    rows = []
    found = False
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[-1] == function_name:
            found = True
            rows.append({"address": parts[0], "type": parts[1], "name": parts[2]})
    return {"ok": result.returncode == 0, "target_symbol_found": found, "target_function": function_name, "symbols": rows}


def disassemble_target(binary_path: Path, function_name: str, cwd: Path, command_log: Path) -> str:
    result = run_command(["/usr/bin/objdump", "-d", "--demangle", str(binary_path)], cwd, command_log, timeout_s=30)
    if result.returncode != 0:
        return ""
    pattern = re.compile(rf"^[0-9a-fA-F]+ <{re.escape(function_name)}>:\s*$")
    lines = result.stdout.splitlines()
    out: list[str] = []
    collecting = False
    for line in lines:
        if pattern.search(line):
            collecting = True
            out.append(line)
            continue
        if collecting and re.match(r"^[0-9a-fA-F]+ <[^>]+>:\s*$", line):
            break
        if collecting:
            out.append(line)
    return "\n".join(out).strip() + ("\n" if out else "")


def process_attempt(
    repo_root: Path,
    function: SelectedFunction,
    artifact: BuildArtifact,
    producer: str,
    availability: dict[str, Any],
    command_log: Path,
) -> dict[str, Any]:
    candidate_id = candidate_id_for(function.record.function_id, producer, artifact.build_view)
    dirs = attempt_dirs(repo_root, candidate_id)
    raw_output_path = dirs["raw"] / "raw_output.c"
    parsed_path = dirs["parsed"] / "parsed_function.c"
    normalized_path = dirs["normalized"] / "candidate.c"
    transform_path = dirs["normalized"] / "transformation_log.json"
    compile_log_path = dirs["compile"] / "compile_log.json"
    prompt_path = dirs["prompts"] / "prompt_payload.json"
    raw_output_path.parent.mkdir(parents=True, exist_ok=True)
    prompt_hash = ""
    prompt_template_id = ""
    if not artifact.ok:
        reason = artifact.reason or "build_unavailable"
        status = "producer_view_unavailable" if reason.startswith("compiler_unavailable:") else "harness_failure"
        write_empty_attempt_artifacts(raw_output_path, parsed_path, normalized_path, transform_path, compile_log_path, reason)
        return base_manifest_row(function, artifact, producer, availability, candidate_id, raw_output_path, parsed_path, normalized_path, transform_path, compile_log_path, prompt_path, prompt_hash, status, "non_evaluable", reason)
    if producer == "ghidra":
        if raw_output_path.exists() and raw_output_path.stat().st_size:
            raw_status, raw_reason = "raw_candidate", ""
        else:
            raw_status, raw_reason = run_ghidra(repo_root, function.record, artifact, raw_output_path, dirs["logs"] / "ghidra_metadata.json", command_log)
    elif producer == "angr":
        if raw_output_path.exists() and raw_output_path.stat().st_size:
            raw_status, raw_reason = "raw_candidate", ""
        else:
            raw_status, raw_reason = run_angr(function.record, artifact, raw_output_path, dirs["logs"] / "angr_metadata.json", command_log)
    elif producer == "llm4decompile":
        prompt_template_id = "phase3a_llm4decompile_disassembly_v1"
        payload = llm_prompt_payload(function.record, artifact)
        prompt_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        prompt_hash = sha256_path(prompt_path)
        if raw_output_path.exists() and raw_output_path.stat().st_size:
            raw_status, raw_reason = "raw_candidate", ""
        else:
            raw_status, raw_reason = "pending_llm4decompile", ""
            raw_output_path.write_text("", encoding="utf-8")
    elif producer == "mycodex_api":
        prompt_template_id = "phase3a_mycodex_disassembly_v1"
        payload = api_prompt_payload(function.record, artifact)
        prompt_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        prompt_hash = sha256_path(prompt_path)
        if raw_output_path.exists() and raw_output_path.stat().st_size:
            raw_status, raw_reason = "raw_candidate", ""
        else:
            raw_status, raw_reason = "pending_api", ""
            raw_output_path.write_text("", encoding="utf-8")
    else:
        raise ValueError(producer)
    if raw_status.startswith("pending_"):
        parse_status = "pending"
        compile_status = "pending"
        final_status = raw_status
        non_evaluable_reason = ""
        transform_path.write_text(json.dumps({"status": raw_status, "forbidden_semantic_repair_used": False}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        compile_log_path.write_text(json.dumps({"status": "pending"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    elif raw_status != "raw_candidate":
        parse_status = "parse_failure"
        compile_status = "non_evaluable"
        final_status = raw_status
        non_evaluable_reason = raw_reason
        write_empty_processing_artifacts(parsed_path, normalized_path, transform_path, compile_log_path, raw_reason)
    else:
        processing = normalize_candidate(raw_output_path.read_text(encoding="utf-8", errors="ignore"), function.record)
        parsed_path.write_text(processing["extracted_source"], encoding="utf-8")
        normalized_path.write_text(processing["normalized_source"], encoding="utf-8")
        transform_path.write_text(json.dumps(processing["transform_log"], sort_keys=True, indent=2) + "\n", encoding="utf-8")
        compile_check = compile_normalized_candidate(repo_root, function.record, normalized_path, dirs["compile"], command_log)
        compile_log_path.write_text(json.dumps(compile_check, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        parse_status = processing["parse_status"]
        compile_status = "compile_ready" if compile_check["ok"] and parse_status == "parsed_function" else "non_evaluable"
        final_status = "minimally_normalized_candidate" if compile_status == "compile_ready" else ("compile_failure" if parse_status == "parsed_function" else "parse_failure")
        non_evaluable_reason = "" if compile_status == "compile_ready" else (compile_check.get("reason") or processing.get("parse_reason") or raw_reason)
    row = base_manifest_row(function, artifact, producer, availability, candidate_id, raw_output_path, parsed_path, normalized_path, transform_path, compile_log_path, prompt_path, prompt_hash, final_status, compile_status, non_evaluable_reason)
    row["parse_status"] = parse_status
    row["compile_status"] = compile_status
    row["harness_status"] = compile_status if compile_status == "compile_ready" else "not_run"
    row["prompt_template_id"] = prompt_template_id
    row["raw_generation_status"] = raw_status
    return row


def run_ghidra(
    repo_root: Path,
    function: corpus.FunctionRecord,
    artifact: BuildArtifact,
    raw_output_path: Path,
    metadata_path: Path,
    command_log: Path,
) -> tuple[str, str]:
    headless = repo_root / GHIDRA_HEADLESS
    java_home = repo_root / GHIDRA_JAVA_HOME
    if not headless.exists() or not java_home.exists():
        raw_output_path.write_text("", encoding="utf-8")
        metadata_path.write_text(json.dumps({"status": "tool_unavailable"}, sort_keys=True) + "\n", encoding="utf-8")
        return "decompilation_failure", "ghidra_unavailable"
    project_dir = repo_root / WORK_DIR / "ghidra_projects"
    project_name = "p3a_" + corpus.safe_name(artifact.function_id + "_" + artifact.build_view)
    env = os.environ.copy()
    env["JAVA_HOME"] = str(java_home)
    env["PATH"] = str(java_home / "bin") + os.pathsep + env.get("PATH", "")
    cmd = [
        str(headless),
        str(project_dir),
        project_name,
        "-import",
        str(artifact.binary_path),
        "-scriptPath",
        str(repo_root / "analysis/decompile_faithfulness/ghidra_scripts"),
        "-postScript",
        "ExportFunctionDecomp.java",
        function.function_name,
        str(raw_output_path),
        str(metadata_path),
        "-deleteProject",
    ]
    result = run_command(cmd, repo_root, command_log, timeout_s=180, env=env)
    if result.returncode != 0:
        raw_output_path.write_text("", encoding="utf-8")
        return "decompilation_failure", "ghidra_headless_failure"
    metadata = load_json_if_exists(metadata_path)
    if metadata.get("status") != "decompiled" or not raw_output_path.exists() or not raw_output_path.read_text(encoding="utf-8", errors="ignore").strip():
        return "decompilation_failure", metadata.get("status", "ghidra_no_output")
    return "raw_candidate", ""


def run_angr(
    function: corpus.FunctionRecord,
    artifact: BuildArtifact,
    raw_output_path: Path,
    metadata_path: Path,
    command_log: Path,
) -> tuple[str, str]:
    if not ANGR_PYTHON.exists():
        raw_output_path.write_text("", encoding="utf-8")
        metadata_path.write_text(json.dumps({"status": "tool_unavailable"}, sort_keys=True) + "\n", encoding="utf-8")
        return "decompilation_failure", "angr_python_unavailable"
    helper = textwrap.dedent(
        """
        import json, sys, traceback
        binary, func_name, raw_path, meta_path = sys.argv[1:5]
        payload = {"status": "started", "function_name": func_name}
        try:
            import angr
            project = angr.Project(binary, auto_load_libs=False)
            cfg = project.analyses.CFGFast(normalize=True, data_references=True)
            func = project.kb.functions.function(name=func_name)
            if func is None:
                payload["status"] = "missing_function"
                open(raw_path, "w", encoding="utf-8").write("")
            else:
                decomp = project.analyses.Decompiler(func, cfg=cfg.model)
                text = str(decomp.codegen.text if decomp.codegen is not None else "")
                open(raw_path, "w", encoding="utf-8").write(text + ("" if text.endswith("\\n") else "\\n"))
                payload.update({"status": "decompiled" if text.strip() else "empty_output", "c_size": len(text)})
        except Exception as exc:
            payload.update({"status": "exception", "error": repr(exc), "traceback_tail": traceback.format_exc()[-2000:]})
            open(raw_path, "w", encoding="utf-8").write("")
        open(meta_path, "w", encoding="utf-8").write(json.dumps(payload, sort_keys=True) + "\\n")
        sys.exit(0 if payload.get("status") == "decompiled" else 2)
        """
    )
    result = run_command([str(ANGR_PYTHON), "-c", helper, str(artifact.binary_path), function.function_name, str(raw_output_path), str(metadata_path)], artifact.binary_path.parent, command_log, timeout_s=180)
    metadata = load_json_if_exists(metadata_path)
    if result.returncode != 0 or metadata.get("status") != "decompiled":
        return "decompilation_failure", metadata.get("status", "angr_failure")
    return "raw_candidate", ""


def run_llm4decompile_batch(repo_root: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pending = [row for row in rows if row.get("final_candidate_status") == "pending_llm4decompile"]
    if not pending:
        return rows
    request_path = repo_root / WORK_DIR / "prompts" / "llm4decompile_requests.jsonl"
    response_path = repo_root / WORK_DIR / "raw" / "llm4decompile_responses.jsonl"
    request_path.parent.mkdir(parents=True, exist_ok=True)
    requests = []
    for row in pending:
        prompt_payload = json.loads(Path(row["prompt_payload_path"]).read_text(encoding="utf-8"))
        requests.append(
            {
                "candidate_id": row["candidate_id"],
                "prompt": prompt_payload["prompt"],
                "raw_output_path": row["raw_output_path"],
                "metadata_path": str(Path(row["raw_output_path"]).with_name("llm4decompile_metadata.json")),
            }
        )
    write_jsonl(request_path, requests)
    helper_path = repo_root / WORK_DIR / "logs" / "llm4decompile_generate_helper.py"
    helper_path.parent.mkdir(parents=True, exist_ok=True)
    helper_path.write_text(llm_helper_source(), encoding="utf-8")
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = env.get("CUDA_VISIBLE_DEVICES", "0")
    env["TOKENIZERS_PARALLELISM"] = "false"
    env["TRANSFORMERS_OFFLINE"] = "1"
    env["HF_HUB_OFFLINE"] = "1"
    command_log = repo_root / COMMAND_LOG
    result = run_command(
        [
            str(LLM_PYTHON),
            str(helper_path),
            "--model-path",
            str(LLM_MODEL_PATH),
            "--requests",
            str(request_path),
            "--responses",
            str(response_path),
            "--max-new-tokens",
            str(LLM_DECODING["max_new_tokens"]),
        ],
        repo_root,
        command_log,
        timeout_s=max(600, 90 * len(requests)),
        env=env,
    )
    response_by_id = {item["candidate_id"]: item for item in read_jsonl(response_path)} if response_path.exists() else {}
    updated = []
    for row in rows:
        if row.get("final_candidate_status") != "pending_llm4decompile":
            updated.append(row)
            continue
        response = response_by_id.get(row["candidate_id"], {"status": "batch_failure", "error": result.stderr[-1000:]})
        raw_path = Path(row["raw_output_path"])
        metadata_path = raw_path.with_name("llm4decompile_metadata.json")
        metadata_path.write_text(json.dumps(response, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        if response.get("status") == "ok":
            raw_path.write_text(response.get("text", ""), encoding="utf-8")
            row = process_generated_raw(repo_root, row, "raw_candidate", "")
            row["llm4decompile_finish_reason"] = response.get("finish_reason", "")
            row["llm4decompile_input_tokens"] = response.get("input_tokens", 0)
            row["llm4decompile_output_tokens"] = response.get("output_tokens", 0)
            row["llm4decompile_gpu_peak_memory_mib"] = response.get("gpu_peak_memory_mib", 0)
            row["llm4decompile_generate_s"] = response.get("generate_s", 0)
        else:
            raw_path.write_text("", encoding="utf-8")
            row = mark_generation_failure(row, "decompilation_failure", "llm4decompile_" + str(response.get("status", "failure")))
        updated.append(row)
    return updated


def llm_helper_source() -> str:
    return r'''
from __future__ import annotations
import argparse, json, time
from pathlib import Path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", required=True)
    parser.add_argument("--requests", required=True)
    parser.add_argument("--responses", required=True)
    parser.add_argument("--max-new-tokens", type=int, required=True)
    args = parser.parse_args()
    import torch
    from transformers import AutoModelForCausalLM, PreTrainedTokenizerFast
    tokenizer = PreTrainedTokenizerFast(tokenizer_file=str(Path(args.model_path) / "tokenizer.json"))
    tokenizer.eos_token = "</s>"
    tokenizer.bos_token = "<s>"
    tokenizer.unk_token = "<unk>"
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model_path,
        local_files_only=True,
        trust_remote_code=False,
        torch_dtype=torch.bfloat16,
        device_map="auto",
    )
    requests = [json.loads(line) for line in Path(args.requests).read_text(encoding="utf-8").splitlines() if line.strip()]
    responses = []
    for item in requests:
        started = time.perf_counter()
        try:
            prompt = item["prompt"]
            inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
            before = torch.cuda.max_memory_allocated() if torch.cuda.is_available() else 0
            with torch.inference_mode():
                outputs = model.generate(
                    **inputs,
                    do_sample=False,
                    max_new_tokens=args.max_new_tokens,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
            new_tokens = outputs[0][inputs["input_ids"].shape[-1]:]
            text = tokenizer.decode(new_tokens, skip_special_tokens=True)
            peak = torch.cuda.max_memory_allocated() if torch.cuda.is_available() else before
            responses.append({
                "candidate_id": item["candidate_id"],
                "status": "ok",
                "text": text,
                "finish_reason": "eos_or_max_new_tokens",
                "input_tokens": int(inputs["input_ids"].shape[-1]),
                "output_tokens": int(new_tokens.shape[-1]),
                "generate_s": round(time.perf_counter() - started, 3),
                "gpu_peak_memory_mib": round(peak / 1024 / 1024, 1),
            })
        except Exception as exc:
            responses.append({"candidate_id": item["candidate_id"], "status": "exception", "error": repr(exc)})
        Path(args.responses).write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in responses), encoding="utf-8")

if __name__ == "__main__":
    main()
'''


def run_api_requests(repo_root: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
            row = mark_generation_failure(row, "decompilation_failure", "api_key_unavailable")
            updated.append(row)
            continue
        payload = json.loads(Path(row["prompt_payload_path"]).read_text(encoding="utf-8"))
        try:
            raw_payload, metadata = call_api(payload["request_payload"], api_key)
        except PermissionError:
            raise
        except Exception as exc:
            text = repr(exc)
            if "Operation not permitted" in text or "Permission denied" in text:
                raise
            metadata_path.write_text(json.dumps({"status": "exception", "error": text}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            row = mark_generation_failure(row, "decompilation_failure", "api_exception")
            updated.append(row)
            continue
        response_json_path.write_text(json.dumps(raw_payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        metadata_path.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        returned_model = raw_payload.get("model", "")
        if returned_model and returned_model != API_MODEL:
            row = mark_generation_failure(row, "decompilation_failure", "api_model_mismatch")
            updated.append(row)
            continue
        text = extract_api_text(raw_payload)
        raw_path.write_text(text, encoding="utf-8")
        row = process_generated_raw(repo_root, row, "raw_candidate", "")
        row["api_returned_model"] = returned_model
        row["api_request_id"] = raw_payload.get("id", "")
        row["api_finish_reason"] = response_finish_reason(raw_payload)
        row["api_usage"] = raw_payload.get("usage", {})
        updated.append(row)
    return updated


def call_api(payload: dict[str, Any], api_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    started = time.perf_counter()
    request = urllib.request.Request(
        API_ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": "Bearer " + api_key, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        raw = response.read().decode("utf-8", "replace")
        return json.loads(raw), {"status": response.status, "elapsed_s": round(time.perf_counter() - started, 3)}


def process_generated_raw(repo_root: Path, row: dict[str, Any], raw_status: str, raw_reason: str) -> dict[str, Any]:
    function = reconstruct_one(repo_root, row["selected_function_id"])
    normalized_path = Path(row["normalized_candidate_path"])
    parsed_path = Path(row["parsed_function_path"])
    transform_path = Path(row["transformation_log_path"])
    compile_log_path = Path(row["compile_log_path"])
    processing = normalize_candidate(Path(row["raw_output_path"]).read_text(encoding="utf-8", errors="ignore"), function.record)
    parsed_path.write_text(processing["extracted_source"], encoding="utf-8")
    normalized_path.write_text(processing["normalized_source"], encoding="utf-8")
    transform_path.write_text(json.dumps(processing["transform_log"], sort_keys=True, indent=2) + "\n", encoding="utf-8")
    compile_check = compile_normalized_candidate(repo_root, function.record, normalized_path, compile_log_path.parent, repo_root / COMMAND_LOG)
    compile_log_path.write_text(json.dumps(compile_check, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    row["raw_generation_status"] = raw_status
    row["parse_status"] = processing["parse_status"]
    row["compile_status"] = "compile_ready" if compile_check["ok"] and processing["parse_status"] == "parsed_function" else "non_evaluable"
    row["harness_status"] = row["compile_status"]
    row["final_candidate_status"] = "minimally_normalized_candidate" if row["compile_status"] == "compile_ready" else ("compile_failure" if processing["parse_status"] == "parsed_function" else "parse_failure")
    row["non_evaluable_reason"] = "" if row["compile_status"] == "compile_ready" else (compile_check.get("reason") or processing.get("parse_reason") or raw_reason)
    return row


def reconstruct_one(repo_root: Path, function_id: str) -> SelectedFunction:
    for selected in load_selected_functions(repo_root):
        if selected.record.function_id == function_id:
            return selected
    raise KeyError(function_id)


def mark_generation_failure(row: dict[str, Any], status: str, reason: str) -> dict[str, Any]:
    Path(row["raw_output_path"]).write_text("", encoding="utf-8")
    write_empty_processing_artifacts(Path(row["parsed_function_path"]), Path(row["normalized_candidate_path"]), Path(row["transformation_log_path"]), Path(row["compile_log_path"]), reason)
    row["parse_status"] = "parse_failure"
    row["compile_status"] = "non_evaluable"
    row["harness_status"] = "not_run"
    row["final_candidate_status"] = status
    row["non_evaluable_reason"] = reason
    return row


def normalize_candidate(raw_text: str, function: corpus.FunctionRecord) -> dict[str, Any]:
    text = strip_markdown_fences(raw_text)
    extracted, parse_reason = extract_first_function(text)
    if not extracted:
        return {
            "parse_status": "parse_failure",
            "parse_reason": parse_reason,
            "extracted_source": "",
            "normalized_source": "",
            "transform_log": transform_log(["markdown_fence_removal", "first_function_extraction_failed"], False, parse_reason),
        }
    body = extracted[extracted.find("{") :].strip()
    raw_params = raw_param_names(extracted)
    params = []
    for index, param in enumerate(function.params):
        name = raw_params[index] if index < len(raw_params) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", raw_params[index]) else param.name
        params.append(corpus.Param(param.type_text, name))
    header = corpus.signature_from_parts(function.return_type, "phase3a_candidate", params)
    normalized = fixed_candidate_prelude() + "\n" + header + "\n" + body + "\n"
    operations = [
        "markdown_fence_removal",
        "first_complete_function_extraction",
        "deterministic_function_renaming",
        "sealed_signature_type_adaptation",
        "fixed_width_header_insertion",
    ]
    return {
        "parse_status": "parsed_function",
        "parse_reason": "",
        "extracted_source": extracted,
        "normalized_source": normalized,
        "transform_log": transform_log(operations, False, ""),
    }


def transform_log(operations: list[str], semantic_repair: bool, parse_reason: str) -> dict[str, Any]:
    return {
        "allowed_operations": operations,
        "forbidden_semantic_repair_used": semantic_repair,
        "consulted_trusted_source": False,
        "consulted_fixtures_or_labels": False,
        "execution_feedback_repair_used": False,
        "source_aware_constant_or_branch_repair_used": False,
        "parse_reason": parse_reason,
    }


def strip_markdown_fences(text: str) -> str:
    text = text.strip()
    match = re.search(r"```(?:c|C|cpp|text)?\s*(.*?)```", text, re.S)
    return match.group(1).strip() if match else text


def extract_first_function(text: str) -> tuple[str, str]:
    clean = text.strip()
    for match in re.finditer(r"([A-Za-z_][A-Za-z0-9_\s\*\(\)]*?)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^;{}]*)\)\s*\{", clean):
        brace = clean.find("{", match.end() - 1)
        end = corpus.matching_brace(clean, brace)
        if end is not None:
            return clean[match.start() : end + 1].strip(), ""
    return "", "no_complete_function_found"


def raw_param_names(function_text: str) -> list[str]:
    header = function_text.split("{", 1)[0]
    params = header.split("(", 1)[1].rsplit(")", 1)[0].strip() if "(" in header and ")" in header else ""
    if not params or params == "void":
        return []
    names = []
    for raw in corpus.split_params(params):
        raw = raw.strip()
        name = raw.split()[-1].replace("*", "").strip()
        names.append(name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else "")
    return names


def fixed_candidate_prelude() -> str:
    return "\n".join(
        [
            "#include <stdbool.h>",
            "#include <stddef.h>",
            "#include <stdint.h>",
            "typedef unsigned char byte;",
            "typedef unsigned char undefined1;",
            "typedef unsigned short undefined2;",
            "typedef unsigned int undefined4;",
            "typedef unsigned long long undefined8;",
            "typedef unsigned int uint;",
            "typedef unsigned long ulong;",
            "typedef unsigned long long ulonglong;",
            "typedef unsigned short ushort;",
            "typedef unsigned char uchar;",
            "typedef signed char sbyte;",
            "typedef signed char int1;",
            "typedef short int2;",
            "typedef int int4;",
            "typedef long long int8;",
            "typedef unsigned char uint1;",
            "typedef unsigned short uint2;",
            "typedef unsigned int uint4;",
            "typedef unsigned long long uint8;",
            "",
        ]
    )


def compile_normalized_candidate(repo_root: Path, function: corpus.FunctionRecord, normalized_path: Path, compile_dir: Path, command_log: Path) -> dict[str, Any]:
    compile_dir.mkdir(parents=True, exist_ok=True)
    harness_path = compile_dir / "compile_harness.c"
    exe_path = compile_dir / "compile_harness.exe"
    args = ", ".join(f"({param.type_text})0" for param in function.params)
    harness_path.write_text(normalized_path.read_text(encoding="utf-8") + f"\nint main(void) {{ return (int)((long long)phase3a_candidate({args}) & 0); }}\n", encoding="utf-8")
    command = ["/usr/bin/gcc", "-std=c11", "-Wall", "-Wextra", "-Wno-unused-function", "-Wno-unused-variable", str(harness_path), "-o", str(exe_path)]
    result = run_command(command, compile_dir, command_log, timeout_s=30)
    return {"ok": result.returncode == 0, "reason": "" if result.returncode == 0 else "compile_failure", "command": command, "returncode": result.returncode, "stdout_tail": result.stdout[-1000:], "stderr_tail": result.stderr[-2000:]}


def base_manifest_row(
    function: SelectedFunction,
    artifact: BuildArtifact,
    producer: str,
    availability: dict[str, Any],
    candidate_id: str,
    raw_output_path: Path,
    parsed_path: Path,
    normalized_path: Path,
    transform_path: Path,
    compile_log_path: Path,
    prompt_path: Path,
    prompt_hash: str,
    final_status: str,
    compile_status: str,
    non_evaluable_reason: str,
) -> dict[str, Any]:
    producer_info = availability.get("producers", {}).get(producer, {})
    version = producer_version(producer, producer_info)
    parse_status = "parsed_function" if final_status == "minimally_normalized_candidate" else ("pending" if final_status.startswith("pending_") else "parse_failure")
    return {
        "candidate_id": candidate_id,
        "selected_function_id": function.record.function_id,
        "project": function.record.project,
        "source_path": function.record.source_file,
        "function_name": function.record.function_name,
        "producer": producer,
        "producer_version": version,
        "build_view": artifact.build_view,
        "compiler": BUILD_VIEWS[artifact.build_view]["compiler_label"],
        "compiler_flags": " ".join(BUILD_VIEWS[artifact.build_view]["flags"]),
        "compiler_command": " ".join(artifact.compiler_command),
        "architecture": "x86_64-linux-gnu",
        "binary_path": str(artifact.binary_path),
        "symbol_metadata_path": str(artifact.symbol_metadata_path),
        "disassembly_path": str(artifact.disassembly_path),
        "raw_output_path": str(raw_output_path),
        "parsed_function_path": str(parsed_path),
        "normalized_candidate_path": str(normalized_path),
        "transformation_log_path": str(transform_path),
        "compile_log_path": str(compile_log_path),
        "prompt_payload_path": str(prompt_path) if prompt_path.exists() else "",
        "parse_status": parse_status,
        "compile_status": compile_status,
        "harness_status": compile_status if compile_status == "compile_ready" else "not_run",
        "final_candidate_status": final_status,
        "non_evaluable_reason": non_evaluable_reason,
        "prompt_hash": prompt_hash,
        "binary_hash": artifact.binary_hash,
        "normalized_candidate_hash": sha256_path(normalized_path) if normalized_path.exists() and normalized_path.stat().st_size else "",
        "raw_output_hash": sha256_path(raw_output_path) if raw_output_path.exists() and raw_output_path.stat().st_size else "",
        "selection_rank": function.rank,
        "signature": corpus.signature(function.record),
        "domain_size": function.record.domain_size,
        "argument_count": len(function.record.params),
    }


def producer_version(producer: str, info: dict[str, Any]) -> str:
    if producer == "ghidra":
        return str(info.get("version", "12.1.2"))
    if producer == "angr":
        return str(info.get("angr_version", "9.2.102"))
    if producer == "llm4decompile":
        return f"{info.get('model_identifier', LLM_MODEL_IDENTIFIER)}@{info.get('model_snapshot', LLM_MODEL_SNAPSHOT)}"
    if producer == "mycodex_api":
        return str(info.get("returned_model", API_MODEL))
    return ""


def finalize_manifest_rows(repo_root: Path, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finalized = []
    for row in rows:
        normalized = Path(row["normalized_candidate_path"])
        raw = Path(row["raw_output_path"])
        row["normalized_candidate_hash"] = sha256_path(normalized) if normalized.exists() and normalized.stat().st_size else ""
        row["raw_output_hash"] = sha256_path(raw) if raw.exists() and raw.stat().st_size else ""
        finalized.append(row)
    return finalized


def attempt_dirs(repo_root: Path, candidate_id: str) -> dict[str, Path]:
    base = repo_root / WORK_DIR
    paths = {
        "raw": base / "raw" / corpus.safe_name(candidate_id),
        "parsed": base / "parsed" / corpus.safe_name(candidate_id),
        "normalized": base / "normalized" / corpus.safe_name(candidate_id),
        "compile": base / "compile" / corpus.safe_name(candidate_id),
        "prompts": base / "prompts" / corpus.safe_name(candidate_id),
        "logs": base / "logs" / corpus.safe_name(candidate_id),
    }
    for path in paths.values():
        path.mkdir(parents=True, exist_ok=True)
    return paths


def write_empty_attempt_artifacts(raw: Path, parsed: Path, normalized: Path, transform: Path, compile_log: Path, reason: str) -> None:
    raw.write_text("", encoding="utf-8")
    write_empty_processing_artifacts(parsed, normalized, transform, compile_log, reason)


def write_empty_processing_artifacts(parsed: Path, normalized: Path, transform: Path, compile_log: Path, reason: str) -> None:
    parsed.parent.mkdir(parents=True, exist_ok=True)
    normalized.parent.mkdir(parents=True, exist_ok=True)
    transform.parent.mkdir(parents=True, exist_ok=True)
    compile_log.parent.mkdir(parents=True, exist_ok=True)
    parsed.write_text("", encoding="utf-8")
    normalized.write_text("", encoding="utf-8")
    transform.write_text(json.dumps(transform_log(["no_normalization"], False, reason), sort_keys=True, indent=2) + "\n", encoding="utf-8")
    compile_log.write_text(json.dumps({"ok": False, "reason": reason}, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def llm_prompt_payload(function: corpus.FunctionRecord, artifact: BuildArtifact) -> dict[str, Any]:
    prompt = "\n".join(
        [
            "[INST] Reconstruct the C function represented by this x86_64 disassembly.",
            "Return exactly one complete C function and no explanation.",
            f"Required signature: {corpus.signature(function)}",
            f"Build view: {artifact.build_view}",
            "Architecture: x86_64-linux-gnu",
            "Disassembly:",
            "```asm",
            artifact.disassembly_path.read_text(encoding="utf-8", errors="ignore"),
            "```",
            "[/INST]",
        ]
    )
    return {"prompt_template_id": "phase3a_llm4decompile_disassembly_v1", "prompt": prompt, "decoding_parameters": LLM_DECODING, "model_identifier": LLM_MODEL_IDENTIFIER, "model_snapshot": LLM_MODEL_SNAPSHOT}


def api_prompt_payload(function: corpus.FunctionRecord, artifact: BuildArtifact) -> dict[str, Any]:
    prompt = "\n".join(
        [
            "Reconstruct the C function represented by the following x86_64 disassembly.",
            "Return exactly one complete C function and no explanation.",
            f"Required signature: {corpus.signature(function)}",
            f"Build view: {artifact.build_view}",
            "Architecture: x86_64-linux-gnu",
            "Disassembly:",
            artifact.disassembly_path.read_text(encoding="utf-8", errors="ignore"),
        ]
    )
    payload = {
        "model": API_MODEL,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        **API_PARAMETERS,
    }
    return {"prompt_template_id": "phase3a_mycodex_disassembly_v1", "prompt": prompt, "request_payload": payload, "generation_parameters": API_PARAMETERS}


def extract_api_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    chunks: list[str] = []
    for item in payload.get("output", []) or []:
        for content in item.get("content", []) or []:
            if isinstance(content, dict) and "text" in content:
                chunks.append(str(content["text"]))
    return "\n".join(chunks)


def response_finish_reason(payload: dict[str, Any]) -> str:
    reasons = []
    for item in payload.get("output", []) or []:
        if item.get("finish_reason"):
            reasons.append(str(item["finish_reason"]))
    return ",".join(reasons)


def candidate_id_for(function_id: str, producer: str, build_view: str) -> str:
    digest = hashlib.sha256(f"{function_id}|{producer}|{build_view}".encode("utf-8")).hexdigest()[:12]
    return f"phase3a::{corpus.safe_name(function_id)}::{producer}::{build_view}::{digest}"


def label_candidates(repo_root: Path) -> dict[str, Any]:
    if not candidate_seal_committed(repo_root):
        raise RuntimeError("candidate seal must be committed before labeling")
    rows = read_jsonl(repo_root / MANIFEST_PATH)
    selected = {item.record.function_id: item for item in load_selected_functions(repo_root)}
    fixtures_by_candidate_source = load_fixtures_by_function(repo_root)
    labels: list[dict[str, Any]] = []
    fixture_replay: list[dict[str, Any]] = []
    descriptors: list[dict[str, Any]] = []
    taxonomy_packet: list[dict[str, Any]] = []
    command_log = repo_root / RESULT_DIR / "phase3a_label_execution_log.jsonl"
    command_log.write_text("", encoding="utf-8")
    for row in rows:
        function = selected[row["selected_function_id"]].record
        if row["compile_status"] != "compile_ready":
            label = non_evaluable_label(row, function)
        else:
            label = execute_label(repo_root, row, function, command_log)
        labels.append(label)
        if label["label"] == "semantic_wrong":
            replay = replay_fixtures(repo_root, row, function, fixtures_by_candidate_source[function.function_id], command_log)
            fixture_replay.append(replay)
            if replay["fixture_replay_label"] == "fixture_passing_semantic_wrong":
                descriptor = build_descriptor(row, function, label, replay)
                descriptors.append(descriptor)
                taxonomy_packet.append(build_taxonomy_packet(repo_root, row, function, label, descriptor))
    write_jsonl(repo_root / LABELS_PATH, labels)
    write_label_summary(repo_root / LABEL_SUMMARY_PATH, labels, fixture_replay)
    write_jsonl(repo_root / FIXTURE_REPLAY_PATH, fixture_replay)
    write_descriptors(repo_root / DESCRIPTORS_PATH, descriptors)
    write_jsonl(repo_root / TAXONOMY_PACKET_PATH, taxonomy_packet)
    gate = census_gate(descriptors)
    write_phase3a_tables_and_figures(repo_root, rows, labels, fixture_replay, descriptors, gate)
    update_handoff_after_labeling(repo_root, rows, labels, fixture_replay, descriptors, gate)
    return {
        "stage": "label",
        "labels": len(labels),
        "semantic_wrong": sum(1 for item in labels if item["label"] == "semantic_wrong"),
        "fixture_passing_semantic_wrong": len(descriptors),
        "gate": gate["minimum_gate_status"],
    }


def candidate_seal_committed(repo_root: Path) -> bool:
    seal_rel = str(CANDIDATE_SEAL_PATH)
    commit = git_at(repo_root, ["log", "-1", "--format=%H", "--", seal_rel])
    if not commit:
        return False
    diff = subprocess.run(["git", "diff", "--quiet", "HEAD", "--", seal_rel, str(CANDIDATE_SEAL_SHA_PATH)], cwd=repo_root)
    return diff.returncode == 0


def execute_label(repo_root: Path, row: dict[str, Any], function: corpus.FunctionRecord, command_log: Path) -> dict[str, Any]:
    out_dir = repo_root / WORK_DIR / "label" / corpus.safe_name(row["candidate_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    harness_path = out_dir / "label_harness.c"
    exe_path = out_dir / "label_harness.exe"
    harness_path.write_text(render_label_harness(function, Path(row["normalized_candidate_path"]).read_text(encoding="utf-8"), list(function.domain)), encoding="utf-8")
    command = ["/usr/bin/gcc", "-std=c11", "-Wall", "-Wextra", "-Wno-unused-function", "-Wno-unused-variable", "-fsanitize=undefined,address", "-fno-sanitize-recover=all", str(harness_path), "-o", str(exe_path)]
    compile_result = run_command(command, out_dir, command_log, timeout_s=60)
    if compile_result.returncode != 0:
        return label_row(row, function, "non_evaluable", "label_harness_compile_failure", 0, [], None, "", False, compile_result.stderr[-2000:])
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=0"
    env["LSAN_OPTIONS"] = "detect_leaks=0"
    run_result = run_command([str(exe_path)], out_dir, command_log, timeout_s=max(30, function.domain_size // 100), env=env)
    if run_result.returncode != 0:
        return label_row(row, function, "non_evaluable", f"runtime_failure_{run_result.returncode}", 0, [], None, "", False, run_result.stderr[-2000:])
    mismatches, output_count_ok = parse_label_outputs(run_result.stdout, list(function.domain))
    if not output_count_ok:
        return label_row(row, function, "non_evaluable", "harness_output_count_mismatch", 0, [], None, "", False, "")
    mismatch_hash = sha256_text(corpus.canonical_json(mismatches))
    first = mismatches[0] if mismatches else None
    reproducible = True
    if first is not None:
        reproducible = repeat_first_mismatch(repo_root, row, function, first["args"], command_log)
    label = "semantic_wrong" if mismatches else "no_mismatch_under_exact_audit_domain"
    return label_row(row, function, label, "", len(mismatches), mismatches, first, mismatch_hash, reproducible, "")


def render_label_harness(function: corpus.FunctionRecord, candidate_source: str, args_list: list[tuple[int, ...]]) -> str:
    arity = len(function.params)
    rows = ",\n".join("    {" + ", ".join(str(int(value)) for value in args) + "}" for args in args_list)
    source_args = ", ".join(f"({param.type_text})inputs[i][{index}]" for index, param in enumerate(function.params))
    cand_args = source_args
    support = function.support_source.strip()
    return "\n".join(
        [
            "#include <stdbool.h>",
            "#include <stddef.h>",
            "#include <stdint.h>",
            "#include <stdio.h>",
            "",
            support,
            "",
            function.source.rstrip(),
            "",
            candidate_source,
            "",
            f"static const long long inputs[{len(args_list)}][{arity}] = {{",
            rows,
            "};",
            "int main(void) {",
            f"    for (size_t i = 0; i < {len(args_list)}; ++i) {{",
            f"        long long source_value = (long long){function.function_name}({source_args});",
            f"        long long candidate_value = (long long)phase3a_candidate({cand_args});",
            '        printf("%lld %lld\\n", source_value, candidate_value);',
            "    }",
            "    return 0;",
            "}",
            "",
        ]
    )


def parse_label_outputs(stdout: str, domain: list[tuple[int, ...]]) -> tuple[list[dict[str, Any]], bool]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if len(lines) != len(domain):
        return [], False
    mismatches = []
    for index, (line, args) in enumerate(zip(lines, domain)):
        parts = line.split()
        if len(parts) != 2:
            return [], False
        source_value, candidate_value = int(parts[0]), int(parts[1])
        if source_value != candidate_value:
            mismatches.append({"domain_index": index, "args": list(args), "source_output": source_value, "candidate_output": candidate_value})
    return mismatches, True


def repeat_first_mismatch(repo_root: Path, row: dict[str, Any], function: corpus.FunctionRecord, args: list[int], command_log: Path) -> bool:
    out_dir = repo_root / WORK_DIR / "label_repeat" / corpus.safe_name(row["candidate_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    harness_path = out_dir / "repeat_harness.c"
    exe_path = out_dir / "repeat_harness.exe"
    harness_path.write_text(render_label_harness(function, Path(row["normalized_candidate_path"]).read_text(encoding="utf-8"), [tuple(args)]), encoding="utf-8")
    command = ["/usr/bin/gcc", "-std=c11", "-Wall", "-Wextra", "-Wno-unused-function", "-Wno-unused-variable", "-fsanitize=undefined,address", "-fno-sanitize-recover=all", str(harness_path), "-o", str(exe_path)]
    compile_result = run_command(command, out_dir, command_log, timeout_s=30)
    if compile_result.returncode != 0:
        return False
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=0"
    env["LSAN_OPTIONS"] = "detect_leaks=0"
    run_result = run_command([str(exe_path)], out_dir, command_log, timeout_s=30, env=env)
    mismatches, ok = parse_label_outputs(run_result.stdout, [tuple(args)])
    return run_result.returncode == 0 and ok and bool(mismatches)


def label_row(row: dict[str, Any], function: corpus.FunctionRecord, label: str, reason: str, mismatch_count: int, mismatches: list[dict[str, Any]], first: dict[str, Any] | None, mismatch_hash: str, reproducible: bool, runtime_stderr_tail: str) -> dict[str, Any]:
    return {
        "candidate_id": row["candidate_id"],
        "selected_function_id": function.function_id,
        "project": function.project,
        "function_name": function.function_name,
        "producer": row["producer"],
        "build_view": row["build_view"],
        "label": label,
        "label_reason": reason,
        "domain_size": function.domain_size,
        "mismatch_count": mismatch_count,
        "mismatch_density": mismatch_count / function.domain_size if function.domain_size else 0,
        "first_mismatch": first or {},
        "mismatch_domain_indices": [item["domain_index"] for item in mismatches],
        "mismatch_trace_sha256": mismatch_hash,
        "first_mismatch_reproducible": reproducible,
        "sanitizer_runtime_status": "normal" if label in {"semantic_wrong", "no_mismatch_under_exact_audit_domain"} else reason,
        "runtime_stderr_tail": runtime_stderr_tail,
    }


def non_evaluable_label(row: dict[str, Any], function: corpus.FunctionRecord) -> dict[str, Any]:
    return label_row(row, function, "non_evaluable", row.get("non_evaluable_reason", row.get("final_candidate_status", "")), 0, [], None, "", False, "")


def load_fixtures_by_function(repo_root: Path) -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in read_jsonl(repo_root / RESULT_DIR / "phase3a_fixtures.jsonl"):
        out[row["function_id"]].append(row)
    return out


def replay_fixtures(repo_root: Path, row: dict[str, Any], function: corpus.FunctionRecord, fixtures: list[dict[str, Any]], command_log: Path) -> dict[str, Any]:
    args_list = [tuple(item["args"]) for item in sorted(fixtures, key=lambda item: item["rank"])]
    out_dir = repo_root / WORK_DIR / "fixture_replay" / corpus.safe_name(row["candidate_id"])
    out_dir.mkdir(parents=True, exist_ok=True)
    harness_path = out_dir / "fixture_harness.c"
    exe_path = out_dir / "fixture_harness.exe"
    harness_path.write_text(render_label_harness(function, Path(row["normalized_candidate_path"]).read_text(encoding="utf-8"), args_list), encoding="utf-8")
    command = ["/usr/bin/gcc", "-std=c11", "-Wall", "-Wextra", "-Wno-unused-function", "-Wno-unused-variable", "-fsanitize=undefined,address", "-fno-sanitize-recover=all", str(harness_path), "-o", str(exe_path)]
    compile_result = run_command(command, out_dir, command_log, timeout_s=30)
    if compile_result.returncode != 0:
        return fixture_replay_row(row, function, "fixture_runtime_failure", 0, len(args_list), "compile_failure", fixtures)
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=0"
    env["LSAN_OPTIONS"] = "detect_leaks=0"
    run_result = run_command([str(exe_path)], out_dir, command_log, timeout_s=30, env=env)
    if run_result.returncode != 0:
        return fixture_replay_row(row, function, "fixture_runtime_failure", 0, len(args_list), f"runtime_failure_{run_result.returncode}", fixtures)
    mismatches, ok = parse_label_outputs(run_result.stdout, args_list)
    if not ok:
        return fixture_replay_row(row, function, "fixture_runtime_failure", 0, len(args_list), "output_count_mismatch", fixtures)
    if mismatches:
        return fixture_replay_row(row, function, "fixture_failing_semantic_wrong", len(mismatches), len(args_list), "", fixtures)
    return fixture_replay_row(row, function, "fixture_passing_semantic_wrong", 0, len(args_list), "", fixtures)


def fixture_replay_row(row: dict[str, Any], function: corpus.FunctionRecord, replay_label: str, mismatch_count: int, fixture_count: int, reason: str, fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "candidate_id": row["candidate_id"],
        "selected_function_id": function.function_id,
        "project": function.project,
        "function_name": function.function_name,
        "producer": row["producer"],
        "build_view": row["build_view"],
        "fixture_replay_label": replay_label,
        "fixture_mismatch_count": mismatch_count,
        "fixture_count": fixture_count,
        "fixture_domain_indices": [item["domain_index"] for item in sorted(fixtures, key=lambda item: item["rank"])],
        "reason": reason,
    }


def build_descriptor(row: dict[str, Any], function: corpus.FunctionRecord, label: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    first = label.get("first_mismatch", {})
    density = float(label["mismatch_density"])
    tags = taxonomy_tags(function, density, first)
    return {
        "candidate_id": row["candidate_id"],
        "project": function.project,
        "producer": row["producer"],
        "build_view": row["build_view"],
        "function": function.function_name,
        "selected_function_id": function.function_id,
        "argument_count": len(function.params),
        "ast_node_count": function.features["ast_node_count"],
        "cyclomatic_complexity": function.features["cyclomatic_complexity"],
        "branch_count": function.features["branch_count"],
        "loop_count": function.features["loop_count"],
        "switch_presence": int(bool(function.features["switch_presence"])),
        "lookup_table_access": int(bool(function.features["lookup_table_access"])),
        "bitwise_operation_count": function.features["bitwise_operation_count"],
        "comparison_count": function.features["comparison_count"],
        "character_literal_count": function.features["character_literal_count"],
        "integer_literal_count": function.features["integer_literal_count"],
        "domain_size": label["domain_size"],
        "mismatch_count": label["mismatch_count"],
        "mismatch_density": density,
        "connected_mismatch_intervals_1d": connected_intervals_1d(label) if len(function.params) == 1 else "",
        "boundary_distance": boundary_distance(function, first),
        "fixture_distance": fixture_distance(first, replay),
        "categorical_value_concentration": categorical_concentration(function, first),
        "argument_interaction_dependent": int(len(function.params) > 1 and bool(function.features["multiple_interacting_arguments"])),
        "compile_normalization_extent": normalization_extent(row),
        "taxonomy_tags": ";".join(tags),
        "primary_taxonomy_tag": tags[0],
    }


def connected_intervals_1d(label: dict[str, Any]) -> int:
    indices = label.get("mismatch_domain_indices", [])
    if not indices:
        return 0
    intervals = 1
    previous = indices[0]
    for index in indices[1:]:
        if index != previous + 1:
            intervals += 1
        previous = index
    return intervals


def boundary_distance(function: corpus.FunctionRecord, first: dict[str, Any]) -> int | str:
    if not first:
        return ""
    values = [value for domain in function.domain_values for value in domain]
    args = first.get("args", [])
    if not args:
        return ""
    return min(abs(args[0] - min(values)), abs(args[0] - max(values)))


def fixture_distance(first: dict[str, Any], replay: dict[str, Any]) -> int | str:
    if not first:
        return ""
    fixture_indices = replay.get("fixture_domain_indices", [])
    if not fixture_indices:
        return ""
    return min(abs(first.get("domain_index", 0) - int(idx)) for idx in fixture_indices)


def categorical_concentration(function: corpus.FunctionRecord, first: dict[str, Any]) -> int:
    return int(bool(first) and function.features["switch_like_categorical_behavior"])


def normalization_extent(row: dict[str, Any]) -> str:
    log = load_json_if_exists(Path(row["transformation_log_path"]))
    return str(len(log.get("allowed_operations", [])))


def taxonomy_tags(function: corpus.FunctionRecord, density: float, first: dict[str, Any]) -> list[str]:
    tags = []
    if function.features["switch_like_categorical_behavior"]:
        tags.append("categorical/default-case error")
    if function.features["lookup_table_access"]:
        tags.append("lookup-table or range-compression error")
    if any(param.type_text in corpus.UNSIGNED_TYPES or param.type_text in corpus.CHAR_LIKE_TYPES for param in function.params):
        tags.append("signedness or width error")
    if function.features["bitwise_operation_count"]:
        tags.append("arithmetic error")
    if function.features["loop_count"]:
        tags.append("loop/state error")
    if len(function.params) > 1 and function.features["multiple_interacting_arguments"]:
        tags.append("multi-argument interaction error")
    if function.features["branch_count"] >= 4 or density <= 0.10:
        tags.append("condition-boundary error")
    if not tags:
        tags.append("unknown/mixed")
    return tags


def build_taxonomy_packet(repo_root: Path, row: dict[str, Any], function: corpus.FunctionRecord, label: dict[str, Any], descriptor: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": row["candidate_id"],
        "project": function.project,
        "function_name": function.function_name,
        "source_path": function.source_file,
        "build_view": row["build_view"],
        "producer": row["producer"],
        "signature": corpus.signature(function),
        "source": function.source,
        "binary_metadata": load_json_if_exists(Path(row["symbol_metadata_path"])),
        "raw_candidate_path": row["raw_output_path"],
        "normalized_candidate_path": row["normalized_candidate_path"],
        "raw_candidate": Path(row["raw_output_path"]).read_text(encoding="utf-8", errors="ignore")[:20000],
        "normalized_candidate": Path(row["normalized_candidate_path"]).read_text(encoding="utf-8", errors="ignore")[:20000],
        "mismatch_summary": {
            "domain_size": label["domain_size"],
            "mismatch_count": label["mismatch_count"],
            "mismatch_density": label["mismatch_density"],
            "first_mismatch": label["first_mismatch"],
            "mismatch_trace_sha256": label["mismatch_trace_sha256"],
        },
        "proposed_tags": descriptor["taxonomy_tags"].split(";"),
    }


def census_gate(descriptors: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(descriptors)
    functions = {row["selected_function_id"] for row in descriptors}
    projects = Counter(row["project"] for row in descriptors)
    producers = Counter(row["producer"] for row in descriptors)
    categories = Counter(row["primary_taxonomy_tag"] for row in descriptors)
    low_density = [row for row in descriptors if float(row["mismatch_density"]) <= 0.10]
    multi_loop_lookup = [
        row for row in descriptors
        if int(row["argument_count"]) > 1 or int(row["loop_count"]) > 0 or int(row["lookup_table_access"]) > 0
    ]
    minimum_checks = {
        "at_least_25_natural_wrong": count >= 25,
        "at_least_15_functions": len(functions) >= 15,
        "at_least_8_projects": len(projects) >= 8,
        "at_least_3_producers": len(producers) >= 3,
        "two_producers_at_least_5": sum(1 for value in producers.values() if value >= 5) >= 2,
        "no_project_over_25_percent": (not projects) or max(projects.values()) / count <= 0.25,
        "no_producer_over_50_percent": (not producers) or max(producers.values()) / count <= 0.50,
        "at_least_10_low_density": len(low_density) >= 10,
        "four_categories_at_least_3": sum(1 for value in categories.values() if value >= 3) >= 4,
    }
    strong_checks = {
        "at_least_40_natural_wrong": count >= 40,
        "at_least_10_projects": len(projects) >= 10,
        "at_least_4_producers": len(producers) >= 4,
        "at_least_20_low_density": len(low_density) >= 20,
        "at_least_6_categories": len(categories) >= 6,
        "at_least_15_multi_loop_lookup": len(multi_loop_lookup) >= 15,
    }
    return {
        "natural_wrong_count": count,
        "distinct_function_count": len(functions),
        "project_counts": dict(projects),
        "producer_counts": dict(producers),
        "category_counts": dict(categories),
        "low_density_count": len(low_density),
        "multi_argument_loop_lookup_count": len(multi_loop_lookup),
        "minimum_checks": minimum_checks,
        "strong_checks": strong_checks,
        "minimum_gate_status": "passed" if all(minimum_checks.values()) else "failed",
        "strong_gate_status": "passed" if all(minimum_checks.values()) and all(strong_checks.values()) else "failed",
        "phase3b_authorized_for_review": all(minimum_checks.values()),
    }


def write_candidate_provenance(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "candidate_id",
        "selected_function_id",
        "project",
        "source_path",
        "function_name",
        "producer",
        "producer_version",
        "build_view",
        "compiler",
        "compiler_flags",
        "architecture",
        "raw_output_path",
        "normalized_candidate_path",
        "transformation_log_path",
        "compile_log_path",
        "parse_status",
        "compile_status",
        "harness_status",
        "final_candidate_status",
        "non_evaluable_reason",
        "prompt_hash",
        "binary_hash",
        "normalized_candidate_hash",
        "raw_output_hash",
    ]
    write_csv(path, rows, fields)


def build_candidate_seal(repo_root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    paths = [
        "docs/paper_agent/phase3a_natural_error_census_preregistration.md",
        "docs/paper_agent/phase3a_producer_setup_log.md",
        "results/decompile_faithfulness/phase3a_producer_availability.json",
        "analysis/decompile_faithfulness/phase3a_function_fixture_seal.json",
        "analysis/decompile_faithfulness/phase3a_function_fixture_seal.sha256",
        "results/decompile_faithfulness/phase3a_corpus_expansion_audit.json",
        "docs/paper_agent/phase3a_corpus_expansion_audit.md",
        "results/decompile_faithfulness/phase3a_selected_functions.csv",
        "results/decompile_faithfulness/phase3a_fixtures.jsonl",
        "results/decompile_faithfulness/phase3a_candidate_manifest.jsonl",
        "results/decompile_faithfulness/phase3a_candidate_provenance.csv",
        "results/decompile_faithfulness/phase3a_candidate_generation_log.jsonl",
        "analysis/decompile_faithfulness/phase3a_candidates.py",
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
            value = row.get(key)
            if value:
                artifact_paths.add(value)
    return {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "branch": git_at(repo_root, ["branch", "--show-current"]),
        "head_before_labeling": git_at(repo_root, ["rev-parse", "HEAD"]),
        "function_fixture_seal_sha256": CANONICAL_FUNCTION_FIXTURE_SEAL,
        "candidate_attempt_count": len(rows),
        "available_producers": list(PRODUCERS),
        "blocked_producers": ["retdec"],
        "build_views": list(BUILD_VIEWS),
        "candidate_manifest_sha256": sha256_path(repo_root / MANIFEST_PATH),
        "candidate_provenance_sha256": sha256_path(repo_root / PROVENANCE_PATH),
        "artifact_hashes": artifact_hashes(repo_root, paths),
        "candidate_artifact_hashes": artifact_hashes_absolute(repo_root, sorted(artifact_paths)),
        "producer_versions": producer_versions_for_seal(repo_root),
        "prompt_templates": {
            "phase3a_llm4decompile_disassembly_v1": "disassembly plus sealed signature, architecture, build view",
            "phase3a_mycodex_disassembly_v1": "disassembly plus sealed signature, architecture, build view",
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


def producer_versions_for_seal(repo_root: Path) -> dict[str, Any]:
    availability = json.loads((repo_root / RESULT_DIR / "phase3a_producer_availability.json").read_text(encoding="utf-8"))
    return {producer: producer_version(producer, availability["producers"].get(producer, {})) for producer in PRODUCERS}


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
    write_csv(path, rows, ["metric", "count"])


def write_descriptors(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "candidate_id",
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
    ]
    write_csv(path, rows, fields)


def write_phase3a_tables_and_figures(repo_root: Path, rows: list[dict[str, Any]], labels: list[dict[str, Any]], replay: list[dict[str, Any]], descriptors: list[dict[str, Any]], gate: dict[str, Any]) -> None:
    candidate_counts = Counter((row["producer"], row["build_view"], row["final_candidate_status"]) for row in rows)
    table_rows = []
    for (producer, build_view, status), count in sorted(candidate_counts.items()):
        table_rows.append((producer, build_view, status, count))
    write_simple_tex_table(repo_root / CANDIDATE_YIELD_TABLE, ["Producer", "Build", "Status", "Count"], table_rows)
    census_rows = [
        ("Natural wrong", gate["natural_wrong_count"]),
        ("Distinct functions", gate["distinct_function_count"]),
        ("Projects", len(gate["project_counts"])),
        ("Producers", len(gate["producer_counts"])),
        ("Low-density", gate["low_density_count"]),
        ("Multi-arg/loop/lookup", gate["multi_argument_loop_lookup_count"]),
        ("Minimum gate", gate["minimum_gate_status"]),
        ("Strong gate", gate["strong_gate_status"]),
    ]
    write_simple_tex_table(repo_root / NATURAL_ERROR_TABLE, ["Metric", "Value"], census_rows)
    selected_rows = read_csv_rows(repo_root / RESULT_DIR / "phase3a_selected_functions.csv")
    by_project = Counter(row["project"] for row in selected_rows)
    write_simple_tex_table(repo_root / FUNCTION_CORPUS_TABLE, ["Project", "Selected functions"], sorted(by_project.items()))
    flow = {
        "candidate_attempts": len(rows),
        "parse_ready": sum(1 for row in rows if row["parse_status"] == "parsed_function"),
        "compile_ready": sum(1 for row in rows if row["compile_status"] == "compile_ready"),
        "semantic_wrong": sum(1 for row in labels if row["label"] == "semantic_wrong"),
        "fixture_passing_semantic_wrong": len(descriptors),
        "fixture_failing_semantic_wrong": sum(1 for row in replay if row["fixture_replay_label"] == "fixture_failing_semantic_wrong"),
        "no_mismatch": sum(1 for row in labels if row["label"] == "no_mismatch_under_exact_audit_domain"),
        "non_evaluable": sum(1 for row in labels if row["label"] == "non_evaluable"),
    }
    write_json(repo_root / FLOW_DATA, flow)
    write_csv(repo_root / ERROR_DENSITY_DATA, descriptors, ["candidate_id", "project", "producer", "build_view", "mismatch_density", "mismatch_count", "domain_size", "primary_taxonomy_tag"])
    producer_distribution = [{"producer": producer, "natural_wrong_count": count} for producer, count in Counter(row["producer"] for row in descriptors).items()]
    write_csv(repo_root / ERROR_PRODUCER_DATA, producer_distribution, ["producer", "natural_wrong_count"])


def write_tables_and_handoff(repo_root: Path) -> dict[str, Any]:
    rows = read_jsonl(repo_root / MANIFEST_PATH)
    labels = read_jsonl(repo_root / LABELS_PATH)
    replay = read_jsonl(repo_root / FIXTURE_REPLAY_PATH)
    descriptors = read_csv_rows(repo_root / DESCRIPTORS_PATH)
    gate = census_gate([dict(row, mismatch_density=float(row["mismatch_density"]), argument_count=int(row["argument_count"]), loop_count=int(row["loop_count"]), lookup_table_access=int(row["lookup_table_access"])) for row in descriptors])
    write_phase3a_tables_and_figures(repo_root, rows, labels, replay, descriptors, gate)
    update_handoff_after_labeling(repo_root, rows, labels, replay, descriptors, gate)
    return {"stage": "tables", "gate": gate["minimum_gate_status"]}


def write_simple_tex_table(path: Path, headers: list[str], rows: Iterable[Iterable[Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    colspec = "l" * len(headers)
    lines = [f"\\begin{{tabular}}{{{colspec}}}", "\\toprule", " & ".join(headers) + r" \\", "\\midrule"]
    for row in rows:
        lines.append(" & ".join(tex_escape(str(item)) for item in row) + r" \\")
    lines.extend(["\\bottomrule", "\\end{tabular}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def tex_escape(text: str) -> str:
    return text.replace("_", r"\_").replace("%", r"\%").replace("&", r"\&")


def update_handoff_after_candidate_seal(repo_root: Path, rows: list[dict[str, Any]], seal_hash: str) -> None:
    handoff = repo_root / "docs/paper_agent/phase3a_natural_error_census_handoff.md"
    text = handoff.read_text(encoding="utf-8")
    marker = "## Candidate Generation, Labeling, And Natural-Error Census Milestone"
    text = text.split(marker)[0].rstrip()
    section = f"""

{marker}

Updated: {now_utc()}

- Branch: `{git_at(repo_root, ["branch", "--show-current"])}`
- Pre-candidate HEAD: `7321baeeff5159f1809eae04a06a72669e2ab13b`
- Candidate seal hash: `{seal_hash}`
- Candidate seal commit: pending commit immediately after seal creation.
- Verified function/fixture seal: `{CANONICAL_FUNCTION_FIXTURE_SEAL}`
- Available producers: `Ghidra 12.1.2`, `angr 9.2.102`, `LLM4Decompile 22B v2`, `mycodex gpt-5.5`.
- Blocked producers: `RetDec`.
- Candidate attempts by producer/build view: `{json.dumps(counts_by(rows, "producer", "build_view"), sort_keys=True)}`
- Parse-ready count: `{sum(1 for row in rows if row["parse_status"] == "parsed_function")}`
- Compile-ready count: `{sum(1 for row in rows if row["compile_status"] == "compile_ready")}`
- Semantic labeling: not run yet; candidate seal created first.

No auditing policy was run. libFuzzer was not run. No budget curves or auditor tables were generated.
"""
    handoff.write_text(text + section + "\n", encoding="utf-8")


def update_handoff_after_labeling(repo_root: Path, rows: list[dict[str, Any]], labels: list[dict[str, Any]], replay: list[dict[str, Any]], descriptors: list[dict[str, Any]], gate: dict[str, Any]) -> None:
    handoff = repo_root / "docs/paper_agent/phase3a_natural_error_census_handoff.md"
    text = handoff.read_text(encoding="utf-8")
    marker = "## Candidate Generation, Labeling, And Natural-Error Census Milestone"
    text = text.split(marker)[0].rstrip()
    label_counts = Counter(row["label"] for row in labels)
    non_eval = Counter(row["label_reason"] for row in labels if row["label"] == "non_evaluable")
    section = f"""

{marker}

Updated: {now_utc()}

- Branch: `{git_at(repo_root, ["branch", "--show-current"])}`
- Pre-candidate HEAD: `7321baeeff5159f1809eae04a06a72669e2ab13b`
- Candidate seal commit and hash: `{git_at(repo_root, ["log", "-1", "--format=%H", "--", str(CANDIDATE_SEAL_PATH)])}` / `{(repo_root / CANDIDATE_SEAL_SHA_PATH).read_text(encoding="utf-8").split()[0] if (repo_root / CANDIDATE_SEAL_SHA_PATH).exists() else ""}`
- Labeling result commit and final HEAD: pending final commit.
- Verified function/fixture seal: `{CANONICAL_FUNCTION_FIXTURE_SEAL}`
- Available producers: `Ghidra 12.1.2`, `angr 9.2.102`, `LLM4Decompile 22B v2`, `mycodex gpt-5.5`.
- Blocked producers: `RetDec`.
- Candidate attempts by producer/build view: `{json.dumps(counts_by(rows, "producer", "build_view"), sort_keys=True)}`
- Parse-ready count: `{sum(1 for row in rows if row["parse_status"] == "parsed_function")}`
- Compile-ready count: `{sum(1 for row in rows if row["compile_status"] == "compile_ready")}`
- Semantic-wrong count: `{label_counts.get("semantic_wrong", 0)}`
- Fixture-passing semantic-wrong count: `{len(descriptors)}`
- Fixture-failing semantic-wrong count: `{sum(1 for row in replay if row["fixture_replay_label"] == "fixture_failing_semantic_wrong")}`
- No-mismatch count: `{label_counts.get("no_mismatch_under_exact_audit_domain", 0)}`
- Non-evaluable count and reasons: `{json.dumps(dict(non_eval.most_common()), sort_keys=True)}`
- Natural wrong counts by project: `{json.dumps(dict(Counter(row["project"] for row in descriptors)), sort_keys=True)}`
- Natural wrong counts by function: `{json.dumps(dict(Counter(row["selected_function_id"] for row in descriptors)), sort_keys=True)}`
- Natural wrong counts by producer: `{json.dumps(dict(Counter(row["producer"] for row in descriptors)), sort_keys=True)}`
- Natural wrong counts by build view: `{json.dumps(dict(Counter(row["build_view"] for row in descriptors)), sort_keys=True)}`
- Preliminary error-category counts: `{json.dumps(gate["category_counts"], sort_keys=True)}`
- Low-density count: `{gate["low_density_count"]}`
- Multi-argument/loop/lookup error count: `{gate["multi_argument_loop_lookup_count"]}`
- API usage and cost: usage metadata sealed per response where available; cost not computed because provider pricing is not sealed in Phase 3a.
- LLM4Decompile GPU time, batch size, precision, peak memory: batch size `{LLM_DECODING["batch_size"]}`, precision `{LLM_DECODING["precision"]}`; per-response timing and peak memory are sealed in metadata.
- Exact census-gate outcome: minimum `{gate["minimum_gate_status"]}`, strong `{gate["strong_gate_status"]}`.
- Phase 3b auditor evaluation authorized: `{gate["phase3b_authorized_for_review"]}`.
- Tests run: pending final test run.

No auditing policy was run. libFuzzer was not run. No budget curves or auditor tables were generated.
"""
    handoff.write_text(text + section + "\n", encoding="utf-8")


def counts_by(rows: list[dict[str, Any]], a: str, b: str) -> dict[str, int]:
    return {f"{ka}/{kb}": value for (ka, kb), value in Counter((row[a], row[b]) for row in rows).items()}


def guard_against_auditor_imports() -> dict[str, bool]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imports_ok = True
    calls_ok = True
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN_AUDITOR_IMPORTS:
            imports_ok = False
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_AUDITOR_IMPORTS:
                    imports_ok = False
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_AUDITOR_CALLS:
                calls_ok = False
            if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_AUDITOR_CALLS:
                calls_ok = False
    return {"imports_ok": imports_ok, "calls_ok": calls_ok}


def run_command(argv: list[str], cwd: Path, command_log: Path, timeout_s: int, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    record = {"created_at_utc": now_utc(), "argv": argv, "cwd": str(cwd), "timeout_s": timeout_s}
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_s, check=False, env=env)
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(argv, 124, exc.stdout or "", exc.stderr or "timeout")
    record.update({"returncode": result.returncode, "stdout_tail": (result.stdout or "")[-1000:], "stderr_tail": (result.stderr or "")[-1000:]})
    append_jsonl(command_log, [record])
    return result


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def load_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.read_text(encoding="utf-8", errors="ignore").strip():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_hashes(repo_root: Path, paths: list[str]) -> dict[str, str]:
    hashes = {}
    for rel in paths:
        path = repo_root / rel
        if path.exists() and path.is_file():
            hashes[rel] = sha256_path(path)
    return hashes


def artifact_hashes_absolute(repo_root: Path, paths: list[str]) -> dict[str, str]:
    hashes = {}
    for raw in paths:
        path = Path(raw)
        if path.exists() and path.is_file():
            try:
                key = path.relative_to(repo_root).as_posix()
            except ValueError:
                key = str(path)
            hashes[key] = sha256_path(path)
    return hashes


def git_at(path: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=path, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
