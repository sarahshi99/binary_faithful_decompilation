from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_PHASE8_JSON = Path("docs/paper_agent/decompile_faithfulness_phase8_sota_hardening.json")
DEFAULT_PHASE10_JSON = Path("docs/paper_agent/decompile_faithfulness_phase10_low_budget_rerun.json")
DEFAULT_PHASE12_JSON = Path("docs/paper_agent/decompile_faithfulness_phase12_unified_low_budget.json")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase13_paper_evidence.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase13_paper_evidence.zh.md")
DEFAULT_DECISION_ZH = Path("docs/paper_agent/decompile_faithfulness_phase13_decision.zh.md")


def main() -> None:
    args = parse_args()
    summary = run_phase13(
        repo_root=args.repo_root,
        phase8_json=args.phase8_json,
        phase10_json=args.phase10_json,
        phase12_json=args.phase12_json,
        output_json=args.output_json,
        output_zh=args.output_zh,
        decision_zh=args.decision_zh,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "method_name": summary["method"]["name"],
                "phase12_verdict": summary["inputs"]["phase12_verdict"],
                "supported_claim_count": len(summary["claims"]["supported"]),
                "unsupported_claim_count": len(summary["claims"]["unsupported"]),
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--phase8-json", type=Path, default=DEFAULT_PHASE8_JSON)
    parser.add_argument("--phase10-json", type=Path, default=DEFAULT_PHASE10_JSON)
    parser.add_argument("--phase12-json", type=Path, default=DEFAULT_PHASE12_JSON)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--decision-zh", type=Path, default=DEFAULT_DECISION_ZH)
    return parser.parse_args()


def run_phase13(
    repo_root: Path,
    phase8_json: Path,
    phase10_json: Path,
    phase12_json: Path,
    output_json: Path,
    output_zh: Path,
    decision_zh: Path,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    phase8 = read_json(_resolve(repo_root, phase8_json))
    phase10 = read_json(_resolve(repo_root, phase10_json))
    phase12 = read_json(_resolve(repo_root, phase12_json))
    table_rows = build_main_table_rows(phase8, phase10, phase12)
    claims = build_claims(phase8, phase12)
    summary = {
        "phase": "phase13_paper_evidence_synthesis",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "inputs": {
            "phase8_verdict": phase8.get("verdict"),
            "phase10_verdict": phase10.get("verdict"),
            "phase12_verdict": phase12.get("verdict"),
        },
        "method": {
            "name": "fixture-neighbor-first low-budget dynamic re-execution",
            "scope": "source-known localized semantic drift auditing",
            "default_budget": 8,
            "core_signal": "generated-input output mismatch under targeted fixture-neighborhood ordering",
        },
        "main_table_rows": table_rows,
        "claims": claims,
        "ccfa_gap": ccfa_gap(),
        "verdict": phase13_verdict(phase12, claims),
    }
    write_json(_resolve(repo_root, output_json), summary)
    write_markdown(_resolve(repo_root, output_zh), summary)
    write_decision(_resolve(repo_root, decision_zh), summary)
    return summary


def build_main_table_rows(
    phase8: dict[str, Any],
    phase10: dict[str, Any],
    phase12: dict[str, Any],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    phase8_by_dataset = {row["dataset_id"]: row for row in phase8.get("point_estimates", [])}
    for dataset_id, dataset in phase12["datasets"].items():
        b8 = dataset["budget_metrics"]["8"]
        baseline = phase10["datasets"][dataset_id]["budget_metrics"]["8"]
        phase8_row = phase8_by_dataset.get(dataset_id, {})
        rows.append(
            {
                "dataset_id": dataset_id,
                "candidate_count": b8["candidate_count"],
                "paired_case_count": b8["paired_case_count"],
                "fixture_auc": b8["fixture_auc"],
                "static_auc": b8["static_auc"],
                "phase10_original_order_auc": baseline["mismatch_auc"],
                "phase12_unified_budget8_auc": b8["mismatch_auc"],
                "phase12_wrong_detection_rate": b8["wrong_detection_rate"],
                "phase12_avg_actual_inputs": b8["avg_actual_inputs_per_candidate"],
                "phase12_missed_wrong_count": b8["missed_wrong_count"],
                "legacy_delta_vs_best": max(
                    b8["mismatch_auc"] - b8["fixture_auc"],
                    b8["mismatch_auc"] - b8["static_auc"],
                ),
                "strong_baseline_delta_from_phase8": phase8_row.get("v3_minus_strong_best", 0.0),
            }
        )
    return rows


def build_claims(phase8: dict[str, Any], phase12: dict[str, Any]) -> dict[str, list[str]]:
    phase12_passed = phase12.get("verdict") == "pass-unified-budget8-low-budget-eval"
    strong_erased = phase8.get("verdict") == "strong-baseline-erases-v3-extra-margin"
    supported = []
    if phase12_passed:
        supported.extend(
            [
                "Budget-8 targeted dynamic re-execution passes current public static-hard, LLM-public, and Ghidra gates.",
                "Fixture-neighbor input ordering improves low-budget detection with negligible average-input overhead.",
                "The method is stronger than fixture-only and static structured legacy baselines in the current source-known setting.",
                "The clean paper scope is source-known localized semantic drift auditing, not decompiler generation quality.",
            ]
        )
    unsupported = [
        "Universal external benchmark SOTA over decompilation-generation papers.",
        "Cross-decompiler robustness beyond the current Ghidra-centered compile-ready evidence.",
        "Replacing full semantic equivalence checking in unbounded programs.",
    ]
    if strong_erased:
        unsupported.append(
            "Dynamic Trace v3 scoring components beat a strong generated-input mismatch baseline on current data."
        )
    return {"supported": supported, "unsupported": unsupported}


def ccfa_gap() -> list[str]:
    return [
        "Add direct public-benchmark rows or clearly justify the CodeFuse/public subset as the paper benchmark.",
        "Add cost/runtime table, not only input-count table.",
        "Add confidence intervals for Phase12 unified budget-8 deltas.",
        "Add failure-case taxonomy for the remaining Ghidra budget-8 misses.",
        "Add second compile-ready decompiler or explicitly state Ghidra-centered scope.",
        "Write related-work comparison as validation/auditing, not generation leaderboard.",
    ]


def phase13_verdict(phase12: dict[str, Any], claims: dict[str, list[str]]) -> str:
    if phase12.get("verdict") == "pass-unified-budget8-low-budget-eval" and claims["supported"]:
        return "paper-evidence-ready-for-method-table"
    return "paper-evidence-needs-more-experiments"


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    table_rows = [
        "| `{dataset}` | `{candidates}` | `{paired}` | `{fixture:.4f}` | `{static:.4f}` | `{old:.4f}` | `{new:.4f}` | `{det:.4f}` | `{avg:.2f}` | `{missed}` |".format(
            dataset=row["dataset_id"],
            candidates=row["candidate_count"],
            paired=row["paired_case_count"],
            fixture=row["fixture_auc"],
            static=row["static_auc"],
            old=row["phase10_original_order_auc"],
            new=row["phase12_unified_budget8_auc"],
            det=row["phase12_wrong_detection_rate"],
            avg=row["phase12_avg_actual_inputs"],
            missed=row["phase12_missed_wrong_count"],
        )
        for row in summary["main_table_rows"]
    ]
    supported = "\n".join(f"- {claim}" for claim in summary["claims"]["supported"])
    unsupported = "\n".join(f"- {claim}" for claim in summary["claims"]["unsupported"])
    gaps = "\n".join(f"- {item}" for item in summary["ccfa_gap"])
    text = f"""# Decompilation Faithfulness Phase 13 Paper Evidence Synthesis

- Verdict: `{summary['verdict']}`
- Method: `{summary['method']['name']}`
- Scope: `{summary['method']['scope']}`
- Default budget: `{summary['method']['default_budget']}`

## Main Paper Table Draft

| Dataset | Candidates | Paired cases | Fixture AUC | Static AUC | Original-order budget-8 AUC | Unified budget-8 AUC | Wrong detection rate | Avg inputs | Missed wrong |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(table_rows)}

## Supported Claims

{supported}

## Unsupported Claims

{unsupported}

## CCF-A Gap

{gaps}

## Interpretation

The evidence now supports a low-budget targeted dynamic re-execution auditor.
The strongest paper story is not that a complex v3 scoring formula beats every
strong baseline; Phase 8 showed that simple generated-input mismatch is already
very strong. The new contribution is the low-budget targeted input policy and a
clean source-known semantic-drift auditing setup where fixture/static checks miss
localized errors.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_decision(path: Path, summary: dict[str, Any]) -> None:
    text = f"""# Decompilation Faithfulness Phase 13 Decision

## Verdict

`{summary['verdict']}`

## Decision

Use `fixture-neighbor-first low-budget dynamic re-execution` as the current paper
method name and default method table row.

The paper should claim source-known localized semantic drift auditing, not
decompiler-generation SOTA. Phase 12 is strong enough for the main method table,
but CCF-A readiness still needs runtime/cost, CI, failure taxonomy, and stronger
external benchmark positioning.

## Next Step

Run a Phase 14 paper-readiness hardening pass:

1. add bootstrap confidence intervals for Phase12;
2. add runtime/cost measurements;
3. summarize remaining misses;
4. convert the Phase13 table into the draft paper section.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
