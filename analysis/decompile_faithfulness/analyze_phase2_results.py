from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable


DEFAULT_RECORDS = Path(
    "analysis_outputs/decompile_faithfulness/phase2_gpu_full_v1_plus_topup/records.jsonl"
)
DEFAULT_GENERATIONS = Path(
    "analysis_outputs/decompile_faithfulness/phase2_gpu_full_v1_plus_topup/generation_metadata.jsonl"
)
DEFAULT_MANIFEST = Path(
    "analysis_outputs/decompile_faithfulness/phase2_gpu_full_v1_plus_topup/manifest.json"
)


def main() -> None:
    args = parse_args()
    summary = analyze_phase2_results(
        records_jsonl=args.records_jsonl,
        generation_metadata_jsonl=args.generation_metadata_jsonl,
        manifest_json=args.manifest_json,
        output_json=args.output_json,
        output_zh=args.output_zh,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "case_count": summary["overall"]["case_count"],
                "compile_pass_count": summary["overall"]["compile_pass_count"],
                "paired_case_count": summary["overall"]["paired_case_count"],
                "trace_pairwise_auc": summary["overall"]["trace_pairwise_auc"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-jsonl", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--generation-metadata-jsonl", type=Path, default=DEFAULT_GENERATIONS)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_result_analysis.json"),
    )
    parser.add_argument(
        "--output-zh",
        type=Path,
        default=Path("docs/paper_agent/decompile_faithfulness_phase2_result_analysis.zh.md"),
    )
    return parser.parse_args()


def analyze_phase2_results(
    records_jsonl: Path,
    generation_metadata_jsonl: Path,
    manifest_json: Path,
    output_json: Path,
    output_zh: Path,
) -> dict[str, Any]:
    records = _read_jsonl(records_jsonl)
    generations = _read_jsonl(generation_metadata_jsonl)
    manifest = _read_json(manifest_json) if manifest_json.exists() else []
    summary = build_summary(records, generations, records_jsonl, generation_metadata_jsonl, manifest)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def build_summary(
    records: list[dict[str, Any]],
    generations: list[dict[str, Any]],
    records_jsonl: Path | None = None,
    generation_metadata_jsonl: Path | None = None,
    manifest: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    eval_records = [record for record in records if _is_eval_record(record)]
    source_by_candidate = _source_by_candidate(manifest or [])
    case_table = _case_table(records, generations)
    prompt_table = _prompt_table(records, generations)
    overall_auc = _pairwise_auc(eval_records, _trace_score)
    full_gate = _full_gate(case_table, overall_auc)
    summary = {
        "records_path": str(records_jsonl) if records_jsonl else "",
        "generation_metadata_path": str(generation_metadata_jsonl) if generation_metadata_jsonl else "",
        "verdict": "pass-phase2-result-analysis" if full_gate["passed"] else "needs-more-analysis",
        "overall": {
            "generation_count": len(generations),
            "parsed_count": sum(1 for row in generations if row.get("cleaning_status") == "parsed_function"),
            "candidate_count": len(records),
            "compile_pass_count": len(eval_records),
            "label_counts": dict(Counter(record["label"] for record in records)),
            "case_count": len({record["case_id"] for record in records}),
            "paired_case_count": sum(1 for row in case_table.values() if row["paired"]),
            "trace_pairwise_auc": overall_auc,
            "fixture_collapse": _fixture_collapse(eval_records),
            "fixture_passing_trace_mismatch_count": _fixture_passing_trace_mismatch_count(eval_records),
            "trace_total_by_label": {
                label: _score_summary(
                    [_trace_score(record) for record in eval_records if record["label"] == label]
                )
                for label in ["faithful", "plausible_wrong"]
            },
            "trace_mismatch_by_label": {
                label: _score_summary(
                    [
                        float(record["features"].get("trace_mismatch_rate", 0.0))
                        for record in eval_records
                        if record["label"] == label
                    ]
                )
                for label in ["faithful", "plausible_wrong"]
            },
        },
        "full_gate": full_gate,
        "case_table": case_table,
        "prompt_table": prompt_table,
        "failure_analysis": {
            "cleaning_status_counts": dict(Counter(row.get("cleaning_status", "") for row in generations)),
            "cleaning_reason_counts": dict(
                Counter(
                    row.get("cleaning_reason", "")
                    for row in generations
                    if row.get("cleaning_status") != "parsed_function"
                ).most_common()
            ),
            "compile_failure_categories": dict(
                Counter(_compile_failure_category(record) for record in records if record["label"] == "compile_fail")
            ),
            "runtime_timeout_count": sum(1 for record in records if int(record.get("exit_code", 0)) == 124),
        },
        "prompt_case_matrix": _prompt_case_matrix(records),
        "hard_examples": {
            "lowest_scored_wrong": _candidate_examples(
                [record for record in eval_records if record["label"] == "plausible_wrong"],
                key=_trace_score,
                reverse=False,
                limit=8,
                source_by_candidate=source_by_candidate,
            ),
            "highest_scored_faithful": _candidate_examples(
                [record for record in eval_records if record["label"] == "faithful"],
                key=_trace_score,
                reverse=True,
                limit=8,
                source_by_candidate=source_by_candidate,
            ),
            "fixture_passing_trace_mismatch": _candidate_examples(
                [
                    record for record in eval_records
                    if record["label"] == "faithful"
                    and float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0
                ],
                key=_trace_score,
                reverse=True,
                limit=8,
                source_by_candidate=source_by_candidate,
            ),
        },
        "paper_claim": {
            "supported": (
                "Dynamic Trace v2 remains highly discriminative on local-LLM generated "
                "source-known candidates for localized semantic bug auditing."
            ),
            "not_supported": (
                "This does not establish a general decompilation faithfulness verifier or "
                "real-project transfer."
            ),
        },
    }
    return summary


def _case_table(
    records: list[dict[str, Any]],
    generations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    records_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    generations_by_case: Counter[str] = Counter()
    parsed_by_case: Counter[str] = Counter()
    for record in records:
        records_by_case[record["case_id"]].append(record)
    for row in generations:
        generations_by_case[row["case_id"]] += 1
        if row.get("cleaning_status") == "parsed_function":
            parsed_by_case[row["case_id"]] += 1

    table: dict[str, dict[str, Any]] = {}
    for case_id in sorted(set(records_by_case) | set(generations_by_case)):
        case_records = records_by_case.get(case_id, [])
        eval_records = [record for record in case_records if _is_eval_record(record)]
        label_counts = Counter(record["label"] for record in case_records)
        faithful_scores = [_trace_score(record) for record in eval_records if record["label"] == "faithful"]
        wrong_scores = [_trace_score(record) for record in eval_records if record["label"] == "plausible_wrong"]
        pair_stats = _pair_stats(eval_records, _trace_score)
        table[case_id] = {
            "generations": generations_by_case[case_id],
            "parsed": parsed_by_case[case_id],
            "candidates": len(case_records),
            "compile_pass": len(eval_records),
            "labels": dict(label_counts),
            "paired": bool(faithful_scores and wrong_scores),
            "fixture_passing_trace_mismatch": _fixture_passing_trace_mismatch_count(eval_records),
            "pairwise_auc": pair_stats["auc"],
            "pair_count": pair_stats["pair_count"],
            "misordered_or_tied_pairs": pair_stats["misordered_or_tied_pairs"],
            "faithful_trace_total": _score_summary(faithful_scores),
            "wrong_trace_total": _score_summary(wrong_scores),
            "separation_margin": (
                min(wrong_scores) - max(faithful_scores)
                if faithful_scores and wrong_scores
                else None
            ),
        }
    return table


def _prompt_table(
    records: list[dict[str, Any]],
    generations: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    records_by_prompt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    generations_by_prompt: Counter[str] = Counter()
    parsed_by_prompt: Counter[str] = Counter()
    for record in records:
        records_by_prompt[_prompt_id(record)].append(record)
    for row in generations:
        prompt_id = str(row.get("prompt_id", ""))
        generations_by_prompt[prompt_id] += 1
        if row.get("cleaning_status") == "parsed_function":
            parsed_by_prompt[prompt_id] += 1

    table: dict[str, dict[str, Any]] = {}
    for prompt_id in sorted(set(records_by_prompt) | set(generations_by_prompt)):
        prompt_records = records_by_prompt.get(prompt_id, [])
        eval_records = [record for record in prompt_records if _is_eval_record(record)]
        label_counts = Counter(record["label"] for record in prompt_records)
        compile_pass = len(eval_records)
        table[prompt_id] = {
            "generations": generations_by_prompt[prompt_id],
            "parsed": parsed_by_prompt[prompt_id],
            "candidates": len(prompt_records),
            "compile_pass": compile_pass,
            "labels": dict(label_counts),
            "parsed_rate": _safe_div(parsed_by_prompt[prompt_id], generations_by_prompt[prompt_id]),
            "compile_rate_among_parsed": _safe_div(compile_pass, parsed_by_prompt[prompt_id]),
            "faithful_rate_among_compiled": _safe_div(label_counts.get("faithful", 0), compile_pass),
            "wrong_rate_among_compiled": _safe_div(label_counts.get("plausible_wrong", 0), compile_pass),
            "fixture_passing_trace_mismatch": _fixture_passing_trace_mismatch_count(eval_records),
            "trace_pairwise_auc": _pairwise_auc(eval_records, _trace_score),
        }
    return table


def _prompt_case_matrix(records: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, int]]]:
    matrix: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for record in records:
        matrix[record["case_id"]][_prompt_id(record)][record["label"]] += 1
    return {
        case_id: {
            prompt_id: dict(counts)
            for prompt_id, counts in sorted(prompt_counts.items())
        }
        for case_id, prompt_counts in sorted(matrix.items())
    }


def _full_gate(case_table: dict[str, dict[str, Any]], overall_auc: float) -> dict[str, Any]:
    compile_pass_by_case = {
        case_id: int(row["compile_pass"])
        for case_id, row in case_table.items()
    }
    paired_cases = [case_id for case_id, row in case_table.items() if row["paired"]]
    checks = {
        "all_8_cases_represented": len(case_table) == 8,
        "min_5_compile_pass_per_case": all(value >= 5 for value in compile_pass_by_case.values()),
        "at_least_5_paired_cases": len(paired_cases) >= 5,
        "all_cases_paired": len(paired_cases) == len(case_table),
        "trace_auc_at_least_0_9": overall_auc >= 0.9,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "compile_pass_by_case": compile_pass_by_case,
        "paired_cases": paired_cases,
    }


def _pairwise_auc(records: list[dict[str, Any]], score: Callable[[dict[str, Any]], float]) -> float:
    credit = 0.0
    pairs = 0
    records_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        records_by_case[record["case_id"]].append(record)
    for case_records in records_by_case.values():
        stats = _pair_stats(case_records, score)
        credit += stats["credit"]
        pairs += stats["pair_count"]
    return credit / pairs if pairs else 0.0


def _pair_stats(records: list[dict[str, Any]], score: Callable[[dict[str, Any]], float]) -> dict[str, Any]:
    faithful = [record for record in records if record["label"] == "faithful"]
    wrong = [record for record in records if record["label"] == "plausible_wrong"]
    correct = 0.0
    misordered_or_tied = 0
    pairs = 0
    for faithful_record in faithful:
        faithful_score = score(faithful_record)
        for wrong_record in wrong:
            pairs += 1
            wrong_score = score(wrong_record)
            if wrong_score > faithful_score:
                correct += 1.0
            elif wrong_score == faithful_score:
                correct += 0.5
                misordered_or_tied += 1
            else:
                misordered_or_tied += 1
    return {
        "auc": correct / pairs if pairs else 0.0,
        "credit": correct,
        "pair_count": pairs,
        "misordered_or_tied_pairs": misordered_or_tied,
    }


def _fixture_collapse(records: list[dict[str, Any]]) -> bool:
    if not records:
        return False
    return all(
        (record["features"].get("trace_mismatch_rate", 0.0) > 0.0)
        == (record["features"].get("fixture_mismatch_rate", 0.0) > 0.0)
        for record in records
    )


def _fixture_passing_trace_mismatch_count(records: list[dict[str, Any]]) -> int:
    return sum(
        1
        for record in records
        if record["label"] == "faithful"
        and float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0
    )


def _score_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": None, "median": None, "mean": None, "max": None}
    return {
        "count": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "max": max(values),
    }


def _candidate_examples(
    records: list[dict[str, Any]],
    key: Callable[[dict[str, Any]], float],
    reverse: bool,
    limit: int,
    source_by_candidate: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    examples = []
    for record in sorted(records, key=key, reverse=reverse)[:limit]:
        features = record.get("features", {})
        candidate_id = record["candidate_id"]
        examples.append(
            {
                "case_id": record["case_id"],
                "candidate_id": candidate_id,
                "prompt_id": _prompt_id(record),
                "label": record["label"],
                "trace_total": float(features.get("trace_total", 0.0)),
                "trace_mismatch_rate": float(features.get("trace_mismatch_rate", 0.0)),
                "fixture_mismatch_rate": float(features.get("fixture_mismatch_rate", 0.0)),
                "exit_code": record.get("exit_code"),
                "function_source": (source_by_candidate or {}).get(candidate_id, ""),
            }
        )
    return examples


def _source_by_candidate(manifest: list[dict[str, Any]]) -> dict[str, str]:
    return {
        candidate["candidate_id"]: candidate.get("function_source", "")
        for entry in manifest
        for candidate in entry.get("candidates", [])
    }


def _compile_failure_category(record: dict[str, Any]) -> str:
    stderr = str(record.get("compile_stderr", "")).lower()
    if "timed out" in stderr or int(record.get("exit_code", 0)) == 124:
        return "timeout"
    if "implicit declaration" in stderr or "undeclared" in stderr:
        return "undeclared_or_forbidden_call"
    if "expected" in stderr or "error:" in stderr:
        return "syntax_or_compile_error"
    if "control reaches end" in stderr:
        return "missing_return"
    return "other_compile_failure"


def _is_eval_record(record: dict[str, Any]) -> bool:
    return record["label"] in {"faithful", "plausible_wrong"} and "features" in record


def _trace_score(record: dict[str, Any]) -> float:
    return float(record["features"].get("trace_total", 0.0))


def _prompt_id(record: dict[str, Any]) -> str:
    return str(record.get("metadata", {}).get("prompt_id", ""))


def _safe_div(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown_zh(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 2 Result Analysis",
        "",
        f"- Verdict: `{summary['verdict']}`",
        f"- Generations: `{summary['overall']['generation_count']}`",
        f"- Parsed candidates: `{summary['overall']['parsed_count']}`",
        f"- Evaluated candidates: `{summary['overall']['candidate_count']}`",
        f"- Compile pass count: `{summary['overall']['compile_pass_count']}`",
        f"- Label counts: `{summary['overall']['label_counts']}`",
        f"- Paired cases: `{summary['overall']['paired_case_count']}` / `{summary['overall']['case_count']}`",
        f"- Fixture collapse: `{summary['overall']['fixture_collapse']}`",
        f"- Fixture-passing trace mismatches: `{summary['overall']['fixture_passing_trace_mismatch_count']}`",
        f"- Trace pairwise AUC: `{summary['overall']['trace_pairwise_auc']:.4f}`",
        "",
        "## Full Gate",
        "",
        f"- Passed: `{summary['full_gate']['passed']}`",
        f"- Checks: `{summary['full_gate']['checks']}`",
        f"- Compile pass by case: `{summary['full_gate']['compile_pass_by_case']}`",
        "",
        "## Case Table",
        "",
        "| Case | Gen | Parsed | Compiled | Labels | Hidden | AUC | Misordered/Tied | Margin |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|",
    ]
    for case_id, row in summary["case_table"].items():
        margin = row["separation_margin"]
        margin_text = "" if margin is None else f"{margin:.4f}"
        lines.append(
            "| "
            f"`{case_id}` | {row['generations']} | {row['parsed']} | {row['compile_pass']} | "
            f"`{row['labels']}` | {row['fixture_passing_trace_mismatch']} | {row['pairwise_auc']:.4f} | "
            f"{row['misordered_or_tied_pairs']} / {row['pair_count']} | {margin_text} |"
        )
    lines.extend([
        "",
        "## Prompt Table",
        "",
        "| Prompt | Gen | Parsed | Compiled | Labels | Hidden | Parsed Rate | Compile Rate | Faithful Rate | Wrong Rate |",
        "|---|---:|---:|---:|---|---:|---:|---:|---:|---:|",
    ])
    for prompt_id, row in summary["prompt_table"].items():
        lines.append(
            "| "
            f"`{prompt_id}` | {row['generations']} | {row['parsed']} | {row['compile_pass']} | "
            f"`{row['labels']}` | {row['fixture_passing_trace_mismatch']} | {row['parsed_rate']:.4f} | "
            f"{row['compile_rate_among_parsed']:.4f} | "
            f"{row['faithful_rate_among_compiled']:.4f} | "
            f"{row['wrong_rate_among_compiled']:.4f} |"
        )
    lines.extend([
        "",
        "## Failure Analysis",
        "",
        f"- Cleaning status counts: `{summary['failure_analysis']['cleaning_status_counts']}`",
        f"- Cleaning reason counts: `{summary['failure_analysis']['cleaning_reason_counts']}`",
        f"- Compile failure categories: `{summary['failure_analysis']['compile_failure_categories']}`",
        f"- Runtime timeout count: `{summary['failure_analysis']['runtime_timeout_count']}`",
        "",
        "## Hard Examples",
        "",
        "Lowest-scored plausible wrong candidates:",
        "",
    ])
    for example in summary["hard_examples"]["lowest_scored_wrong"]:
        lines.append(
            f"- `{example['case_id']}` `{example['prompt_id']}` "
            f"`{example['candidate_id']}`: trace_total `{example['trace_total']:.4f}`, "
            f"trace_mismatch `{example['trace_mismatch_rate']:.4f}`, fixture_mismatch `{example['fixture_mismatch_rate']:.4f}`"
        )
    lines.extend(["", "Highest-scored faithful candidates:", ""])
    for example in summary["hard_examples"]["highest_scored_faithful"]:
        lines.append(
            f"- `{example['case_id']}` `{example['prompt_id']}` "
            f"`{example['candidate_id']}`: trace_total `{example['trace_total']:.4f}`, "
            f"trace_mismatch `{example['trace_mismatch_rate']:.4f}`, fixture_mismatch `{example['fixture_mismatch_rate']:.4f}`"
        )
    lines.extend(["", "Fixture-passing but trace-mismatching candidates:", ""])
    for example in summary["hard_examples"]["fixture_passing_trace_mismatch"]:
        lines.append(
            f"- `{example['case_id']}` `{example['prompt_id']}` "
            f"`{example['candidate_id']}`: trace_total `{example['trace_total']:.4f}`, "
            f"trace_mismatch `{example['trace_mismatch_rate']:.4f}`, fixture_mismatch `{example['fixture_mismatch_rate']:.4f}`"
        )
        if example.get("function_source"):
            lines.extend(["", "```c", example["function_source"].rstrip(), "```", ""])
    lines.extend([
        "",
        "## Qualitative Findings",
        "",
        "- Positive non-oracle example: `count_bits8` generated a fixture-passing implementation that counts 16 low bits instead of 8. The original fixture did not expose this because its tested values stay within the low-byte regime; Dynamic Trace v2 exposed the semantic drift on broader generated inputs.",
        "- Boundary blind spot: the lowest-scored wrong examples include `signum` and `is_power_of_two` bugs around zero. These were caught by the fixture behavior gate but received trace_total `0.0000`, which means the primary generated trace set did not sufficiently cover those exact boundary inputs. A future v3 should fold fixture/boundary mismatch into the primary score or force zero-boundary coverage per domain.",
        "",
        "## Interpretation",
        "",
        "Phase 2 结果支持一个收窄但可防守的结论：在 source-known、小函数、bounded generated inputs 的 localized semantic bug auditing 设置下，Dynamic Trace v2 对本地 LLM 生成候选仍保持强区分度。",
        "",
        "`faithful` 在这批实验中表示 fixture behavior gate 通过，不等于完整语义真值。报告中的 `Fixture-passing trace mismatches` 是最重要的 non-oracle 证据：这些候选通过了原 fixture，但在更宽的 generated trace inputs 上和源函数不一致。",
        "",
        "这不支持 general decompilation faithfulness verifier，也不支持 real-project transfer。当前证据更适合写成：generated candidates 让 candidate distribution 更 realistic，而 Dynamic Trace v2 在这个分布上没有退化成 fixture-only oracle。",
        "",
        "下一步不应继续堆 GPU 生成量。更有价值的是写 Phase 2 result table、case-level qualitative analysis、failure attribution，并设计一个小的 Phase 3 real-project-transfer readiness check。",
        "",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
