from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import compile as ccompile


DEFAULT_POOL_JSON = Path("docs/paper_agent/decompile_faithfulness_phase3_source_pool.json")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase3_source_selection")
DEFAULT_OUTPUT_JSON = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_source_selection.json"
)
DEFAULT_OUTPUT_ZH = Path(
    "docs/paper_agent/decompile_faithfulness_phase3_source_selection.zh.md"
)
CRITICAL_TAGS = {
    "arithmetic",
    "bitwise",
    "boundary",
    "branch",
    "division",
    "loop",
    "multi_arg",
    "sign_zero",
}


def main() -> None:
    args = parse_args()
    summary = run_selection(
        repo_root=args.repo_root,
        pool_json=args.pool_json,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        min_size=args.min_size,
        max_size=args.max_size,
        top_k=args.top_k,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "eligible_count": summary["eligible_count"],
                "subset_count": summary["subset_count"],
                "recommended_subset_count": len(summary["recommended_subsets"]),
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--pool-json", type=Path, default=DEFAULT_POOL_JSON)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--min-size", type=int, default=5)
    parser.add_argument("--max-size", type=int, default=10)
    parser.add_argument("--top-k", type=int, default=12)
    return parser.parse_args()


def run_selection(
    repo_root: Path,
    pool_json: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    min_size: int = 5,
    max_size: int = 10,
    top_k: int = 12,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    pool = json.loads(pool_json.read_text(encoding="utf-8"))
    functions = pool["functions"]
    validation = validate_source_pool(repo_root, functions, output_dir / "compile")
    eligible_ids = {
        item["case_id"]
        for item in validation
        if item["source_exists"] and item["compiled"] and item["fixture_passed"]
    }
    eligible_functions = [
        function for function in functions if function["case_id"] in eligible_ids
    ]
    scored_subsets = enumerate_source_subsets(
        eligible_functions,
        min_size=min_size,
        max_size=max_size,
    )
    top_subsets = scored_subsets[:top_k]
    top_by_size = top_subset_by_size(scored_subsets)
    recommended_subsets = build_tiered_recommendations(
        scored_subsets,
        top_by_size=top_by_size,
        target_sizes=(min_size, min(7, max_size), max_size),
        limit=5,
    )
    summary: dict[str, Any] = {
        "pool_json": str(pool_json),
        "output_dir": str(output_dir),
        "candidate_count": len(functions),
        "eligible_count": len(eligible_functions),
        "validation": validation,
        "min_size": min_size,
        "max_size": max_size,
        "subset_count": len(scored_subsets),
        "top_subsets": top_subsets,
        "top_by_size": top_by_size,
        "recommended_subsets": recommended_subsets,
        "verdict": _verdict(len(eligible_functions), len(scored_subsets), min_size),
        "negative_conclusion_policy": pool.get("selection_policy", {}).get(
            "negative_conclusion_policy"
        ),
    }
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def validate_source_pool(
    repo_root: Path,
    functions: list[dict[str, Any]],
    output_dir: Path,
) -> list[dict[str, Any]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for function in functions:
        source_path = repo_root / function["source_path"]
        source_exists = source_path.exists()
        compiled = False
        fixture_passed = False
        exit_code: int | None = None
        stderr = ""
        if source_exists:
            harness = render_fixture_harness(
                source_path.read_text(encoding="utf-8"),
                function["function_name"],
                function.get("fixtures", []),
            )
            stem = function["case_id"]
            harness_path = output_dir / f"{stem}.harness.c"
            exe_path = output_dir / f"{stem}.harness.exe"
            harness_path.write_text(harness, encoding="utf-8")
            compile_result = ccompile.run_command(
                [
                    "/usr/bin/gcc",
                    "-std=c11",
                    "-Wall",
                    "-Wextra",
                    "-Werror",
                    "-O0",
                    str(harness_path),
                    "-o",
                    str(exe_path),
                ]
            )
            compiled = compile_result.returncode == 0
            stderr = compile_result.stderr
            if compiled:
                run_result = ccompile.run_command([str(exe_path)])
                fixture_passed = run_result.returncode == 0
                exit_code = run_result.returncode
                stderr += run_result.stderr
            else:
                exit_code = compile_result.returncode
        results.append(
            {
                "case_id": function["case_id"],
                "source_path": function["source_path"],
                "source_exists": source_exists,
                "compiled": compiled,
                "fixture_passed": fixture_passed,
                "exit_code": exit_code,
                "tags": function.get("tags", []),
                "risk_families": function.get("risk_families", []),
                "stderr": stderr[-1000:],
            }
        )
    return results


def render_fixture_harness(
    function_source: str,
    function_name: str,
    fixtures: list[dict[str, Any]],
) -> str:
    lines = [function_source.rstrip(), "", "int main(void) {"]
    for index, fixture in enumerate(fixtures):
        args = ", ".join(str(value) for value in fixture["args"])
        expected = int(fixture["expected"])
        lines.append(f"    if ({function_name}({args}) != {expected}) {{")
        lines.append(f"        return {100 + index};")
        lines.append("    }")
    lines.append("    return 0;")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def enumerate_source_subsets(
    functions: list[dict[str, Any]],
    min_size: int,
    max_size: int,
) -> list[dict[str, Any]]:
    subsets: list[dict[str, Any]] = []
    for size in range(min_size, min(max_size, len(functions)) + 1):
        for combo in itertools.combinations(functions, size):
            subsets.append(score_subset(combo))
    return sorted(
        subsets,
        key=lambda item: (
            item["score"],
            item["critical_tag_coverage"],
            item["risk_family_coverage"],
            -abs(item["size"] - 7),
        ),
        reverse=True,
    )


def score_subset(combo: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    case_ids = [function["case_id"] for function in combo]
    tags = sorted({tag for function in combo for tag in function.get("tags", [])})
    risk_families = sorted(
        {
            risk
            for function in combo
            for risk in function.get("risk_families", [])
        }
    )
    critical_covered = sorted(set(tags) & CRITICAL_TAGS)
    size = len(combo)
    score = (
        100 * len(critical_covered)
        + 20 * len(risk_families)
        + 4 * len(tags)
        + 2 * size
        - 3 * abs(size - 7)
    )
    return {
        "case_ids": case_ids,
        "size": size,
        "score": score,
        "tags": tags,
        "risk_families": risk_families,
        "critical_tags": critical_covered,
        "critical_tag_coverage": len(critical_covered),
        "risk_family_coverage": len(risk_families),
    }


def select_diverse_subsets(
    scored_subsets: list[dict[str, Any]],
    limit: int,
    max_jaccard: float = 0.7,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for subset in scored_subsets:
        if all(
            _jaccard(set(subset["case_ids"]), set(existing["case_ids"])) <= max_jaccard
            for existing in selected
        ):
            selected.append(subset)
        if len(selected) >= limit:
            return selected
    return selected


def top_subset_by_size(scored_subsets: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    top: dict[str, dict[str, Any]] = {}
    for subset in scored_subsets:
        key = str(subset["size"])
        if key not in top:
            top[key] = subset
    return top


def build_tiered_recommendations(
    scored_subsets: list[dict[str, Any]],
    top_by_size: dict[str, dict[str, Any]],
    target_sizes: tuple[int, ...],
    limit: int,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, ...]] = set()
    for size in target_sizes:
        subset = top_by_size.get(str(size))
        if subset is None:
            continue
        key = tuple(subset["case_ids"])
        if key not in seen_keys:
            selected.append(subset)
            seen_keys.add(key)

    for subset in select_diverse_subsets(scored_subsets, limit=limit):
        key = tuple(subset["case_ids"])
        if key not in seen_keys:
            selected.append(subset)
            seen_keys.add(key)
        if len(selected) >= limit:
            break
    return selected[:limit]


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def _verdict(eligible_count: int, subset_count: int, min_size: int) -> str:
    if eligible_count < min_size:
        return "needs-more-eligible-source-functions"
    if subset_count == 0:
        return "needs-subset-configuration"
    return "ready-for-combinatorial-phase3-cpu-audit"


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown_zh(path: Path, summary: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    validation_rows = "\n".join(
        "| `{case_id}` | `{compiled}` | `{fixture_passed}` | `{tags}` |".format(
            case_id=item["case_id"],
            compiled=item["compiled"],
            fixture_passed=item["fixture_passed"],
            tags=", ".join(item["tags"]),
        )
        for item in summary["validation"]
    )
    top_rows = "\n".join(
        "| {rank} | `{score}` | `{size}` | `{cases}` | `{tags}` |".format(
            rank=index,
            score=item["score"],
            size=item["size"],
            cases=", ".join(item["case_ids"]),
            tags=", ".join(item["critical_tags"]),
        )
        for index, item in enumerate(summary["top_subsets"], start=1)
    )
    by_size_rows = "\n".join(
        "| `{size}` | `{score}` | `{cases}` | `{tags}` |".format(
            size=size,
            score=item["score"],
            cases=", ".join(item["case_ids"]),
            tags=", ".join(item["critical_tags"]),
        )
        for size, item in sorted(
            summary["top_by_size"].items(),
            key=lambda pair: int(pair[0]),
        )
    )
    recommended_rows = "\n".join(
        "| {rank} | `{score}` | `{size}` | `{cases}` |".format(
            rank=index,
            score=item["score"],
            size=item["size"],
            cases=", ".join(item["case_ids"]),
        )
        for index, item in enumerate(summary["recommended_subsets"], start=1)
    )
    text = f"""# Decompilation Faithfulness Phase 3 Source Selection

- Verdict: `{summary['verdict']}`
- Candidate functions: `{summary['candidate_count']}`
- Eligible functions: `{summary['eligible_count']}`
- Enumerated subsets: `{summary['subset_count']}`
- Subset size range: `{summary['min_size']}` - `{summary['max_size']}`

## Key Point

Phase 3 不采用一次性固定 5 个函数的脆弱设计，而是先建立候选池，再枚举多个 5-10 函数子集。单个子集失败只能触发局部归因：可能是该函数、该风险族、该 oracle/domain 定义或 candidate distribution 有问题。只有多个低重叠、高覆盖子集反复失败，才应升级为方法层面的负结论。

Negative conclusion policy: {summary['negative_conclusion_policy']}

## Source Validation

| Case | Compiled | Fixture Passed | Tags |
|---|---:|---:|---|
{validation_rows}

## Top Subsets

| Rank | Score | Size | Cases | Critical Tags |
|---:|---:|---:|---|---|
{top_rows}

## Top Subset By Size

| Size | Score | Cases | Critical Tags |
|---:|---:|---|---|
{by_size_rows}

## Recommended Diverse Subsets

| Rank | Score | Size | Cases |
|---:|---:|---:|---|
{recommended_rows}

## How To Interpret Future Failures

1. 如果单个函数原始 source 编译或 fixture 失败，先修 source manifest，不记录为方法失败。
2. 如果一个子集失败但其他低重叠子集通过，记录为 subset-specific failure。
3. 如果同一风险族反复失败，进入 targeted hard-case analysis。
4. 只有多个低重叠、高覆盖子集都无法维持 no-fixture-collapse 和合理 AUC，才考虑 Phase 3 方法 gate 失败。
"""
    path.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
