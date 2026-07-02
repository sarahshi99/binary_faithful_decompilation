from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_phase2_cpu_smoke as cpu_smoke
from analysis.decompile_faithfulness import run_phase2_gpu_smoke as phase2_gpu
from analysis.decompile_faithfulness import run_phase3_combinatorial_cpu_audit as phase3_cpu


DEFAULT_MODEL_PATH = phase2_gpu.DEFAULT_MODEL_PATH
DEFAULT_SOURCE_POOL = Path("docs/paper_agent/decompile_faithfulness_phase3_source_pool.json")
DEFAULT_SOURCE_SELECTION = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_source_selection.json"
)
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase3_gpu_generated_smoke")
DEFAULT_OUTPUT_JSON = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_gpu_generated_smoke.json"
)
DEFAULT_OUTPUT_ZH = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_gpu_generated_smoke.zh.md"
)
DEFAULT_PROMPT_IDS = ["strict_rewrite", "strict_bug"]
SUPPORTED_PROMPT_IDS = {"strict_rewrite", "strict_bug"}

CASE_SPECS = {
    "bounded_abs100": "Return abs(x), but saturate the result at 100.",
    "sat_add8": "Return a + b clamped into the inclusive range 0..255.",
    "within_range_inclusive": "Return 1 exactly when lo <= x <= hi, otherwise return 0.",
    "parity8": "Return the parity bit of the low 8 bits of x.",
    "high_nibble": "Return bits 4..7 of x as a value in 0..15.",
    "gcd_nonnegative": "Return gcd(abs(a), abs(b)); gcd(0, 0) is 0.",
    "mod3_sum_digits": "Return the sum of decimal digits of abs(n), reduced modulo 3.",
    "days_before_month": "Return days before the given month in a non-leap year; <=1 maps to 0 and >12 maps to 365.",
    "triangle_wave10": "Return a nonnegative triangle wave with period 20 and peak 10.",
    "safe_div_round0": "Return 0 when b == 0, otherwise return C integer division a / b.",
    "clamp_then_square": "Clamp x into -10..10, then return x squared.",
    "popcount_nibble_diff": "Return popcount(low_nibble(a)) - popcount(low_nibble(b)).",
}

BUG_HINTS = {
    "bounded_abs100": "Mishandle one saturation boundary.",
    "sat_add8": "Mishandle total == 256 or one saturation direction.",
    "within_range_inclusive": "Use an exclusive comparison or mix up an endpoint.",
    "parity8": "Count the wrong bit width.",
    "high_nibble": "Extract the wrong nibble or mishandle signed values.",
    "gcd_nonnegative": "Forget one sign normalization or return the wrong loop variable.",
    "mod3_sum_digits": "Mishandle negative numbers or the final modulus.",
    "days_before_month": "Use one wrong month length or boundary rule.",
    "triangle_wave10": "Mishandle negative inputs or the period boundary.",
    "safe_div_round0": "Mishandle division by zero or divisor 1.",
    "clamp_then_square": "Forget one clamp side.",
    "popcount_nibble_diff": "Swap the arguments or count the wrong number of bits.",
}


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
        repo_root=args.repo_root,
        source_pool=args.source_pool,
        source_selection=args.source_selection,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        model_path=args.model_path,
        device=args.device,
        case_ids=args.case_id,
        prompt_ids=args.prompt_id,
        subset_rank=args.subset_rank,
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
                "behavior_label_counts": summary["behavior_label_counts"],
                "model_loaded": summary["model_info"]["model_loaded"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--source-pool", type=Path, default=DEFAULT_SOURCE_POOL)
    parser.add_argument("--source-selection", type=Path, default=DEFAULT_SOURCE_SELECTION)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--model-path", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--device", default="cuda:2")
    parser.add_argument("--case-id", action="append", default=None)
    parser.add_argument("--prompt-id", action="append", default=None)
    parser.add_argument("--subset-rank", type=int, default=1)
    parser.add_argument("--candidates-per-prompt", type=int, default=1)
    parser.add_argument("--max-new-tokens", type=int, default=180)
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
    repo_root: Path,
    source_pool: Path,
    source_selection: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    model_path: Path = DEFAULT_MODEL_PATH,
    device: str = "cuda:2",
    case_ids: list[str] | None = None,
    prompt_ids: list[str] | None = None,
    subset_rank: int = 1,
    candidates_per_prompt: int = 1,
    max_new_tokens: int = 180,
    steps: int = 32,
    temperature: float = 0.0,
    top_p: float = 1.0,
    torch_dtype: str = "auto",
    seed: int = 20260618,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    source_pool = _resolve(repo_root, source_pool)
    source_selection = _resolve(repo_root, source_selection)
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    model_path = _resolve(repo_root, model_path)

    prompt_ids = prompt_ids or DEFAULT_PROMPT_IDS
    for prompt_id in prompt_ids:
        if prompt_id not in SUPPORTED_PROMPT_IDS:
            raise ValueError(f"unsupported prompt id: {prompt_id}")

    cases = _load_cases(repo_root, source_pool)
    if case_ids is None:
        case_ids = _case_ids_from_subset(source_selection, subset_rank)
    selected_cases = {case_id: cases[case_id] for case_id in case_ids}

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    prompt_dir = output_dir / "prompts"
    trace_dir = output_dir / "traces"
    for path in [raw_dir, prompt_dir, trace_dir]:
        path.mkdir(parents=True, exist_ok=True)

    generation_path = output_dir / "generation_metadata.jsonl"
    records_path = output_dir / "records.jsonl"
    requests = build_generation_requests(
        selected_cases,
        prompt_ids,
        candidates_per_prompt,
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
        case = selected_cases[request.case_id]
        cleaning = phase2_gpu.extract_expected_c_function(raw_text, case)
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
            features = phase3_cpu._dynamic_trace_v3_features(
                case=case,
                candidate_id=request.candidate_id,
                candidate_source=cleaning.function_source,
                trace_dir=trace_dir,
            )
            records.append(
                _record_from_features(
                    request,
                    cleaning.function_source,
                    features,
                    metadata,
                )
            )
    _write_jsonl(generation_path, generation_records)
    _write_jsonl(records_path, records)
    summary = summarize(
        output_dir=output_dir,
        output_json=output_json,
        output_zh=output_zh,
        generation_path=generation_path,
        records_path=records_path,
        generation_records=generation_records,
        records=records,
        model_info=model_info,
        case_ids=case_ids,
        prompt_ids=prompt_ids,
    )
    generator.unload()
    return summary


def build_generation_requests(
    cases: dict[str, fixtures.FunctionCase],
    prompt_ids: list[str],
    candidates_per_prompt: int,
) -> list[GenerationRequest]:
    requests: list[GenerationRequest] = []
    for case_id, case in cases.items():
        for prompt_id in prompt_ids:
            for generation_index in range(candidates_per_prompt):
                candidate_id = f"phase3_gpu_{case_id}_{prompt_id}_{generation_index:02d}"
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
    if prompt_id == "strict_rewrite":
        task = (
            "Write an equivalent implementation of the reference function. "
            "Keep the behavior exactly the same, but use simple clear C.\n\n"
            f"Reference function:\n{case.function_source.strip()}"
        )
    elif prompt_id == "strict_bug":
        task = (
            "Write a compilable implementation with exactly one subtle semantic bug. "
            "It should look plausible and pass some obvious inputs, but it should not be fully correct.\n"
            f"Correct behavior: {spec}\n"
            f"Bug guidance: {BUG_HINTS[case.case_id]}\n\n"
            f"Reference function:\n{case.function_source.strip()}"
        )
    else:
        raise ValueError(f"unsupported prompt id: {prompt_id}")
    return phase2_gpu._strict_prompt(signature, task)


def summarize(
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    generation_path: Path,
    records_path: Path,
    generation_records: list[dict[str, Any]],
    records: list[dict[str, Any]],
    model_info: dict[str, Any],
    case_ids: list[str],
    prompt_ids: list[str],
) -> dict[str, Any]:
    parsed_count = sum(
        1 for record in generation_records
        if record["cleaning_status"] == "parsed_function"
    )
    compile_pass_count = sum(1 for record in records if record["compiled"])
    behavior_label_counts = {
        "faithful": sum(1 for record in records if record["label"] == "faithful"),
        "plausible_wrong": sum(1 for record in records if record["label"] == "plausible_wrong"),
        "compile_fail": sum(1 for record in records if record["label"] == "compile_fail"),
    }
    eval_records = [
        record for record in records
        if record["label"] in {"faithful", "plausible_wrong"}
    ]
    paired_case_count = sum(
        1
        for case_id in case_ids
        if any(record["case_id"] == case_id and record["label"] == "faithful" for record in records)
        and any(record["case_id"] == case_id and record["label"] == "plausible_wrong" for record in records)
    )
    trace_pairwise_auc = phase3_cpu._pairwise_auc(eval_records, phase3_cpu._trace_score)
    fixture_collapse = phase3_cpu.v1._fixture_collapse(eval_records)
    summary = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "generation_metadata_path": str(generation_path),
        "records_path": str(records_path),
        "case_ids": case_ids,
        "prompt_ids": prompt_ids,
        "model_info": model_info,
        "generation_count": len(generation_records),
        "parsed_count": parsed_count,
        "parsed_rate": parsed_count / len(generation_records) if generation_records else 0.0,
        "candidate_count": len(records),
        "compile_pass_count": compile_pass_count,
        "compile_rate_among_parsed": compile_pass_count / parsed_count if parsed_count else 0.0,
        "behavior_label_counts": behavior_label_counts,
        "paired_case_count": paired_case_count,
        "trace_pairwise_auc": trace_pairwise_auc,
        "fixture_collapse": fixture_collapse,
        "cleaning_status_counts": _count_by(generation_records, "cleaning_status"),
    }
    summary["verdict"] = _verdict(summary)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def _record_from_features(
    request: GenerationRequest,
    function_source: str,
    features: dict[str, float],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if features["compiled"] != 1.0:
        label = "compile_fail"
    elif features["fixture_mismatch_rate"] == 0.0:
        label = "faithful"
    else:
        label = "plausible_wrong"
    return {
        "case_id": request.case_id,
        "candidate_id": request.candidate_id,
        "label": label,
        "mutation_type": f"phase3_gpu_{request.prompt_id}",
        "compiled": features["compiled"] == 1.0,
        "behavior_passed": features["fixture_mismatch_rate"] == 0.0,
        "features": {
            key: value
            for key, value in features.items()
            if key not in {"compiled", "primary_exit_code", "fixture_exit_code"}
        },
        "metadata": {
            **metadata,
            "function_source": function_source,
        },
    }


def _load_cases(repo_root: Path, source_pool: Path) -> dict[str, fixtures.FunctionCase]:
    pool = json.loads(source_pool.read_text(encoding="utf-8"))
    return {
        entry["case_id"]: phase3_cpu._case_from_pool_entry(repo_root, entry)
        for entry in pool["functions"]
    }


def _case_ids_from_subset(source_selection: Path, subset_rank: int) -> list[str]:
    selection = json.loads(source_selection.read_text(encoding="utf-8"))
    subsets = selection.get("recommended_subsets", [])
    if not 1 <= subset_rank <= len(subsets):
        raise ValueError(f"subset rank out of range: {subset_rank}")
    return list(subsets[subset_rank - 1]["case_ids"])


def _verdict(summary: dict[str, Any]) -> str:
    if not summary["model_info"].get("model_loaded"):
        return "gpu-model-not-loaded"
    if summary["parsed_count"] < 1 or summary["compile_pass_count"] < 1:
        return "needs-generation-cleaning"
    if summary["paired_case_count"] >= 1 and not summary["fixture_collapse"]:
        return "pass-phase3-gpu-generated-smoke"
    return "needs-more-phase3-gpu-generated-samples"


def _count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _write_markdown_zh(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 3 GPU Generated Smoke",
        "",
        f"- Verdict: `{summary['verdict']}`",
        f"- Model loaded: `{summary['model_info']['model_loaded']}`",
        f"- Device: `{summary['model_info']['device']}`",
        f"- Cases: `{summary['case_ids']}`",
        f"- Prompt IDs: `{summary['prompt_ids']}`",
        f"- Generations: `{summary['generation_count']}`",
        f"- Parsed candidates: `{summary['parsed_count']}`",
        f"- Parsed rate: `{summary['parsed_rate']:.4f}`",
        f"- Evaluated candidates: `{summary['candidate_count']}`",
        f"- Compile pass count: `{summary['compile_pass_count']}`",
        f"- Compile rate among parsed: `{summary['compile_rate_among_parsed']:.4f}`",
        f"- Behavior labels: `{summary['behavior_label_counts']}`",
        f"- Paired case count: `{summary['paired_case_count']}`",
        f"- Trace pairwise AUC: `{summary['trace_pairwise_auc']:.4f}`",
        f"- Fixture collapse: `{summary['fixture_collapse']}`",
        f"- Cleaning statuses: `{summary['cleaning_status_counts']}`",
        f"- Records: `{summary['records_path']}`",
        "",
        "脚本不会设置 `CUDA_VISIBLE_DEVICES`；只通过 `--device cuda:2` 或 `--device cuda:3` 显式放置模型和输入。运行前仍必须检查 GPU 2/3 是否不会干扰他人任务。",
        "",
    ]
    if summary["model_info"].get("model_error"):
        lines.extend(["## Model Error", "", f"`{summary['model_info']['model_error']}`", ""])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
