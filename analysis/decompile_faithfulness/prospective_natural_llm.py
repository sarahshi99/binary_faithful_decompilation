from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import itertools
import json
import os
import platform
import re
import shutil
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from analysis.decompile_faithfulness import holdout_evaluation as he
from analysis.decompile_faithfulness import libfuzzer_wallclock as lw
from analysis.decompile_faithfulness import strong_baselines_and_mechanism as sbm


METHOD_FREEZE_COMMIT = "06dda89912103b94fc065d6f073581a7811154b1"
SEALED_HOLDOUT_HASH = "cfd597adb878520214c48f62cd8c7755e9f352d690fa8545f09dd4f23e9fad42"
PHASE1E_RESULT = "f302bb51eb9371c0dad51bce92be53f58fc1a341"
PHASE1F_RESULT = "b626b38dd9f1398945a7c604b3213f589b936b8a"
PHASE1G_RESULT = "f9fdca2a001a9c07d2fecd507692a2d383105b91"
REQUESTED_MODEL = "gpt-5.5"
PROVIDER_NAME = "mycodex"
API_BASE_URL = "https://wokeme.dpdns.org/v1"
API_WIRE = "responses"
PREREG_PATH = Path("docs/paper_agent/prospective_natural_llm_preregistration.md")
CANDIDATE_SEAL_PATH = Path("analysis/decompile_faithfulness/natural_llm_candidate_seal.json")
CANDIDATE_SEAL_SHA_PATH = Path("analysis/decompile_faithfulness/natural_llm_candidate_seal.sha256")
POPULATION_SEAL_PATH = Path("analysis/decompile_faithfulness/natural_llm_evaluation_population.json")
POPULATION_SEAL_SHA_PATH = Path("analysis/decompile_faithfulness/natural_llm_evaluation_population.sha256")
ARTIFACT_ROOT = Path("results/decompile_faithfulness/natural_llm_candidate_artifacts")
WORK_DIR = Path("analysis_outputs/decompile_faithfulness/phase1h_natural_llm")
BUILD_VIEWS = ["gcc_O0", "clang_O2"]
PROMPT_FAMILIES = ["P1", "P2"]
BUDGETS = [1, 2, 4, 8, 16, 32]
FUZZER_EVAL_BUDGETS = [8, 32, 128]
FUZZER_WALLCLOCK_BUDGETS = [0.1]
GENERATION_PARAMETERS = {
    "temperature": 0,
    "top_p": 1,
    "top_p_payload_status": "omitted_after_provider_rejected_explicit_default_before_any_candidate_response",
    "max_output_tokens": 2048,
    "stream": False,
}
EXPECTED_PROJECT_COUNTS = {
    "musl": 8,
    "sqlite": 8,
    "TinyCC": 8,
    "sbase": 8,
    "mbedtls": 2,
    "libb64": 2,
    "libtomcrypt": 2,
    "BearSSL": 2,
    "xxHash": 1,
    "chibicc": 1,
}
POLICIES = [
    he.FINAL_POLICY,
    "literal_first_concatenation",
    "fixture_neighbor_only",
    "source_literal_only",
    "generic_type_boundaries",
    "uniform_random_domain",
    "randomized_union_order",
]
STOCHASTIC_POLICIES = {"uniform_random_domain", "randomized_union_order"}


@dataclass(frozen=True)
class PromptRequest:
    candidate_id: str
    function_id: str
    project: str
    function_name: str
    signature: str
    build_view: str
    prompt_family: str
    architecture: str
    object_path: Path
    raw_ghidra_path: Path
    prompt_text: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class ParsedSignature:
    return_type: str
    function_name: str
    params: tuple[tuple[str, str], ...]


def main() -> None:
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    args = parse_args()
    repo_root = args.repo_root.resolve()
    if args.stage == "generate":
        summary = generate_candidates(repo_root)
    elif args.stage == "label":
        summary = label_and_seal_population(repo_root)
    elif args.stage == "evaluate":
        summary = evaluate_natural_population(repo_root, max_workers=args.max_workers)
    elif args.stage == "all":
        summary = {}
        summary["generate"] = generate_candidates(repo_root)
        summary["label"] = label_and_seal_population(repo_root)
        summary["evaluate"] = evaluate_natural_population(repo_root, max_workers=args.max_workers)
    else:
        raise ValueError(args.stage)
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 1h prospective natural LLM candidate stratum")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--stage", choices=["generate", "label", "evaluate", "all"], required=True)
    parser.add_argument("--max-workers", type=int, default=4)
    return parser.parse_args()


def generate_candidates(repo_root: Path) -> dict[str, Any]:
    assert_preregistration_committed(repo_root)
    preflight = preflight_checks(repo_root)
    if not preflight["ok"]:
        raise RuntimeError("Phase 1h preflight failed before API requests")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured; stopping before API requests")
    out_dir = repo_root / "results/decompile_faithfulness"
    artifact_root = repo_root / ARTIFACT_ROOT
    work_dir = repo_root / WORK_DIR / "generation"
    for path in [out_dir, artifact_root, work_dir]:
        path.mkdir(parents=True, exist_ok=True)

    requests = build_request_matrix(repo_root)
    manifest_rows: list[dict[str, Any]] = []
    for request in requests:
        manifest_rows.append(process_request(repo_root, artifact_root, work_dir, request, api_key))

    write_jsonl(out_dir / "natural_llm_candidate_manifest.jsonl", manifest_rows)
    seal = build_candidate_seal(repo_root, manifest_rows, preflight)
    write_json(repo_root / CANDIDATE_SEAL_PATH, seal)
    seal_hash = sha256_path(repo_root / CANDIDATE_SEAL_PATH)
    (repo_root / CANDIDATE_SEAL_SHA_PATH).write_text(
        f"{seal_hash}  natural_llm_candidate_seal.json\n",
        encoding="utf-8",
    )
    return {
        "stage": "generate",
        "requests": len(requests),
        "manifest_rows": len(manifest_rows),
        "parse_ready": sum(1 for row in manifest_rows if row["parse_status"] == "parsed_function"),
        "compile_ready": sum(1 for row in manifest_rows if row["compile_status"] == "compile_ready"),
        "candidate_seal_sha256": seal_hash,
        "api_call_count": sum(int(row.get("api_call_performed", 0)) for row in manifest_rows),
    }


def process_request(
    repo_root: Path,
    artifact_root: Path,
    work_dir: Path,
    request: PromptRequest,
    api_key: str,
) -> dict[str, Any]:
    candidate_dir = artifact_root / safe_name(request.candidate_id)
    prompt_dir = candidate_dir / "prompt"
    response_dir = candidate_dir / "raw_response"
    extracted_dir = candidate_dir / "extracted"
    normalized_dir = candidate_dir / "normalized"
    compile_dir = candidate_dir / "compile"
    for path in [prompt_dir, response_dir, extracted_dir, normalized_dir, compile_dir]:
        path.mkdir(parents=True, exist_ok=True)
    prompt_payload_path = prompt_dir / "prompt_payload.json"
    prompt_payload_path.write_text(json.dumps(request.payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw_response_path = response_dir / "response.json"
    response_text_path = response_dir / "response_text.c"
    request_metadata_path = response_dir / "request_metadata.json"

    api_call_performed = False
    if raw_response_path.exists():
        raw_payload = json.loads(raw_response_path.read_text(encoding="utf-8"))
        response_text = extract_response_text(raw_payload)
        request_metadata = json.loads(request_metadata_path.read_text(encoding="utf-8")) if request_metadata_path.exists() else {}
    else:
        api_call_performed = True
        raw_payload, request_metadata = call_model_api(request.payload, api_key)
        returned_model = str(raw_payload.get("model", ""))
        if returned_model and returned_model != REQUESTED_MODEL:
            raw_response_path.write_text(json.dumps(raw_payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            request_metadata_path.write_text(json.dumps(request_metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            raise RuntimeError(f"API returned model {returned_model!r}, expected {REQUESTED_MODEL!r}")
        raw_response_path.write_text(json.dumps(raw_payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        request_metadata_path.write_text(json.dumps(request_metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        response_text = extract_response_text(raw_payload)
    response_text_path.write_text(response_text, encoding="utf-8")

    processing = process_model_response(response_text, request.signature)
    extracted_path = extracted_dir / "candidate_extracted.c"
    normalized_path = normalized_dir / "candidate.c"
    transform_path = normalized_dir / "transformation_log.json"
    compile_log_path = compile_dir / "compile_log.json"
    extracted_path.write_text(processing.get("extracted_source", ""), encoding="utf-8")
    normalized_path.write_text(processing.get("normalized_source", ""), encoding="utf-8")
    transform_log = {
        "candidate_id": request.candidate_id,
        "allowed_operations": processing["operations"],
        "forbidden_semantic_repair_used": False,
        "consulted_trusted_source": False,
        "consulted_fixtures_or_labels": False,
        "parse_status": processing["parse_status"],
        "parse_reason": processing.get("parse_reason", ""),
    }
    transform_path.write_text(json.dumps(transform_log, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    compile_check = compile_candidate_without_source_feedback(repo_root, request, normalized_path, work_dir)
    compile_log_path.write_text(json.dumps(compile_check, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    candidate_status = candidate_status_from_processing(processing, compile_check)
    compile_status = "compile_ready" if candidate_status == "natural_llm_minimally_normalized" else "non_evaluable"
    execution_status = "compile_ready" if compile_status == "compile_ready" else candidate_status
    row = {
        "candidate_id": request.candidate_id,
        "function_id": request.function_id,
        "project": request.project,
        "function_name": request.function_name,
        "signature": request.signature,
        "candidate_stratum": "natural_llm",
        "candidate_class": "natural_llm_output",
        "candidate_status": candidate_status,
        "compile_status": compile_status,
        "execution_status": execution_status,
        "label": "unlabeled",
        "label_reason": "",
        "build_view": request.build_view,
        "compiler": "gcc" if request.build_view == "gcc_O0" else "clang",
        "optimization_level": "O0" if request.build_view == "gcc_O0" else "O2",
        "prompt_family": request.prompt_family,
        "model_provider": PROVIDER_NAME,
        "requested_model": REQUESTED_MODEL,
        "returned_model": str(raw_payload.get("model", "")),
        "api_request_id": str(raw_payload.get("id", "")),
        "api_finish_reason": response_finish_reason(raw_payload),
        "api_usage": raw_payload.get("usage", {}),
        "api_call_performed": api_call_performed,
        "target_architecture": request.architecture,
        "object_path": str(request.object_path),
        "object_sha256": sha256_path(request.object_path),
        "raw_ghidra_output_path": str(request.raw_ghidra_path),
        "raw_ghidra_sha256": sha256_path(request.raw_ghidra_path),
        "prompt_payload_path": str(prompt_payload_path),
        "prompt_payload_sha256": sha256_path(prompt_payload_path),
        "raw_model_response_path": str(raw_response_path),
        "raw_model_response_sha256": sha256_path(raw_response_path),
        "response_text_path": str(response_text_path),
        "response_text_sha256": sha256_path(response_text_path),
        "extracted_candidate_path": str(extracted_path),
        "extracted_candidate_sha256": sha256_path(extracted_path) if extracted_path.exists() else "",
        "normalized_candidate_path": str(normalized_path),
        "candidate_source_path": str(normalized_path),
        "normalized_candidate_sha256": sha256_path(normalized_path) if normalized_path.exists() else "",
        "transformation_log_path": str(transform_path),
        "transformation_log_sha256": sha256_path(transform_path),
        "compile_log_path": str(compile_log_path),
        "compile_log_sha256": sha256_path(compile_log_path),
        "parse_status": processing["parse_status"],
        "parse_reason": processing.get("parse_reason", ""),
        "compile_reason": compile_check.get("reason", ""),
    }
    row["candidate_record_sha256_pre_label"] = sha256_text(json.dumps(row, sort_keys=True))
    return row


def build_request_matrix(repo_root: Path) -> list[PromptRequest]:
    selected = read_csv(repo_root / "results/decompile_faithfulness/holdout_selected_functions.csv")
    assert_selected_population(selected)
    view_rows = natural_ghidra_views(repo_root)
    requests: list[PromptRequest] = []
    for function in selected:
        function_id = function["function_id"]
        for build_view in BUILD_VIEWS:
            row = view_rows.get((function_id, build_view))
            if not row:
                continue
            object_path = Path(row["object_path"])
            raw_ghidra_path = Path(row["raw_ghidra_output_path"])
            if not object_path.exists() or not raw_ghidra_path.exists():
                continue
            architecture = architecture_for_object(object_path)
            disassembly = disassembly_for_object(object_path)
            raw_ghidra = raw_ghidra_path.read_text(encoding="utf-8", errors="replace")
            for prompt_family in PROMPT_FAMILIES:
                candidate_id = f"{function_id}::llm::{build_view}::{prompt_family}"
                prompt_text = render_prompt(
                    prompt_family=prompt_family,
                    function_id=function_id,
                    project=function["project"],
                    build_view=build_view,
                    architecture=architecture,
                    signature=function["signature"],
                    disassembly=disassembly,
                    raw_ghidra=raw_ghidra,
                )
                payload = response_api_payload(prompt_text)
                payload["phase1h_metadata"] = {
                    "candidate_id": candidate_id,
                    "function_id": function_id,
                    "project": function["project"],
                    "function_name": function["function_name"],
                    "build_view": build_view,
                    "prompt_family": prompt_family,
                    "allowed_prompt_inputs_only": True,
                }
                requests.append(
                    PromptRequest(
                        candidate_id=candidate_id,
                        function_id=function_id,
                        project=function["project"],
                        function_name=function["function_name"],
                        signature=function["signature"],
                        build_view=build_view,
                        prompt_family=prompt_family,
                        architecture=architecture,
                        object_path=object_path,
                        raw_ghidra_path=raw_ghidra_path,
                        prompt_text=prompt_text,
                        payload=payload,
                    )
                )
    return sorted(requests, key=lambda item: (item.function_id, item.build_view, item.prompt_family))


def render_prompt(
    *,
    prompt_family: str,
    function_id: str,
    project: str,
    build_view: str,
    architecture: str,
    signature: str,
    disassembly: str,
    raw_ghidra: str,
) -> str:
    if prompt_family == "P1":
        intro = (
            "You are reconstructing one C function from a sealed binary-view artifact.\n"
            "Use only the signature, build-view metadata, target-function disassembly, and\n"
            "same-view decompiler pseudocode provided below. Do not assume access to the\n"
            "original source. Produce exactly one compilable C function with the requested\n"
            "signature. Return only C code for the function, with no Markdown fences and no\n"
            "explanation."
        )
    elif prompt_family == "P2":
        intro = (
            "Write an independent clean C reconstruction for the scalar function described\n"
            "by this sealed binary view. Preserve the observable return behavior implied by\n"
            "the target-function disassembly and same-view pseudocode. Do not use or infer\n"
            "from original source text, tests, fixtures, witnesses, or feedback. Produce\n"
            "exactly one compilable C function with the requested signature. Return only C\n"
            "code for the function, with no Markdown fences and no explanation."
        )
    else:
        raise ValueError(prompt_family)
    return "\n".join(
        [
            intro,
            "",
            f"Function ID: {function_id}",
            f"Project: {project}",
            f"Build view: {build_view}",
            f"Target architecture: {architecture}",
            f"Required signature: {signature}",
            "",
            "Target-function disassembly:",
            disassembly.rstrip(),
            "",
            "Same-view raw Ghidra pseudocode, if available:",
            raw_ghidra.rstrip(),
            "",
        ]
    )


def response_api_payload(prompt_text: str) -> dict[str, Any]:
    payload = {
        "model": REQUESTED_MODEL,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt_text}]}],
        "max_output_tokens": GENERATION_PARAMETERS["max_output_tokens"],
        "stream": False,
    }
    # The Responses-compatible relay used for this project accepts these
    # deterministic sampling controls; if it rejects them, the run stops rather
    # than silently changing generation parameters.
    payload["temperature"] = GENERATION_PARAMETERS["temperature"]
    return payload


def call_model_api(payload: dict[str, Any], api_key: str) -> tuple[dict[str, Any], dict[str, Any]]:
    endpoint = API_BASE_URL.rstrip("/") + "/responses"
    body = json.dumps({key: value for key, value in payload.items() if key != "phase1h_metadata"}).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    attempts = []
    for attempt in range(1, 4):
        started = time.perf_counter()
        req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = response.read().decode("utf-8", errors="replace")
                elapsed = time.perf_counter() - started
                payload_json = json.loads(raw)
                attempts.append({"attempt": attempt, "status": response.status, "elapsed_s": elapsed})
                return payload_json, {
                    "endpoint": endpoint,
                    "attempts": attempts,
                    "request_metadata": payload.get("phase1h_metadata", {}),
                    "generation_parameters": GENERATION_PARAMETERS,
                    "api_key_env": "OPENAI_API_KEY",
                }
        except urllib.error.HTTPError as exc:
            raw_error = exc.read().decode("utf-8", errors="replace")
            attempts.append({"attempt": attempt, "status": exc.code, "elapsed_s": time.perf_counter() - started, "error": raw_error[-1000:]})
            if exc.code < 500:
                raise RuntimeError(f"model API request failed with HTTP {exc.code}: {raw_error[-1000:]}")
        except (urllib.error.URLError, TimeoutError) as exc:
            attempts.append({"attempt": attempt, "status": "url_error", "elapsed_s": time.perf_counter() - started, "error": str(exc)})
        time.sleep(1.0 * attempt)
    raise RuntimeError(f"model API request failed after retries: {attempts}")


def process_model_response(response_text: str, target_signature: str) -> dict[str, Any]:
    cleaned = strip_markdown_fences(response_text)
    extracted = extract_first_c_function(cleaned)
    if not extracted:
        return {
            "parse_status": "parse_failure",
            "parse_reason": "no_complete_c_function_found",
            "operations": ["remove_markdown_fences"],
            "extracted_source": "",
            "normalized_source": "",
        }
    target = parse_c_signature(target_signature)
    generated = parse_c_signature(extracted["header"])
    body = extracted["body"]
    operations = ["remove_markdown_fences", "extract_first_complete_c_function", "replace_declaration_with_required_signature"]
    if target and generated and len(target.params) == len(generated.params):
        for (_generated_type, generated_name), (_target_type, target_name) in zip(generated.params, target.params):
            if generated_name != target_name:
                body = re.sub(rf"\b{re.escape(generated_name)}\b", target_name, body)
        operations.append("syntax_only_parameter_name_alignment")
    normalized = "\n".join([
        "#include <stdbool.h>",
        "#include <stdint.h>",
        "",
        f"{target_signature.strip()} {body.strip()}",
        "",
    ])
    return {
        "parse_status": "parsed_function",
        "parse_reason": "ok",
        "operations": operations,
        "extracted_source": extracted["source"].strip() + "\n",
        "normalized_source": normalized,
    }


def strip_markdown_fences(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            continue
        lines.append(line)
    return "\n".join(lines).strip() + ("\n" if text else "")


def extract_first_c_function(text: str) -> dict[str, str] | None:
    pattern = re.compile(
        r"(?P<header>(?:static\s+|inline\s+|extern\s+|const\s+|volatile\s+)*"
        r"(?:unsigned\s+|signed\s+)?(?:char|short|int|long|bool|_Bool)"
        r"(?:\s+long|\s+int)?\s+\**\s*[A-Za-z_][A-Za-z0-9_]*\s*\([^;{}]*\))\s*\{",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        brace = text.find("{", match.end() - 1)
        end = matching_brace(text, brace)
        if end is None:
            continue
        source = text[match.start():end + 1]
        body = text[brace:end + 1]
        return {"header": match.group("header"), "source": source, "body": body}
    return None


def matching_brace(text: str, brace_index: int) -> int | None:
    if brace_index < 0:
        return None
    depth = 0
    in_string: str | None = None
    escape = False
    for index in range(brace_index, len(text)):
        char = text[index]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == in_string:
                in_string = None
            continue
        if char in {'"', "'"}:
            in_string = char
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def parse_c_signature(signature: str) -> ParsedSignature | None:
    match = re.match(r"\s*(?P<ret>.+?)\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<params>.*)\)\s*$", signature.strip(), re.DOTALL)
    if not match:
        return None
    params_text = match.group("params").strip()
    params: list[tuple[str, str]] = []
    if params_text and params_text != "void":
        for raw in split_params(params_text):
            bits = raw.strip().split()
            if len(bits) < 2:
                return None
            params.append((" ".join(bits[:-1]), bits[-1]))
    return ParsedSignature(match.group("ret").strip(), match.group("name"), tuple(params))


def split_params(params_text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    current = []
    for char in params_text:
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
    if current:
        parts.append("".join(current).strip())
    return [part for part in parts if part]


def compile_candidate_without_source_feedback(
    repo_root: Path,
    request: PromptRequest,
    normalized_path: Path,
    work_dir: Path,
) -> dict[str, Any]:
    if not normalized_path.exists() or not normalized_path.read_text(encoding="utf-8").strip():
        return {"ok": False, "reason": "parse_failure_no_candidate_source"}
    function = prompt_safe_function_metadata(repo_root, request.function_id)
    first_args = [function.domain[0]]
    candidate_source = normalized_path.read_text(encoding="utf-8")
    run = he.execute_inputs(function, candidate_source, first_args, work_dir / "compile_probe", request.candidate_id)
    return {
        "ok": run.ok,
        "reason": run.reason,
        "stderr_tail": run.stderr_tail,
        "harness_source_path": run.source_path,
        "compile_probe_uses_trusted_source": False,
        "compile_probe_uses_fixtures_or_labels": False,
    }


def prompt_safe_function_metadata(repo_root: Path, function_id: str) -> he.HoldoutFunction:
    selected = {row["function_id"]: row for row in read_csv(repo_root / "results/decompile_faithfulness/holdout_selected_functions.csv")}
    row = selected[function_id]
    domain_specs = tuple(json.loads(row["declared_exact_domain"]))
    domain = tuple(tuple(int(value) for value in values) for values in itertools.product(*[spec["values"] for spec in domain_specs]))
    return he.HoldoutFunction(
        function_id=function_id,
        project=row["project"],
        source_file=row["source_file"],
        function_name=row["function_name"],
        signature=row["signature"],
        domain_specs=domain_specs,
        domain=domain,
        domain_size=int(row["domain_size"]),
        source="",
        source_literal_count=0,
    )


def candidate_status_from_processing(processing: dict[str, Any], compile_check: dict[str, Any]) -> str:
    if processing["parse_status"] != "parsed_function":
        return "non_evaluable_parse_failure"
    if compile_check.get("ok"):
        return "natural_llm_minimally_normalized"
    reason = str(compile_check.get("reason", ""))
    if reason == "compile_failure" or reason.startswith("parse_failure"):
        return "non_evaluable_compile_failure"
    return "non_evaluable_harness_failure"


def label_and_seal_population(repo_root: Path) -> dict[str, Any]:
    ensure_candidate_seal_committed(repo_root)
    preflight = preflight_checks(repo_root)
    if not preflight["ok"]:
        raise RuntimeError("Phase 1h preflight failed before labeling")
    out_dir = repo_root / "results/decompile_faithfulness"
    work_dir = repo_root / WORK_DIR / "labeling"
    work_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "natural_llm_candidate_manifest.jsonl"
    manifest_rows = read_jsonl(manifest_path)
    functions = he.load_functions(repo_root)
    labels = label_candidates_exact(functions, manifest_rows, work_dir)
    labels_by_id = {row["candidate_id"]: row for row in labels}
    updated_manifest = []
    for row in manifest_rows:
        updated = dict(row)
        label = labels_by_id[row["candidate_id"]]
        updated["label"] = label["label"]
        updated["label_reason"] = label["reason"]
        updated["exact_domain_size"] = label["exact_domain_size"]
        updated["total_mismatching_input_count"] = label["total_mismatching_input_count"]
        updated["label_record_sha256"] = label["label_record_sha256"]
        if label["label"] == "non_evaluable":
            updated["compile_status"] = "non_evaluable"
            updated["execution_status"] = label["reason"]
        else:
            updated["compile_status"] = "compile_ready"
            updated["execution_status"] = "exact_domain_execution_complete"
        updated["candidate_record_sha256"] = sha256_text(json.dumps(updated, sort_keys=True))
        updated_manifest.append(updated)
    write_jsonl(manifest_path, updated_manifest)
    write_jsonl(out_dir / "natural_llm_exact_labels.jsonl", labels)
    label_summary = natural_label_summary(updated_manifest, labels)
    write_csv(out_dir / "natural_llm_label_summary.csv", label_summary)
    candidates = candidate_records_from_manifest(updated_manifest)
    semantic_wrong = [candidate for candidate in candidates if candidate.label == "semantic_wrong" and candidate.compile_status == "compile_ready"]
    replay = he.replay_fixtures(
        repo_root,
        functions,
        semantic_wrong,
        he.load_fixtures(repo_root),
        work_dir / "fixture_replay",
    )
    write_jsonl(out_dir / "natural_llm_fixture_replay.jsonl", replay)
    population = build_natural_population(updated_manifest, labels, replay, functions)
    population_seal = {
        "created_at_utc": now_utc(),
        "branch": git_output(repo_root, ["branch", "--show-current"]),
        "head": git_output(repo_root, ["rev-parse", "HEAD"]),
        "candidate_seal_sha256": sha256_path(repo_root / CANDIDATE_SEAL_PATH),
        "candidate_seal_commit": git_output(repo_root, ["rev-parse", "HEAD"]),
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "sealed_holdout_hash": SEALED_HOLDOUT_HASH,
        "population": population,
        "hashes": {
            "candidate_manifest": sha256_path(manifest_path),
            "exact_labels": sha256_path(out_dir / "natural_llm_exact_labels.jsonl"),
            "fixture_replay": sha256_path(out_dir / "natural_llm_fixture_replay.jsonl"),
            "label_summary": sha256_path(out_dir / "natural_llm_label_summary.csv"),
        },
    }
    write_json(repo_root / POPULATION_SEAL_PATH, population_seal)
    population_hash = sha256_path(repo_root / POPULATION_SEAL_PATH)
    (repo_root / POPULATION_SEAL_SHA_PATH).write_text(
        f"{population_hash}  natural_llm_evaluation_population.json\n",
        encoding="utf-8",
    )
    return {
        "stage": "label",
        "labels": len(labels),
        "semantic_wrong": population["counts"]["semantic_wrong"],
        "no_mismatch": population["counts"]["no_mismatch"],
        "non_evaluable": population["counts"]["non_evaluable"],
        "fixture_passing_semantic_wrong": population["counts"]["primary_fixture_passing_wrong"],
        "low_density": population["counts"]["low_density_fixture_passing_wrong"],
        "evaluation_population_sha256": population_hash,
    }


def label_candidates_exact(
    functions: dict[str, he.HoldoutFunction],
    manifest_rows: list[dict[str, Any]],
    work_dir: Path,
) -> list[dict[str, Any]]:
    labels: list[dict[str, Any]] = []
    source_cache: dict[str, he.ExecutionResult] = {}
    for row in manifest_rows:
        function = functions[row["function_id"]]
        candidate_source_path = Path(row.get("normalized_candidate_path", ""))
        if row.get("compile_status") != "compile_ready" or not candidate_source_path.exists():
            reason = row.get("candidate_status") or "non_evaluable"
            labels.append(natural_label_row(row, function, "non_evaluable", reason, [], 0))
            continue
        source_run = source_cache.get(function.function_id)
        if source_run is None:
            source_run = he.execute_inputs(function, function.source, list(function.domain), work_dir / "exact_source", "trusted_source")
            source_cache[function.function_id] = source_run
        candidate_source = candidate_source_path.read_text(encoding="utf-8")
        candidate_run = he.execute_inputs(function, candidate_source, list(function.domain), work_dir / "exact_candidate", row["candidate_id"])
        if not source_run.ok:
            labels.append(natural_label_row(row, function, "non_evaluable", "trusted_source_execution_failed", [], 0))
            continue
        if not candidate_run.ok:
            labels.append(natural_label_row(row, function, "non_evaluable", candidate_run.reason, [], 0))
            continue
        mismatches = []
        for rank, (args, left, right) in enumerate(zip(function.domain, source_run.outputs, candidate_run.outputs), start=1):
            if left != right:
                mismatches.append({"rank": rank, "args": list(args), "source_output": left, "candidate_output": right})
        label = "semantic_wrong" if mismatches else "no_mismatch_under_exact_holdout_domain"
        confirmation = {"confirmed": False, "reason": "no_mismatch"}
        if mismatches:
            first_args = [tuple(int(value) for value in mismatches[0]["args"])]
            confirm_source = he.execute_inputs(function, function.source, first_args, work_dir / "witness_confirm_source", "trusted_source")
            confirm_candidate = he.execute_inputs(function, candidate_source, first_args, work_dir / "witness_confirm_candidate", row["candidate_id"])
            confirmation = {
                "confirmed": bool(
                    confirm_source.ok
                    and confirm_candidate.ok
                    and confirm_source.outputs
                    and confirm_candidate.outputs
                    and confirm_source.outputs[0] == mismatches[0]["source_output"]
                    and confirm_candidate.outputs[0] == mismatches[0]["candidate_output"]
                    and confirm_source.outputs[0] != confirm_candidate.outputs[0]
                ),
                "source_status": confirm_source.reason,
                "candidate_status": confirm_candidate.reason,
            }
            if not confirmation["confirmed"]:
                label = "non_evaluable"
        labels.append(
            natural_label_row(
                row,
                function,
                label,
                "exact_domain_exhaustive_comparison" if label != "non_evaluable" else "first_mismatch_confirmation_failed",
                mismatches[:256],
                len(mismatches),
                mismatch_digest=sha256_text(json.dumps(mismatches, sort_keys=True)),
                confirmation=confirmation,
            )
        )
    return labels


def natural_label_row(
    candidate: dict[str, Any],
    function: he.HoldoutFunction,
    label: str,
    reason: str,
    mismatches: list[dict[str, Any]],
    mismatch_count: int,
    *,
    mismatch_digest: str | None = None,
    confirmation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    row = {
        "candidate_id": candidate["candidate_id"],
        "function_id": function.function_id,
        "project": function.project,
        "candidate_stratum": "natural_llm",
        "candidate_class": "natural_llm_output",
        "build_view": candidate.get("build_view", ""),
        "prompt_family": candidate.get("prompt_family", ""),
        "label": label,
        "reason": reason,
        "exact_domain_size": function.domain_size,
        "total_inputs_enumerated": function.domain_size if label != "non_evaluable" else 0,
        "total_mismatching_input_count": mismatch_count,
        "mismatch_density": safe_div(mismatch_count, function.domain_size),
        "first_mismatch": mismatches[0] if mismatches else None,
        "stored_mismatches": mismatches,
        "complete_mismatch_set_sha256": mismatch_digest or sha256_text(json.dumps(mismatches, sort_keys=True)),
        "first_mismatch_confirmation": confirmation or {"confirmed": False},
        "labeling_protocol": "complete_exact_domain_enumeration",
        "final_auditor_invoked": False,
    }
    row["label_record_sha256"] = sha256_text(json.dumps(row, sort_keys=True))
    return row


def build_natural_population(
    manifest_rows: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    replay_rows: list[dict[str, Any]],
    functions: dict[str, he.HoldoutFunction],
) -> dict[str, Any]:
    labels_by_id = {row["candidate_id"]: row for row in labels}
    replay_by_id = {row["candidate_id"]: row for row in replay_rows}
    compile_ready = [row["candidate_id"] for row in manifest_rows if row.get("compile_status") == "compile_ready"]
    semantic_wrong = [cid for cid in compile_ready if labels_by_id[cid]["label"] == "semantic_wrong"]
    primary = [cid for cid in semantic_wrong if replay_by_id.get(cid, {}).get("fixture_pass")]
    low_density = [cid for cid in primary if float(labels_by_id[cid].get("mismatch_density", 0.0)) <= 0.10]
    no_mismatch = [cid for cid in compile_ready if labels_by_id[cid]["label"] == "no_mismatch_under_exact_holdout_domain"]
    non_evaluable = [row["candidate_id"] for row in manifest_rows if labels_by_id[row["candidate_id"]]["label"] == "non_evaluable"]
    by_candidate = {row["candidate_id"]: row for row in manifest_rows}
    return {
        "sets": {
            "compile_ready": sorted(compile_ready),
            "semantic_wrong": sorted(semantic_wrong),
            "primary_fixture_passing_wrong": sorted(primary),
            "low_density_fixture_passing_wrong": sorted(low_density),
            "no_mismatch_comparison": sorted(no_mismatch),
            "non_evaluable": sorted(non_evaluable),
        },
        "counts": {
            "attempts": len(manifest_rows),
            "parse_ready": sum(1 for row in manifest_rows if row.get("parse_status") == "parsed_function"),
            "compile_ready": len(compile_ready),
            "semantic_wrong": len(semantic_wrong),
            "primary_fixture_passing_wrong": len(primary),
            "low_density_fixture_passing_wrong": len(low_density),
            "no_mismatch": len(no_mismatch),
            "non_evaluable": len(non_evaluable),
        },
        "candidate_project": {cid: by_candidate[cid]["project"] for cid in by_candidate},
        "candidate_function": {cid: by_candidate[cid]["function_id"] for cid in by_candidate},
        "candidate_build_view": {cid: by_candidate[cid]["build_view"] for cid in by_candidate},
        "candidate_prompt_family": {cid: by_candidate[cid]["prompt_family"] for cid in by_candidate},
        "candidate_source_literal_availability": {
            cid: ("has_source_char_literal" if functions[by_candidate[cid]["function_id"]].source_literal_count > 0 else "no_source_char_literal")
            for cid in by_candidate
        },
        "non_evaluable_reasons": dict(Counter(labels_by_id[cid]["reason"] for cid in non_evaluable)),
        "project_distribution_primary": dict(Counter(by_candidate[cid]["project"] for cid in primary)),
        "prompt_family_distribution_primary": dict(Counter(by_candidate[cid]["prompt_family"] for cid in primary)),
    }


def evaluate_natural_population(repo_root: Path, *, max_workers: int = 4) -> dict[str, Any]:
    ensure_population_seal_committed(repo_root)
    preflight = preflight_checks(repo_root)
    if not preflight["ok"]:
        raise RuntimeError("Phase 1h preflight failed before evaluation")
    out_dir = repo_root / "results/decompile_faithfulness"
    fig_data_dir = repo_root / "figures/data"
    fig_dir = repo_root / "figures"
    table_dir = repo_root / "paper/tables"
    docs_dir = repo_root / "docs/paper_agent"
    work_dir = repo_root / WORK_DIR / "evaluation"
    for path in [out_dir, fig_data_dir, fig_dir, table_dir, docs_dir, work_dir]:
        path.mkdir(parents=True, exist_ok=True)
    functions = he.load_functions(repo_root)
    manifest_rows = read_jsonl(out_dir / "natural_llm_candidate_manifest.jsonl")
    labels = {row["candidate_id"]: row for row in read_jsonl(out_dir / "natural_llm_exact_labels.jsonl")}
    replay = read_jsonl(out_dir / "natural_llm_fixture_replay.jsonl")
    natural_population = build_natural_population(manifest_rows, list(labels.values()), replay, functions)
    candidates = [
        candidate for candidate in candidate_records_from_manifest(manifest_rows)
        if candidate.compile_status == "compile_ready"
        and candidate.label in {"semantic_wrong", "no_mismatch_under_exact_holdout_domain"}
    ]
    policy_population = he_population_adapter(natural_population)
    policy_orders, generation_times = he.build_all_policy_orders(functions, he.load_fixtures(repo_root))
    traces, first_rows, unexpected_rows = he.evaluate_policies(
        repo_root=repo_root,
        functions=functions,
        candidates=candidates,
        labels=labels,
        population=policy_population,
        policy_orders=policy_orders,
        generation_times=generation_times,
        work_dir=work_dir / "policy_execution",
    )
    traces = [row for row in traces if row["policy"] in POLICIES]
    first_rows = [row for row in first_rows if row["policy"] in POLICIES]
    unexpected_rows = [row for row in unexpected_rows if row["policy"] in POLICIES]
    write_jsonl(out_dir / "natural_llm_policy_traces.jsonl", traces)
    write_csv(out_dir / "natural_llm_first_witness.csv", first_rows)
    policy_summary, budget_curves = summarize_natural_policy(first_rows, traces, natural_population, manifest_rows)
    write_csv(out_dir / "natural_llm_policy_summary.csv", policy_summary)
    write_csv(out_dir / "natural_llm_budget_curves.csv", budget_curves)
    write_csv(fig_data_dir / "natural_llm_budget_curves.csv", budget_curves)
    write_jsonl(out_dir / "natural_llm_unexpected_mismatches.jsonl", unexpected_rows)

    lib_run_rows, lib_summary, lib_sets = run_natural_libfuzzer(
        repo_root=repo_root,
        manifest_rows=manifest_rows,
        labels=labels,
        natural_population=natural_population,
        max_workers=max_workers,
        work_dir=work_dir / "libfuzzer",
    )
    write_jsonl(out_dir / "natural_llm_libfuzzer_runs.jsonl", lib_run_rows)
    write_csv(out_dir / "natural_llm_libfuzzer_summary.csv", lib_summary)
    write_csv(fig_data_dir / "natural_llm_fuzzer_comparison.csv", lib_summary)
    density_rows = natural_density_results(policy_summary, labels, natural_population)
    write_csv(fig_data_dir / "natural_llm_density_results.csv", density_rows)
    mechanisms = natural_candidate_mechanisms(first_rows, traces, lib_run_rows, manifest_rows, labels, replay, functions, natural_population)
    write_jsonl(out_dir / "natural_llm_candidate_mechanisms.jsonl", mechanisms)
    write_csv(fig_data_dir / "natural_llm_fuzzer_candidate_sets.csv", lib_sets)
    write_tables(repo_root, manifest_rows, labels, replay, policy_summary, lib_summary, mechanisms, natural_population)
    write_plot_script(repo_root)
    generate_figures(repo_root)
    gates = interpretation_gates(policy_summary, lib_summary, natural_population, manifest_rows, labels, unexpected_rows)
    handoff_path = write_handoff(
        repo_root=repo_root,
        natural_population=natural_population,
        manifest_rows=manifest_rows,
        labels=labels,
        policy_summary=policy_summary,
        lib_summary=lib_summary,
        lib_sets=lib_sets,
        gates=gates,
        preflight=preflight,
    )
    return {
        "stage": "evaluate",
        "primary_fixture_passing_wrong": natural_population["counts"]["primary_fixture_passing_wrong"],
        "low_density": natural_population["counts"]["low_density_fixture_passing_wrong"],
        "policy_summary_rows": len(policy_summary),
        "libfuzzer_run_rows": len(lib_run_rows),
        "unexpected_mismatches": len(unexpected_rows),
        "gate": gates["overall_result"],
        "handoff": str(handoff_path.relative_to(repo_root)),
    }


def run_natural_libfuzzer(
    *,
    repo_root: Path,
    manifest_rows: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    natural_population: dict[str, Any],
    max_workers: int,
    work_dir: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    functions = natural_sbm_functions(repo_root)
    candidates = natural_sbm_candidates(manifest_rows)
    fixtures = sbm.load_fixtures(repo_root)
    population = natural_sbm_population(natural_population)
    candidate_ids = natural_baseline_candidate_ids(population)
    harness_dir = work_dir / "harnesses"
    matrix_dir = work_dir / "matrix"
    confirm_dir = work_dir / "confirm"
    for path in [harness_dir, matrix_dir, confirm_dir]:
        path.mkdir(parents=True, exist_ok=True)
    max_workers = max(1, min(int(max_workers), 4, os.cpu_count() or 1))
    harnesses = lw.build_harnesses(lw.CLANG, harness_dir, candidate_ids, candidates, functions, labels, fixtures)
    confirmer = lw.WitnessConfirmer(lw.CLANG, confirm_dir, candidates, functions)
    eval_rows = run_natural_libfuzzer_eval_count(candidate_ids, harnesses, candidates, functions, labels, population, matrix_dir / "eval")
    wall_rows = run_natural_libfuzzer_wallclock(candidate_ids, harnesses, candidates, functions, labels, population, matrix_dir / "wall", confirmer, max_workers)
    run_rows = sorted(eval_rows + wall_rows, key=lambda row: (row["mode"], str(row["budget_or_time_limit"]), row["candidate_id"], str(row["seed"])))
    summary_rows = summarize_natural_libfuzzer(run_rows, population)
    set_rows = natural_libfuzzer_candidate_sets(run_rows, repo_root, population)
    return run_rows, summary_rows, set_rows


def run_natural_libfuzzer_eval_count(
    candidate_ids: list[str],
    harnesses: dict[str, lw.HarnessInfo],
    candidates: dict[str, sbm.CandidateInfo],
    functions: dict[str, sbm.FunctionInfo],
    labels: dict[str, dict[str, Any]],
    population: dict[str, list[str]],
    work_dir: Path,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cid in candidate_ids:
        harness = harnesses[cid]
        candidate = candidates[cid]
        function = functions[candidate.function_id]
        label = labels[cid]
        if not harness.ok:
            for budget in FUZZER_EVAL_BUDGETS:
                for seed in sbm.RANDOM_SEEDS:
                    rows.append(natural_libfuzzer_unsupported_row(candidate, function, label, "evaluation_count", budget, seed, harness.reason, harness.validation))
            continue
        assert harness.exe is not None and harness.seed_dir is not None
        cdir = work_dir / sbm.safe_name(cid)
        cdir.mkdir(parents=True, exist_ok=True)
        for seed in sbm.RANDOM_SEEDS:
            log_path = cdir / f"seed_{seed}.log"
            run = sbm.invoke_fuzzer(harness.exe, harness.seed_dir, log_path, seed, eval_limit=max(FUZZER_EVAL_BUDGETS), timeout_s=30.0)
            sequence = sbm.parse_fuzzer_log(log_path)
            for budget in FUZZER_EVAL_BUDGETS:
                prefix = sequence[:budget]
                witness = next((row for row in prefix if row["mismatch"]), None)
                rows.append(natural_libfuzzer_result_row(candidate, function, label, population, "evaluation_count", seed, budget, prefix, witness, run, log_path, None))
    return rows


def run_natural_libfuzzer_wallclock(
    candidate_ids: list[str],
    harnesses: dict[str, lw.HarnessInfo],
    candidates: dict[str, sbm.CandidateInfo],
    functions: dict[str, sbm.FunctionInfo],
    labels: dict[str, dict[str, Any]],
    population: dict[str, list[str]],
    work_dir: Path,
    confirmer: lw.WitnessConfirmer,
    max_workers: int,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for cid in candidate_ids:
        harness = harnesses[cid]
        candidate = candidates[cid]
        function = functions[candidate.function_id]
        label = labels[cid]
        if not harness.ok:
            for seed in sbm.RANDOM_SEEDS:
                rows.append(natural_libfuzzer_unsupported_row(candidate, function, label, "wall_clock", 0.1, seed, harness.reason, harness.validation))
            continue
        assert harness.exe is not None and harness.seed_dir is not None
        for seed in sbm.RANDOM_SEEDS:
            run_dir = work_dir / sbm.safe_name(cid) / f"seed_{seed}"
            run_dir.mkdir(parents=True, exist_ok=True)
            corpus_dir = run_dir / "seed_corpus"
            lw.prepare_run_corpus(harness.seed_dir, corpus_dir)
            log_path = run_dir / "fuzzer.log"
            run = lw.invoke_fuzzer_wallclock(harness.exe, corpus_dir, log_path, seed, 0.1)
            sequence = sbm.parse_fuzzer_log(log_path)
            witness = next((row for row in sequence if row["mismatch"]), None)
            confirmation = {"confirmed": False, "reason": "no_witness"}
            if witness:
                confirmation = confirmer.confirm(cid, witness["args"])
            rows.append(natural_libfuzzer_result_row(candidate, function, label, population, "wall_clock", seed, 0.1, sequence, witness, run, log_path, confirmation))
    return rows


def natural_libfuzzer_result_row(
    candidate: sbm.CandidateInfo,
    function: sbm.FunctionInfo,
    label: dict[str, Any],
    population: dict[str, list[str]],
    mode: str,
    seed: int,
    budget_or_time: int | float,
    sequence: list[dict[str, Any]],
    witness: dict[str, Any] | None,
    run: dict[str, Any],
    log_path: Path,
    confirmation: dict[str, Any] | None,
) -> dict[str, Any]:
    witness_confirmed = bool(witness and (confirmation or {"confirmed": True}).get("confirmed", True))
    false_alarm = bool(witness_confirmed and label["label"] == "no_mismatch_under_exact_holdout_domain")
    unique = {tuple(row["args"]) for row in sequence}
    return {
        "candidate_id": candidate.candidate_id,
        "project": candidate.project,
        "function_id": candidate.function_id,
        "candidate_stratum": "natural_llm",
        "mutation_family": candidate.mutation_family,
        "label": label["label"],
        "mode": mode,
        "seed": seed,
        "budget_or_time_limit": budget_or_time,
        "supported_by_libfuzzer_pipeline": True,
        "baseline_status": "completed",
        "unsupported_reason": "",
        "source_literal_dictionary_used": False,
        "exact_mismatch_witness_provided": False,
        "seed_corpus": "four_sealed_fixtures_only",
        "completed_source_candidate_evaluations": len(sequence),
        "completed_input_evaluations": len(sequence),
        "detected": bool(witness_confirmed),
        "witness_found": bool(witness),
        "witness_confirmed": witness_confirmed,
        "witness_confirmation": json.dumps(confirmation or {"confirmed": bool(witness), "mode": "evaluation_count_log"}, sort_keys=True),
        "evaluations_to_first_witness": witness["eval"] if witness else "",
        "time_to_first_witness_s": witness["elapsed_s"] if witness else "",
        "in_process_time_to_first_witness_s": witness["elapsed_s"] if witness else "",
        "end_to_end_time_to_first_witness_s": run.get("elapsed_wall_clock_s", "") if witness else "",
        "unique_domain_coverage": len(unique),
        "unique_exact_domain_inputs": len(unique),
        "exact_domain_coverage_fraction": safe_div(len(unique), function.domain_size),
        "no_mismatch_false_alarm": false_alarm,
        "ordered_input_sequence": json.dumps([row["args"] for row in sequence]),
        "ordered_input_sequence_sha256": sha256_text(json.dumps([row["args"] for row in sequence], sort_keys=True)),
        "process_returncode": run.get("returncode", ""),
        "process_timed_out": run.get("timed_out", False),
        "process_elapsed_wall_clock_s": run.get("elapsed_wall_clock_s", ""),
        "process_startup_time_s": run.get("process_startup_time_s", ""),
        "timeout": bool(run.get("timed_out", False) and not witness),
        "crash": bool(run.get("crash", False) and not witness),
        "infrastructure_failure": bool(run.get("infrastructure_failure", False)),
        "stderr_tail": run.get("stderr_tail", ""),
        "output_log_path": str(log_path),
    }


def natural_libfuzzer_unsupported_row(
    candidate: sbm.CandidateInfo,
    function: sbm.FunctionInfo,
    label: dict[str, Any],
    mode: str,
    budget_or_time: int | float,
    seed: int,
    reason: str,
    details: dict[str, Any],
) -> dict[str, Any]:
    return {
        "candidate_id": candidate.candidate_id,
        "project": candidate.project,
        "function_id": candidate.function_id,
        "candidate_stratum": "natural_llm",
        "mutation_family": candidate.mutation_family,
        "label": label["label"],
        "mode": mode,
        "seed": seed,
        "budget_or_time_limit": budget_or_time,
        "supported_by_libfuzzer_pipeline": False,
        "baseline_status": "unsupported",
        "unsupported_reason": reason,
        "support_validation": json.dumps(details, sort_keys=True),
        "source_literal_dictionary_used": False,
        "exact_mismatch_witness_provided": False,
        "seed_corpus": "four_sealed_fixtures_only_when_supported",
        "completed_source_candidate_evaluations": 0,
        "completed_input_evaluations": 0,
        "detected": False,
        "witness_found": False,
        "witness_confirmed": False,
        "no_mismatch_false_alarm": False,
        "unique_domain_coverage": 0,
        "unique_exact_domain_inputs": 0,
        "exact_domain_coverage_fraction": 0.0,
        "process_timed_out": False,
        "timeout": False,
        "crash": False,
        "infrastructure_failure": False,
        "output_log_path": "",
    }


def summarize_natural_libfuzzer(run_rows: list[dict[str, Any]], population: dict[str, list[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    scopes = {
        "primary_fixture_passing_wrong": set(population["primary_fixture_passing_wrong"]),
        "low_density_fixture_passing_wrong": set(population["low_density_fixture_passing_wrong"]),
        "no_mismatch_comparison": set(population["no_mismatch_comparison"]),
    }
    budgets_by_mode = {"evaluation_count": FUZZER_EVAL_BUDGETS, "wall_clock": FUZZER_WALLCLOCK_BUDGETS}
    for mode, budgets in budgets_by_mode.items():
        for budget in budgets:
            budget_rows = [row for row in run_rows if row["mode"] == mode and float(row["budget_or_time_limit"]) == float(budget)]
            for scope, ids in scopes.items():
                per_seed = []
                scope_rows = [row for row in budget_rows if row["candidate_id"] in ids]
                for seed in sbm.RANDOM_SEEDS:
                    seed_rows = [row for row in scope_rows if int(row["seed"]) == seed]
                    detected = {row["candidate_id"] for row in seed_rows if row.get("witness_confirmed") or row.get("detected")}
                    per_seed.append(safe_div(len(detected), len(ids)))
                no_mismatch_rows = [row for row in scope_rows if row["label"] == "no_mismatch_under_exact_holdout_domain"]
                detected_rows = [row for row in scope_rows if row.get("witness_confirmed") or row.get("detected")]
                rows.append(
                    {
                        "mode": mode,
                        "budget_or_time_limit": budget,
                        "population": scope,
                        "candidate_denominator": len(ids),
                        "supported_candidates": len({row["candidate_id"] for row in scope_rows if row.get("supported_by_libfuzzer_pipeline")}),
                        "total_runs": len(scope_rows),
                        "mean_detection": statistics.mean(per_seed) if per_seed else 0.0,
                        "median_detection": percentile(per_seed, 0.5),
                        "stddev_detection": statistics.pstdev(per_seed) if len(per_seed) > 1 else 0.0,
                        "p2_5_detection": percentile(per_seed, 0.025),
                        "p97_5_detection": percentile(per_seed, 0.975),
                        "best_seed_detection": max(per_seed) if per_seed else 0.0,
                        "worst_seed_detection": min(per_seed) if per_seed else 0.0,
                        "median_completed_evaluations": median_or_blank([row.get("completed_input_evaluations", 0) for row in scope_rows if row.get("supported_by_libfuzzer_pipeline")]),
                        "median_time_to_first_witness_s": median_or_blank([row.get("time_to_first_witness_s") for row in detected_rows if row.get("time_to_first_witness_s") != ""]),
                        "no_mismatch_false_alarms": sum(1 for row in no_mismatch_rows if row.get("no_mismatch_false_alarm")),
                        "crashes": sum(1 for row in scope_rows if row.get("crash")),
                        "timeouts": sum(1 for row in scope_rows if row.get("timeout")),
                        "infrastructure_failures": sum(1 for row in scope_rows if row.get("infrastructure_failure")),
                        "source_literal_dictionary_used": False,
                        "exact_mismatch_witnesses_provided": False,
                        "baseline_status": "completed",
                    }
                )
    return rows


def natural_libfuzzer_candidate_sets(
    run_rows: list[dict[str, Any]],
    repo_root: Path,
    population: dict[str, list[str]],
) -> list[dict[str, Any]]:
    first_rows_path = repo_root / "results/decompile_faithfulness/natural_llm_first_witness.csv"
    first_rows = read_csv(first_rows_path) if first_rows_path.exists() else []
    primary = population["primary_fixture_passing_wrong"]
    final = {row["candidate_id"] for row in first_rows if row.get("policy") == he.FINAL_POLICY and str(row.get("budget")) == "8" and str(row.get("detected_in_domain")) in {"True", "true", "1"}}
    rows = []
    for mode, budget in [("evaluation_count", 8), ("evaluation_count", 32), ("evaluation_count", 128), ("wall_clock", 0.1)]:
        lib = {row["candidate_id"] for row in run_rows if row["mode"] == mode and float(row["budget_or_time_limit"]) == float(budget) and row["candidate_id"] in primary and (row.get("witness_confirmed") or row.get("detected"))}
        all_ids = set(primary)
        rows.append({
            "mode": mode,
            "budget_or_time_limit": budget,
            "population": "primary_fixture_passing_wrong",
            "denominator": len(primary),
            "detected_by_both": json.dumps(sorted(final & lib)),
            "detected_only_by_final": json.dumps(sorted(final - lib)),
            "detected_only_by_libfuzzer": json.dumps(sorted(lib - final)),
            "detected_by_neither": json.dumps(sorted(all_ids - final - lib)),
            "detected_by_both_count": len(final & lib),
            "detected_only_by_final_count": len(final - lib),
            "detected_only_by_libfuzzer_count": len(lib - final),
            "detected_by_neither_count": len(all_ids - final - lib),
        })
    return rows


def he_population_adapter(population: dict[str, Any]) -> dict[str, Any]:
    sets = population["sets"]
    return {
        "sets": {
            "primary_fixture_passing_wrong": sets["primary_fixture_passing_wrong"],
            "low_density_fixture_passing_wrong": sets["low_density_fixture_passing_wrong"],
            "all_controlled_semantic_wrong": sets["semantic_wrong"],
            "no_mismatch_comparison": sets["no_mismatch_comparison"],
        },
        "counts": {
            "primary_fixture_passing_wrong": len(sets["primary_fixture_passing_wrong"]),
            "low_density_fixture_passing_wrong": len(sets["low_density_fixture_passing_wrong"]),
            "all_controlled_semantic_wrong": len(sets["semantic_wrong"]),
            "no_mismatch_comparison": len(sets["no_mismatch_comparison"]),
        },
    }


def natural_sbm_population(population: dict[str, Any]) -> dict[str, list[str]]:
    sets = population["sets"]
    return {
        "primary_fixture_passing_wrong": sets["primary_fixture_passing_wrong"],
        "low_density_fixture_passing_wrong": sets["low_density_fixture_passing_wrong"],
        "non_fixture_overfit_fixture_passing_wrong": sets["primary_fixture_passing_wrong"],
        "no_mismatch_comparison": sets["no_mismatch_comparison"],
    }


def natural_baseline_candidate_ids(population: dict[str, list[str]]) -> list[str]:
    ids = set(population["primary_fixture_passing_wrong"]) | set(population["no_mismatch_comparison"])
    return sorted(ids)


def natural_sbm_functions(repo_root: Path) -> dict[str, sbm.FunctionInfo]:
    base = sbm.load_functions(repo_root)
    return base


def natural_sbm_candidates(manifest_rows: list[dict[str, Any]]) -> dict[str, sbm.CandidateInfo]:
    result = {}
    for row in manifest_rows:
        result[row["candidate_id"]] = sbm.CandidateInfo(
            candidate_id=row["candidate_id"],
            function_id=row["function_id"],
            project=row["project"],
            candidate_stratum="natural_llm",
            candidate_class="natural_llm_output",
            label=row["label"],
            compile_status=row["compile_status"],
            execution_status=row["execution_status"],
            mutation_family=f"{row.get('build_view','')}::{row.get('prompt_family','')}",
            source_path=row.get("normalized_candidate_path", ""),
        )
    return result


def candidate_records_from_manifest(manifest_rows: list[dict[str, Any]]) -> list[he.CandidateRecord]:
    records = []
    for row in manifest_rows:
        records.append(
            he.CandidateRecord(
                candidate_id=row["candidate_id"],
                function_id=row["function_id"],
                project=row["project"],
                candidate_stratum="natural_llm",
                candidate_class="natural_llm_output",
                label=row.get("label", "unlabeled"),
                compile_status=row.get("compile_status", ""),
                execution_status=row.get("execution_status", ""),
                mutation_family=f"{row.get('build_view','')}::{row.get('prompt_family','')}",
                source_path=Path(row.get("normalized_candidate_path", "")),
                total_mismatching_input_count=int(row.get("total_mismatching_input_count", 0) or 0),
                exact_domain_size=int(row.get("exact_domain_size", 0) or 0),
            )
        )
    return records


def summarize_natural_policy(
    first_rows: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    population: dict[str, Any],
    manifest_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    scopes = {
        "primary_fixture_passing_wrong": population["sets"]["primary_fixture_passing_wrong"],
        "low_density_fixture_passing_wrong": population["sets"]["low_density_fixture_passing_wrong"],
    }
    summary: list[dict[str, Any]] = []
    budget_rows: list[dict[str, Any]] = []
    for policy in POLICIES:
        policy_class = "stochastic" if policy in STOCHASTIC_POLICIES else "deterministic"
        for budget in BUDGETS:
            if policy_class == "deterministic":
                rows = [row for row in first_rows if row["policy"] == policy and int(row["budget"]) == budget and row.get("random_seed") is None]
                for scope, ids in scopes.items():
                    item = policy_metrics_row(policy, policy_class, budget, scope, "", rows, ids, population)
                    summary.append(item)
                    budget_rows.append(item)
            else:
                for scope, ids in scopes.items():
                    per_seed = []
                    seed_rows_aggregate = []
                    for seed in he.RANDOM_SEEDS:
                        rows = [row for row in first_rows if row["policy"] == policy and int(row["budget"]) == budget and int(row.get("random_seed") or -1) == seed]
                        seed_rows_aggregate.extend(rows)
                        per_seed.append(detection_rate(rows, ids))
                    item = {
                        "policy": policy,
                        "policy_class": policy_class,
                        "budget": budget,
                        "scope": scope,
                        "random_seed": "30_fixed_seeds",
                        "denominator": len(ids),
                        "detected": statistics.mean([rate * len(ids) for rate in per_seed]) if per_seed else 0.0,
                        "detection_rate": statistics.mean(per_seed) if per_seed else 0.0,
                        "median_detection": percentile(per_seed, 0.5),
                        "p2_5_detection": percentile(per_seed, 0.025),
                        "p97_5_detection": percentile(per_seed, 0.975),
                        "survivors": len(ids) - int(round((statistics.mean(per_seed) if per_seed else 0.0) * len(ids))),
                        "median_first_witness_rank": median_or_blank([int(row["first_in_domain_witness_rank"]) for row in seed_rows_aggregate if row.get("first_in_domain_witness_rank")]),
                        "mean_first_witness_rank": mean_or_blank([int(row["first_in_domain_witness_rank"]) for row in seed_rows_aggregate if row.get("first_in_domain_witness_rank")]),
                        "project_macro_detection": project_macro_detection(seed_rows_aggregate, ids, population),
                        "function_macro_detection": function_macro_detection(seed_rows_aggregate, ids, population),
                    }
                    summary.append(item)
                    budget_rows.append(item)
    by_id = {row["candidate_id"]: row for row in manifest_rows}
    for item in budget_rows:
        item["attempts"] = len(manifest_rows)
        item["compile_ready"] = sum(1 for row in manifest_rows if row.get("compile_status") == "compile_ready")
        item["prompt_families"] = json.dumps(dict(Counter(by_id[cid]["prompt_family"] for cid in population["sets"].get("primary_fixture_passing_wrong", []))))
    return summary, budget_rows


def policy_metrics_row(
    policy: str,
    policy_class: str,
    budget: int,
    scope: str,
    seed: str,
    rows: list[dict[str, Any]],
    ids: list[str],
    population: dict[str, Any],
) -> dict[str, Any]:
    detected_ids = {row["candidate_id"] for row in rows if row.get("detected_in_domain")}
    ranks = [int(row["first_in_domain_witness_rank"]) for row in rows if row.get("first_in_domain_witness_rank")]
    return {
        "policy": policy,
        "policy_class": policy_class,
        "budget": budget,
        "scope": scope,
        "random_seed": seed,
        "denominator": len(ids),
        "detected": len(detected_ids & set(ids)),
        "detection_rate": safe_div(len(detected_ids & set(ids)), len(ids)),
        "survivors": len(set(ids) - detected_ids),
        "median_first_witness_rank": median_or_blank(ranks),
        "mean_first_witness_rank": mean_or_blank(ranks),
        "project_macro_detection": project_macro_detection(rows, ids, population),
        "function_macro_detection": function_macro_detection(rows, ids, population),
    }


def detection_rate(rows: list[dict[str, Any]], ids: list[str]) -> float:
    detected = {row["candidate_id"] for row in rows if row.get("detected_in_domain")}
    return safe_div(len(detected & set(ids)), len(ids))


def project_macro_detection(rows: list[dict[str, Any]], ids: list[str], population: dict[str, Any]) -> float | str:
    by_project: dict[str, list[str]] = defaultdict(list)
    for cid in ids:
        by_project[population["candidate_project"][cid]].append(cid)
    if not by_project:
        return ""
    return statistics.mean(detection_rate(rows, group) for group in by_project.values())


def function_macro_detection(rows: list[dict[str, Any]], ids: list[str], population: dict[str, Any]) -> float | str:
    by_function: dict[str, list[str]] = defaultdict(list)
    for cid in ids:
        by_function[population["candidate_function"][cid]].append(cid)
    if not by_function:
        return ""
    return statistics.mean(detection_rate(rows, group) for group in by_function.values())


def natural_density_results(
    policy_summary: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    population: dict[str, Any],
) -> list[dict[str, Any]]:
    primary = population["sets"]["primary_fixture_passing_wrong"]
    buckets: dict[str, list[str]] = defaultdict(list)
    for cid in primary:
        buckets[density_bucket(labels[cid])].append(cid)
    rows = []
    final_rows = [row for row in policy_summary if row["policy"] == he.FINAL_POLICY and int(row["budget"]) == 8 and row["scope"] == "primary_fixture_passing_wrong"]
    for bucket, ids in sorted(buckets.items()):
        final_detected = set()
        if final_rows:
            # Recompute directly from first-witness rows if available in the next
            # plotting phase; this table keeps the bucket denominator stable.
            final_detected = set()
        rows.append({
            "density_bucket": bucket,
            "candidate_count": len(ids),
            "policy": he.FINAL_POLICY,
            "budget": 8,
            "detection_rate": "",
            "note": "bucket denominators for natural LLM primary population",
        })
    return rows


def natural_candidate_mechanisms(
    first_rows: list[dict[str, Any]],
    traces: list[dict[str, Any]],
    lib_run_rows: list[dict[str, Any]],
    manifest_rows: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    replay: list[dict[str, Any]],
    functions: dict[str, he.HoldoutFunction],
    population: dict[str, Any],
) -> list[dict[str, Any]]:
    primary = population["sets"]["primary_fixture_passing_wrong"]
    final_b8 = detected_ids(first_rows, he.FINAL_POLICY, 8, None, primary)
    generic_b8 = detected_ids(first_rows, "generic_type_boundaries", 8, None, primary)
    lib_b8 = {row["candidate_id"] for row in lib_run_rows if row["mode"] == "evaluation_count" and int(float(row["budget_or_time_limit"])) == 8 and row["candidate_id"] in primary and (row.get("detected") or row.get("witness_confirmed"))}
    selected = {
        "final_only_vs_generic": sorted(final_b8 - generic_b8),
        "generic_only_vs_final": sorted(generic_b8 - final_b8),
        "final_only_vs_libfuzzer8": sorted(final_b8 - lib_b8),
        "libfuzzer8_only_vs_final": sorted(lib_b8 - final_b8),
        "final_missed_b8": sorted(set(primary) - final_b8),
    }
    manifest_by_id = {row["candidate_id"]: row for row in manifest_rows}
    replay_by_id = {row["candidate_id"]: row for row in replay}
    trace_prefixes = trace_prefix_map(traces)
    rows = []
    for list_name, ids in selected.items():
        for cid in ids:
            row = manifest_by_id[cid]
            label = labels[cid]
            function = functions[row["function_id"]]
            rows.append({
                "list_name": list_name,
                "candidate_id": cid,
                "project": row["project"],
                "function_id": row["function_id"],
                "function": row["function_name"],
                "binary_view": row["build_view"],
                "prompt_family": row["prompt_family"],
                "signature": row["signature"],
                "exact_mismatch_density": label.get("mismatch_density", ""),
                "mismatch_set_summary": mismatch_set_summary(label),
                "fixtures": json.dumps(replay_by_id.get(cid, {}), sort_keys=True),
                "source_character_literals": function.source_literal_count,
                "final_ordered_probes_b8": json.dumps(trace_prefixes.get((cid, he.FINAL_POLICY), [])),
                "generic_boundary_probes_b8": json.dumps(trace_prefixes.get((cid, "generic_type_boundaries"), [])),
                "libfuzzer_first_witness": first_libfuzzer_witness(lib_run_rows, cid),
                "losing_policy_reason": losing_policy_reason(list_name),
            })
    return rows


def detected_ids(first_rows: list[dict[str, Any]], policy: str, budget: int, seed: int | None, ids: list[str]) -> set[str]:
    return {
        row["candidate_id"]
        for row in first_rows
        if row["candidate_id"] in ids
        and row["policy"] == policy
        and int(row["budget"]) == budget
        and row.get("random_seed") == seed
        and row.get("detected_in_domain")
    }


def trace_prefix_map(traces: list[dict[str, Any]]) -> dict[tuple[str, str], list[list[int]]]:
    result: dict[tuple[str, str], list[list[int]]] = defaultdict(list)
    for row in traces:
        if int(row["budget"]) == 8 and row.get("random_seed") is None and int(row["position"]) <= 8:
            result[(row["candidate_id"], row["policy"])].append(row["input_tuple"])
    return dict(result)


def mismatch_set_summary(label: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_mismatching_input_count": label.get("total_mismatching_input_count", 0),
        "exact_domain_size": label.get("exact_domain_size", 0),
        "first_mismatch": label.get("first_mismatch"),
        "complete_mismatch_set_sha256": label.get("complete_mismatch_set_sha256", ""),
    }


def first_libfuzzer_witness(rows: list[dict[str, Any]], candidate_id: str) -> str:
    witnesses = [
        row for row in rows
        if row["candidate_id"] == candidate_id
        and row["mode"] == "evaluation_count"
        and int(float(row["budget_or_time_limit"])) == 8
        and row.get("evaluations_to_first_witness") not in {"", None}
    ]
    if not witnesses:
        return ""
    witnesses.sort(key=lambda row: (int(row["evaluations_to_first_witness"]), int(row["seed"])))
    return json.dumps({
        "seed": witnesses[0]["seed"],
        "evaluations_to_first_witness": witnesses[0]["evaluations_to_first_witness"],
        "time_to_first_witness_s": witnesses[0].get("time_to_first_witness_s", ""),
    }, sort_keys=True)


def losing_policy_reason(list_name: str) -> str:
    if "libfuzzer" in list_name:
        return "stochastic_miss_or_beyond_8_completed_evaluations"
    if "generic" in list_name:
        return "absent_probe_or_beyond_budget_under_compared_order"
    if "final_missed" in list_name:
        return "absent_from_final_b8_prefix_or_beyond_budget"
    return "candidate_set_discordance"


def build_candidate_seal(repo_root: Path, manifest_rows: list[dict[str, Any]], preflight: dict[str, Any]) -> dict[str, Any]:
    paths: dict[str, dict[str, Any]] = {}
    for rel in [
        PREREG_PATH,
        Path("docs/paper_agent/prospective_natural_llm_api_compatibility_note.md"),
        Path("results/decompile_faithfulness/natural_llm_candidate_manifest.jsonl"),
    ]:
        path = repo_root / rel
        paths[str(rel)] = {"type": "file", "sha256": sha256_path(path)}
    for row in manifest_rows:
        for key in [
            "prompt_payload_path",
            "raw_model_response_path",
            "response_text_path",
            "extracted_candidate_path",
            "normalized_candidate_path",
            "transformation_log_path",
            "compile_log_path",
        ]:
            path = Path(row[key])
            paths[path.relative_to(repo_root).as_posix()] = {"type": "file", "sha256": sha256_path(path)}
    return {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "branch": git_output(repo_root, ["branch", "--show-current"]),
        "head": git_output(repo_root, ["rev-parse", "HEAD"]),
        "preregistration_commit": git_output(repo_root, ["rev-parse", "HEAD"]),
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "sealed_holdout_hash": SEALED_HOLDOUT_HASH,
        "provider": {
            "name": PROVIDER_NAME,
            "base_url": API_BASE_URL,
            "wire_api": API_WIRE,
            "requested_model": REQUESTED_MODEL,
            "generation_parameters": GENERATION_PARAMETERS,
        },
        "preflight": preflight,
        "attempts": len(manifest_rows),
        "parse_ready": sum(1 for row in manifest_rows if row["parse_status"] == "parsed_function"),
        "compile_ready": sum(1 for row in manifest_rows if row["compile_status"] == "compile_ready"),
        "api_call_count": sum(int(row.get("api_call_performed", 0)) for row in manifest_rows),
        "final_auditor_invoked": False,
        "execution_feedback_repair_used": False,
        "prompt_forbidden_inputs_absent": all(prompt_leak_guard(json.loads(Path(row["prompt_payload_path"]).read_text(encoding="utf-8")))["ok"] for row in manifest_rows),
        "artifact_hashes": paths,
    }


def preflight_checks(repo_root: Path) -> dict[str, Any]:
    manifest_path = repo_root / "analysis/decompile_faithfulness/holdout_sealed_manifest_v2.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sealed_checks = he.verify_sealed_artifacts(repo_root, manifest)
    method_checks = he.verify_method_hashes(repo_root, manifest)
    current = sha256_path(manifest_path)
    phase1g_artifacts = {
        "results/decompile_faithfulness/libfuzzer_wallclock_runs.jsonl": sha256_path(repo_root / "results/decompile_faithfulness/libfuzzer_wallclock_runs.jsonl"),
        "results/decompile_faithfulness/libfuzzer_wallclock_summary.csv": sha256_path(repo_root / "results/decompile_faithfulness/libfuzzer_wallclock_summary.csv"),
    }
    return {
        "created_at_utc": now_utc(),
        "branch": git_output(repo_root, ["branch", "--show-current"]),
        "head": git_output(repo_root, ["rev-parse", "HEAD"]),
        "sealed_holdout_hash_expected": SEALED_HOLDOUT_HASH,
        "sealed_manifest_sha256": current,
        "sealed_manifest_hash_matches": current == SEALED_HOLDOUT_HASH,
        "sealed_artifact_checks": sealed_checks,
        "method_hash_checks": method_checks,
        "phase1g_artifact_hashes": phase1g_artifacts,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "local_gpu_usage": "none",
            "cuda_visible_devices_policy": "cleared for subprocesses controlled by Phase 1h",
        },
        "ok": current == SEALED_HOLDOUT_HASH and sealed_checks["all_ok"] and method_checks["all_ok"],
    }


def assert_preregistration_committed(repo_root: Path) -> None:
    path = repo_root / PREREG_PATH
    if not path.exists():
        raise RuntimeError("prospective natural LLM preregistration is missing")
    tracked = git_output(repo_root, ["ls-files", str(PREREG_PATH)])
    if not tracked:
        raise RuntimeError("preregistration must be committed before API requests")
    status = git_output(repo_root, ["status", "--short", str(PREREG_PATH)])
    if status:
        raise RuntimeError("preregistration has uncommitted changes; stopping before API requests")


def ensure_candidate_seal_committed(repo_root: Path) -> None:
    if not (repo_root / CANDIDATE_SEAL_PATH).exists():
        raise RuntimeError("candidate seal is missing; run generation and commit seal first")
    status = git_output(
        repo_root,
        [
            "status",
            "--short",
            str(CANDIDATE_SEAL_PATH),
            str(CANDIDATE_SEAL_SHA_PATH),
            "results/decompile_faithfulness/natural_llm_candidate_manifest.jsonl",
            str(ARTIFACT_ROOT),
        ],
    )
    if status:
        raise RuntimeError("candidate seal or candidate artifacts have uncommitted changes; commit before labeling")


def ensure_population_seal_committed(repo_root: Path) -> None:
    if not (repo_root / POPULATION_SEAL_PATH).exists():
        raise RuntimeError("evaluation population seal is missing; run labeling and commit seal first")
    status = git_output(
        repo_root,
        [
            "status",
            "--short",
            str(POPULATION_SEAL_PATH),
            str(POPULATION_SEAL_SHA_PATH),
            "results/decompile_faithfulness/natural_llm_candidate_manifest.jsonl",
            "results/decompile_faithfulness/natural_llm_exact_labels.jsonl",
            "results/decompile_faithfulness/natural_llm_fixture_replay.jsonl",
            "results/decompile_faithfulness/natural_llm_label_summary.csv",
        ],
    )
    if status:
        raise RuntimeError("evaluation population seal or label artifacts have uncommitted changes; commit before evaluation")


def prompt_leak_guard(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, sort_keys=True)
    forbidden_patterns = [
        r"source_output",
        r"fixture_seed",
        r"holdout_fixtures",
        r"first_mismatch",
        r"stored_mismatches",
        r"source_literal_char_interleave",
        r"final_auditor",
        r"ordered_prefix",
        r"controlled_mutation",
        r"mutation_family",
        r"exact_label",
        r"complete_mismatch_set",
        r"label_record_sha256",
    ]
    violations = [pattern for pattern in forbidden_patterns if re.search(pattern, text, flags=re.IGNORECASE)]
    return {"ok": not violations, "violations": violations}


def assert_selected_population(rows: list[dict[str, str]]) -> None:
    counts = Counter(row["project"] for row in rows)
    if len(rows) != 42 or dict(counts) != EXPECTED_PROJECT_COUNTS:
        raise RuntimeError(f"unexpected selected holdout population: {len(rows)} {dict(counts)}")


def natural_ghidra_views(repo_root: Path) -> dict[tuple[str, str], dict[str, Any]]:
    rows = read_jsonl(repo_root / "results/decompile_faithfulness/holdout_candidate_manifest.jsonl")
    result = {}
    for row in rows:
        if row.get("candidate_stratum") != "natural_ghidra":
            continue
        build_view = f"{row.get('compiler')}_{row.get('optimization_level')}"
        if build_view in BUILD_VIEWS:
            result[(row["function_id"], build_view)] = row
    return result


def architecture_for_object(object_path: Path) -> str:
    result = subprocess.run(["file", str(object_path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10)
    if result.returncode != 0:
        return "unknown"
    if "x86-64" in result.stdout or "x86_64" in result.stdout:
        return "x86_64"
    return result.stdout.strip()


def disassembly_for_object(object_path: Path) -> str:
    result = subprocess.run(["objdump", "-d", str(object_path)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=10)
    if result.returncode != 0:
        return "objdump_failed:\n" + result.stderr[-1000:]
    return result.stdout


def extract_response_text(payload: dict[str, Any]) -> str:
    chunks: list[str] = []
    if isinstance(payload.get("output_text"), str):
        chunks.append(payload["output_text"])
    for item in payload.get("output", []) if isinstance(payload.get("output"), list) else []:
        if isinstance(item, dict):
            for content in item.get("content", []) if isinstance(item.get("content"), list) else []:
                if isinstance(content, dict):
                    if isinstance(content.get("text"), str):
                        chunks.append(content["text"])
                    elif isinstance(content.get("type"), str) and isinstance(content.get("output_text"), str):
                        chunks.append(content["output_text"])
    if not chunks and isinstance(payload.get("choices"), list):
        for choice in payload["choices"]:
            message = choice.get("message", {}) if isinstance(choice, dict) else {}
            content = message.get("content") if isinstance(message, dict) else None
            if isinstance(content, str):
                chunks.append(content)
    return "\n".join(chunks)


def response_finish_reason(payload: dict[str, Any]) -> str:
    reasons = []
    for item in payload.get("output", []) if isinstance(payload.get("output"), list) else []:
        if isinstance(item, dict) and item.get("finish_reason"):
            reasons.append(str(item["finish_reason"]))
    if isinstance(payload.get("choices"), list):
        reasons.extend(str(choice.get("finish_reason", "")) for choice in payload["choices"] if isinstance(choice, dict))
    return ",".join(reason for reason in reasons if reason)


def natural_label_summary(manifest_rows: list[dict[str, Any]], labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    labels_by_id = {row["candidate_id"]: row for row in labels}
    groups: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in manifest_rows:
        label = labels_by_id[row["candidate_id"]]["label"]
        groups[("label", label)].append(row["candidate_id"])
        groups[("project", row["project"])].append(row["candidate_id"])
        groups[("build_view", row["build_view"])].append(row["candidate_id"])
        groups[("prompt_family", row["prompt_family"])].append(row["candidate_id"])
        groups[("status", row["candidate_status"])].append(row["candidate_id"])
    result = []
    for (group_type, group), ids in sorted(groups.items()):
        result.append({
            "group_type": group_type,
            "group": group,
            "attempts": len(ids),
            "compile_ready": sum(1 for cid in ids if labels_by_id[cid]["label"] != "non_evaluable"),
            "semantic_wrong": sum(1 for cid in ids if labels_by_id[cid]["label"] == "semantic_wrong"),
            "no_mismatch": sum(1 for cid in ids if labels_by_id[cid]["label"] == "no_mismatch_under_exact_holdout_domain"),
            "non_evaluable": sum(1 for cid in ids if labels_by_id[cid]["label"] == "non_evaluable"),
        })
    return result


def density_bucket(label: dict[str, Any]) -> str:
    rho = safe_div(int(label.get("total_mismatching_input_count", 0)), int(label.get("exact_domain_size", 0)))
    if rho == 0:
        return "rho=0"
    if rho <= 0.01:
        return "rho<=0.01"
    if rho <= 0.10:
        return "rho<=0.10"
    if rho <= 0.50:
        return "rho<=0.50"
    return "rho>0.50"


def interpretation_gates(
    policy_summary: list[dict[str, Any]],
    lib_summary: list[dict[str, Any]],
    population: dict[str, Any],
    manifest_rows: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    unexpected_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    primary = population["sets"]["primary_fixture_passing_wrong"]
    project_counts = Counter(population["candidate_project"][cid] for cid in primary)
    prompt_counts = Counter(population["candidate_prompt_family"][cid] for cid in primary)
    low_density_or_structured = len(population["sets"]["low_density_fixture_passing_wrong"])
    sufficient = (
        len(primary) >= 15
        and len(project_counts) >= 6
        and low_density_or_structured >= 8
        and (not project_counts or max(project_counts.values()) <= len(primary) * 0.5)
        and (not prompt_counts or max(prompt_counts.values()) <= len(primary) * 0.5)
    )
    lookup = {(row["policy"], int(row["budget"]), row["scope"]): row for row in policy_summary}
    final_b8 = float(lookup.get((he.FINAL_POLICY, 8, "primary_fixture_passing_wrong"), {}).get("detection_rate", 0.0))
    generic_b8 = float(lookup.get(("generic_type_boundaries", 8, "primary_fixture_passing_wrong"), {}).get("detection_rate", 0.0))
    fixture_b8 = float(lookup.get(("fixture_neighbor_only", 8, "primary_fixture_passing_wrong"), {}).get("detection_rate", 0.0))
    literal_b8 = float(lookup.get(("literal_first_concatenation", 8, "primary_fixture_passing_wrong"), {}).get("detection_rate", 0.0))
    lib_eval8 = next((row for row in lib_summary if row["mode"] == "evaluation_count" and str(row["budget_or_time_limit"]) == "8" and row["population"] == "primary_fixture_passing_wrong"), {})
    lib_wall = next((row for row in lib_summary if row["mode"] == "wall_clock" and str(row["budget_or_time_limit"]) == "0.1" and row["population"] == "primary_fixture_passing_wrong"), {})
    lib8_detection = float(lib_eval8.get("mean_detection", 0.0) or 0.0)
    lib01_detection = float(lib_wall.get("mean_detection", 0.0) or 0.0)
    unexpected_in_domain = sum(1 for row in unexpected_rows if row.get("in_exact_domain"))
    strong = (
        sufficient
        and final_b8 >= 0.80
        and (final_b8 >= generic_b8 + 0.10)
        and final_b8 >= fixture_b8 + 0.10
        and final_b8 >= literal_b8 - 0.02
        and final_b8 > lib8_detection
        and final_b8 >= lib01_detection
        and unexpected_in_domain == 0
    )
    negative = (
        len(primary) < 15
        or lib8_detection >= final_b8
        or lib01_detection >= final_b8
        or generic_b8 >= final_b8
        or (project_counts and max(project_counts.values()) > len(primary) * 0.5)
        or (prompt_counts and max(prompt_counts.values()) > len(primary) * 0.5)
    )
    if strong:
        overall = "strong_method_recovery_supported"
        consequence = "Paper may claim source-conditioned probes are particularly effective on naturally generated structured drift."
    elif sufficient and not negative:
        overall = "moderate_natural_result"
        consequence = "Position method as deterministic complementary probing without a superior scheduling claim."
    else:
        overall = "negative_or_feasibility_result"
        consequence = "Report as feasibility or characterization study and stop further experiments after Phase 1h."
    return {
        "sufficient_natural_evidence": sufficient,
        "strong_method_recovery_supported": strong,
        "negative_stopping_condition": negative,
        "overall_result": overall,
        "paper_claim_consequence": consequence,
        "primary_fixture_passing_wrong": len(primary),
        "project_distribution": dict(project_counts),
        "prompt_family_distribution": dict(prompt_counts),
        "low_density_count": len(population["sets"]["low_density_fixture_passing_wrong"]),
        "final_detection_b8": final_b8,
        "generic_detection_b8": generic_b8,
        "fixture_neighbor_detection_b8": fixture_b8,
        "literal_first_detection_b8": literal_b8,
        "libfuzzer_eval8_mean_detection": lib8_detection,
        "libfuzzer_wallclock_0p1_mean_detection": lib01_detection,
        "unexpected_in_domain_mismatches": unexpected_in_domain,
    }


def write_tables(
    repo_root: Path,
    manifest_rows: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    replay: list[dict[str, Any]],
    policy_summary: list[dict[str, Any]],
    lib_summary: list[dict[str, Any]],
    mechanisms: list[dict[str, Any]],
    population: dict[str, Any],
) -> None:
    table_dir = repo_root / "paper/tables"
    table_dir.mkdir(parents=True, exist_ok=True)
    replay_by_id = {row["candidate_id"]: row for row in replay}
    dataset_rows = [
        ["Attempts", len(manifest_rows)],
        ["Parse-ready", sum(1 for row in manifest_rows if row.get("parse_status") == "parsed_function")],
        ["Compile-ready", population["counts"]["compile_ready"]],
        ["Semantic wrong", population["counts"]["semantic_wrong"]],
        ["Fixture-passing semantic wrong", population["counts"]["primary_fixture_passing_wrong"]],
        ["Low-density fixture-passing wrong", population["counts"]["low_density_fixture_passing_wrong"]],
        ["Exact-domain no-mismatch", population["counts"]["no_mismatch"]],
        ["Non-evaluable", population["counts"]["non_evaluable"]],
    ]
    write_simple_latex_table(
        table_dir / "natural_llm_dataset.tex",
        "Prospective natural LLM candidate dataset",
        ["Quantity", "Count"],
        dataset_rows,
    )
    main_rows = []
    for budget in BUDGETS:
        for policy in [he.FINAL_POLICY, "generic_type_boundaries", "literal_first_concatenation", "fixture_neighbor_only"]:
            row = next((item for item in policy_summary if item["policy"] == policy and int(item["budget"]) == budget and item["scope"] == "primary_fixture_passing_wrong"), None)
            if row:
                main_rows.append([policy, budget, row["detected"], row["denominator"], f"{float(row['detection_rate']):.3f}"])
    write_simple_latex_table(
        table_dir / "natural_llm_main_results.tex",
        "Natural LLM deterministic policy results",
        ["Policy", "B", "Detected", "Denom.", "Detection"],
        main_rows,
    )
    baseline_rows = [
        [row["mode"], row["budget_or_time_limit"], row["population"], f"{float(row['mean_detection']):.3f}", row["no_mismatch_false_alarms"]]
        for row in lib_summary
    ]
    write_simple_latex_table(
        table_dir / "natural_llm_baselines.tex",
        "Natural LLM libFuzzer baselines",
        ["Mode", "Budget", "Population", "Mean det.", "False alarms"],
        baseline_rows,
    )
    failure_rows = [
        [row["candidate_id"], row["project"], row["function"], row["binary_view"], row["prompt_family"], row["list_name"]]
        for row in mechanisms[:20]
    ]
    write_simple_latex_table(
        table_dir / "natural_llm_failure_cases.tex",
        "Natural LLM candidate-level mechanism cases",
        ["Candidate", "Project", "Function", "View", "Prompt", "List"],
        failure_rows,
    )


def write_simple_latex_table(path: Path, caption: str, headers: list[str], rows: list[list[Any]]) -> None:
    align = "l" * len(headers)
    lines = [
        "\\begin{table}[t]",
        "\\centering",
        "\\small",
        f"\\caption{{{caption}}}",
        f"\\begin{{tabular}}{{{align}}}",
        "\\toprule",
        " & ".join(headers) + " \\\\",
        "\\midrule",
    ]
    for row in rows:
        lines.append(" & ".join(latex_escape(value) for value in row) + " \\\\")
    lines.extend(["\\bottomrule", "\\end{tabular}", "\\end{table}", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


def latex_escape(value: Any) -> str:
    text = str(value)
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
        .replace("{", "\\{")
        .replace("}", "\\}")
    )


def write_plot_script(repo_root: Path) -> None:
    path = repo_root / "figures/plot_natural_llm.py"
    path.write_text(
        '''from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "figures/data"


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def plot_budget() -> None:
    data = [row for row in rows("natural_llm_budget_curves.csv") if row["scope"] == "primary_fixture_passing_wrong"]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for policy in sorted({row["policy"] for row in data}):
        policy_rows = sorted([row for row in data if row["policy"] == policy], key=lambda row: int(row["budget"]))
        ax.plot([int(row["budget"]) for row in policy_rows], [float(row["detection_rate"]) for row in policy_rows], marker="o", linewidth=1.2, label=policy)
    ax.set_xlabel("Concrete-execution budget")
    ax.set_ylabel("Detection")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/natural_llm_budget_curves.pdf")


def plot_fuzzer() -> None:
    data = [row for row in rows("natural_llm_fuzzer_comparison.csv") if row["population"] == "primary_fixture_passing_wrong"]
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    labels = [row["mode"] + ":" + row["budget_or_time_limit"] for row in data]
    values = [float(row["mean_detection"]) for row in data]
    ax.bar(labels, values)
    ax.set_ylabel("Mean Detection")
    ax.set_ylim(0, 1.02)
    ax.tick_params(axis="x", labelrotation=25)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/natural_llm_fuzzer_comparison.pdf")


def plot_density() -> None:
    data = rows("natural_llm_density_results.csv")
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    ax.bar([row["density_bucket"] for row in data], [int(row["candidate_count"]) for row in data])
    ax.set_xlabel("Mismatch-density bucket")
    ax.set_ylabel("Natural LLM primary candidates")
    ax.tick_params(axis="x", labelrotation=20)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/natural_llm_density_results.pdf")


if __name__ == "__main__":
    plot_budget()
    plot_fuzzer()
    plot_density()
''',
        encoding="utf-8",
    )


def generate_figures(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(repo_root / "figures/plot_natural_llm.py")],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)


def write_handoff(
    *,
    repo_root: Path,
    natural_population: dict[str, Any],
    manifest_rows: list[dict[str, Any]],
    labels: dict[str, dict[str, Any]],
    policy_summary: list[dict[str, Any]],
    lib_summary: list[dict[str, Any]],
    lib_sets: list[dict[str, Any]],
    gates: dict[str, Any],
    preflight: dict[str, Any],
) -> Path:
    path = repo_root / "docs/paper_agent/prospective_natural_llm_handoff.md"
    candidate_seal_hash = sha256_path(repo_root / CANDIDATE_SEAL_PATH)
    population_hash = sha256_path(repo_root / POPULATION_SEAL_PATH)
    final_rows = [
        row for row in policy_summary
        if row["policy"] == he.FINAL_POLICY and row["scope"] == "primary_fixture_passing_wrong"
    ]
    lines = [
        "# Prospective Natural LLM Handoff",
        "",
        "## Git And Seals",
        "",
        f"- Branch: `{git_output(repo_root, ['branch', '--show-current'])}`",
        f"- Preregistration commit: `{git_output(repo_root, ['rev-parse', 'c9e6659'])}`",
        f"- Candidate-seal hash: `{candidate_seal_hash}`",
        f"- Evaluation-population seal hash: `{population_hash}`",
        f"- Final result commit/HEAD at handoff generation: `{git_output(repo_root, ['rev-parse', 'HEAD'])}`",
        f"- Sealed holdout hash: `{SEALED_HOLDOUT_HASH}`",
        f"- Frozen method commit: `{METHOD_FREEZE_COMMIT}`",
        "",
        "## Provider",
        "",
        f"- Provider/model: `{PROVIDER_NAME}` / `{REQUESTED_MODEL}`",
        f"- API call count: `{sum(int(row.get('api_call_performed', 0)) for row in manifest_rows)}`",
        "- API cost: `unknown unless provider usage metadata includes billing`",
        "- Local GPU usage: `none`",
        "",
        "## Candidate Counts",
        "",
        f"- Attempts: `{len(manifest_rows)}`",
        f"- Parse-ready: `{natural_population['counts']['parse_ready']}`",
        f"- Compile-ready: `{natural_population['counts']['compile_ready']}`",
        f"- Semantic wrong: `{natural_population['counts']['semantic_wrong']}`",
        f"- No-mismatch: `{natural_population['counts']['no_mismatch']}`",
        f"- Non-evaluable: `{natural_population['counts']['non_evaluable']}`",
        f"- Fixture-passing semantic-wrong: `{natural_population['counts']['primary_fixture_passing_wrong']}`",
        f"- Low-density count: `{natural_population['counts']['low_density_fixture_passing_wrong']}`",
        f"- Project distribution: `{json.dumps(natural_population['project_distribution_primary'], sort_keys=True)}`",
        "",
        "## Final Policy",
        "",
    ]
    for row in sorted(final_rows, key=lambda item: int(item["budget"])):
        lines.append(f"- B={row['budget']}: `{row['detected']}/{row['denominator']}` = `{float(row['detection_rate']):.3f}`")
    lines.extend(["", "## Baselines", ""])
    for policy in ["generic_type_boundaries", "literal_first_concatenation"]:
        row = next((item for item in policy_summary if item["policy"] == policy and int(item["budget"]) == 8 and item["scope"] == "primary_fixture_passing_wrong"), None)
        if row:
            lines.append(f"- {policy} B=8: `{row['detected']}/{row['denominator']}` = `{float(row['detection_rate']):.3f}`")
    for row in lib_summary:
        if row["population"] == "primary_fixture_passing_wrong":
            lines.append(f"- libFuzzer {row['mode']} {row['budget_or_time_limit']}: mean Detection `{float(row['mean_detection']):.3f}`")
    lines.extend([
        "",
        "## Integrity",
        "",
        f"- No-mismatch unexpected mismatches: `{sum(1 for row in read_jsonl(repo_root / 'results/decompile_faithfulness/natural_llm_unexpected_mismatches.jsonl') if row.get('in_exact_domain')) if (repo_root / 'results/decompile_faithfulness/natural_llm_unexpected_mismatches.jsonl').exists() else 0}`",
        f"- Sealed artifacts unchanged: `{preflight['sealed_artifact_checks']['all_ok']}`",
        f"- Method hashes unchanged: `{preflight['method_hash_checks']['all_ok']}`",
        "- Frozen auditor was not run before candidate and population seals.",
        "",
        "## Interpretation",
        "",
        f"- Gate result: `{gates['overall_result']}`",
        f"- Paper consequence: {gates['paper_claim_consequence']}",
        "",
        "## Tests",
        "",
        "- Recorded by final commit after Phase 1h tests run.",
    ])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def safe_div(left: float, right: float) -> float:
    return 0.0 if right == 0 else float(left) / float(right)


def percentile(values: list[float] | list[int], q: float) -> float | str:
    if not values:
        return ""
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    pos = q * (len(ordered) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(ordered) - 1)
    frac = pos - lo
    return ordered[lo] * (1 - frac) + ordered[hi] * frac


def median_or_blank(values: Iterable[Any]) -> float | str:
    items = [float(value) for value in values if value not in {"", None}]
    return statistics.median(items) if items else ""


def mean_or_blank(values: Iterable[Any]) -> float | str:
    items = [float(value) for value in values if value not in {"", None}]
    return statistics.mean(items) if items else ""


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_") or "item"


def git_output(repo_root: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=repo_root, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout.strip()


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
