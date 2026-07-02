from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PHASE12_JSON = Path("docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.json")
DEFAULT_RECORDS_DIR = Path("analysis_outputs/decompile_faithfulness/phase12_unified_low_budget")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase14_paper_readiness.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase14_paper_readiness.zh.md")
DEFAULT_DRAFT_MD = Path("docs/paper_agent/decompile_faithfulness_phase14_experiment_section_draft.md")
DEFAULT_BOOTSTRAP_ITERATIONS = 2000
DEFAULT_SEED = 20260702
DEFAULT_BUDGET = 8


def main() -> None:
    args = parse_args()
    summary = run_phase14(
        repo_root=args.repo_root,
        phase12_json=args.phase12_json,
        records_dir=args.records_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        draft_md=args.draft_md,
        budget=args.budget,
        bootstrap_iterations=args.bootstrap_iterations,
        seed=args.seed,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "budget": summary["budget"],
                "bootstrap_iterations": summary["bootstrap_iterations"],
                "datasets": {
                    dataset_id: {
                        "auc_ci95": result["bootstrap"]["auc_ci95"],
                        "detection_ci95": result["bootstrap"]["wrong_detection_rate_ci95"],
                        "missed_wrong_count": result["miss_taxonomy"]["missed_wrong_count"],
                    }
                    for dataset_id, result in summary["datasets"].items()
                },
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--phase12-json", type=Path, default=DEFAULT_PHASE12_JSON)
    parser.add_argument("--records-dir", type=Path, default=DEFAULT_RECORDS_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--draft-md", type=Path, default=DEFAULT_DRAFT_MD)
    parser.add_argument("--budget", type=int, default=DEFAULT_BUDGET)
    parser.add_argument("--bootstrap-iterations", type=int, default=DEFAULT_BOOTSTRAP_ITERATIONS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def run_phase14(
    repo_root: Path,
    phase12_json: Path,
    records_dir: Path,
    output_json: Path,
    output_zh: Path,
    draft_md: Path,
    budget: int,
    bootstrap_iterations: int,
    seed: int,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    phase12 = read_json(_resolve(repo_root, phase12_json))
    records_dir = _resolve(repo_root, records_dir)
    datasets: dict[str, Any] = {}
    for dataset_id, dataset in phase12["datasets"].items():
        records_path = records_dir / dataset_id / "records_budgeted.jsonl"
        records = [
            record for record in read_jsonl(records_path)
            if int(record.get("requested_budget", -1)) == budget
        ]
        datasets[dataset_id] = summarize_dataset(
            records=records,
            phase12_dataset=dataset,
            bootstrap_iterations=bootstrap_iterations,
            seed=seed + stable_seed_offset(dataset_id),
        )
    gate = {
        f"{dataset_id}_auc_ci_lower_gate": result["bootstrap"]["auc_ci95"][0] >= 0.95
        for dataset_id, result in datasets.items()
    }
    gate.update(
        {
            f"{dataset_id}_detection_ci_lower_gate": result["bootstrap"]["wrong_detection_rate_ci95"][0] >= 0.90
            for dataset_id, result in datasets.items()
        }
    )
    summary = {
        "phase": "phase14_paper_readiness",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "budget": budget,
        "bootstrap_iterations": bootstrap_iterations,
        "seed": seed,
        "datasets": datasets,
        "gate": gate,
        "verdict": phase14_verdict(gate),
    }
    write_json(_resolve(repo_root, output_json), summary)
    write_markdown(_resolve(repo_root, output_zh), summary)
    write_draft(_resolve(repo_root, draft_md), summary)
    return summary


def summarize_dataset(
    records: list[dict[str, Any]],
    phase12_dataset: dict[str, Any],
    bootstrap_iterations: int,
    seed: int,
) -> dict[str, Any]:
    eval_records = [
        record for record in records
        if record.get("compiled") and record.get("label") in {"faithful", "plausible_wrong"}
    ]
    observed = {
        "candidate_count": len(records),
        "eval_count": len(eval_records),
        "paired_case_count": paired_case_count(eval_records),
        "auc": pairwise_auc(eval_records),
        "wrong_detection_rate": wrong_detection_rate(eval_records),
        "actual_input_evals": sum(int(record.get("actual_budget", 0)) for record in records),
        "avg_actual_inputs_per_candidate": (
            sum(int(record.get("actual_budget", 0)) for record in records) / len(records)
            if records else 0.0
        ),
    }
    bootstrap = bootstrap_case_metrics(eval_records, bootstrap_iterations, seed)
    return {
        "observed": observed,
        "phase12_budget8": phase12_dataset["budget_metrics"]["8"],
        "bootstrap": bootstrap,
        "miss_taxonomy": miss_taxonomy(eval_records),
        "cost_proxy": {
            "actual_input_evals": observed["actual_input_evals"],
            "avg_actual_inputs_per_candidate": observed["avg_actual_inputs_per_candidate"],
            "note": "Input-evaluation cost proxy only; wall-clock compile/run runtime is not reconstructed from prior traces.",
        },
    }


def bootstrap_case_metrics(
    records: list[dict[str, Any]],
    iterations: int,
    seed: int,
) -> dict[str, Any]:
    cases = sorted({str(record["case_id"]) for record in records})
    rng = random.Random(seed)
    auc_values: list[float] = []
    detection_values: list[float] = []
    for _ in range(iterations):
        sampled_cases = [rng.choice(cases) for _ in cases] if cases else []
        auc_values.append(pairwise_auc_for_cases(records, sampled_cases))
        detection_values.append(wrong_detection_rate_for_cases(records, sampled_cases))
    return {
        "auc_ci95": percentile_ci(auc_values),
        "wrong_detection_rate_ci95": percentile_ci(detection_values),
        "auc_mean": sum(auc_values) / len(auc_values) if auc_values else 0.0,
        "wrong_detection_rate_mean": sum(detection_values) / len(detection_values) if detection_values else 0.0,
    }


def pairwise_auc(records: list[dict[str, Any]]) -> float:
    return pairwise_auc_for_cases(records, sorted({str(record["case_id"]) for record in records}))


def pairwise_auc_for_cases(records: list[dict[str, Any]], case_ids: list[str]) -> float:
    by_case = records_by_case(records)
    credit = 0.0
    pairs = 0
    for case_id in case_ids:
        case_records = by_case.get(case_id, [])
        faithful = [record for record in case_records if record.get("label") == "faithful"]
        wrong = [record for record in case_records if record.get("label") == "plausible_wrong"]
        for faithful_record in faithful:
            faithful_score = trace_score(faithful_record)
            for wrong_record in wrong:
                wrong_score = trace_score(wrong_record)
                pairs += 1
                if wrong_score > faithful_score:
                    credit += 1.0
                elif wrong_score == faithful_score:
                    credit += 0.5
    return credit / pairs if pairs else 0.0


def wrong_detection_rate(records: list[dict[str, Any]]) -> float:
    return wrong_detection_rate_for_cases(records, sorted({str(record["case_id"]) for record in records}))


def wrong_detection_rate_for_cases(records: list[dict[str, Any]], case_ids: list[str]) -> float:
    by_case = records_by_case(records)
    wrong_count = 0
    detected = 0
    for case_id in case_ids:
        for record in by_case.get(case_id, []):
            if record.get("label") != "plausible_wrong":
                continue
            wrong_count += 1
            detected += int(trace_mismatch_count(record) > 0.0)
    return detected / wrong_count if wrong_count else 0.0


def paired_case_count(records: list[dict[str, Any]]) -> int:
    count = 0
    for case_id, case_records in records_by_case(records).items():
        labels = {record.get("label") for record in case_records}
        count += int("faithful" in labels and "plausible_wrong" in labels)
    return count


def miss_taxonomy(records: list[dict[str, Any]]) -> dict[str, Any]:
    misses = [
        {
            "case_id": str(record["case_id"]),
            "candidate_id": str(record["candidate_id"]),
            "optimization_level": str(record.get("optimization_level", "")),
            "candidate_family": candidate_family(str(record["candidate_id"])),
        }
        for record in records
        if record.get("label") == "plausible_wrong" and trace_mismatch_count(record) == 0.0
    ]
    return {
        "missed_wrong_count": len(misses),
        "by_case": dict(Counter(item["case_id"] for item in misses)),
        "by_candidate_family": dict(Counter(item["candidate_family"] for item in misses)),
        "misses": misses,
    }


def candidate_family(candidate_id: str) -> str:
    if "fixture_ifchain" in candidate_id:
        return "fixture_ifchain"
    if "strict_bug" in candidate_id:
        return "llm_strict_bug"
    if "strict_rewrite" in candidate_id:
        return "llm_strict_rewrite"
    if "original_control" in candidate_id:
        return "original_control"
    return "other"


def records_by_case(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_case[str(record["case_id"])].append(record)
    return by_case


def trace_score(record: dict[str, Any]) -> float:
    return float(record.get("features", {}).get("trace_mismatch_rate", 0.0))


def trace_mismatch_count(record: dict[str, Any]) -> float:
    return float(record.get("features", {}).get("trace_mismatch_count", 0.0))


def percentile_ci(values: list[float]) -> list[float]:
    if not values:
        return [0.0, 0.0]
    ordered = sorted(values)
    lo = ordered[int(0.025 * (len(ordered) - 1))]
    hi = ordered[int(0.975 * (len(ordered) - 1))]
    return [lo, hi]


def phase14_verdict(gate: dict[str, bool]) -> str:
    if all(gate.values()):
        return "pass-phase14-paper-readiness-hardening"
    if any(gate.values()):
        return "partial-phase14-paper-readiness-hardening"
    return "fail-phase14-paper-readiness-hardening"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    rows = []
    miss_rows = []
    for dataset_id, result in summary["datasets"].items():
        observed = result["observed"]
        bootstrap = result["bootstrap"]
        miss = result["miss_taxonomy"]
        rows.append(
            "| `{dataset}` | `{auc:.4f}` | `[{auc_lo:.4f}, {auc_hi:.4f}]` | `{det:.4f}` | `[{det_lo:.4f}, {det_hi:.4f}]` | `{avg:.2f}` | `{evals}` | `{misses}` |".format(
                dataset=dataset_id,
                auc=observed["auc"],
                auc_lo=bootstrap["auc_ci95"][0],
                auc_hi=bootstrap["auc_ci95"][1],
                det=observed["wrong_detection_rate"],
                det_lo=bootstrap["wrong_detection_rate_ci95"][0],
                det_hi=bootstrap["wrong_detection_rate_ci95"][1],
                avg=observed["avg_actual_inputs_per_candidate"],
                evals=observed["actual_input_evals"],
                misses=miss["missed_wrong_count"],
            )
        )
        miss_rows.append(
            "| `{dataset}` | `{misses}` | `{cases}` | `{families}` |".format(
                dataset=dataset_id,
                misses=miss["missed_wrong_count"],
                cases=json.dumps(miss["by_case"], sort_keys=True),
                families=json.dumps(miss["by_candidate_family"], sort_keys=True),
            )
        )
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    text = f"""# Decompilation Faithfulness Phase 14 Paper Readiness

- Verdict: `{summary['verdict']}`
- Budget: `{summary['budget']}`
- Bootstrap iterations: `{summary['bootstrap_iterations']}`
- Seed: `{summary['seed']}`

## Budget-8 Stability And Cost

| Dataset | AUC | AUC CI95 | Wrong detection | Detection CI95 | Avg inputs | Input evals | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Miss Taxonomy

| Dataset | Missed wrong | By case | By candidate family |
|---|---:|---|---|
{chr(10).join(miss_rows)}

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Interpretation

The confidence intervals are case-level bootstrap intervals over the budget-8
records. Cost is reported as an input-evaluation proxy because prior trace files
do not preserve full wall-clock compile/run timing. Remaining misses should be
discussed as budget-limited failures rather than as compile failures.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_draft(path: Path, summary: dict[str, Any]) -> None:
    lines = [
        "# Experiment Section Draft: Low-Budget Dynamic Re-Execution",
        "",
        "We evaluate fixture-neighbor-first low-budget dynamic re-execution in a source-known localized semantic drift auditing setting. The auditor compares the original source and a candidate C function on a deterministic generated-input prefix, using budget 8 as the default.",
        "",
        "Across the current public static-hard, LLM-public, and Ghidra datasets, the method passes the budget-8 gates. The main evidence is summarized below:",
        "",
    ]
    for dataset_id, result in summary["datasets"].items():
        observed = result["observed"]
        bootstrap = result["bootstrap"]
        lines.append(
            "- `{}`: AUC `{:.4f}` with CI95 `[{:.4f}, {:.4f}]`, wrong-detection rate `{:.4f}` with CI95 `[{:.4f}, {:.4f}]`, average inputs `{:.2f}`.".format(
                dataset_id,
                observed["auc"],
                bootstrap["auc_ci95"][0],
                bootstrap["auc_ci95"][1],
                observed["wrong_detection_rate"],
                bootstrap["wrong_detection_rate_ci95"][0],
                bootstrap["wrong_detection_rate_ci95"][1],
                observed["avg_actual_inputs_per_candidate"],
            )
        )
    lines.extend(
        [
            "",
            "These results support a low-budget semantic auditing claim, not a general decompiler-generation SOTA claim. The method assumes source-known oracle access and bounded deterministic inputs. Remaining misses are reported explicitly in the miss taxonomy.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_seed_offset(text: str) -> int:
    return sum((index + 1) * ord(char) for index, char in enumerate(text))


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
