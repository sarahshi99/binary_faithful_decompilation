from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from analysis.decompile_faithfulness import fixtures


@dataclass(frozen=True)
class CompileResult:
    case_id: str
    candidate_id: str
    opt_level: str
    source_path: Path
    object_path: Path
    exe_path: Path
    compiled: bool
    behavior_passed: bool
    exit_code: int
    stdout: str
    stderr: str
    run_stdout: str
    run_stderr: str


def run_command(
    argv: list[str],
    cwd: Path | None = None,
    timeout_s: int = 10,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            timeout=timeout_s,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout if isinstance(exc.stdout, str) else ""
        stderr = exc.stderr if isinstance(exc.stderr, str) else ""
        timeout_message = f"command timed out after {timeout_s} seconds"
        if stderr:
            stderr = f"{stderr}\n{timeout_message}"
        else:
            stderr = timeout_message
        return subprocess.CompletedProcess(
            argv,
            returncode=124,
            stdout=stdout,
            stderr=stderr,
        )


def compile_candidate(
    case: fixtures.FunctionCase,
    candidate_id: str,
    function_source: str,
    output_dir: Path,
    opt_level: str = "O0",
) -> CompileResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{case.case_id}__{_safe_name(candidate_id)}__{opt_level}"
    function_path = output_dir / f"{stem}.function.c"
    harness_path = output_dir / f"{stem}.harness.c"
    object_path = output_dir / f"{stem}.function.o"
    exe_path = output_dir / f"{stem}.harness.exe"

    function_path.write_text(function_source, encoding="utf-8")
    harness_path.write_text(
        fixtures.render_translation_unit(case, function_source),
        encoding="utf-8",
    )

    object_cmd = [
        "/usr/bin/gcc",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        f"-{opt_level}",
        "-c",
        str(function_path),
        "-o",
        str(object_path),
    ]
    object_result = run_command(object_cmd)
    stdout = object_result.stdout
    stderr = object_result.stderr

    if object_result.returncode != 0:
        return CompileResult(
            case_id=case.case_id,
            candidate_id=candidate_id,
            opt_level=opt_level,
            source_path=function_path,
            object_path=object_path,
            exe_path=exe_path,
            compiled=False,
            behavior_passed=False,
            exit_code=object_result.returncode,
            stdout=stdout,
            stderr=stderr,
            run_stdout="",
            run_stderr="",
        )

    exe_cmd = [
        "/usr/bin/gcc",
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        f"-{opt_level}",
        str(harness_path),
        "-o",
        str(exe_path),
    ]
    exe_result = run_command(exe_cmd)
    stdout += exe_result.stdout
    stderr += exe_result.stderr
    if exe_result.returncode != 0:
        return CompileResult(
            case_id=case.case_id,
            candidate_id=candidate_id,
            opt_level=opt_level,
            source_path=function_path,
            object_path=object_path,
            exe_path=exe_path,
            compiled=False,
            behavior_passed=False,
            exit_code=exe_result.returncode,
            stdout=stdout,
            stderr=stderr,
            run_stdout="",
            run_stderr="",
        )

    run_result = run_command([str(exe_path)])
    return CompileResult(
        case_id=case.case_id,
        candidate_id=candidate_id,
        opt_level=opt_level,
        source_path=function_path,
        object_path=object_path,
        exe_path=exe_path,
        compiled=True,
        behavior_passed=run_result.returncode == 0,
        exit_code=run_result.returncode,
        stdout=stdout,
        stderr=stderr,
        run_stdout=run_result.stdout,
        run_stderr=run_result.stderr,
    )


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return safe.strip("._") or "candidate"
