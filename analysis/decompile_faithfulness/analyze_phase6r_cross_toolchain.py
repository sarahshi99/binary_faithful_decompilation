from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase6r_cross_toolchain_summary.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase6r_cross_toolchain_summary.zh.md")


def main() -> None:
    args = parse_args()
    summary = summarize_runs(
        ghidra_result_json=args.ghidra_result_json,
        radare2_json=args.radare2_json,
        output_json=args.output_json,
        output_zh=args.output_zh,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "ghidra_run_count": summary["ghidra_run_count"],
                "radare2_run_count": summary["radare2_run_count"],
                "all_ghidra_main_gates_pass": summary["all_ghidra_main_gates_pass"],
                "min_ghidra_sota_delta": summary["min_ghidra_sota_delta"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ghidra-result-json", type=Path, action="append", default=[])
    parser.add_argument("--radare2-json", type=Path, action="append", default=[])
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    return parser.parse_args()


def summarize_runs(
    ghidra_result_json: list[Path],
    radare2_json: list[Path],
    output_json: Path,
    output_zh: Path,
) -> dict[str, Any]:
    ghidra_runs = [ghidra_row(json.loads(path.read_text(encoding="utf-8")), path) for path in ghidra_result_json]
    radare2_runs = [radare2_row(json.loads(path.read_text(encoding="utf-8")), path) for path in radare2_json]
    ghidra_passes = [row["verdict"] == "pass-phase6r-real-decompiler-output-main-evidence" for row in ghidra_runs]
    deltas = [row["sota_delta_vs_best_baseline"] for row in ghidra_runs]
    summary = {
        "phase": "phase6r_cross_toolchain_summary",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "ghidra_run_count": len(ghidra_runs),
        "radare2_run_count": len(radare2_runs),
        "ghidra_runs": ghidra_runs,
        "radare2_runs": radare2_runs,
        "all_ghidra_main_gates_pass": bool(ghidra_runs) and all(ghidra_passes),
        "min_ghidra_sota_delta": min(deltas) if deltas else 0.0,
        "external_sota_claim_ready": False,
        "external_sota_claim_blocker": (
            "Needs explicit related-work baselines and at least one compile-ready second decompiler "
            "beyond Ghidra; current summary is cross-toolchain robustness, not external-paper SOTA."
        ),
    }
    summary["verdict"] = cross_toolchain_verdict(summary)
    write_json(output_json, summary)
    write_markdown(output_zh, summary)
    return summary


def ghidra_row(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    binary_compiler = payload.get("binary_compiler", "") or "/usr/bin/gcc"
    toolchain_label = payload.get("toolchain_label", "") or "default-gcc"
    return {
        "path": str(path),
        "tool": "ghidra",
        "toolchain_label": toolchain_label,
        "binary_compiler": binary_compiler,
        "verdict": payload.get("verdict", ""),
        "candidate_count": payload.get("candidate_count", 0),
        "ghidra_decompiled_count": payload.get("ghidra_decompiled_count", 0),
        "compile_pass_count": payload.get("compile_pass_count", 0),
        "source_function_count": payload.get("source_function_count", 0),
        "paired_case_count": payload.get("paired_case_count", 0),
        "fixture_only_auc": payload.get("baseline_auc", {}).get("fixture_only", 0.0),
        "static_structured_auc": payload.get("baseline_auc", {}).get("static_structured_proxy", 0.0),
        "v3_trace_total_auc": payload.get("baseline_auc", {}).get("v3_trace_total", 0.0),
        "sota_delta_vs_best_baseline": payload.get("sota_delta_vs_best_baseline", 0.0),
        "behavior_preserving_fp_rate": payload.get("v3_behavior_preserving_false_positive_rate", 0.0),
        "normalization_or_compile_fail_count": payload.get("failure_taxonomy", {}).get(
            "ghidra_or_normalization_failure",
            0,
        ),
    }


def radare2_row(payload: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "tool": "radare2",
        "toolchain_label": payload.get("toolchain_label", ""),
        "binary_compiler": payload.get("binary_compiler", ""),
        "verdict": payload.get("verdict", ""),
        "binary_count": payload.get("binary_count", 0),
        "compile_pass_count": payload.get("compile_pass_count", 0),
        "symbol_found_count": payload.get("symbol_found_count", 0),
        "pdc_c_like_count": payload.get("pdc_c_like_count", 0),
        "pdc_compile_ready_count": payload.get("pdc_compile_ready_count", 0),
        "ccfa_interpretation": payload.get("ccfa_interpretation", ""),
    }


def cross_toolchain_verdict(summary: dict[str, Any]) -> str:
    if summary["all_ghidra_main_gates_pass"] and summary["ghidra_run_count"] >= 2:
        if summary["radare2_run_count"] > 0:
            return "pass-phase6r-cross-toolchain-ghidra-plus-radare2-importability"
        return "pass-phase6r-cross-toolchain-ghidra"
    if summary["ghidra_run_count"] > 0:
        return "partial-phase6r-cross-toolchain"
    return "blocked-no-cross-toolchain-results"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    ghidra_rows = "\n".join(
        "| `{toolchain_label}` | `{candidate_count}` | `{compile_pass_count}` | "
        "`{paired_case_count}` | `{static_structured_auc:.4f}` | `{v3_trace_total_auc:.4f}` | "
        "`{sota_delta_vs_best_baseline:.4f}` | `{normalization_or_compile_fail_count}` | `{verdict}` |".format(**row)
        for row in summary["ghidra_runs"]
    )
    radare2_rows = "\n".join(
        "| `{toolchain_label}` | `{binary_count}` | `{symbol_found_count}` | `{pdc_c_like_count}` | "
        "`{pdc_compile_ready_count}` | `{verdict}` |".format(**row)
        for row in summary["radare2_runs"]
    )
    text = f"""# Decompilation Faithfulness Phase 6R Cross-toolchain Summary

- Verdict: `{summary['verdict']}`
- Ghidra run count: `{summary['ghidra_run_count']}`
- radare2 run count: `{summary['radare2_run_count']}`
- All Ghidra main gates pass: `{summary['all_ghidra_main_gates_pass']}`
- Min Ghidra SOTA delta vs in-project baseline: `{summary['min_ghidra_sota_delta']:.4f}`
- External-paper SOTA claim ready: `{summary['external_sota_claim_ready']}`
- External-paper SOTA blocker: {summary['external_sota_claim_blocker']}

## Ghidra Main Evidence

| Toolchain | Candidates | Compile pass | Paired cases | Static AUC | V3 AUC | Delta | Norm/compile fail | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---|
{ghidra_rows}

## radare2 Importability

| Toolchain | Binaries | Symbols | Pseudo-C-like | Compile-ready C | Verdict |
|---|---:|---:|---:|---:|---|
{radare2_rows}

## Interpretation

This is cross-toolchain robustness evidence. It strengthens the Ghidra-based claim by checking whether the result survives different binary-producing GCC versions. radare2 is kept as real-tool importability evidence because its `pdc` output is pseudo-C, not compile-ready C.

This still does not by itself establish external-paper SOTA. For that, the project needs explicit related-work baselines, at least one second compile-ready decompiler source, and a broader benchmark table.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
