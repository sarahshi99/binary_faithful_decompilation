from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_PHASE2_V3_JSON = Path(
    "docs/paper_agent/decompile_faithfulness_phase2_v3_boundary_trace.json"
)
DEFAULT_PHASE3_MANIFEST = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_source_manifest.json"
)
DEFAULT_PHASE3_SOURCE_POOL = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_source_pool.json"
)
DEFAULT_PHASE3_SOURCE_SELECTION = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_source_selection.json"
)
DEFAULT_OUTPUT_JSON = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_readiness_preflight.json"
)
DEFAULT_OUTPUT_ZH = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_readiness_preflight.zh.md"
)

EXCLUDED_SOURCE_DIRS = {
    ".git",
    "__pycache__",
    "analysis_outputs",
    "docs",
    "tests",
}


@dataclass(frozen=True)
class SourceCandidate:
    path: str
    kind: str


def main() -> None:
    args = parse_args()
    summary = run_preflight(
        repo_root=args.repo_root,
        phase2_v3_json=args.phase2_v3_json,
        phase3_manifest=args.phase3_manifest,
        phase3_source_pool=args.phase3_source_pool,
        phase3_source_selection=args.phase3_source_selection,
        output_json=args.output_json,
        output_zh=args.output_zh,
        min_selected_functions=args.min_selected_functions,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "method_gate_passed": summary["method_gate_passed"],
                "repository_source_candidate_count": summary[
                    "repository_source_candidate_count"
                ],
                "selected_function_count": summary["selected_function_count"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--phase2-v3-json", type=Path, default=DEFAULT_PHASE2_V3_JSON)
    parser.add_argument("--phase3-manifest", type=Path, default=DEFAULT_PHASE3_MANIFEST)
    parser.add_argument("--phase3-source-pool", type=Path, default=DEFAULT_PHASE3_SOURCE_POOL)
    parser.add_argument(
        "--phase3-source-selection",
        type=Path,
        default=DEFAULT_PHASE3_SOURCE_SELECTION,
    )
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--min-selected-functions", type=int, default=5)
    return parser.parse_args()


def run_preflight(
    repo_root: Path,
    phase2_v3_json: Path,
    phase3_manifest: Path,
    output_json: Path,
    output_zh: Path,
    phase3_source_pool: Path = DEFAULT_PHASE3_SOURCE_POOL,
    phase3_source_selection: Path = DEFAULT_PHASE3_SOURCE_SELECTION,
    min_selected_functions: int = 5,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    phase2_v3_json = _resolve_under_repo(repo_root, phase2_v3_json)
    phase3_manifest = _resolve_under_repo(repo_root, phase3_manifest)
    phase3_source_pool = _resolve_under_repo(repo_root, phase3_source_pool)
    phase3_source_selection = _resolve_under_repo(repo_root, phase3_source_selection)
    output_json = _resolve_under_repo(repo_root, output_json)
    output_zh = _resolve_under_repo(repo_root, output_zh)
    method_summary = _read_json_if_exists(phase2_v3_json)
    method_gate_passed = _method_gate_passed(method_summary)
    source_candidates = find_repository_source_candidates(repo_root)
    selected_functions = _read_selected_functions(phase3_manifest)
    pool_summary = _read_source_pool_summary(phase3_source_pool)
    selection_summary = _read_json_if_exists(phase3_source_selection)
    selected_function_count = len(selected_functions)
    fixture_ready_count = sum(
        1 for item in selected_functions if item.get("fixtures") and item.get("oracle")
    )
    summary: dict[str, Any] = {
        "phase2_v3_json": str(phase2_v3_json),
        "phase2_v3_verdict": method_summary.get("verdict"),
        "phase2_v3_pairwise_auc": method_summary.get("pairwise_auc"),
        "phase2_v3_fixture_collapse": method_summary.get("fixture_collapse"),
        "phase2_v3_trace_zero_blind_spot_wrong_count": method_summary.get(
            "trace_zero_blind_spot_wrong_count"
        ),
        "method_gate_passed": method_gate_passed,
        "repository_source_candidate_count": len(source_candidates),
        "repository_source_candidates": [
            {"path": candidate.path, "kind": candidate.kind}
            for candidate in source_candidates[:50]
        ],
        "excluded_source_dirs": sorted(EXCLUDED_SOURCE_DIRS),
        "phase3_manifest": str(phase3_manifest),
        "phase3_manifest_exists": phase3_manifest.exists(),
        "phase3_source_pool": str(phase3_source_pool),
        "phase3_source_pool_exists": phase3_source_pool.exists(),
        "phase3_source_pool_function_count": pool_summary["function_count"],
        "phase3_source_selection": str(phase3_source_selection),
        "phase3_source_selection_exists": phase3_source_selection.exists(),
        "phase3_source_selection_verdict": selection_summary.get("verdict"),
        "phase3_source_selection_eligible_count": selection_summary.get("eligible_count"),
        "phase3_source_selection_subset_count": selection_summary.get("subset_count"),
        "selected_function_count": selected_function_count,
        "fixture_ready_count": fixture_ready_count,
        "min_selected_functions": min_selected_functions,
    }
    summary["verdict"] = _verdict(
        method_gate_passed=method_gate_passed,
        manifest_exists=phase3_manifest.exists(),
        selected_function_count=selected_function_count,
        fixture_ready_count=fixture_ready_count,
        min_selected_functions=min_selected_functions,
        source_pool_exists=phase3_source_pool.exists(),
        source_pool_function_count=pool_summary["function_count"],
        source_selection_verdict=selection_summary.get("verdict"),
    )
    summary["recommended_next_steps"] = _recommended_next_steps(summary)
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def find_repository_source_candidates(repo_root: Path) -> list[SourceCandidate]:
    candidates: list[SourceCandidate] = []
    for path in sorted(repo_root.rglob("*")):
        if not path.is_file() or path.suffix not in {".c", ".h"}:
            continue
        if _is_excluded(path.relative_to(repo_root)):
            continue
        kind = "header" if path.suffix == ".h" else "c_source"
        candidates.append(SourceCandidate(str(path.relative_to(repo_root)), kind))
    return candidates


def _resolve_under_repo(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _is_excluded(relative_path: Path) -> bool:
    return any(part in EXCLUDED_SOURCE_DIRS for part in relative_path.parts)


def _read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _method_gate_passed(summary: dict[str, Any]) -> bool:
    return (
        summary.get("verdict") == "pass-v3-boundary-trace"
        and float(summary.get("pairwise_auc", 0.0)) >= 0.9623
        and summary.get("fixture_collapse") is False
        and summary.get("trace_zero_blind_spot_wrong_count") == 0
    )


def _read_selected_functions(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        functions = data.get("functions", [])
    else:
        functions = data
    if not isinstance(functions, list):
        raise TypeError("phase3 source manifest must contain a list of functions")
    return [item for item in functions if isinstance(item, dict)]


def _read_source_pool_summary(path: Path) -> dict[str, int]:
    if not path.exists():
        return {"function_count": 0}
    data = json.loads(path.read_text(encoding="utf-8"))
    functions = data.get("functions", []) if isinstance(data, dict) else []
    return {"function_count": len(functions) if isinstance(functions, list) else 0}


def _verdict(
    method_gate_passed: bool,
    manifest_exists: bool,
    selected_function_count: int,
    fixture_ready_count: int,
    min_selected_functions: int,
    source_pool_exists: bool = False,
    source_pool_function_count: int = 0,
    source_selection_verdict: str | None = None,
) -> str:
    if not method_gate_passed:
        return "blocked-method-gate"
    if source_selection_verdict == "ready-for-combinatorial-phase3-cpu-audit":
        return "ready-for-combinatorial-phase3-cpu-audit"
    if not manifest_exists:
        if source_pool_exists and source_pool_function_count >= min_selected_functions:
            return "needs-phase3-source-selection"
        return "needs-phase3-source-manifest"
    if selected_function_count < min_selected_functions:
        return "needs-more-phase3-sources"
    if fixture_ready_count < selected_function_count:
        return "needs-oracle-fixture-coverage"
    return "ready-for-phase3-cpu-audit"


def _recommended_next_steps(summary: dict[str, Any]) -> list[str]:
    if summary["verdict"] == "blocked-method-gate":
        return [
            "Do not start Phase 3. Re-run or repair the Phase 2 v3 boundary-trace gate first."
        ]
    if summary["verdict"] == "needs-phase3-source-manifest":
        return [
            "Create docs/paper_agent/decompile_faithfulness_phase3_source_pool.json with 10-12 source-known small C functions.",
            "Each selected function needs a source path, exact function name, bounded input domain, fixtures, and oracle policy.",
            "Keep this CPU-only until the manifest passes compile and oracle checks.",
        ]
    if summary["verdict"] == "needs-phase3-source-selection":
        return [
            "Run the Phase 3 source subset selector before CPU audit.",
            "Use multiple 5-10 function subsets so one bad selection does not decide the whole phase.",
            "Keep this CPU-only; GPU generation is still later.",
        ]
    if summary["verdict"] == "needs-more-phase3-sources":
        return [
            "Add more selected functions before running Phase 3.",
            "Target at least the configured min_selected_functions with diverse branch, loop, arithmetic, and bitwise behavior.",
        ]
    if summary["verdict"] == "needs-oracle-fixture-coverage":
        return [
            "Add fixtures and oracle policies for every selected function before candidate generation.",
            "Do not score candidates whose original source behavior cannot be re-executed under bounded inputs.",
        ]
    return [
        "Run the combinatorial Phase 3 CPU audit using v3 boundary trace across the recommended subsets.",
        "Treat one subset failure as local evidence; only repeated failures across diverse subsets should count against the method.",
        "Only consider GPU candidate generation after CPU audit confirms compile/oracle coverage and no fixture collapse.",
    ]


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown_zh(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    candidate_rows = "\n".join(
        f"| `{item['path']}` | `{item['kind']}` |"
        for item in summary["repository_source_candidates"]
    )
    if not candidate_rows:
        candidate_rows = "| _none_ | _none_ |"
    next_steps = "\n".join(
        f"{index}. {step}"
        for index, step in enumerate(summary["recommended_next_steps"], start=1)
    )
    text = f"""# Decompilation Faithfulness Phase 3 Readiness Preflight

- Verdict: `{summary['verdict']}`
- Method gate passed: `{summary['method_gate_passed']}`
- Phase 2 v3 verdict: `{summary['phase2_v3_verdict']}`
- Phase 2 v3 pairwise AUC: `{summary['phase2_v3_pairwise_auc']}`
- Phase 2 v3 fixture collapse: `{summary['phase2_v3_fixture_collapse']}`
- Phase 2 v3 trace-zero blind spots: `{summary['phase2_v3_trace_zero_blind_spot_wrong_count']}`
- Repository source candidate count: `{summary['repository_source_candidate_count']}`
- Phase 3 manifest exists: `{summary['phase3_manifest_exists']}`
- Phase 3 source pool exists: `{summary['phase3_source_pool_exists']}`
- Phase 3 source pool function count: `{summary['phase3_source_pool_function_count']}`
- Phase 3 source selection verdict: `{summary['phase3_source_selection_verdict']}`
- Phase 3 source selection eligible count: `{summary['phase3_source_selection_eligible_count']}`
- Phase 3 source selection subset count: `{summary['phase3_source_selection_subset_count']}`
- Selected function count: `{summary['selected_function_count']}`
- Fixture-ready count: `{summary['fixture_ready_count']}`

## Interpretation

Phase 2 v3 的方法 gate 已经足够支持设计 Phase 3 readiness check。现在 Phase 3 不再依赖一次性固定 5 个函数，而是使用 source pool + combinatorial subset selection。

因此当前还不应该直接启动 GPU candidate generation，也不应该宣称 arbitrary real-project transfer 已经完成。下一步应先在多个推荐子集上跑 CPU-only v3 boundary trace audit。

## Repository Source Candidates

Excluded dirs: `{', '.join(summary['excluded_source_dirs'])}`

| Path | Kind |
|---|---|
{candidate_rows}

## Recommended Next Steps

{next_steps}
"""
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
