from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase7_second_decompiler_decision.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase7_second_decompiler_decision.zh.md")
DEFAULT_GHIDRA_HEADLESS = Path(
    "analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/"
    "ghidra_12.1.2_PUBLIC/support/analyzeHeadless"
)
DEFAULT_RADARE2 = Path("analysis_outputs/decompile_faithfulness/phase6r_tools/apt_radare2/root/usr/bin/radare2")
RADARE2_RESULT_FILES = (
    Path("docs/paper_agent/decompile_faithfulness_phase6r_radare2_smoke.json"),
    Path("docs/paper_agent/decompile_faithfulness_phase6r_radare2_smoke_gcc11.json"),
    Path("docs/paper_agent/decompile_faithfulness_phase6r_radare2_smoke_gcc9.json"),
)


def main() -> None:
    args = parse_args()
    summary = run_decision(
        repo_root=args.repo_root,
        output_json=args.output_json,
        output_zh=args.output_zh,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "ready_tool_count": summary["ready_tool_count"],
                "available_tool_count": summary["available_tool_count"],
                "ghidra_first_decompiler_ready": summary["ghidra_first_decompiler_ready"],
                "radare2_importability_only": summary["radare2_importability_only"],
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


def run_decision(repo_root: Path, output_json: Path, output_zh: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    tools = build_tool_rows(repo_root)
    ready_tools = [row for row in tools if row["available"] and row["compile_ready_c_candidate"]]
    available_tools = [row for row in tools if row["available"]]
    summary = {
        "phase": "phase7_second_compile_ready_decompiler_decision",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "repo_root": str(repo_root),
        "tools": tools,
        "ready_tool_count": len(ready_tools),
        "available_tool_count": len(available_tools),
        "ghidra_first_decompiler_ready": ghidra_headless_path(repo_root).exists(),
        "radare2_importability_only": radare2_importability_only(repo_root),
        "verdict": second_decompiler_verdict(tools),
    }
    summary["recommended_next_action"] = recommended_next_action(summary)
    _write_json(output_json, summary)
    write_markdown(output_zh, summary)
    return summary


def build_tool_rows(repo_root: Path) -> list[dict[str, Any]]:
    ghidra = ghidra_headless_path(repo_root)
    radare2 = radare2_path(repo_root)
    return [
        tool_row(
            name="Ghidra",
            available=ghidra.exists(),
            detected_path=str(ghidra) if ghidra.exists() else "",
            evidence_kind="first_compile_ready_decompiler",
            compile_ready_c_candidate=False,
            reason="Already used as Phase 6R main decompiler; not counted as the second decompiler.",
        ),
        tool_row(
            name="radare2/r2 pdc",
            available=radare2.exists() or bool(shutil.which("radare2") or shutil.which("r2")),
            detected_path=str(radare2) if radare2.exists() else (shutil.which("radare2") or shutil.which("r2") or ""),
            evidence_kind="real_tool_importability_only",
            compile_ready_c_candidate=False,
            reason="Project Phase 6R shows pdc pseudo-C/importability, but not compile-ready C function candidates.",
        ),
        tool_row(
            name="RetDec",
            available=bool(shutil.which("retdec-decompiler")),
            detected_path=shutil.which("retdec-decompiler") or "",
            evidence_kind="candidate_second_decompiler",
            compile_ready_c_candidate=bool(shutil.which("retdec-decompiler")),
            reason="Could be a second compile-ready C decompiler if installed and its output normalizes/compiles.",
        ),
        tool_row(
            name="rev.ng",
            available=bool(shutil.which("revng")),
            detected_path=shutil.which("revng") or "",
            evidence_kind="candidate_second_decompiler",
            compile_ready_c_candidate=bool(shutil.which("revng")),
            reason="Could provide decompiled C/IR if installed; not available in this environment.",
        ),
        tool_row(
            name="angr AIL",
            available=all(python_module_available(name) for name in ["angr", "ailment", "claripy", "capstone"]),
            detected_path=python_module_paths(["angr", "ailment", "claripy", "capstone"]),
            evidence_kind="candidate_evaluable_ir",
            compile_ready_c_candidate=False,
            reason="Even if available, this would likely be evaluable IR rather than compile-ready C; current modules are absent.",
        ),
        tool_row(
            name="Binary Ninja",
            available=bool(shutil.which("binaryninja") or shutil.which("bn_headless") or python_module_available("binaryninja")),
            detected_path=shutil.which("binaryninja") or shutil.which("bn_headless") or python_module_paths(["binaryninja"]),
            evidence_kind="candidate_second_decompiler_or_mlil",
            compile_ready_c_candidate=False,
            reason="License/tool not detected; MLIL/HLIL may be useful, but compile-ready C is not assumed.",
        ),
        tool_row(
            name="Hex-Rays / IDA",
            available=bool(shutil.which("ida") or shutil.which("idat") or shutil.which("idat64")),
            detected_path=shutil.which("ida") or shutil.which("idat") or shutil.which("idat64") or "",
            evidence_kind="candidate_second_decompiler",
            compile_ready_c_candidate=bool(shutil.which("ida") or shutil.which("idat") or shutil.which("idat64")),
            reason="Could be strong second decompiler evidence if licensed and headless export is available.",
        ),
    ]


def tool_row(
    name: str,
    available: bool,
    detected_path: str,
    evidence_kind: str,
    compile_ready_c_candidate: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "available": available,
        "detected_path": detected_path,
        "evidence_kind": evidence_kind,
        "compile_ready_c_candidate": compile_ready_c_candidate,
        "reason": reason,
    }


def ghidra_headless_path(repo_root: Path) -> Path:
    return _resolve(repo_root, DEFAULT_GHIDRA_HEADLESS)


def radare2_path(repo_root: Path) -> Path:
    return _resolve(repo_root, DEFAULT_RADARE2)


def radare2_importability_only(repo_root: Path) -> bool:
    for path in RADARE2_RESULT_FILES:
        resolved = _resolve(repo_root, path)
        if not resolved.exists():
            continue
        payload = json.loads(resolved.read_text(encoding="utf-8"))
        if payload.get("pdc_c_like_count", 0) > 0 and payload.get("pdc_compile_ready_count", 0) == 0:
            return True
    return False


def python_module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def python_module_paths(names: list[str]) -> str:
    paths = []
    for name in names:
        spec = importlib.util.find_spec(name)
        paths.append(f"{name}:{spec.origin if spec is not None else 'not found'}")
    return "; ".join(paths)


def second_decompiler_verdict(tools: list[dict[str, Any]]) -> str:
    if any(
        row["available"]
        and row["compile_ready_c_candidate"]
        and row["name"] != "Ghidra"
        for row in tools
    ):
        return "ready-second-decompiler-run"
    if any(row["available"] and row["name"] == "radare2/r2 pdc" for row in tools):
        return "blocked-awaiting-second-decompiler-approval"
    return "blocked-awaiting-second-decompiler-approval"


def recommended_next_action(summary: dict[str, Any]) -> str:
    if summary["verdict"] == "ready-second-decompiler-run":
        return "Run a Phase 7D full import for the available second compile-ready decompiler."
    return (
        "No second compile-ready decompiler is available locally. Keep Ghidra as the main real-decompiler "
        "evidence, keep radare2 as importability-only, and proceed to Phase 7E LLM-generated/LLM-judge "
        "public benchmark baselines on GPU 2/3 unless the user approves installing RetDec, rev.ng, "
        "Binary Ninja, or Hex-Rays."
    )


def write_markdown(path: Path, summary: dict[str, Any]) -> None:
    rows = "\n".join(
        "| `{name}` | `{available}` | `{compile_ready_c_candidate}` | `{evidence_kind}` | `{detected_path}` | {reason} |".format(**row)
        for row in summary["tools"]
    )
    text = f"""# Decompilation Faithfulness Phase 7D Second Decompiler Decision

- Verdict: `{summary['verdict']}`
- Ready second-decompiler tool count: `{summary['ready_tool_count']}`
- Available tool count: `{summary['available_tool_count']}`
- Ghidra first decompiler ready: `{summary['ghidra_first_decompiler_ready']}`
- radare2 importability-only: `{summary['radare2_importability_only']}`
- Recommended next action: {summary['recommended_next_action']}

## Tool Matrix

| Tool | Available | Compile-ready C candidate | Evidence kind | Path/module | Reason |
|---|---:|---:|---|---|---|
{rows}

## Interpretation

Phase 7D does not currently provide a second compile-ready decompiler. Ghidra remains the first real-decompiler main evidence; radare2 remains real-tool importability evidence because its `pdc` output is pseudo-C rather than compile-ready C.

For the CCF-A/SOTA path, the next practical step is Phase 7E: run LLM-generated candidates or an LLM judge baseline on the public CodeFuse subset using GPU 2/3, unless a new decompiler dependency is approved.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
