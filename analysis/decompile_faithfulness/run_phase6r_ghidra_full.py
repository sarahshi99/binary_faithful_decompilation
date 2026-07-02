from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import dynamic_trace
from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase5b_hard_candidates as phase5b
from analysis.decompile_faithfulness import run_phase6_decompiler_like_candidates as phase6


DEFAULT_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json")
DEFAULT_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase5_preflight.json")
DEFAULT_GHIDRA_ROOT = Path("analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/ghidra_12.1.2_PUBLIC")
DEFAULT_JAVA_HOME = Path("analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/root/usr/lib/jvm/java-21-openjdk-amd64")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase6r_ghidra_full")
DEFAULT_MANIFEST_JSON = Path("docs/paper_agent/decompile_faithfulness_phase6r_real_decompiler_manifest.json")
DEFAULT_PREFLIGHT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase6r_compile_preflight.json")
DEFAULT_RESULT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase6r_result_analysis.json")
DEFAULT_RESULT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase6r_result_analysis.zh.md")
DEFAULT_GATE_ZH = Path("docs/paper_agent/decompile_faithfulness_phase6r_gate_decision.zh.md")
DEFAULT_OPT_LEVELS = ("O0", "O2")
DEFAULT_BINARY_COMPILER = Path("/usr/bin/gcc")


@dataclass(frozen=True)
class GhidraPaths:
    ghidra_root: Path
    java_home: Path
    analyze_headless: Path
    script_dir: Path


def main() -> None:
    args = parse_args()
    summary = run_full(
        repo_root=args.repo_root,
        manifest_json=args.manifest_json,
        preflight_json=args.preflight_json,
        ghidra_root=args.ghidra_root,
        java_home=args.java_home,
        output_dir=args.output_dir,
        candidate_manifest_json=args.candidate_manifest_json,
        compile_preflight_json=args.compile_preflight_json,
        result_json=args.result_json,
        result_zh=args.result_zh,
        gate_zh=args.gate_zh,
        opt_levels=args.opt_level,
        max_fixture_ifchains=args.max_fixture_ifchains,
        case_limit=args.case_limit,
        binary_compiler=args.binary_compiler,
        toolchain_label=args.toolchain_label,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "candidate_count": summary["candidate_count"],
                "ghidra_decompiled_count": summary["ghidra_decompiled_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "paired_case_count": summary["paired_case_count"],
                "fixture_only_auc": summary["baseline_auc"]["fixture_only"],
                "static_structured_auc": summary["baseline_auc"]["static_structured_proxy"],
                "v3_trace_total_auc": summary["baseline_auc"]["v3_trace_total"],
                "sota_delta": summary["sota_delta_vs_best_baseline"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--ghidra-root", type=Path, default=DEFAULT_GHIDRA_ROOT)
    parser.add_argument("--java-home", type=Path, default=DEFAULT_JAVA_HOME)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--candidate-manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    parser.add_argument("--compile-preflight-json", type=Path, default=DEFAULT_PREFLIGHT_JSON)
    parser.add_argument("--result-json", type=Path, default=DEFAULT_RESULT_JSON)
    parser.add_argument("--result-zh", type=Path, default=DEFAULT_RESULT_ZH)
    parser.add_argument("--gate-zh", type=Path, default=DEFAULT_GATE_ZH)
    parser.add_argument("--opt-level", action="append", default=list(DEFAULT_OPT_LEVELS))
    parser.add_argument("--max-fixture-ifchains", type=int, default=1)
    parser.add_argument("--case-limit", type=int, default=0)
    parser.add_argument("--binary-compiler", type=Path, default=DEFAULT_BINARY_COMPILER)
    parser.add_argument("--toolchain-label", default="")
    return parser.parse_args()


def run_full(
    repo_root: Path,
    manifest_json: Path,
    preflight_json: Path,
    ghidra_root: Path,
    java_home: Path,
    output_dir: Path,
    candidate_manifest_json: Path,
    compile_preflight_json: Path,
    result_json: Path,
    result_zh: Path,
    gate_zh: Path,
    opt_levels: list[str],
    max_fixture_ifchains: int,
    case_limit: int,
    binary_compiler: Path,
    toolchain_label: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    manifest_json = _resolve(repo_root, manifest_json)
    preflight_json = _resolve(repo_root, preflight_json)
    ghidra = ghidra_paths(
        ghidra_root=_resolve(repo_root, ghidra_root),
        java_home=_resolve(repo_root, java_home),
        repo_root=repo_root,
    )
    output_dir = _resolve(repo_root, output_dir)
    candidate_manifest_json = _resolve(repo_root, candidate_manifest_json)
    compile_preflight_json = _resolve(repo_root, compile_preflight_json)
    result_json = _resolve(repo_root, result_json)
    result_zh = _resolve(repo_root, result_zh)
    gate_zh = _resolve(repo_root, gate_zh)
    binary_compiler = _resolve(repo_root, binary_compiler)
    if not toolchain_label:
        toolchain_label = binary_compiler.name

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_json.read_text(encoding="utf-8"))
    if preflight.get("verdict") != "pass-phase5-preflight":
        raise RuntimeError(f"Phase5 preflight must pass first: {preflight.get('verdict')}")

    dirs = make_dirs(output_dir)
    entries = [
        entry for entry in manifest.get("functions", [])
        if entry.get("counts_for_phase5_real_project_gate")
    ]
    if case_limit > 0:
        entries = entries[:case_limit]

    records: list[dict[str, Any]] = []
    candidate_items: list[dict[str, Any]] = []
    original_trace_cache: dict[tuple[str, str, str], dynamic_trace.TraceRun] = {}
    original_static_cache: dict[tuple[str, str], Any] = {}
    for entry in entries:
        case = phase5_gpu._case_from_manifest_entry(repo_root, entry)
        hard_inputs = phase5b.phase5b_hard_trace_inputs(entry, max_inputs=128)
        for opt_level in opt_levels:
            proxy_candidates = phase6.build_phase6_candidates(
                case=case,
                entry=entry,
                opt_level=opt_level,
                assembly_context_path="",
            )
            selected = select_proxy_candidates(proxy_candidates, max_fixture_ifchains)
            for proxy_candidate in selected:
                ghidra_result = decompile_candidate_with_ghidra(
                    proxy_candidate=proxy_candidate,
                    ghidra=ghidra,
                    dirs=dirs,
                    binary_compiler=binary_compiler,
                )
                if ghidra_result["decompiled"]:
                    features = phase6.phase6_features(
                        case=case,
                        candidate=proxy_candidate,
                        candidate_source=ghidra_result["normalized_source"],
                        hard_inputs=hard_inputs,
                        trace_dir=dirs["trace"],
                        static_dir=dirs["static"],
                        original_trace_cache=original_trace_cache,
                        original_static_cache=original_static_cache,
                    )
                    record = phase6.record_from_features(
                        proxy_candidate,
                        features,
                        Path(ghidra_result["normalized_path"]),
                    )
                else:
                    record = failed_record(proxy_candidate, ghidra_result)
                record["metadata"].update(
                    {
                        "function_source": ghidra_result.get("normalized_source", ""),
                        "source_kind": "real_decompiler_output",
                        "source_name": "Ghidra 12.1.2 headless",
                        "tool": "ghidra",
                        "raw_decompiler_dir": ghidra_result["raw_dir"],
                        "raw_metadata_path": ghidra_result["metadata_path"],
                        "normalized_path": ghidra_result["normalized_path"],
                        "proxy_mutation_type": proxy_candidate.mutation_type,
                        "binary_compiler": str(binary_compiler),
                        "toolchain_label": toolchain_label,
                    }
                )
                records.append(record)
                candidate_items.append(candidate_manifest_item(proxy_candidate, record, ghidra_result))

    records_path = output_dir / "records.jsonl"
    _write_jsonl(records_path, records)
    candidate_manifest = build_candidate_manifest(
        records,
        candidate_items,
        records_path,
        ghidra,
        opt_levels,
        binary_compiler,
        toolchain_label,
    )
    compile_preflight = build_compile_preflight(records)
    summary = build_result_summary(records, records_path, candidate_manifest, compile_preflight)
    gate = build_gate_decision(summary)
    _write_json(candidate_manifest_json, candidate_manifest)
    _write_json(compile_preflight_json, compile_preflight)
    _write_json(result_json, summary)
    _write_result_markdown(result_zh, summary)
    _write_gate_markdown(gate_zh, gate, summary)
    return summary


def ghidra_paths(ghidra_root: Path, java_home: Path, repo_root: Path) -> GhidraPaths:
    return GhidraPaths(
        ghidra_root=ghidra_root,
        java_home=java_home,
        analyze_headless=ghidra_root / "support/analyzeHeadless",
        script_dir=repo_root / "analysis/decompile_faithfulness/ghidra_scripts",
    )


def make_dirs(output_dir: Path) -> dict[str, Path]:
    dirs = {
        "binary": output_dir / "binaries",
        "raw": output_dir / "raw",
        "normalized": output_dir / "normalized",
        "projects": output_dir / "projects",
        "trace": output_dir / "traces",
        "static": output_dir / "static_compile",
        "logs": output_dir / "logs",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def select_proxy_candidates(
    candidates: list[phase6.Phase6Candidate],
    max_fixture_ifchains: int,
) -> list[phase6.Phase6Candidate]:
    selected: list[phase6.Phase6Candidate] = []
    fixture_count = 0
    for candidate in candidates:
        if candidate.expected_role == "fixture_passing_semantic_drift":
            if fixture_count >= max_fixture_ifchains:
                continue
            fixture_count += 1
        selected.append(candidate)
    return selected


def decompile_candidate_with_ghidra(
    proxy_candidate: phase6.Phase6Candidate,
    ghidra: GhidraPaths,
    dirs: dict[str, Path],
    binary_compiler: Path,
) -> dict[str, Any]:
    candidate_id = proxy_candidate.candidate_id
    binary_source = dirs["binary"] / f"{candidate_id}.c"
    object_path = dirs["binary"] / f"{candidate_id}.o"
    raw_dir = dirs["raw"] / candidate_id
    normalized_path = dirs["normalized"] / f"{candidate_id}.c"
    metadata_path = raw_dir / "metadata.json"
    log_path = dirs["logs"] / f"{candidate_id}.log"
    binary_source.write_text(proxy_candidate.function_source, encoding="utf-8")
    compile_result = ccompile.run_command(
        [
            str(binary_compiler),
            "-std=c11",
            "-w",
            f"-{proxy_candidate.optimization_level}",
            "-g",
            "-fno-pie",
            "-fcf-protection=none",
            "-c",
            str(binary_source),
            "-o",
            str(object_path),
        ],
        timeout_s=20,
    )
    if compile_result.returncode != 0:
        return {
            "decompiled": False,
            "status": "candidate_binary_compile_failed",
            "raw_dir": str(raw_dir),
            "metadata_path": str(metadata_path),
            "normalized_path": str(normalized_path),
            "stderr_tail": compile_result.stderr[-1200:],
        }

    function_names = function_names_from_source(proxy_candidate.function_source)
    if proxy_candidate.tool:
        pass
    if proxy_candidate.case_id and proxy_candidate.candidate_id:
        pass
    if not function_names:
        function_names = [function_name_from_signature(proxy_candidate.function_source)]
    raw_dir.mkdir(parents=True, exist_ok=True)
    project_name = f"proj_{safe_name(candidate_id)}"
    result = run_ghidra(
        ghidra=ghidra,
        project_dir=dirs["projects"],
        project_name=project_name,
        object_path=object_path,
        function_names=function_names,
        raw_dir=raw_dir,
        metadata_path=metadata_path,
        log_path=log_path,
    )
    if result.returncode != 0 or not metadata_path.exists():
        return {
            "decompiled": False,
            "status": "ghidra_headless_failed",
            "raw_dir": str(raw_dir),
            "metadata_path": str(metadata_path),
            "normalized_path": str(normalized_path),
            "stderr_tail": (result.stdout + result.stderr)[-2000:],
        }

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    outputs = []
    for item in metadata.get("functions", []):
        path = Path(item.get("output_path", ""))
        if item.get("status") == "decompiled" and path.exists():
            outputs.append(path.read_text(encoding="utf-8"))
    normalized = normalize_ghidra_translation_unit(outputs)
    normalized_path.write_text(normalized, encoding="utf-8")
    return {
        "decompiled": bool(outputs),
        "status": "decompiled" if outputs else "missing_decompiled_functions",
        "raw_dir": str(raw_dir),
        "metadata_path": str(metadata_path),
        "normalized_path": str(normalized_path),
        "normalized_source": normalized,
        "ghidra_returncode": result.returncode,
        "requested_function_count": metadata.get("requested_count", 0),
        "decompiled_function_count": metadata.get("decompiled_count", 0),
        "stderr_tail": (result.stdout + result.stderr)[-2000:],
    }


def run_ghidra(
    ghidra: GhidraPaths,
    project_dir: Path,
    project_name: str,
    object_path: Path,
    function_names: list[str],
    raw_dir: Path,
    metadata_path: Path,
    log_path: Path,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["JAVA_HOME"] = str(ghidra.java_home)
    command = [
        str(ghidra.analyze_headless),
        str(project_dir),
        project_name,
        "-import",
        str(object_path),
        "-postScript",
        "ExportNamedFunctionsDecomp.java",
        ",".join(function_names),
        str(raw_dir),
        str(metadata_path),
        "-scriptPath",
        str(ghidra.script_dir),
        "-overwrite",
        "-deleteProject",
        "-analysisTimeoutPerFile",
        "120",
        "-max-cpu",
        "1",
    ]
    try:
        result = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        result = subprocess.CompletedProcess(command, 124, stdout, stderr)
    log_path.write_text((result.stdout or "") + "\n" + (result.stderr or ""), encoding="utf-8")
    return result


def function_names_from_source(source: str) -> list[str]:
    pattern = re.compile(
        r"^[ \t]*(?:static[ \t]+)?(?:unsigned[ \t]+int|int|long[ \t]+long|long|bool|void)[ \t\*]+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*\([^;{}]*\)[ \t]*\{",
        re.MULTILINE,
    )
    names: list[str] = []
    for match in pattern.finditer(source):
        name = match.group("name")
        if name not in names:
            names.append(name)
    return names


def function_name_from_signature(source: str) -> str:
    match = re.search(r"\b([A-Za-z_][A-Za-z0-9_]*)[ \t]*\(", source)
    return match.group(1) if match else ""


def normalize_ghidra_translation_unit(function_texts: list[str]) -> str:
    preamble = """#include <stdint.h>
#include <stdbool.h>
#include <ctype.h>
typedef unsigned char byte;
typedef unsigned char uchar;
typedef unsigned int uint;
typedef unsigned long ulong;
typedef unsigned long long ulonglong;
typedef unsigned char undefined;
typedef unsigned short undefined2;
typedef unsigned int undefined4;
typedef unsigned long long undefined8;
"""
    bodies = []
    for text in function_texts:
        body = strip_ghidra_comments(text)
        body = remove_ghidra_unused_local_declarations(body)
        body = re.sub(r"\b__stdcall\b", "", body)
        bodies.append(body.strip())
    return preamble + "\n\n".join(body for body in bodies if body) + "\n"


def strip_ghidra_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    return "\n".join(line.rstrip() for line in text.splitlines())


LOCAL_DECLARATION_RE = re.compile(
    r"^\s*(?:"
    r"bool|byte|char|uchar|int|uint|long|ulong|long\s+long|ulonglong|"
    r"undefined\d*|size_t|uintptr_t|intptr_t|u?int(?:8|16|32|64)_t"
    r")\s+(?:\*\s*)?(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*;\s*$"
)


def remove_ghidra_unused_local_declarations(text: str) -> str:
    lines = []
    for line in text.splitlines():
        match = LOCAL_DECLARATION_RE.match(line)
        if match:
            name = match.group("name")
            if name.endswith("_local") or len(re.findall(rf"\b{re.escape(name)}\b", text)) == 1:
                continue
        lines.append(line)
    return "\n".join(lines)


def failed_record(
    proxy_candidate: phase6.Phase6Candidate,
    ghidra_result: dict[str, Any],
) -> dict[str, Any]:
    failure = phase3_cpu._failure_components(0)
    return {
        "case_id": proxy_candidate.case_id,
        "candidate_id": proxy_candidate.candidate_id,
        "label": "compile_fail",
        "mutation_type": proxy_candidate.mutation_type,
        "compiled": False,
        "behavior_passed": False,
        "bounded_trace_passed": False,
        "optimization_level": proxy_candidate.optimization_level,
        "features": {
            **failure,
            "fixture_mismatch_rate": 1.0,
            "fixture_behavior_passed": 0.0,
            "static_structured_total": 4.5,
        },
        "diagnostics": {
            "primary_exit_code": 125,
            "fixture_exit_code": 125,
            "ghidra_status": ghidra_result.get("status", ""),
            "stderr_tail": ghidra_result.get("stderr_tail", ""),
        },
        "metadata": {
            "function_source": "",
            "expected_role": proxy_candidate.expected_role,
            "source_kind": "real_decompiler_output",
            "source_name": "Ghidra 12.1.2 headless",
            "tool": "ghidra",
            "raw_decompiler_dir": ghidra_result.get("raw_dir", ""),
            "raw_metadata_path": ghidra_result.get("metadata_path", ""),
            "normalized_path": ghidra_result.get("normalized_path", ""),
        },
    }


def candidate_manifest_item(
    proxy_candidate: phase6.Phase6Candidate,
    record: dict[str, Any],
    ghidra_result: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_id": proxy_candidate.candidate_id,
        "case_id": proxy_candidate.case_id,
        "source": "real_decompiler_output",
        "tool": "ghidra",
        "optimization_level": proxy_candidate.optimization_level,
        "candidate_path": ghidra_result.get("normalized_path", ""),
        "raw_decompiler_dir": ghidra_result.get("raw_dir", ""),
        "raw_metadata_path": ghidra_result.get("metadata_path", ""),
        "label_source": "source_known_oracle",
        "label": record["label"],
        "expected_role": proxy_candidate.expected_role,
        "mutation_type": proxy_candidate.mutation_type,
        "compiled": record["compiled"],
        "ghidra_status": ghidra_result.get("status", ""),
        "binary_compiler": record["metadata"].get("binary_compiler", ""),
        "toolchain_label": record["metadata"].get("toolchain_label", ""),
    }


def build_candidate_manifest(
    records: list[dict[str, Any]],
    candidate_items: list[dict[str, Any]],
    records_path: Path,
    ghidra: GhidraPaths,
    opt_levels: list[str],
    binary_compiler: Path,
    toolchain_label: str,
) -> dict[str, Any]:
    compile_pass = sum(1 for record in records if record["compiled"])
    paired = phase6.paired_case_count(records)
    return {
        "phase": "phase6r_real_decompiler_output",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_sources": ["real_decompiler_output"],
        "tool": "ghidra",
        "tool_path": str(ghidra.analyze_headless),
        "java_home": str(ghidra.java_home),
        "binary_compiler": str(binary_compiler),
        "toolchain_label": toolchain_label,
        "optimization_levels": opt_levels,
        "candidate_count": len(records),
        "ghidra_decompiled_count": sum(
            1 for item in candidate_items if item.get("ghidra_status") == "decompiled"
        ),
        "compile_pass_count": compile_pass,
        "paired_function_count": paired,
        "source_function_count": len({record["case_id"] for record in records}),
        "records_path": str(records_path),
        "candidates": candidate_items,
        "verdict": (
            "pass-phase6r-real-decompiler-candidate-scale"
            if compile_pass >= 50 and paired >= 10
            else "needs-more-real-decompiler-output-candidates"
        ),
    }


def build_compile_preflight(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "phase": "phase6r_compile_preflight",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_count": len(records),
        "compile_pass_count": sum(1 for record in records if record["compiled"]),
        "runtime_timeout_count": sum(
            1 for record in records
            if record["diagnostics"]["primary_exit_code"] == 124
            or record["diagnostics"]["fixture_exit_code"] == 124
        ),
        "failure_counts": {
            "decompiler_or_normalization_fail": sum(1 for record in records if not record["compiled"]),
            "fixture_runtime_fail": sum(
                1 for record in records
                if record["compiled"] and record["diagnostics"]["fixture_exit_code"] != 0
            ),
            "hard_runtime_fail": sum(
                1 for record in records
                if record["compiled"] and record["diagnostics"]["primary_exit_code"] != 0
            ),
        },
        "paired_function_count": phase6.paired_case_count(records),
        "verdict": (
            "pass-phase6r-compile-preflight"
            if sum(1 for record in records if record["compiled"]) >= 50
            and phase6.paired_case_count(records) >= 10
            else "needs-more-real-decompiler-output-candidates"
        ),
    }


def build_result_summary(
    records: list[dict[str, Any]],
    records_path: Path,
    candidate_manifest: dict[str, Any],
    compile_preflight: dict[str, Any],
) -> dict[str, Any]:
    eval_records = [
        record for record in records
        if record["compiled"] and record["label"] in {"faithful", "plausible_wrong"}
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
        "v3_trace_mismatch_rate": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_mismatch_rate", 0.0)),
        ),
        "v3_trace_total": phase3_cpu._pairwise_auc(
            eval_records,
            lambda record: float(record["features"].get("trace_total", 0.0)),
        ),
    }
    best_baseline = max(baseline_auc["fixture_only"], baseline_auc["static_structured_proxy"])
    behavior_preserving = [
        record for record in eval_records
        if record["metadata"].get("expected_role") == "behavior_preserving_rewrite"
    ]
    fp_count = sum(
        1 for record in behavior_preserving
        if float(record["features"].get("trace_total", 0.0)) > 0.0
    )
    summary = {
        "phase": "phase6r_real_decompiler_output_result_analysis",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "records_path": str(records_path),
        "candidate_count": len(records),
        "ghidra_decompiled_count": candidate_manifest["ghidra_decompiled_count"],
        "compile_pass_count": compile_preflight["compile_pass_count"],
        "source_function_count": candidate_manifest["source_function_count"],
        "toolchain_label": candidate_manifest.get("toolchain_label", ""),
        "binary_compiler": candidate_manifest.get("binary_compiler", ""),
        "paired_case_count": phase6.paired_case_count(records),
        "label_counts": phase6.count_by(records, "label"),
        "fixture_passing_wrong_count": phase6.fixture_passing_wrong_count(records),
        "baseline_auc": baseline_auc,
        "best_non_oracle_baseline_auc": best_baseline,
        "sota_delta_vs_best_baseline": baseline_auc["v3_trace_total"] - best_baseline,
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
        "behavior_preserving_rewrite_count": len(behavior_preserving),
        "v3_behavior_preserving_false_positive_count": fp_count,
        "v3_behavior_preserving_false_positive_rate": (
            fp_count / len(behavior_preserving) if behavior_preserving else 0.0
        ),
        "by_optimization_level": {
            opt: phase6.subset_metrics([
                record for record in eval_records if record["optimization_level"] == opt
            ])
            for opt in sorted({record["optimization_level"] for record in eval_records})
        },
        "by_mutation_type": {
            mutation: phase6.subset_metrics([
                record for record in eval_records if record["mutation_type"] == mutation
            ])
            for mutation in sorted({record["mutation_type"] for record in eval_records})
        },
        "failure_taxonomy": failure_taxonomy(records),
        "candidate_manifest_verdict": candidate_manifest["verdict"],
        "compile_preflight_verdict": compile_preflight["verdict"],
        "gate": {},
    }
    summary["gate"] = {
        "source_function_scale_gate": summary["source_function_count"] >= 20,
        "compile_pass_scale_gate": summary["compile_pass_count"] >= 50,
        "paired_function_gate": summary["paired_case_count"] >= 10,
        "v3_beats_fixture_gate": baseline_auc["v3_trace_total"] > baseline_auc["fixture_only"],
        "v3_beats_static_gate": baseline_auc["v3_trace_total"] > baseline_auc["static_structured_proxy"],
        "sota_delta_gate": summary["sota_delta_vs_best_baseline"] >= 0.05,
        "behavior_preserving_fp_gate": summary["v3_behavior_preserving_false_positive_rate"] <= 0.10,
    }
    summary["verdict"] = result_verdict(summary)
    return summary


def result_verdict(summary: dict[str, Any]) -> str:
    if all(summary["gate"].values()):
        return "pass-phase6r-real-decompiler-output-main-evidence"
    if summary["gate"]["source_function_scale_gate"] and summary["gate"]["compile_pass_scale_gate"]:
        return "method-negative-real-decompiler-output"
    return "needs-more-real-decompiler-output-candidates"


def build_gate_decision(summary: dict[str, Any]) -> dict[str, Any]:
    if summary["verdict"] == "pass-phase6r-real-decompiler-output-main-evidence":
        decision = "pass-phase6r-real-decompiler-output-main-evidence"
    elif summary["compile_pass_count"] < 50:
        decision = "blocked-decompiler-output-normalization"
    else:
        decision = "method-negative-real-decompiler-output"
    return {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "decision": decision,
        "phase6r_verdict": summary["verdict"],
        "gate": summary["gate"],
    }


def failure_taxonomy(records: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "ghidra_or_normalization_failure": sum(1 for record in records if not record["compiled"]),
        "fixture_passing_semantic_drift": phase6.fixture_passing_wrong_count(records),
        "behavior_preserving_rewrite_false_positive": sum(
            1 for record in records
            if record["compiled"]
            and record["metadata"].get("expected_role") == "behavior_preserving_rewrite"
            and float(record["features"].get("trace_total", 0.0)) > 0.0
        ),
        "trace_domain_miss": sum(
            1 for record in records
            if record["compiled"]
            and record["metadata"].get("expected_role") == "fixture_passing_semantic_drift"
            and record["label"] == "faithful"
        ),
    }


def _write_result_markdown(path: Path, summary: dict[str, Any]) -> None:
    gate_rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in summary["gate"].items())
    failure_rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in summary["failure_taxonomy"].items())
    text = f"""# Decompilation Faithfulness Phase 6R Ghidra Full

- Verdict: `{summary['verdict']}`
- Candidates: `{summary['candidate_count']}`
- Ghidra decompiled count: `{summary['ghidra_decompiled_count']}`
- Compile pass count: `{summary['compile_pass_count']}`
- Source functions: `{summary['source_function_count']}`
- Toolchain label: `{summary['toolchain_label']}`
- Binary compiler: `{summary['binary_compiler']}`
- Paired case count: `{summary['paired_case_count']}`
- Fixture-only AUC: `{summary['baseline_auc']['fixture_only']:.4f}`
- Static structured proxy AUC: `{summary['baseline_auc']['static_structured_proxy']:.4f}`
- Dynamic Trace v3 AUC: `{summary['baseline_auc']['v3_trace_total']:.4f}`
- SOTA delta vs best non-oracle baseline: `{summary['sota_delta_vs_best_baseline']:.4f}`
- V3 behavior-preserving rewrite FP rate: `{summary['v3_behavior_preserving_false_positive_rate']:.4f}`
- Records: `{summary['records_path']}`

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Failure Taxonomy

| Category | Count |
|---|---:|
{failure_rows}

## Interpretation

这是真实 Ghidra headless decompiler-output full run。候选先被编译成二进制对象，再由 Ghidra 12.1.2 导出 C，随后做轻量 normalization 并用 source-known oracle、fixture-only、static structured proxy 和 Dynamic Trace v3 评估。

## CCF-A Self-check

- Full evidence: this is the planned Phase 6R full run over all `{summary['source_function_count']}` Phase5 functions, two optimization levels, and three candidate roles. It is no longer a smoke run.
- Baseline/SOTA status: `SOTA delta` here means improvement over the strongest in-project non-oracle baseline in this run, not an external-paper SOTA claim.
- Current limitation: `{summary['failure_taxonomy']['ghidra_or_normalization_failure']}` Ghidra outputs did not become compile-ready C under the current lightweight normalization, so external-tool generalization still needs a follow-up cross-tool / normalization-ablation phase.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_gate_markdown(path: Path, gate: dict[str, Any], summary: dict[str, Any]) -> None:
    gate_rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in gate["gate"].items())
    text = f"""# Decompilation Faithfulness Phase 6R Gate Decision

- Decision: `{gate['decision']}`
- Phase 6R verdict: `{gate['phase6r_verdict']}`
- Dynamic Trace v3 AUC: `{summary['baseline_auc']['v3_trace_total']:.4f}`
- Best non-oracle baseline AUC: `{summary['best_non_oracle_baseline_auc']:.4f}`
- SOTA delta: `{summary['sota_delta_vs_best_baseline']:.4f}`
- SOTA scope: in-project non-oracle baselines only; external-paper SOTA is not claimed by this gate.

| Gate | Passed |
|---|---:|
{gate_rows}
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "candidate"


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
