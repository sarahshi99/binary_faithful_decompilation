from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import fixtures
from analysis.decompile_faithfulness import run_phase5_gpu_generated_full as phase5_gpu


DEFAULT_MANIFEST = Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json")
DEFAULT_TOOL_ROOT = Path("analysis_outputs/decompile_faithfulness/phase6r_tools/apt_radare2/root")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase6r_radare2_smoke")
DEFAULT_OUTPUT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase6r_radare2_smoke.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase6r_radare2_smoke.zh.md")
DEFAULT_OPT_LEVELS = ("O0", "O2")
DEFAULT_BINARY_COMPILER = Path("/usr/bin/gcc")


@dataclass(frozen=True)
class R2Paths:
    tool_root: Path
    binary: Path
    lib_dir: Path


def main() -> None:
    args = parse_args()
    summary = run_smoke(
        repo_root=args.repo_root,
        manifest_json=args.manifest_json,
        tool_root=args.tool_root,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_zh=args.output_zh,
        opt_levels=args.opt_level,
        binary_compiler=args.binary_compiler,
        toolchain_label=args.toolchain_label,
    )
    print(
        json.dumps(
            {
                "verdict": summary["verdict"],
                "binary_count": summary["binary_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "symbol_found_count": summary["symbol_found_count"],
                "pdf_output_count": summary["pdf_output_count"],
                "pdc_output_count": summary["pdc_output_count"],
                "pdc_c_like_count": summary["pdc_c_like_count"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--tool-root", type=Path, default=DEFAULT_TOOL_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--opt-level", action="append", default=list(DEFAULT_OPT_LEVELS))
    parser.add_argument("--binary-compiler", type=Path, default=DEFAULT_BINARY_COMPILER)
    parser.add_argument("--toolchain-label", default="")
    return parser.parse_args()


def run_smoke(
    repo_root: Path,
    manifest_json: Path,
    tool_root: Path,
    output_dir: Path,
    output_json: Path,
    output_zh: Path,
    opt_levels: list[str],
    binary_compiler: Path,
    toolchain_label: str,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    manifest_json = _resolve(repo_root, manifest_json)
    tool_root = _resolve(repo_root, tool_root)
    output_dir = _resolve(repo_root, output_dir)
    output_json = _resolve(repo_root, output_json)
    output_zh = _resolve(repo_root, output_zh)
    binary_compiler = _resolve(repo_root, binary_compiler)
    if not toolchain_label:
        toolchain_label = binary_compiler.name

    r2 = r2_paths(tool_root)
    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    entries = [
        entry for entry in manifest.get("functions", [])
        if entry.get("counts_for_phase5_real_project_gate")
    ]

    binary_dir = output_dir / "binaries"
    raw_dir = output_dir / "raw"
    for path in [binary_dir, raw_dir]:
        path.mkdir(parents=True, exist_ok=True)

    version = run_r2_version(r2)
    records: list[dict[str, Any]] = []
    for entry in entries:
        case = phase5_gpu._case_from_manifest_entry(repo_root, entry)
        for opt_level in opt_levels:
            records.append(
                smoke_record_for_case(
                    case=case,
                    opt_level=opt_level,
                    r2=r2,
                    binary_dir=binary_dir,
                    raw_dir=raw_dir,
                    binary_compiler=binary_compiler,
                    toolchain_label=toolchain_label,
                )
            )

    records_path = output_dir / "records.jsonl"
    _write_jsonl(records_path, records)
    summary = summarize(
        records=records,
        records_path=records_path,
        output_dir=output_dir,
        r2=r2,
        version=version,
        opt_levels=opt_levels,
        binary_compiler=binary_compiler,
        toolchain_label=toolchain_label,
    )
    _write_json(output_json, summary)
    _write_markdown_zh(output_zh, summary)
    return summary


def r2_paths(tool_root: Path) -> R2Paths:
    return R2Paths(
        tool_root=tool_root,
        binary=tool_root / "usr/bin/radare2",
        lib_dir=tool_root / "usr/lib/x86_64-linux-gnu",
    )


def run_r2_version(r2: R2Paths) -> str:
    result = run_with_r2_env([str(r2.binary), "-v"], r2, timeout_s=5)
    return (result.stdout + result.stderr).strip()


def smoke_record_for_case(
    case: fixtures.FunctionCase,
    opt_level: str,
    r2: R2Paths,
    binary_dir: Path,
    raw_dir: Path,
    binary_compiler: Path,
    toolchain_label: str,
) -> dict[str, Any]:
    source_path = binary_dir / f"{case.case_id}_{opt_level}.c"
    exe_path = binary_dir / f"{case.case_id}_{opt_level}.exe"
    source_path.write_text(
        fixtures.render_translation_unit(case, case.function_source),
        encoding="utf-8",
    )
    compile_result = ccompile.run_command(
        [
            str(binary_compiler),
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            f"-{opt_level}",
            "-g",
            "-fno-pie",
            "-no-pie",
            "-fcf-protection=none",
            str(source_path),
            "-o",
            str(exe_path),
        ]
    )
    record: dict[str, Any] = {
        "case_id": case.case_id,
        "function_name": case.function_name,
        "optimization_level": opt_level,
        "binary_compiler": str(binary_compiler),
        "toolchain_label": toolchain_label,
        "source_path": str(source_path),
        "binary_path": str(exe_path),
        "compiled": compile_result.returncode == 0,
        "compile_exit_code": compile_result.returncode,
        "compile_stderr_tail": compile_result.stderr[-1200:],
    }
    if compile_result.returncode != 0:
        return {
            **record,
            "symbol_found": False,
            "pdf_output_nonempty": False,
            "pdc_output_nonempty": False,
            "pdc_c_like": False,
            "failure_category": "compile_failure",
        }

    nm_result = ccompile.run_command(["/usr/bin/nm", "-C", str(exe_path)])
    symbol_address = parse_nm_symbol_address(nm_result.stdout, case.function_name)
    record.update(
        {
            "nm_exit_code": nm_result.returncode,
            "symbol_found": symbol_address is not None,
            "symbol_address": symbol_address or "",
        }
    )
    if symbol_address is None:
        return {
            **record,
            "pdf_output_nonempty": False,
            "pdc_output_nonempty": False,
            "pdc_c_like": False,
            "failure_category": "symbol_not_found",
        }

    pdf_path = raw_dir / f"{case.case_id}_{opt_level}.pdf.txt"
    pdc_path = raw_dir / f"{case.case_id}_{opt_level}.pdc.txt"
    pdf = run_r2_function_command(r2, exe_path, symbol_address, case.function_name, "pdf")
    pdc = run_r2_function_command(r2, exe_path, symbol_address, case.function_name, "pdc")
    pdf_text = pdf.stdout + pdf.stderr
    pdc_text = pdc.stdout + pdc.stderr
    pdf_path.write_text(pdf_text, encoding="utf-8")
    pdc_path.write_text(pdc_text, encoding="utf-8")
    pdc_c_like = is_pdc_c_like(pdc_text)
    return {
        **record,
        "pdf_exit_code": pdf.returncode,
        "pdc_exit_code": pdc.returncode,
        "pdf_output_path": str(pdf_path),
        "pdc_output_path": str(pdc_path),
        "pdf_output_nonempty": output_has_body(pdf_text),
        "pdc_output_nonempty": output_has_body(pdc_text),
        "pdc_c_like": pdc_c_like,
        "pdc_compile_ready": False,
        "failure_category": "" if pdc_c_like else "pseudo_c_not_compile_ready",
    }


def parse_nm_symbol_address(nm_stdout: str, function_name: str) -> str | None:
    pattern = re.compile(rf"^([0-9a-fA-F]+)\s+[Tt]\s+{re.escape(function_name)}$")
    for line in nm_stdout.splitlines():
        match = pattern.match(line.strip())
        if match:
            return "0x" + match.group(1).lower()
    return None


def run_r2_function_command(
    r2: R2Paths,
    binary_path: Path,
    symbol_address: str,
    function_name: str,
    command: str,
) -> subprocess.CompletedProcess[str]:
    return run_with_r2_env(
        [
            str(r2.binary),
            "-q",
            "-e",
            "scr.color=false",
            "-e",
            "asm.bytes=false",
            "-c",
            f"s {symbol_address}",
            "-c",
            f"af {function_name}",
            "-c",
            command,
            "-c",
            "q",
            str(binary_path),
        ],
        r2,
        timeout_s=15,
    )


def run_with_r2_env(
    argv: list[str],
    r2: R2Paths,
    timeout_s: int,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    current = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = str(r2.lib_dir) + (f":{current}" if current else "")
    try:
        return subprocess.run(
            argv,
            timeout=timeout_s,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        return subprocess.CompletedProcess(
            argv,
            124,
            stdout,
            f"{stderr}\ncommand timed out after {timeout_s} seconds",
        )


def output_has_body(text: str) -> bool:
    stripped = strip_ansi(text).strip()
    if not stripped:
        return False
    bad_fragments = [
        "Cannot find function",
        "Invalid address",
        "No such file",
    ]
    return not all(fragment in stripped for fragment in bad_fragments)


def is_pdc_c_like(text: str) -> bool:
    stripped = strip_ansi(text)
    return "function " in stripped and "return" in stripped and "{" in stripped and "}" in stripped


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def summarize(
    records: list[dict[str, Any]],
    records_path: Path,
    output_dir: Path,
    r2: R2Paths,
    version: str,
    opt_levels: list[str],
    binary_compiler: Path,
    toolchain_label: str,
) -> dict[str, Any]:
    summary = {
        "phase": "phase6r_radare2_importability_smoke",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "output_dir": str(output_dir),
        "records_path": str(records_path),
        "tool": "radare2",
        "tool_path": str(r2.binary),
        "tool_version": version,
        "binary_compiler": str(binary_compiler),
        "toolchain_label": toolchain_label,
        "optimization_levels": opt_levels,
        "binary_count": len(records),
        "compile_pass_count": sum(1 for record in records if record["compiled"]),
        "symbol_found_count": sum(1 for record in records if record.get("symbol_found")),
        "pdf_output_count": sum(1 for record in records if record.get("pdf_output_nonempty")),
        "pdc_output_count": sum(1 for record in records if record.get("pdc_output_nonempty")),
        "pdc_c_like_count": sum(1 for record in records if record.get("pdc_c_like")),
        "pdc_compile_ready_count": sum(1 for record in records if record.get("pdc_compile_ready")),
        "failure_counts": count_by(
            [record for record in records if record.get("failure_category")],
            "failure_category",
        ),
    }
    summary["verdict"] = smoke_verdict(summary)
    summary["ccfa_interpretation"] = (
        "real-tool-importability-only; radare2 pdc output is pseudo-C and not yet compile-ready"
    )
    return summary


def smoke_verdict(summary: dict[str, Any]) -> str:
    if (
        summary["binary_count"] >= 50
        and summary["compile_pass_count"] == summary["binary_count"]
        and summary["symbol_found_count"] >= 50
        and summary["pdc_c_like_count"] >= 50
    ):
        return "pass-phase6r-radare2-importability-smoke"
    if summary["pdc_c_like_count"] > 0:
        return "partial-phase6r-radare2-importability-smoke"
    return "blocked-radare2-pseudo-c-import"


def count_by(records: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in records:
        value = str(record.get(key, ""))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


def _write_markdown_zh(path: Path, summary: dict[str, Any]) -> None:
    failure_rows = "\n".join(
        f"| `{key}` | `{value}` |"
        for key, value in summary["failure_counts"].items()
    )
    text = f"""# Decompilation Faithfulness Phase 6R radare2 Smoke

- Verdict: `{summary['verdict']}`
- Tool: `{summary['tool']}`
- Tool path: `{summary['tool_path']}`
- Tool version: `{summary['tool_version']}`
- Toolchain label: `{summary['toolchain_label']}`
- Binary compiler: `{summary['binary_compiler']}`
- Optimization levels: `{summary['optimization_levels']}`
- Binaries: `{summary['binary_count']}`
- Compile pass: `{summary['compile_pass_count']}`
- Symbol found: `{summary['symbol_found_count']}`
- Disassembly output count: `{summary['pdf_output_count']}`
- Pseudo-C output count: `{summary['pdc_output_count']}`
- Pseudo-C-like output count: `{summary['pdc_c_like_count']}`
- Compile-ready decompiler C count: `{summary['pdc_compile_ready_count']}`
- Records: `{summary['records_path']}`

## Failure Counts

| Category | Count |
|---|---:|
{failure_rows}

## Interpretation

这是 Phase 6R 的真实工具链 importability smoke。`radare2` 已经能在用户态运行，并能对 Phase 5 的 source-known 函数二进制做符号定位、反汇编和 `pdc` pseudo-C 输出。

但是 `pdc` 输出是 pseudo-C，不是可直接编译的 C function candidate。因此这个结果只能证明真实工具入口可用，不能替代 Ghidra/RetDec 真实 decompiler-output full experiment，也不能作为 CCF-A 主结果。

下一步建议直接走 Ghidra main evidence：安装或启用 headless Ghidra，导出真实 decompiler C，再复用 Phase 6 的 source-known oracle、baseline 和 Dynamic Trace v3 gate。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
