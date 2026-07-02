from __future__ import annotations

import argparse
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase7_benchmark_feasibility.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase7_benchmark_feasibility.zh.md")


@dataclass(frozen=True)
class BenchmarkSpec:
    name: str
    aliases: tuple[str, ...]
    expected_input_format: str
    source_known_possible: bool
    compile_harness_needed: bool
    license_or_repro_note: str


def main() -> None:
    args = parse_args()
    summary = run_preflight(
        repo_root=args.repo_root,
        output_json=args.output_json,
        output_zh=args.output_zh,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "available_count": summary["available_count"],
                "format_identified_count": summary["format_identified_count"],
                "benchmark_count": summary["benchmark_count"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    return parser.parse_args()


def run_preflight(repo_root: Path, output_json: Path, output_zh: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    rows = [
        build_row(repo_root, spec, find_local_matches(repo_root, spec))
        for spec in benchmark_specs()
    ]
    summary = {
        "phase": "phase7_benchmark_feasibility",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "benchmark_count": len(rows),
        "available_count": sum(1 for row in rows if row["available"]),
        "format_identified_count": sum(1 for row in rows if row["format_identified"]),
        "benchmarks": rows,
        "network_used": False,
        "dependency_install_used": False,
        "verdict": classify_verdict(rows),
    }
    write_json(output_json, summary)
    write_markdown(output_zh, summary)
    return summary


def benchmark_specs() -> list[BenchmarkSpec]:
    return [
        BenchmarkSpec(
            name="Decompile-Eval / HumanEval-style",
            aliases=("decompile-eval", "humaneval-decompile", "human-eval-decompile", "humaneval"),
            expected_input_format="small source-known programming tasks with tests or executable oracles",
            source_known_possible=True,
            compile_harness_needed=True,
            license_or_repro_note="Requires dataset/repo availability; keep prompt/test split provenance.",
        ),
        BenchmarkSpec(
            name="ExeBench-style",
            aliases=("exebench", "exe-bench"),
            expected_input_format="source/binary function pairs or executable tasks",
            source_known_possible=True,
            compile_harness_needed=True,
            license_or_repro_note="Requires source/binary extraction and local execution harness.",
        ),
        BenchmarkSpec(
            name="DecompileBench",
            aliases=("decompilebench", "decompile-bench-acl"),
            expected_input_format="real-world binary/source function pairs with semantic validation metadata",
            source_known_possible=True,
            compile_harness_needed=True,
            license_or_repro_note="ACL Findings benchmark; verify data license and split usage.",
        ),
        BenchmarkSpec(
            name="CodeFuse-DeBench",
            aliases=("codefuse-debench", "debench"),
            expected_input_format="benchmark framework with readability/recompilation/functionality stages",
            source_known_possible=True,
            compile_harness_needed=True,
            license_or_repro_note="GitHub benchmark; verify license and whether generated artifacts are redistributable.",
        ),
        BenchmarkSpec(
            name="Decompile-Bench",
            aliases=("decompile-bench", "decompile_bench"),
            expected_input_format="large binary-source function pair benchmark",
            source_known_possible=True,
            compile_harness_needed=True,
            license_or_repro_note="Large benchmark; likely requires explicit download/storage plan.",
        ),
    ]


def find_local_matches(repo_root: Path, spec: BenchmarkSpec) -> list[str]:
    roots = [
        repo_root,
        repo_root / "analysis_inputs",
        repo_root / "external",
        repo_root / "third_party",
        repo_root / "datasets",
        repo_root / "benchmarks",
    ]
    aliases = tuple(alias.lower() for alias in spec.aliases)
    matches: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.name.lower() in aliases or any(alias in path.name.lower() for alias in aliases):
                matches.append(path)
    unique = sorted({path.resolve() for path in matches})
    return [str(path) for path in unique]


def build_row(repo_root: Path, spec: BenchmarkSpec, matches: list[str]) -> dict[str, Any]:
    available = bool(matches)
    format_identified = any(path_has_identifiable_format(Path(match)) for match in matches)
    recommended = (
        "import local benchmark with a dedicated adapter"
        if format_identified
        else "inspect local files to identify format"
        if available
        else "request approval to download or point Codex to a local benchmark checkout"
    )
    return {
        "benchmark_name": spec.name,
        "aliases": list(spec.aliases),
        "available": available,
        "local_paths": matches,
        "format_identified": format_identified,
        "expected_input_format": spec.expected_input_format,
        "source_known_possible": spec.source_known_possible,
        "compile_harness_needed": spec.compile_harness_needed,
        "license_or_repro_note": spec.license_or_repro_note,
        "recommended_next_action": recommended,
        "repo_root": str(repo_root),
    }


def path_has_identifiable_format(path: Path) -> bool:
    if path.is_file():
        return path.suffix.lower() in {".json", ".jsonl", ".csv", ".c", ".cpp", ".tar", ".gz", ".zip"}
    if not path.is_dir():
        return False
    if (path / ".git").exists() and git_tree_has_identifiable_format(path):
        return True
    marker_names = {
        "README.md",
        "readme.md",
        "LICENSE",
        "license",
        "dataset.json",
        "metadata.json",
        "manifest.json",
    }
    if any((path / marker).exists() for marker in marker_names):
        return True
    return any(child.suffix.lower() in {".json", ".jsonl", ".csv", ".c", ".cpp"} for child in path.glob("*"))


def git_tree_has_identifiable_format(path: Path) -> bool:
    try:
        completed = subprocess.run(
            ["git", "-C", str(path), "ls-tree", "--name-only", "HEAD"],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    if completed.returncode != 0:
        return False
    names = tuple(line.strip() for line in completed.stdout.splitlines() if line.strip())
    return tree_names_identify_benchmark(names)


def tree_names_identify_benchmark(names: tuple[str, ...] | list[str] | set[str]) -> bool:
    name_set = {name.rstrip("/") for name in names}
    public_benchmark_markers = {
        "binbench-x64.yaml",
        "binbench-arm.yaml",
        "binbench-mips.yaml",
        "binbench-x86.yaml",
        "decompiled",
        "evaluator",
        "src",
    }
    codefuse_markers = {"src", "decompiled", "evaluator", "binbench-x64.yaml"}
    if len(name_set & codefuse_markers) >= 2:
        return True
    return bool(name_set & public_benchmark_markers)


def classify_verdict(rows: list[dict[str, Any]]) -> str:
    if any(row["available"] and row["format_identified"] for row in rows):
        return "ready-public-benchmark-import"
    if any(row["available"] for row in rows):
        return "blocked-benchmark-format-unknown"
    return "blocked-needs-benchmark-download-approval"


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    rows = "\n".join(
        "| `{benchmark_name}` | `{available}` | `{format_identified}` | `{source_known_possible}` | "
        "`{compile_harness_needed}` | {recommended_next_action} |".format(**row)
        for row in summary["benchmarks"]
    )
    text = f"""# Decompilation Faithfulness Phase 7 Benchmark Feasibility

- Verdict: `{summary['verdict']}`
- Benchmark count: `{summary['benchmark_count']}`
- Available count: `{summary['available_count']}`
- Format identified count: `{summary['format_identified_count']}`
- Network used: `{summary['network_used']}`
- Dependency install used: `{summary['dependency_install_used']}`

## Availability Matrix

| Benchmark | Available | Format identified | Source-known possible | Compile harness needed | Recommended next action |
|---|---:|---:|---:|---:|---|
{rows}

## Interpretation

This preflight only scans local project paths. It does not download benchmarks, install dependencies, or use GPU.

If the verdict is `blocked-needs-benchmark-download-approval`, Phase 7 cannot yet claim public benchmark alignment. The next step is to approve one benchmark acquisition route or provide a local checkout path.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
