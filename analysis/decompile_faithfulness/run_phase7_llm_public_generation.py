from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase2_gpu_smoke as phase2_gpu
from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu
from analysis.decompile_faithfulness import run_phase5b_hard_candidates as phase5b
from analysis.decompile_faithfulness import run_phase6_decompiler_like_candidates as phase6


DEFAULT_MODEL_PATH = phase2_gpu.DEFAULT_MODEL_PATH
DEFAULT_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json")
DEFAULT_PREFLIGHT = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_import_preflight.json")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase7_llm_public")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public.zh.md")
DEFAULT_CANDIDATE_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_candidate_manifest.json")
DEFAULT_PROMPT_IDS = ("strict_rewrite", "strict_bug")
SUPPORTED_PROMPT_IDS = set(DEFAULT_PROMPT_IDS)


@dataclass(frozen=True)
class GenerationRequest:
    case_id: str
    prompt_id: str
    generation_index: int
    candidate_id: str
    prompt: str


@dataclass(frozen=True)
class CleaningResult:
    status: str
    function_source: str
    reason: str


def main() -> None:
    args = parse_args()
    summary = run_generation(
        repo_root=args.repo_root,
        manifest_json=args.manifest_json,
        preflight_json=args.preflight_json,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        candidate_manifest_json=args.candidate_manifest_json,
        model_path=args.model_path,
        device=args.device,
        case_ids=args.case_id,
        prompt_ids=args.prompt_id,
        shard_index=args.shard_index,
        shard_count=args.shard_count,
        run_tag=args.run_tag,
        candidates_per_prompt=args.candidates_per_prompt,
        max_new_tokens=args.max_new_tokens,
        steps=args.steps,
        temperature=args.temperature,
        top_p=args.top_p,
        torch_dtype=args.torch_dtype,
        seed=args.seed,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "generation_count": summary["generation_count"],
                "parsed_count": summary["parsed_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "paired_case_count": summary["paired_case_count"],
                "model_loaded": summary["model_info"]["model_loaded"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--candidate-manifest-json", type=Path, default=DEFAULT_CANDIDATE_MANIFEST)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--device", default="cuda:2")
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--prompt-id", action="append", default=None)
    parser.add_argument("--shard-index", type=int, default=0)
    parser.add_argument("--shard-count", type=int, default=1)
    parser.add_argument("--run-tag", default="phase7_llm_public")
    parser.add_argument("--candidates-per-prompt", type=int, default=1)
    parser.add_argument("--max-new-tokens", type=int, default=220)
    parser.add_argument("--steps", type=int, default=24)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument(
        "--torch-dtype",
        choices=["auto", "float16", "bfloat16", "float32"],
        default="float16",
    )
    parser.add_argument("--seed", type=int, default=20260701)
    return parser.parse_args()


def run_generation(
    repo_root: Path,
    manifest_json: Path,
    preflight_json: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    candidate_manifest_json: Path,
    model_path: Path,
    device: str,
    case_ids: list[str] | None,
    prompt_ids: list[str] | None,
    shard_index: int,
    shard_count: int,
    run_tag: str,
    candidates_per_prompt: int,
    max_new_tokens: int,
    steps: int,
    temperature: float,
    top_p: float,
    torch_dtype: str,
    seed: int,
) -> dict[str, Any]:
    if candidates_per_prompt < 1:
        raise ValueError("candidates_per_prompt must be >= 1")
    if shard_count < 1 or not 0 <= shard_index < shard_count:
        raise ValueError("invalid shard configuration")
    prompt_ids = prompt_ids or list(DEFAULT_PROMPT_IDS)
    for prompt_id in prompt_ids:
        if prompt_id not in SUPPORTED_PROMPT_IDS:
            raise ValueError(f"unsupported prompt id: {prompt_id}")

    repo_root = repo_root.resolve()
    manifest_json = _resolve(repo_root, manifest_json)
    preflight_json = _resolve(repo_root, preflight_json)
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    candidate_manifest_json = _resolve(repo_root, candidate_manifest_json)
    model_path = _resolve(repo_root, model_path)

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    preflight = json.loads(preflight_json.read_text(encoding="utf-8"))
    if preflight.get("verdict") != "pass-phase7-codefuse-import":
        raise RuntimeError(f"Phase7 CodeFuse import must pass first: {preflight.get('verdict')}")

    entries = [
        entry for entry in manifest["functions"]
        if entry.get("counts_for_phase7_public_benchmark_gate")
    ]
    if case_ids is not None:
        requested = set(case_ids)
        entries = [entry for entry in entries if entry["case_id"] in requested]
    entries = phase5_gpu.shard_entries(entries, shard_index=shard_index, shard_count=shard_count)
    cases = {entry["case_id"]: phase5_gpu._case_from_manifest_entry(repo_root, entry) for entry in entries}
    entries_by_case = {entry["case_id"]: entry for entry in entries}

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    prompt_dir = output_dir / "prompts"
    trace_dir = output_dir / "traces"
    static_dir = output_dir / "static_compile"
    for path in [raw_dir, prompt_dir, trace_dir, static_dir]:
        path.mkdir(parents=True, exist_ok=True)

    generation_path = output_dir / "generation_metadata.jsonl"
    records_path = output_dir / "records.jsonl"
    requests = build_generation_requests(
        cases=cases,
        entries_by_case=entries_by_case,
        prompt_ids=prompt_ids,
        candidates_per_prompt=candidates_per_prompt,
        shard_index=shard_index,
        run_tag=run_tag,
    )
    model_info = {
        "model_path": str(model_path),
        "device": device,
        "torch_dtype": torch_dtype,
        "max_new_tokens": max_new_tokens,
        "steps": steps,
        "temperature": temperature,
        "top_p": top_p,
        "seed": seed,
        "cuda_visible_devices_policy": "not_set_by_script; explicit --device placement only",
    }
    generator = phase2_gpu._DreamCoderGenerator(model_path, device, torch_dtype, seed)
    load_started = time.monotonic()
    model_loaded = False
    model_error = ""
    try:
        generator.load()
        model_loaded = True
    except Exception as exc:  # pragma: no cover - exercised only with local GPU/model.
        model_error = repr(exc)
    model_info["model_load_seconds"] = round(time.monotonic() - load_started, 3)
    model_info["model_loaded"] = model_loaded
    model_info["model_error"] = model_error

    generation_records: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    candidate_manifest_by_case: dict[str, list[dict[str, Any]]] = {case_id: [] for case_id in cases}
    original_trace_cache: dict[tuple[str, str, str], Any] = {}
    original_static_cache: dict[tuple[str, str], Any] = {}
    for request in requests:
        prompt_path = prompt_dir / f"{request.candidate_id}.prompt.txt"
        raw_path = raw_dir / f"{request.candidate_id}.raw.txt"
        prompt_path.write_text(request.prompt, encoding="utf-8")
        raw_text = ""
        generation_error = ""
        token_stats: dict[str, Any] = {}
        started = time.monotonic()
        if model_loaded:
            try:
                raw_text, token_stats = generator.generate(
                    request.prompt,
                    max_new_tokens=max_new_tokens,
                    steps=steps,
                    temperature=temperature,
                    top_p=top_p,
                )
            except Exception as exc:  # pragma: no cover - exercised only with local GPU/model.
                generation_error = repr(exc)
        raw_path.write_text(raw_text, encoding="utf-8")
        entry = entries_by_case[request.case_id]
        case = cases[request.case_id]
        cleaning = extract_public_c_function(raw_text, entry)
        metadata = {
            "case_id": request.case_id,
            "candidate_id": request.candidate_id,
            "prompt_id": request.prompt_id,
            "prompt_path": str(prompt_path),
            "raw_output_path": str(raw_path),
            "cleaning_status": cleaning.status,
            "cleaning_reason": cleaning.reason,
            "generation_index": request.generation_index,
            "generation_error": generation_error,
            "generation_seconds": round(time.monotonic() - started, 3),
            "source_kind": "phase7_public_local_llm",
            "source_name": "Dream-Coder-v0-Instruct-7B",
            "sampling": {
                "temperature": temperature,
                "top_p": top_p,
                "max_new_tokens": max_new_tokens,
                "steps": steps,
            },
            **token_stats,
        }
        generation_records.append(metadata)
        if cleaning.status != "parsed_function":
            continue

        candidate = phase6.Phase6Candidate(
            case_id=case.case_id,
            candidate_id=request.candidate_id,
            mutation_type=f"phase7_llm_public_{request.prompt_id}",
            function_source=cleaning.function_source,
            expected_role="llm_generated_unknown",
            source_kind="phase7_public_local_llm",
            source_name="Dream-Coder-v0-Instruct-7B",
            tool="Dream-Coder-v0-Instruct-7B",
            optimization_level="O0",
            assembly_context_path="",
        )
        features = phase6.phase6_features(
            case=case,
            candidate=candidate,
            hard_inputs=phase5b.phase5b_hard_trace_inputs(entry, max_inputs=128),
            trace_dir=trace_dir,
            static_dir=static_dir,
            original_trace_cache=original_trace_cache,
            original_static_cache=original_static_cache,
        )
        record = record_from_features(request, cleaning.function_source, features, metadata)
        records.append(record)
        if record["compiled"]:
            candidate_manifest_by_case[request.case_id].append(
                {
                    "case_id": request.case_id,
                    "candidate_id": request.candidate_id,
                    "label": record["label"],
                    "mutation_type": record["mutation_type"],
                    "function_source": cleaning.function_source,
                    "source_kind": "phase7_public_local_llm",
                    "source_name": "Dream-Coder-v0-Instruct-7B",
                    "prompt_id": request.prompt_id,
                    "raw_output_path": str(raw_path),
                    "cleaning_status": cleaning.status,
                    "generation_index": request.generation_index,
                    "sampling": metadata["sampling"],
                }
            )

    _write_jsonl(generation_path, generation_records)
    _write_jsonl(records_path, records)
    candidate_manifest = build_candidate_manifest(
        manifest=manifest,
        output_dir=output_dir,
        records_path=records_path,
        generation_path=generation_path,
        candidate_manifest_by_case=candidate_manifest_by_case,
        records=records,
        shard_index=shard_index,
        shard_count=shard_count,
    )
    _write_json(candidate_manifest_json, candidate_manifest)
    summary = summarize(
        output_dir=output_dir,
        output_json=output_json,
        output_zh=output_zh,
        generation_path=generation_path,
        records_path=records_path,
        generation_records=generation_records,
        records=records,
        model_info=model_info,
        entries=entries,
        prompt_ids=prompt_ids,
        candidate_manifest=candidate_manifest,
    )
    generator.unload()
    return summary


def build_generation_requests(
    cases: dict[str, phase5_gpu.fixtures.FunctionCase],
    entries_by_case: dict[str, dict[str, Any]],
    prompt_ids: list[str],
    candidates_per_prompt: int,
    shard_index: int,
    run_tag: str,
) -> list[GenerationRequest]:
    requests: list[GenerationRequest] = []
    for case_id, case in sorted(cases.items()):
        entry = entries_by_case[case_id]
        for prompt_id in prompt_ids:
            for generation_index in range(candidates_per_prompt):
                candidate_id = f"{run_tag}_s{shard_index}_{case_id}_{prompt_id}_{generation_index:02d}"
                requests.append(
                    GenerationRequest(
                        case_id=case_id,
                        prompt_id=prompt_id,
                        generation_index=generation_index,
                        candidate_id=candidate_id,
                        prompt=build_prompt(case, entry, prompt_id),
                    )
                )
    return requests


def build_prompt(
    case: phase5_gpu.fixtures.FunctionCase,
    entry: dict[str, Any],
    prompt_id: str,
) -> str:
    signature = entry["signature"]
    risk_text = ", ".join(entry.get("risk_families", [])) or "integer boundary behavior"
    fixtures_text = "; ".join(
        f"{entry['function_name']}({', '.join(map(str, item['args']))}) == {item['expected']}"
        for item in entry.get("fixtures", [])[:6]
    )
    if prompt_id == "strict_rewrite":
        task = (
            "Rewrite the target CodeFuse-DeBench function with identical behavior over the documented bounded integer domain.\n"
            "Output one complete C function only. No comments, no explanation, no includes, no main, no helper functions.\n\n"
            f"Risk areas to preserve: {risk_text}\n"
            f"Fixture examples: {fixtures_text}\n\n"
            f"Target function name: {entry['function_name']}\n"
            f"Reference source:\n{case.function_source.strip()}"
        )
    elif prompt_id == "strict_bug":
        task = (
            "Write one plausible compilable implementation with exactly one subtle semantic bug.\n"
            "Output one complete C function only. No comments, no explanation, no includes, no main, no helper functions.\n"
            f"Prefer a bug around these risk areas: {risk_text}.\n"
            f"Fixture examples from the correct behavior: {fixtures_text}\n\n"
            f"Target function name: {entry['function_name']}\n"
            f"Reference source:\n{case.function_source.strip()}"
        )
    else:
        raise ValueError(f"unsupported prompt id: {prompt_id}")
    return phase2_gpu._strict_prompt(signature, task)


def extract_public_c_function(raw_text: str, entry: dict[str, Any]) -> CleaningResult:
    if not raw_text.strip():
        return CleaningResult("empty_output", "", "raw output is empty")
    statuses: list[str] = []
    for candidate_text in phase2_gpu._candidate_texts(raw_text):
        normalized = drop_preprocessor_lines(candidate_text)
        result = extract_public_from_text(normalized, entry)
        if result.status == "parsed_function":
            return result
        statuses.append(result.status)
    reason = "no candidate text yielded target function"
    if statuses:
        reason = f"tried statuses: {', '.join(statuses[:5])}"
    return CleaningResult("parse_failed", "", reason)


def extract_public_from_text(text: str, entry: dict[str, Any]) -> CleaningResult:
    if re.search(r"\bmain\s*\(", text):
        return CleaningResult("rejected_main", "", "main function found")
    function_name = entry["function_name"]
    starts = [
        match.start()
        for match in re.finditer(
            rf"\b(?:int|unsigned\s+int|short|char|long|long\s+long|_Bool)\s+{re.escape(function_name)}\s*\(",
            text,
        )
    ]
    if not starts:
        return CleaningResult("missing_expected_function", "", "expected scalar function not found")
    statuses: list[str] = []
    for header_start in starts:
        open_brace = text.find("{", header_start)
        if open_brace == -1:
            statuses.append("missing_body")
            continue
        close_brace = phase2_gpu._matching_brace(text, open_brace)
        if close_brace is None:
            statuses.append("unbalanced_braces")
            continue
        function_source = text[header_start:close_brace + 1].strip() + "\n"
        if "..." in function_source:
            statuses.append("rejected_ellipsis")
            continue
        if re.search(r"\b(?:abs|labs|llabs)\s*\(", function_source):
            statuses.append("rejected_library_call")
            continue
        if public_function_definition_count(function_source) != 1:
            statuses.append("multiple_functions")
            continue
        surrounding = (text[:header_start] + "\n" + text[close_brace + 1:]).strip()
        if surrounding and public_function_definition_count(surrounding) > 0:
            statuses.append("extra_helper_function")
            continue
        return CleaningResult("parsed_function", function_source, "")
    reason = f"target function candidates failed: {', '.join(statuses[:5])}" if statuses else ""
    return CleaningResult("parse_failed", "", reason)


def public_function_definition_count(text: str) -> int:
    return len(
        re.findall(
            r"\b(?:int|unsigned\s+int|short|char|long|long\s+long|_Bool|void)\s+\w+\s*\([^;{}]*\)\s*\{",
            text,
        )
    )


def drop_preprocessor_lines(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def record_from_features(
    request: GenerationRequest,
    function_source: str,
    features: dict[str, float],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if features["compiled"] != 1.0:
        label = "compile_fail"
    elif features["trace_mismatch_rate"] == 0.0:
        label = "faithful"
    else:
        label = "plausible_wrong"
    return {
        "case_id": request.case_id,
        "candidate_id": request.candidate_id,
        "label": label,
        "mutation_type": f"phase7_llm_public_{request.prompt_id}",
        "compiled": features["compiled"] == 1.0,
        "behavior_passed": features["fixture_mismatch_rate"] == 0.0,
        "bounded_trace_passed": features["trace_mismatch_rate"] == 0.0,
        "optimization_level": "O0",
        "features": {
            key: value
            for key, value in features.items()
            if key not in {"compiled", "primary_exit_code", "fixture_exit_code"}
        },
        "diagnostics": {
            "primary_exit_code": features["primary_exit_code"],
            "fixture_exit_code": features["fixture_exit_code"],
        },
        "metadata": {
            **metadata,
            "function_source": function_source,
        },
    }


def build_candidate_manifest(
    manifest: dict[str, Any],
    output_dir: Path,
    records_path: Path,
    generation_path: Path,
    candidate_manifest_by_case: dict[str, list[dict[str, Any]]],
    records: list[dict[str, Any]],
    shard_index: int,
    shard_count: int,
) -> dict[str, Any]:
    compile_pass_count = sum(1 for record in records if record["compiled"])
    paired_case_count = paired_case_count_for_records(records)
    return {
        "phase": "phase7_llm_public_candidate_generation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": manifest.get("benchmark", "CodeFuse-DeBench"),
        "source_manifest_function_count": manifest.get("function_count", 0),
        "candidate_layers": ["llm_strict_rewrite", "llm_strict_bug"],
        "candidate_count": len(records),
        "compile_pass_count": compile_pass_count,
        "compile_pass_target_min": 100,
        "paired_function_count": paired_case_count,
        "paired_function_target_min": 20,
        "shard_index": shard_index,
        "shard_count": shard_count,
        "output_dir": str(output_dir),
        "records_path": str(records_path),
        "generation_metadata_path": str(generation_path),
        "candidates": [
            {"case_id": case_id, "candidates": candidates}
            for case_id, candidates in sorted(candidate_manifest_by_case.items())
            if candidates
        ],
        "verdict": candidate_manifest_verdict(compile_pass_count, paired_case_count),
        "gpu_decision": "started",
    }


def summarize(
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    generation_path: Path,
    records_path: Path,
    generation_records: list[dict[str, Any]],
    records: list[dict[str, Any]],
    model_info: dict[str, Any],
    entries: list[dict[str, Any]],
    prompt_ids: list[str],
    candidate_manifest: dict[str, Any],
) -> dict[str, Any]:
    parsed_count = sum(1 for record in generation_records if record["cleaning_status"] == "parsed_function")
    compile_pass_count = sum(1 for record in records if record["compiled"])
    eval_records = [record for record in records if record["label"] in {"faithful", "plausible_wrong"}]
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
    summary = {
        "phase": "phase7_llm_public_generation",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "generation_metadata_path": str(generation_path),
        "records_path": str(records_path),
        "case_ids": [entry["case_id"] for entry in entries],
        "prompt_ids": prompt_ids,
        "model_info": model_info,
        "generation_count": len(generation_records),
        "parsed_count": parsed_count,
        "parsed_rate": parsed_count / len(generation_records) if generation_records else 0.0,
        "candidate_count": len(records),
        "compile_pass_count": compile_pass_count,
        "compile_rate_among_parsed": compile_pass_count / parsed_count if parsed_count else 0.0,
        "behavior_label_counts": count_by(records, "label"),
        "cleaning_status_counts": count_by(generation_records, "cleaning_status"),
        "paired_case_count": paired_case_count_for_records(records),
        "fixture_passing_wrong_count": fixture_passing_wrong_count(records),
        "baseline_auc": baseline_auc,
        "best_non_oracle_baseline_auc": best_baseline,
        "sota_delta_vs_best_baseline": baseline_auc["v3_trace_total"] - best_baseline,
        "fixture_collapse": phase3_cpu.v1._fixture_collapse(eval_records),
        "candidate_manifest_verdict": candidate_manifest["verdict"],
    }
    summary["verdict"] = summary_verdict(summary)
    _write_json(output_json, summary)
    write_markdown(output_zh, summary)
    return summary


def candidate_manifest_verdict(compile_pass_count: int, paired_case_count: int) -> str:
    if compile_pass_count >= 100 and paired_case_count >= 20:
        return "pass-phase7-llm-public-candidate-generation"
    return "needs-more-phase7-llm-public-samples"


def summary_verdict(summary: dict[str, Any]) -> str:
    if not summary["model_info"].get("model_loaded"):
        return "gpu-model-not-loaded"
    if summary["parsed_count"] < 1 or summary["compile_pass_count"] < 1:
        return "needs-generation-cleaning"
    if summary["candidate_manifest_verdict"] == "pass-phase7-llm-public-candidate-generation":
        return "pass-phase7-llm-public-generation"
    return "needs-more-phase7-llm-public-samples"


def paired_case_count_for_records(records: list[dict[str, Any]]) -> int:
    total = 0
    for case_id in sorted({record["case_id"] for record in records}):
        labels = {record["label"] for record in records if record["case_id"] == case_id and record["compiled"]}
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


def count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    text = f"""# Decompilation Faithfulness Phase 7E LLM Public Generation

- Verdict: `{summary['verdict']}`
- Model loaded: `{summary['model_info']['model_loaded']}`
- Device: `{summary['model_info']['device']}`
- Cases: `{len(summary['case_ids'])}`
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
- Records: `{summary['records_path']}`

## Interpretation

This is the GPU-backed public benchmark LLM candidate layer. It uses CodeFuse-DeBench source-known scalar C functions and evaluates generated candidates with the same Dynamic Trace v3 plus static structured proxy used in Phase 7C/C2.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
