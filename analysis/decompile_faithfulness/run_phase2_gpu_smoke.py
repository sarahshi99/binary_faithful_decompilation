from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_dynamic_trace_audit as v1
from analysis.decompile_faithfulness import run_phase2_cpu_smoke as cpu_smoke


DEFAULT_MODEL_PATH = Path(
    "/home/shx/.cache/huggingface/hub/"
    "models--Dream-org--Dream-Coder-v0-Instruct-7B/"
    "snapshots/5d9e88c723af9045f362748b5284bdf43d9c501e"
)
DEFAULT_CASE_IDS = ["signum", "absdiff"]
DEFAULT_PROMPT_IDS = ["source_rewrite", "signature_spec"]
SUPPORTED_PROMPT_IDS = {
    "signature_spec",
    "source_rewrite",
    "bug_seed",
    "strict_signature",
    "strict_rewrite",
    "strict_bug",
}


CASE_SPECS = {
    "absdiff": "Return the absolute difference between a and b.",
    "clamp8": "Clamp x into the inclusive range 0..255.",
    "count_bits8": "Return the number of set bits in the low 8 bits of x.",
    "max3": "Return the maximum of a, b, and c.",
    "sum_to_n": "Return 0 when n <= 0, otherwise return 1 + ... + n.",
    "signum": "Return -1 for negative x, 1 for positive x, and 0 for x == 0.",
    "is_power_of_two": "Return 1 exactly when x is a positive power of two, otherwise return 0.",
    "gcd_positive": "Return the greatest common divisor of positive a and b.",
}

BUG_HINTS = {
    "absdiff": "For example, mishandle one ordering case while keeping equal inputs sensible.",
    "clamp8": "For example, mishandle one boundary such as 255 or negative values.",
    "count_bits8": "For example, count the wrong number of low bits or skip one bit position.",
    "max3": "For example, ignore one argument in one ordering pattern.",
    "sum_to_n": "For example, use a subtly wrong loop bound.",
    "signum": "For example, swap the negative or zero case while positive values still look right.",
    "is_power_of_two": "For example, mishandle zero, one, or non-positive values.",
    "gcd_positive": "For example, stop the Euclidean loop one step too early or return the wrong variable.",
}


@dataclass(frozen=True)
class CleaningResult:
    status: str
    function_source: str
    reason: str


@dataclass(frozen=True)
class GenerationRequest:
    case_id: str
    prompt_id: str
    generation_index: int
    candidate_id: str
    prompt: str


def main() -> None:
    args = parse_args()
    summary = run_gpu_smoke(
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_md=args.output_md,
        output_zh=args.output_zh,
        model_path=args.model_path,
        device=args.device,
        case_ids=args.case_id,
        prompt_ids=args.prompt_id,
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
                "generation_count": summary["generation_count"],
                "parsed_count": summary["parsed_count"],
                "candidate_count": summary["candidate_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "behavior_label_counts": summary["behavior_label_counts"],
                "gpu_smoke_gate_passed": summary["gpu_smoke_gate_passed"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("analysis_outputs/decompile_faithfulness/phase2_gpu_smoke"),
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_gpu_smoke.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_gpu_smoke.md"),
    )
    parser.add_argument(
        "--output-zh",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_gpu_smoke.zh.md"),
    )
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--device", default="cuda:2")
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--prompt-id", action="append", default=None)
    parser.add_argument("--candidates-per-prompt", type=int, default=1)
    parser.add_argument("--max-new-tokens", type=int, default=160)
    parser.add_argument("--steps", type=int, default=32)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-p", type=float, default=1.0)
    parser.add_argument(
        "--torch-dtype",
        choices=["auto", "float16", "bfloat16", "float32"],
        default="auto",
    )
    parser.add_argument("--seed", type=int, default=20260618)
    return parser.parse_args()


def run_gpu_smoke(
    output_dir: Path,
    output_json: Path,
    output_md: Path,
    output_zh: Path,
    model_path: Path = DEFAULT_MODEL_PATH,
    device: str = "cuda:2",
    case_ids: list[str] | None = None,
    prompt_ids: list[str] | None = None,
    candidates_per_prompt: int = 1,
    max_new_tokens: int = 160,
    steps: int = 32,
    temperature: float = 0.0,
    top_p: float = 1.0,
    torch_dtype: str = "auto",
    seed: int = 20260618,
) -> dict[str, Any]:
    if candidates_per_prompt < 1:
        raise ValueError("candidates_per_prompt must be >= 1")

    case_ids = case_ids or DEFAULT_CASE_IDS
    prompt_ids = prompt_ids or DEFAULT_PROMPT_IDS
    for case_id in case_ids:
        fixtures.case_by_id(case_id)
    for prompt_id in prompt_ids:
        if prompt_id not in SUPPORTED_PROMPT_IDS:
            raise ValueError(f"unsupported prompt id: {prompt_id}")

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    prompt_dir = output_dir / "prompts"
    candidate_dir = output_dir / "candidates"
    trace_dir = output_dir / "traces"
    for path in [raw_dir, prompt_dir, candidate_dir, trace_dir]:
        path.mkdir(parents=True, exist_ok=True)

    generation_path = output_dir / "generation_metadata.jsonl"
    manifest_path = output_dir / "manifest.json"
    records_path = output_dir / "records.jsonl"
    requests = build_generation_requests(case_ids, prompt_ids, candidates_per_prompt)
    model_info = {
        "model_path": str(model_path),
        "device": device,
        "torch_dtype": torch_dtype,
        "max_new_tokens": max_new_tokens,
        "steps": steps,
        "temperature": temperature,
        "top_p": top_p,
        "seed": seed,
        "cuda_visible_devices_policy": (
            "not_set_by_script; model and tensors are explicitly moved to requested device"
        ),
    }
    generator = _DreamCoderGenerator(model_path, device, torch_dtype, seed)
    generation_records: list[dict[str, Any]] = []
    manifest_by_case: dict[str, list[dict[str, Any]]] = {case_id: [] for case_id in case_ids}

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

    for request in requests:
        prompt_path = prompt_dir / f"{request.candidate_id}.prompt.txt"
        raw_path = raw_dir / f"{request.candidate_id}.raw.txt"
        prompt_path.write_text(request.prompt, encoding="utf-8")
        generation_started = time.monotonic()
        raw_text = ""
        generation_error = ""
        token_stats: dict[str, Any] = {}
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
        cleaning = extract_expected_c_function(
            raw_text,
            fixtures.case_by_id(request.case_id),
        )
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
            "generation_seconds": round(time.monotonic() - generation_started, 3),
            "source_kind": "local_llm",
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
        if cleaning.status == "parsed_function":
            manifest_by_case[request.case_id].append(
                {
                    "case_id": request.case_id,
                    "candidate_id": request.candidate_id,
                    "label": "unknown",
                    "mutation_type": f"phase2_gpu_smoke_{request.prompt_id}",
                    "function_source": cleaning.function_source,
                    "source_kind": "local_llm",
                    "source_name": "Dream-Coder-v0-Instruct-7B",
                    "prompt_id": request.prompt_id,
                    "raw_output_path": str(raw_path),
                    "cleaning_status": cleaning.status,
                    "generation_index": request.generation_index,
                    "sampling": metadata["sampling"],
                }
            )

    manifest = [
        {"case_id": case_id, "candidates": candidates}
        for case_id, candidates in manifest_by_case.items()
        if candidates
    ]
    _write_json(manifest_path, manifest)
    _write_jsonl(generation_path, generation_records)

    records = [
        cpu_smoke._evaluate_candidate(candidate, candidate_dir, trace_dir)
        for candidate in cpu_smoke._load_candidates(manifest)
    ] if manifest else []
    _write_jsonl(records_path, records)

    summary = summarize_gpu_smoke(
        output_dir=output_dir,
        output_json=output_json,
        output_md=output_md,
        output_zh=output_zh,
        manifest_path=manifest_path,
        generation_path=generation_path,
        records_path=records_path,
        generation_records=generation_records,
        records=records,
        model_info=model_info,
    )
    generator.unload()
    return summary


def build_generation_requests(
    case_ids: list[str],
    prompt_ids: list[str],
    candidates_per_prompt: int,
) -> list[GenerationRequest]:
    requests = []
    for case_id in case_ids:
        case = fixtures.case_by_id(case_id)
        for prompt_id in prompt_ids:
            for generation_index in range(candidates_per_prompt):
                candidate_id = f"phase2_gpu_{case_id}_{prompt_id}_{generation_index:02d}"
                requests.append(
                    GenerationRequest(
                        case_id=case_id,
                        prompt_id=prompt_id,
                        generation_index=generation_index,
                        candidate_id=candidate_id,
                        prompt=build_prompt(case, prompt_id),
                    )
                )
    return requests


def build_prompt(case: fixtures.FunctionCase, prompt_id: str) -> str:
    signature = cpu_smoke._function_signature(case.function_source)
    spec = CASE_SPECS[case.case_id]
    common = (
        "Return only one complete C11 function.\n"
        "Do not use markdown fences, explanations, comments, #include, main, or helper functions.\n"
        f"The function name and signature must be exactly: {signature}\n"
    )
    if prompt_id == "signature_spec":
        return (
            f"{common}\n"
            f"Behavior: {spec}\n\n"
            "Write the implementation now.\n"
        )
    if prompt_id == "strict_signature":
        return _strict_prompt(
            signature,
            f"Implement this behavior exactly: {spec}",
        )
    if prompt_id == "strict_rewrite":
        return _strict_prompt(
            signature,
            (
                "Write an equivalent implementation of the reference function. "
                "Keep the behavior exactly the same, but use simple clear C.\n\n"
                f"Reference function:\n{case.function_source.strip()}"
            ),
        )
    if prompt_id == "strict_bug":
        return _strict_prompt(
            signature,
            (
                "Write a compilable implementation with exactly one subtle semantic bug. "
                "It should look plausible and pass some obvious inputs, but it should not be fully correct.\n"
                f"Correct behavior: {spec}\n"
                f"Bug guidance: {BUG_HINTS[case.case_id]}\n\n"
                f"Reference function:\n{case.function_source.strip()}"
            ),
        )
    if prompt_id == "source_rewrite":
        return (
            f"{common}\n"
            "Rewrite the following function into an equivalent implementation with simple C code.\n"
            "Keep the behavior exactly the same.\n\n"
            f"{case.function_source.strip()}\n\n"
            "Output only the rewritten function.\n"
        )
    if prompt_id == "bug_seed":
        return (
            f"{common}\n"
            "Create a plausible implementation with one subtle semantic bug.\n"
            "The code should still compile and look like a realistic decompiler-style output.\n\n"
            f"Correct behavior: {spec}\n"
            f"Reference implementation:\n{case.function_source.strip()}\n\n"
            "Output only the buggy function.\n"
        )
    raise ValueError(f"unsupported prompt id: {prompt_id}")


def _strict_prompt(signature: str, task: str) -> str:
    return (
        "Print C code only. No markdown, no prose, no comments.\n"
        "The first line of your answer must be exactly:\n"
        f"{signature} {{\n\n"
        "Forbidden: #include, main, helper functions, tests, examples, ellipsis (...), "
        "abs/labs/llabs, undeclared variables, labels, gotos.\n"
        "Use only C11 integer arithmetic, if/else, while/for loops, assignments, and return.\n\n"
        f"{task}\n\n"
        "Now print exactly one complete function and nothing else.\n"
    )


def extract_expected_c_function(
    raw_text: str,
    case: fixtures.FunctionCase,
) -> CleaningResult:
    if not raw_text.strip():
        return CleaningResult("empty_output", "", "raw output is empty")

    statuses: list[str] = []
    for candidate_text in _candidate_texts(raw_text):
        result = _extract_from_text(candidate_text, case)
        if result.status == "parsed_function":
            return result
        statuses.append(result.status)
    reason = "no candidate text yielded exactly one allowed function"
    if statuses:
        reason = f"tried statuses: {', '.join(statuses[:5])}"
    return CleaningResult("parse_failed", "", reason)


def summarize_gpu_smoke(
    output_dir: Path,
    output_json: Path,
    output_md: Path,
    output_zh: Path,
    manifest_path: Path,
    generation_path: Path,
    records_path: Path,
    generation_records: list[dict[str, Any]],
    records: list[dict[str, Any]],
    model_info: dict[str, Any],
) -> dict[str, Any]:
    behavior_label_counts = {
        "faithful": sum(1 for record in records if record["label"] == "faithful"),
        "plausible_wrong": sum(1 for record in records if record["label"] == "plausible_wrong"),
        "compile_fail": sum(1 for record in records if record["label"] == "compile_fail"),
    }
    eval_records = [
        record for record in records
        if record["label"] in {"faithful", "plausible_wrong"} and "features" in record
    ]
    case_label_counts = _case_label_counts(records)
    paired_case_count = sum(
        1
        for counts in case_label_counts.values()
        if counts.get("faithful", 0) >= 1 and counts.get("plausible_wrong", 0) >= 1
    )
    fixture_collapse = v1._fixture_collapse(eval_records)
    trace_pairwise_auc = v1._pairwise_auc(
        eval_records,
        lambda record: float(record["features"]["trace_mismatch_rate"]),
    )
    parsed_count = sum(
        1 for record in generation_records
        if record["cleaning_status"] == "parsed_function"
    )
    compile_pass_count = sum(1 for record in records if record["compiled"])
    generation_count = len(generation_records)
    parsed_rate = parsed_count / generation_count if generation_count else 0.0
    compile_rate = compile_pass_count / parsed_count if parsed_count else 0.0
    gpu_smoke_gate_passed = (
        bool(model_info.get("model_loaded"))
        and bool(generation_records)
        and parsed_count >= 1
        and compile_pass_count >= 1
        and bool(records)
    )
    label_diversity_gate_passed = (
        behavior_label_counts["faithful"] >= 1
        and behavior_label_counts["plausible_wrong"] >= 1
    )
    paired_generation_gate_passed = (
        paired_case_count >= 2
        and compile_rate >= 0.50
        and parsed_rate >= 0.50
    )
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "manifest_path": str(manifest_path),
        "generation_metadata_path": str(generation_path),
        "records_path": str(records_path),
        "model_info": model_info,
        "generation_count": generation_count,
        "parsed_count": parsed_count,
        "parsed_rate": parsed_rate,
        "candidate_count": len(records),
        "compile_pass_count": compile_pass_count,
        "compile_rate_among_parsed": compile_rate,
        "behavior_label_counts": behavior_label_counts,
        "case_label_counts": case_label_counts,
        "paired_case_count": paired_case_count,
        "fixture_collapse": fixture_collapse,
        "trace_metrics_interpretable": paired_case_count >= 1,
        "trace_pairwise_auc": trace_pairwise_auc,
        "gpu_smoke_gate_passed": gpu_smoke_gate_passed,
        "label_diversity_gate_passed": label_diversity_gate_passed,
        "paired_generation_gate_passed": paired_generation_gate_passed,
        "cleaning_status_counts": _count_by(generation_records, "cleaning_status"),
        "generation_error_count": sum(
            1 for record in generation_records if record.get("generation_error")
        ),
    }
    _write_json(output_json, summary)
    _write_markdown(output_md, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def _candidate_texts(raw_text: str) -> list[str]:
    fenced = re.findall(r"```(?:c|C|cpp|C\+\+)?\s*(.*?)```", raw_text, flags=re.DOTALL)
    texts = [text.strip() for text in fenced if text.strip()]
    texts.append(raw_text.strip())
    return texts


def _extract_from_text(text: str, case: fixtures.FunctionCase) -> CleaningResult:
    if re.search(r"^\s*#", text, flags=re.MULTILINE):
        return CleaningResult("rejected_preprocessor", "", "preprocessor directive found")
    if re.search(r"\bmain\s*\(", text):
        return CleaningResult("rejected_main", "", "main function found")

    starts = [
        match.start()
        for match in re.finditer(rf"\bint\s+{re.escape(case.function_name)}\s*\(", text)
    ]
    if not starts:
        return CleaningResult("missing_expected_function", "", "expected function not found")
    if len(starts) > 1:
        return CleaningResult("multiple_expected_functions", "", "expected function appears multiple times")

    header_start = starts[0]
    open_brace = text.find("{", header_start)
    if open_brace == -1:
        return CleaningResult("missing_body", "", "function body opening brace not found")
    close_brace = _matching_brace(text, open_brace)
    if close_brace is None:
        return CleaningResult("unbalanced_braces", "", "function braces are unbalanced")

    function_source = text[header_start:close_brace + 1].strip() + "\n"
    if "..." in function_source:
        return CleaningResult("rejected_ellipsis", "", "ellipsis placeholder found")
    if re.search(r"\b(?:abs|labs|llabs)\s*\(", function_source):
        return CleaningResult("rejected_library_call", "", "forbidden library call found")
    if _function_definition_count(function_source) != 1:
        return CleaningResult("multiple_functions", "", "extracted source has multiple function definitions")
    surrounding = (text[:header_start] + "\n" + text[close_brace + 1:]).strip()
    if surrounding and _function_definition_count(surrounding) > 0:
        return CleaningResult("extra_helper_function", "", "extra helper function found")
    return CleaningResult("parsed_function", function_source, "")


def _matching_brace(text: str, open_brace: int) -> int | None:
    depth = 0
    for index in range(open_brace, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _function_definition_count(text: str) -> int:
    return len(
        re.findall(
            r"\b(?:int|void|long|short|char|float|double)\s+\w+\s*\([^;{}]*\)\s*\{",
            text,
        )
    )


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _case_label_counts(records: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for record in records:
        case_counts = counts.setdefault(
            record["case_id"],
            {"faithful": 0, "plausible_wrong": 0, "compile_fail": 0},
        )
        label = record["label"]
        case_counts[label] = case_counts.get(label, 0) + 1
    return counts


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 2 GPU Smoke",
        "",
        f"- GPU smoke gate passed: `{payload['gpu_smoke_gate_passed']}`",
        f"- Label diversity gate passed: `{payload['label_diversity_gate_passed']}`",
        f"- Paired generation gate passed: `{payload['paired_generation_gate_passed']}`",
        f"- Model loaded: `{payload['model_info']['model_loaded']}`",
        f"- Device: `{payload['model_info']['device']}`",
        f"- Generations: `{payload['generation_count']}`",
        f"- Parsed candidates: `{payload['parsed_count']}`",
        f"- Parsed rate: `{payload['parsed_rate']:.4f}`",
        f"- Evaluated candidates: `{payload['candidate_count']}`",
        f"- Compile pass count: `{payload['compile_pass_count']}`",
        f"- Compile rate among parsed: `{payload['compile_rate_among_parsed']:.4f}`",
        f"- Behavior labels: `{payload['behavior_label_counts']}`",
        f"- Paired cases for trace AUC: `{payload['paired_case_count']}`",
        f"- Trace metrics interpretable: `{payload['trace_metrics_interpretable']}`",
        f"- Cleaning statuses: `{payload['cleaning_status_counts']}`",
        f"- Fixture collapse: `{payload['fixture_collapse']}`",
        f"- Trace pairwise AUC: `{payload['trace_pairwise_auc']:.4f}`",
        "",
        "Raw outputs and prompt files are preserved under the output directory.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_markdown_zh(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 2 GPU Smoke",
        "",
        f"- GPU smoke gate passed: `{payload['gpu_smoke_gate_passed']}`",
        f"- Label diversity gate passed: `{payload['label_diversity_gate_passed']}`",
        f"- Paired generation gate passed: `{payload['paired_generation_gate_passed']}`",
        f"- Model loaded: `{payload['model_info']['model_loaded']}`",
        f"- Device: `{payload['model_info']['device']}`",
        f"- Generations: `{payload['generation_count']}`",
        f"- Parsed candidates: `{payload['parsed_count']}`",
        f"- Parsed rate: `{payload['parsed_rate']:.4f}`",
        f"- Evaluated candidates: `{payload['candidate_count']}`",
        f"- Compile pass count: `{payload['compile_pass_count']}`",
        f"- Compile rate among parsed: `{payload['compile_rate_among_parsed']:.4f}`",
        f"- Behavior labels: `{payload['behavior_label_counts']}`",
        f"- Paired cases for trace AUC: `{payload['paired_case_count']}`",
        f"- Trace metrics interpretable: `{payload['trace_metrics_interpretable']}`",
        f"- Cleaning statuses: `{payload['cleaning_status_counts']}`",
        f"- Fixture collapse: `{payload['fixture_collapse']}`",
        f"- Trace pairwise AUC: `{payload['trace_pairwise_auc']:.4f}`",
        "",
        "raw output 和 prompt 文件都保存在 output directory 下，便于失败归因。脚本不会设置 `CUDA_VISIBLE_DEVICES`；实际约束由 `--device cuda:2` 和显式 `.to(device)` 完成。",
        "",
        "如果 `Paired cases for trace AUC` 为 0，则当前样本还没有同一 case 内的 faithful/wrong 配对，`fixture_collapse` 和 `trace_pairwise_auc` 只能作为占位统计，不能解读为 Dynamic Trace v2 失败。",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


class _DreamCoderGenerator:
    def __init__(self, model_path: Path, device: str, torch_dtype: str, seed: int) -> None:
        self.model_path = model_path
        self.device = device
        self.torch_dtype = torch_dtype
        self.seed = seed
        self.model: Any = None
        self.tokenizer: Any = None
        self.torch: Any = None

    def load(self) -> None:  # pragma: no cover - exercised only with local GPU/model.
        import torch
        from transformers import AutoModel, AutoTokenizer

        if not self.model_path.exists():
            raise FileNotFoundError(f"model path not found: {self.model_path}")
        device_obj = torch.device(self.device)
        if device_obj.type != "cuda" or not torch.cuda.is_available():
            raise RuntimeError(f"requested CUDA device is not available: {self.device}")
        torch.cuda.set_device(device_obj)
        torch.manual_seed(self.seed)
        torch.cuda.manual_seed_all(self.seed)
        kwargs: dict[str, Any] = {
            "trust_remote_code": True,
            "local_files_only": True,
        }
        dtype = _resolve_torch_dtype(torch, self.torch_dtype)
        if dtype is not None:
            kwargs["torch_dtype"] = dtype
        self.tokenizer = AutoTokenizer.from_pretrained(
            str(self.model_path),
            trust_remote_code=True,
            local_files_only=True,
        )
        self.model = AutoModel.from_pretrained(str(self.model_path), **kwargs)
        self.model.to(device_obj)
        self.model.eval()
        self.torch = torch

    def generate(
        self,
        prompt: str,
        max_new_tokens: int,
        steps: int,
        temperature: float,
        top_p: float,
    ) -> tuple[str, dict[str, Any]]:  # pragma: no cover - exercised only with local GPU/model.
        if self.model is None or self.tokenizer is None or self.torch is None:
            raise RuntimeError("generator is not loaded")
        input_text = _format_for_tokenizer(self.tokenizer, prompt)
        inputs = self.tokenizer(input_text, return_tensors="pt")
        device_obj = self.torch.device(self.device)
        input_ids = inputs["input_ids"].to(device_obj)
        attention_mask = inputs.get("attention_mask")
        if attention_mask is not None:
            attention_mask = attention_mask.to(device_obj)
        input_len = int(input_ids.shape[-1])
        if not hasattr(self.model, "diffusion_generate"):
            raise RuntimeError("model does not expose diffusion_generate")
        with self.torch.inference_mode():
            output_ids = self.model.diffusion_generate(
                inputs=input_ids,
                attention_mask=attention_mask,
                max_new_tokens=max_new_tokens,
                steps=steps,
                temperature=temperature,
                top_p=top_p,
            )
        if isinstance(output_ids, tuple):
            output_ids = output_ids[0]
        if output_ids.dim() == 1:
            output_ids = output_ids.unsqueeze(0)
        output_len = int(output_ids.shape[-1])
        if output_len > input_len:
            generated_ids = output_ids[0, input_len:]
        else:
            generated_ids = output_ids[0]
        raw_text = self.tokenizer.decode(generated_ids, skip_special_tokens=True)
        return raw_text, {
            "input_token_count": input_len,
            "output_token_count": output_len,
            "decoded_token_count": int(generated_ids.shape[-1]),
        }

    def unload(self) -> None:  # pragma: no cover - exercised only with local GPU/model.
        if self.model is not None:
            del self.model
        if self.tokenizer is not None:
            del self.tokenizer
        if self.torch is not None and self.torch.cuda.is_available():
            self.torch.cuda.empty_cache()
        self.model = None
        self.tokenizer = None


def _format_for_tokenizer(tokenizer: Any, prompt: str) -> str:
    chat_template = getattr(tokenizer, "chat_template", None)
    if chat_template and hasattr(tokenizer, "apply_chat_template"):
        return tokenizer.apply_chat_template(
            [{"role": "user", "content": prompt}],
            tokenize=False,
            add_generation_prompt=True,
        )
    return prompt


def _resolve_torch_dtype(torch: Any, torch_dtype: str) -> Any:
    if torch_dtype == "auto":
        return None
    return {
        "float16": torch.float16,
        "bfloat16": torch.bfloat16,
        "float32": torch.float32,
    }[torch_dtype]


if __name__ == "__main__":
    main()
