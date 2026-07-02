from __future__ import annotations

import argparse
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase8_sota_hardening.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase8_sota_hardening.zh.md")
DEFAULT_BOOTSTRAP_ITERATIONS = 2000
DEFAULT_SEED = 20260702


@dataclass(frozen=True)
class DatasetSpec:
    dataset_id: str
    title: str
    records_path: Path | None = None
    combined_summary_path: Path | None = None


DEFAULT_DATASETS = [
    DatasetSpec(
        dataset_id="phase7c2_static_hard_public",
        title="Phase 7C2 static-hard public",
        records_path=Path("analysis_outputs/decompile_faithfulness/phase7_static_hard/records.jsonl"),
    ),
    DatasetSpec(
        dataset_id="phase7e_llm_public_full_topup",
        title="Phase 7E LLM public full+top-up",
        combined_summary_path=Path("docs/paper_agent/decompile_faithfulness_phase7_llm_public_combined.json"),
    ),
    DatasetSpec(
        dataset_id="phase6r_ghidra_full",
        title="Phase 6R Ghidra full",
        records_path=Path("analysis_outputs/decompile_faithfulness/phase6r_ghidra_full/records.jsonl"),
    ),
    DatasetSpec(
        dataset_id="phase6r_ghidra_gcc9_full",
        title="Phase 6R Ghidra gcc9 full",
        records_path=Path("analysis_outputs/decompile_faithfulness/phase6r_ghidra_gcc9_full/records.jsonl"),
    ),
]


SCORE_NAMES = [
    "fixture_only",
    "static_structured_proxy",
    "fuzzing_mismatch_rate",
    "fuzzing_any_mismatch",
    "v3_trace_total",
]


def main() -> None:
    args = parse_args()
    summary = run_phase8(
        repo_root=args.repo_root,
        output_json=args.output_json,
        output_zh=args.output_zh,
        bootstrap_iterations=args.bootstrap_iterations,
        seed=args.seed,
    )
    primary = summary["datasets"]["phase7c2_static_hard_public"]
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "phase7c2_legacy_delta": primary["delta"]["v3_vs_legacy_best"]["point"],
                "phase7c2_legacy_delta_ci": primary["delta"]["v3_vs_legacy_best"]["ci95"],
                "phase7c2_strong_delta": primary["delta"]["v3_vs_strong_best"]["point"],
                "phase7c2_strong_delta_ci": primary["delta"]["v3_vs_strong_best"]["ci95"],
                "strong_baseline_not_erased": summary["gate"]["strong_baseline_not_erased"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--bootstrap-iterations", type=int, default=DEFAULT_BOOTSTRAP_ITERATIONS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def run_phase8(
    repo_root: Path,
    output_json: Path,
    output_zh: Path,
    bootstrap_iterations: int,
    seed: int,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    datasets: dict[str, Any] = {}
    for index, spec in enumerate(DEFAULT_DATASETS):
        records = load_dataset_records(repo_root, spec)
        datasets[spec.dataset_id] = analyze_dataset(
            spec=spec,
            records=records,
            bootstrap_iterations=bootstrap_iterations,
            seed=seed + index * 997,
        )
    primary = datasets["phase7c2_static_hard_public"]
    gate = {
        "phase7c2_present": primary["paired_case_count"] > 0,
        "legacy_delta_ci_lower_gt_zero": primary["delta"]["v3_vs_legacy_best"]["ci95"][0] > 0.0,
        "strong_baseline_not_erased": primary["delta"]["v3_vs_strong_best"]["point"] >= 0.01,
    }
    summary = {
        "phase": "phase8_sota_hardening",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "bootstrap_iterations": bootstrap_iterations,
        "seed": seed,
        "datasets": datasets,
        "gate": gate,
        "verdict": phase8_verdict(gate),
        "interpretation": phase8_interpretation(gate),
    }
    write_json(output_json, summary)
    write_markdown(output_zh, summary)
    return summary


def load_dataset_records(repo_root: Path, spec: DatasetSpec) -> list[dict[str, Any]]:
    if spec.records_path is not None:
        return read_jsonl(_resolve(repo_root, spec.records_path))
    if spec.combined_summary_path is None:
        raise ValueError(f"dataset spec has no input path: {spec.dataset_id}")
    summary = json.loads(_resolve(repo_root, spec.combined_summary_path).read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = []
    for run_dir in summary.get("run_dirs", []):
        records.extend(read_jsonl(Path(run_dir) / "records.jsonl"))
    return dedupe_records(records)


def analyze_dataset(
    spec: DatasetSpec,
    records: list[dict[str, Any]],
    bootstrap_iterations: int,
    seed: int,
) -> dict[str, Any]:
    eval_records = [
        record for record in records
        if record.get("compiled") and record.get("label") in {"faithful", "plausible_wrong"}
    ]
    case_stats = build_case_stats(eval_records)
    point = aggregate_metric(case_stats, list(case_stats))
    bootstrap = bootstrap_metrics(case_stats, iterations=bootstrap_iterations, seed=seed)
    delta = {
        "v3_vs_legacy_best": {
            "point": point["v3_trace_total"] - max(point["fixture_only"], point["static_structured_proxy"]),
            "ci95": ci95(bootstrap["delta_v3_vs_legacy_best"]),
        },
        "v3_vs_strong_best": {
            "point": point["v3_trace_total"] - max(
                point["fixture_only"],
                point["static_structured_proxy"],
                point["fuzzing_mismatch_rate"],
                point["fuzzing_any_mismatch"],
            ),
            "ci95": ci95(bootstrap["delta_v3_vs_strong_best"]),
        },
    }
    return {
        "dataset_id": spec.dataset_id,
        "title": spec.title,
        "records_path": str(spec.records_path) if spec.records_path else "",
        "combined_summary_path": str(spec.combined_summary_path) if spec.combined_summary_path else "",
        "candidate_count": len(records),
        "eval_count": len(eval_records),
        "compile_pass_count": sum(1 for record in records if record.get("compiled")),
        "paired_case_count": len(case_stats),
        "label_counts": count_by(records, "label"),
        "point_auc": point,
        "auc_ci95": {
            score_name: ci95(bootstrap[score_name])
            for score_name in SCORE_NAMES
        },
        "delta": delta,
        "strong_baseline_best_name": best_strong_baseline_name(point),
        "legacy_baseline_best_name": (
            "fixture_only"
            if point["fixture_only"] >= point["static_structured_proxy"]
            else "static_structured_proxy"
        ),
    }


def build_case_stats(records: list[dict[str, Any]]) -> dict[str, dict[str, tuple[float, int]]]:
    stats: dict[str, dict[str, tuple[float, int]]] = {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[str(record["case_id"])].append(record)
    for case_id, case_records in grouped.items():
        faithful = [record for record in case_records if record["label"] == "faithful"]
        wrong = [record for record in case_records if record["label"] == "plausible_wrong"]
        if not faithful or not wrong:
            continue
        stats[case_id] = {
            score_name: pair_credit(faithful, wrong, score_fn)
            for score_name, score_fn in score_functions().items()
        }
    return dict(sorted(stats.items()))


def pair_credit(
    faithful: list[dict[str, Any]],
    wrong: list[dict[str, Any]],
    score_fn: Callable[[dict[str, Any]], float],
) -> tuple[float, int]:
    credit = 0.0
    pairs = 0
    for faithful_record in faithful:
        faithful_score = score_fn(faithful_record)
        for wrong_record in wrong:
            pairs += 1
            wrong_score = score_fn(wrong_record)
            if wrong_score > faithful_score:
                credit += 1.0
            elif wrong_score == faithful_score:
                credit += 0.5
    return credit, pairs


def aggregate_metric(
    case_stats: dict[str, dict[str, tuple[float, int]]],
    sampled_case_ids: list[str],
) -> dict[str, float]:
    totals = {score_name: [0.0, 0] for score_name in SCORE_NAMES}
    for case_id in sampled_case_ids:
        for score_name, (credit, pairs) in case_stats[case_id].items():
            totals[score_name][0] += credit
            totals[score_name][1] += pairs
    return {
        score_name: (credit / pairs if pairs else 0.0)
        for score_name, (credit, pairs) in totals.items()
    }


def bootstrap_metrics(
    case_stats: dict[str, dict[str, tuple[float, int]]],
    iterations: int,
    seed: int,
) -> dict[str, list[float]]:
    rng = random.Random(seed)
    case_ids = list(case_stats)
    values = {score_name: [] for score_name in SCORE_NAMES}
    values["delta_v3_vs_legacy_best"] = []
    values["delta_v3_vs_strong_best"] = []
    if not case_ids:
        return values
    for _ in range(iterations):
        sampled = [rng.choice(case_ids) for _ in case_ids]
        metric = aggregate_metric(case_stats, sampled)
        for score_name in SCORE_NAMES:
            values[score_name].append(metric[score_name])
        legacy_best = max(metric["fixture_only"], metric["static_structured_proxy"])
        strong_best = max(
            metric["fixture_only"],
            metric["static_structured_proxy"],
            metric["fuzzing_mismatch_rate"],
            metric["fuzzing_any_mismatch"],
        )
        values["delta_v3_vs_legacy_best"].append(metric["v3_trace_total"] - legacy_best)
        values["delta_v3_vs_strong_best"].append(metric["v3_trace_total"] - strong_best)
    return values


def score_functions() -> dict[str, Callable[[dict[str, Any]], float]]:
    return {
        "fixture_only": lambda record: float(record["features"].get("fixture_mismatch_rate", 1.0)),
        "static_structured_proxy": lambda record: float(record["features"].get("static_structured_total", 0.0)),
        "fuzzing_mismatch_rate": lambda record: float(record["features"].get("trace_mismatch_rate", 0.0)),
        "fuzzing_any_mismatch": lambda record: (
            1.0 if float(record["features"].get("trace_mismatch_rate", 0.0)) > 0.0 else 0.0
        ),
        "v3_trace_total": lambda record: float(record["features"].get("trace_total", 0.0)),
    }


def ci95(values: list[float]) -> list[float]:
    if not values:
        return [0.0, 0.0]
    ordered = sorted(values)
    return [quantile(ordered, 0.025), quantile(ordered, 0.975)]


def quantile(ordered_values: list[float], q: float) -> float:
    if not ordered_values:
        return 0.0
    if len(ordered_values) == 1:
        return ordered_values[0]
    position = q * (len(ordered_values) - 1)
    low = int(position)
    high = min(low + 1, len(ordered_values) - 1)
    fraction = position - low
    return ordered_values[low] * (1.0 - fraction) + ordered_values[high] * fraction


def best_strong_baseline_name(point: dict[str, float]) -> str:
    candidates = {
        "fixture_only": point["fixture_only"],
        "static_structured_proxy": point["static_structured_proxy"],
        "fuzzing_mismatch_rate": point["fuzzing_mismatch_rate"],
        "fuzzing_any_mismatch": point["fuzzing_any_mismatch"],
    }
    return max(candidates.items(), key=lambda item: (item[1], item[0]))[0]


def phase8_verdict(gate: dict[str, bool]) -> str:
    if all(gate.values()):
        return "pass-phase8-sota-hardening"
    if gate["phase7c2_present"] and gate["legacy_delta_ci_lower_gt_zero"]:
        return "strong-baseline-erases-v3-extra-margin"
    return "needs-more-stable-phase7c2-margin"


def phase8_interpretation(gate: dict[str, bool]) -> str:
    if gate["strong_baseline_not_erased"]:
        return (
            "Dynamic Trace v3 keeps margin over both legacy fixture/static baselines and the "
            "generated-input fuzzing-style baseline."
        )
    return (
        "Dynamic Trace v3 keeps the legacy fixture/static margin, but generated-input "
        "fuzzing-style re-execution reaches the same AUC on the current records. The paper "
        "should claim dynamic re-execution evidence, not v3 component SOTA margin, unless a "
        "harder dataset shows v3-only gains."
    )


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    return dict(Counter(str(record.get(key, "")) for record in records))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    rows = []
    for dataset in summary["datasets"].values():
        rows.append(
            "| `{dataset_id}` | `{paired_case_count}` | `{fixture:.4f}` | `{static:.4f}` | "
            "`{fuzz:.4f}` | `{any_fuzz:.4f}` | `{v3:.4f}` | `{legacy_delta:.4f}` | "
            "`{strong_delta:.4f}` |".format(
                dataset_id=dataset["dataset_id"],
                paired_case_count=dataset["paired_case_count"],
                fixture=dataset["point_auc"]["fixture_only"],
                static=dataset["point_auc"]["static_structured_proxy"],
                fuzz=dataset["point_auc"]["fuzzing_mismatch_rate"],
                any_fuzz=dataset["point_auc"]["fuzzing_any_mismatch"],
                v3=dataset["point_auc"]["v3_trace_total"],
                legacy_delta=dataset["delta"]["v3_vs_legacy_best"]["point"],
                strong_delta=dataset["delta"]["v3_vs_strong_best"]["point"],
            )
        )
    ci_rows = []
    for dataset in summary["datasets"].values():
        ci_rows.append(
            "| `{dataset_id}` | `{legacy_low:.4f}`, `{legacy_high:.4f}` | "
            "`{strong_low:.4f}`, `{strong_high:.4f}` | `{best}` |".format(
                dataset_id=dataset["dataset_id"],
                legacy_low=dataset["delta"]["v3_vs_legacy_best"]["ci95"][0],
                legacy_high=dataset["delta"]["v3_vs_legacy_best"]["ci95"][1],
                strong_low=dataset["delta"]["v3_vs_strong_best"]["ci95"][0],
                strong_high=dataset["delta"]["v3_vs_strong_best"]["ci95"][1],
                best=dataset["strong_baseline_best_name"],
            )
        )
    gate_rows = "\n".join(f"| `{key}` | `{value}` |" for key, value in summary["gate"].items())
    text = f"""# Decompilation Faithfulness Phase 8 SOTA Hardening

- Verdict: `{summary['verdict']}`
- Bootstrap iterations: `{summary['bootstrap_iterations']}`
- Seed: `{summary['seed']}`
- Interpretation: {summary['interpretation']}

## Point Estimates

| Dataset | Paired cases | Fixture AUC | Static AUC | Fuzz mismatch AUC | Fuzz any AUC | V3 AUC | V3 - legacy best | V3 - strong best |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(rows)}

## Delta CI

| Dataset | V3 - legacy best CI95 | V3 - strong best CI95 | Strong best baseline |
|---|---:|---:|---|
{chr(10).join(ci_rows)}

## Gate

| Gate | Passed |
|---|---:|
{gate_rows}

## Interpretation

Phase 8 separates two claims:

1. Dynamic re-execution versus legacy fixture/static baselines.
2. Dynamic Trace v3's richer components versus a stronger generated-input fuzzing-style baseline.

If `fuzzing_mismatch_rate` or `fuzzing_any_mismatch` reaches the same AUC as
`v3_trace_total`, then the current evidence supports dynamic re-execution as the
core mechanism, but not a separate SOTA-margin claim for v3's extra trace
components.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
