from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


DEFAULT_PHASE18_UNIFIED_JSON = Path(
    "analysis_outputs/decompile_faithfulness/phase18_source_literal_char_policy/phase12_unified_low_budget.json"
)
DEFAULT_PHASE18_JSON = Path("docs/paper_agent/decompile_faithfulness_phase18_source_literal_char_policy.json")
DEFAULT_PHASE17_JSON = Path("docs/paper_agent/decompile_faithfulness_phase17_operator_char_policy.json")
DEFAULT_PHASE19_READINESS_JSON = Path("docs/paper_agent/decompile_faithfulness_phase19_final_method_readiness.json")
DEFAULT_PHASE19_RUNTIME_JSON = Path("docs/paper_agent/decompile_faithfulness_phase19_final_runtime_risk.json")
DEFAULT_OUTPUT_MD = Path("docs/paper_agent/decompile_faithfulness_phase20_paper_tables.md")
DATASET_LABELS = {
    "phase7c2_static_hard_public": "Public static-hard",
    "phase7e_llm_public_full_topup": "LLM-public",
    "phase6r_ghidra_full": "Ghidra",
}
DATASET_ORDER = [
    "phase7c2_static_hard_public",
    "phase7e_llm_public_full_topup",
    "phase6r_ghidra_full",
]


def main() -> None:
    args = parse_args()
    summary = build_tables(
        repo_root=args.repo_root,
        phase18_unified_json=args.phase18_unified_json,
        phase18_json=args.phase18_json,
        phase17_json=args.phase17_json,
        phase19_readiness_json=args.phase19_readiness_json,
        phase19_runtime_json=args.phase19_runtime_json,
    )
    write_markdown(_resolve(args.repo_root.resolve(), args.output_md), summary)
    print(json.dumps({"output": str(args.output_md), "tables": sorted(summary)}, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--phase18-unified-json", type=Path, default=DEFAULT_PHASE18_UNIFIED_JSON)
    parser.add_argument("--phase18-json", type=Path, default=DEFAULT_PHASE18_JSON)
    parser.add_argument("--phase17-json", type=Path, default=DEFAULT_PHASE17_JSON)
    parser.add_argument("--phase19-readiness-json", type=Path, default=DEFAULT_PHASE19_READINESS_JSON)
    parser.add_argument("--phase19-runtime-json", type=Path, default=DEFAULT_PHASE19_RUNTIME_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    return parser.parse_args()


def build_tables(
    repo_root: Path,
    phase18_unified_json: Path,
    phase18_json: Path,
    phase17_json: Path,
    phase19_readiness_json: Path,
    phase19_runtime_json: Path,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    phase18_unified = read_json(_resolve(repo_root, phase18_unified_json))
    phase18 = read_json(_resolve(repo_root, phase18_json))
    phase17 = read_json(_resolve(repo_root, phase17_json))
    readiness = read_json(_resolve(repo_root, phase19_readiness_json))
    runtime = read_json(_resolve(repo_root, phase19_runtime_json))
    return {
        "main_results": main_result_rows(phase18_unified),
        "stability_runtime": stability_runtime_rows(readiness, runtime),
        "ablation": ablation_rows(phase18, phase17),
        "ghidra_risk": ghidra_risk_rows(runtime),
    }


def main_result_rows(phase18_unified: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for dataset_id in DATASET_ORDER:
        dataset = phase18_unified["datasets"][dataset_id]
        metrics = dataset["budget_metrics"]["8"]
        rows.append(
            {
                "dataset_id": dataset_id,
                "label": DATASET_LABELS[dataset_id],
                "candidates": metrics["candidate_count"],
                "paired_cases": metrics["paired_case_count"],
                "fixture_auc": metrics["fixture_auc"],
                "static_auc": metrics["static_auc"],
                "final_auc": metrics["mismatch_auc"],
                "detection": metrics["wrong_detection_rate"],
                "avg_inputs": metrics["avg_actual_inputs_per_candidate"],
                "missed": metrics["missed_wrong_count"],
            }
        )
    return rows


def stability_runtime_rows(readiness: dict[str, Any], runtime: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for dataset_id in DATASET_ORDER:
        observed = readiness["datasets"][dataset_id]["observed"]
        bootstrap = readiness["datasets"][dataset_id]["bootstrap"]
        timing = runtime["runtime"][dataset_id]
        rows.append(
            {
                "dataset_id": dataset_id,
                "label": DATASET_LABELS[dataset_id],
                "auc": observed["auc"],
                "auc_ci95": bootstrap["auc_ci95"],
                "detection": observed["wrong_detection_rate"],
                "detection_ci95": bootstrap["wrong_detection_rate_ci95"],
                "total_seconds": timing["total_seconds"],
                "p95_seconds": timing["p95_seconds_per_candidate"],
                "input_evals_per_second": timing["input_evals_per_second"],
            }
        )
    return rows


def ablation_rows(phase18: dict[str, Any], phase17: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for method, source in [
        ("Fixture-neighbor", phase18["dataset_comparison"]),
        ("Operator-char-first", phase17["dataset_comparison"]),
        ("Source-literal interleave", phase18["dataset_comparison"]),
    ]:
        row = {"method": method}
        for dataset_id in DATASET_ORDER:
            metrics = source[dataset_id]["baseline"] if method == "Fixture-neighbor" else source[dataset_id]["new"]
            row[f"{dataset_id}_auc"] = metrics["mismatch_auc"]
            row[f"{dataset_id}_detection"] = metrics["wrong_detection_rate"]
            row[f"{dataset_id}_missed"] = metrics["missed_wrong_count"]
        rows.append(row)
    return rows


def ghidra_risk_rows(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        row for row in runtime["risk_breakdown"]["phase6r_ghidra_full"]
        if row["paired_case_count"] >= 3
    ]
    return sorted(rows, key=lambda row: (-row["paired_case_count"], row["risk_family"]))


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    text = "\n\n".join(
        [
            "# Decompilation Faithfulness Phase 20 Paper Tables",
            main_result_markdown(summary["main_results"]),
            stability_runtime_markdown(summary["stability_runtime"]),
            ablation_markdown(summary["ablation"]),
            ghidra_risk_markdown(summary["ghidra_risk"]),
            latex_tables(summary),
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text + "\n", encoding="utf-8")


def main_result_markdown(rows: list[dict[str, Any]]) -> str:
    rendered = [
        "| {label} | {candidates} | {paired_cases} | {fixture_auc:.4f} | {static_auc:.4f} | {final_auc:.4f} | {detection:.4f} | {avg_inputs:.2f} | {missed} |".format(**row)
        for row in rows
    ]
    return """## Main Results

| Dataset | Candidates | Paired cases | Fixture AUC | Static AUC | Final AUC | Detection | Avg inputs | Missed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
{}""".format("\n".join(rendered))


def stability_runtime_markdown(rows: list[dict[str, Any]]) -> str:
    rendered = [
        "| {label} | {auc:.4f} | [{auc_lo:.4f}, {auc_hi:.4f}] | {detection:.4f} | [{det_lo:.4f}, {det_hi:.4f}] | {total:.2f} | {p95:.4f} | {rate:.2f} |".format(
            label=row["label"],
            auc=row["auc"],
            auc_lo=row["auc_ci95"][0],
            auc_hi=row["auc_ci95"][1],
            detection=row["detection"],
            det_lo=row["detection_ci95"][0],
            det_hi=row["detection_ci95"][1],
            total=row["total_seconds"],
            p95=row["p95_seconds"],
            rate=row["input_evals_per_second"],
        )
        for row in rows
    ]
    return """## Stability And Runtime

| Dataset | AUC | AUC CI95 | Detection | Detection CI95 | Total seconds | P95 sec/cand | Input evals/sec |
|---|---:|---:|---:|---:|---:|---:|---:|
{}""".format("\n".join(rendered))


def ablation_markdown(rows: list[dict[str, Any]]) -> str:
    rendered = []
    for row in rows:
        rendered.append(
            "| {method} | {p_auc:.4f} / {p_det:.4f} / {p_miss} | {l_auc:.4f} / {l_det:.4f} / {l_miss} | {g_auc:.4f} / {g_det:.4f} / {g_miss} |".format(
                method=row["method"],
                p_auc=row["phase7c2_static_hard_public_auc"],
                p_det=row["phase7c2_static_hard_public_detection"],
                p_miss=row["phase7c2_static_hard_public_missed"],
                l_auc=row["phase7e_llm_public_full_topup_auc"],
                l_det=row["phase7e_llm_public_full_topup_detection"],
                l_miss=row["phase7e_llm_public_full_topup_missed"],
                g_auc=row["phase6r_ghidra_full_auc"],
                g_det=row["phase6r_ghidra_full_detection"],
                g_miss=row["phase6r_ghidra_full_missed"],
            )
        )
    return """## Ablation

Each cell is `AUC / detection / missed`.

| Method | Public static-hard | LLM-public | Ghidra |
|---|---:|---:|---:|
{}""".format("\n".join(rendered))


def ghidra_risk_markdown(rows: list[dict[str, Any]]) -> str:
    rendered = [
        "| {risk_family} | {paired_case_count} | {auc:.4f} | {wrong_detection_rate:.4f} | {missed_wrong_count} |".format(**row)
        for row in rows
    ]
    return """## Ghidra Risk Families

| Risk family | Paired cases | AUC | Detection | Missed |
|---|---:|---:|---:|---:|
{}""".format("\n".join(rendered))


def latex_tables(summary: dict[str, Any]) -> str:
    return "\n\n".join(
        [
            "## LaTeX Drafts",
            latex_main_result(summary["main_results"]),
            latex_ablation(summary["ablation"]),
            latex_runtime(summary["stability_runtime"]),
        ]
    )


def latex_main_result(rows: list[dict[str, Any]]) -> str:
    body = "\n".join(
        r"{label} & {candidates} & {paired_cases} & {fixture_auc:.4f} & {static_auc:.4f} & {final_auc:.4f} & {detection:.4f} & {avg_inputs:.2f} & {missed} \\".format(**row)
        for row in rows
    )
    return """### Main Result LaTeX

```latex
\\begin{tabular}{lrrrrrrrr}
\\toprule
Dataset & Cand. & Cases & Fixture & Static & Final & Detect. & Avg. Inp. & Miss \\\\
\\midrule
%s
\\bottomrule
\\end{tabular}
```""" % body


def latex_ablation(rows: list[dict[str, Any]]) -> str:
    body = "\n".join(
        r"{method} & {p_auc:.4f}/{p_det:.4f}/{p_miss} & {l_auc:.4f}/{l_det:.4f}/{l_miss} & {g_auc:.4f}/{g_det:.4f}/{g_miss} \\".format(
            method=row["method"],
            p_auc=row["phase7c2_static_hard_public_auc"],
            p_det=row["phase7c2_static_hard_public_detection"],
            p_miss=row["phase7c2_static_hard_public_missed"],
            l_auc=row["phase7e_llm_public_full_topup_auc"],
            l_det=row["phase7e_llm_public_full_topup_detection"],
            l_miss=row["phase7e_llm_public_full_topup_missed"],
            g_auc=row["phase6r_ghidra_full_auc"],
            g_det=row["phase6r_ghidra_full_detection"],
            g_miss=row["phase6r_ghidra_full_missed"],
        )
        for row in rows
    )
    return """### Ablation LaTeX

```latex
\\begin{tabular}{lrrr}
\\toprule
Method & Public & LLM-public & Ghidra \\\\
\\midrule
%s
\\bottomrule
\\end{tabular}
```""" % body


def latex_runtime(rows: list[dict[str, Any]]) -> str:
    body = "\n".join(
        r"{label} & {total_seconds:.2f} & {p95_seconds:.4f} & {input_evals_per_second:.2f} \\".format(**row)
        for row in rows
    )
    return """### Runtime LaTeX

```latex
\\begin{tabular}{lrrr}
\\toprule
Dataset & Total s & P95 s/cand. & Input evals/s \\\\
\\midrule
%s
\\bottomrule
\\end{tabular}
```""" % body


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
