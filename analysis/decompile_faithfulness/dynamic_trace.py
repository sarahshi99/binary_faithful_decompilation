from __future__ import annotations

import itertools
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import fixtures


@dataclass(frozen=True, order=True)
class TraceInput:
    args: tuple[int, ...]
    bucket: str


@dataclass(frozen=True)
class TraceRun:
    case_id: str
    candidate_id: str
    compiled: bool
    exit_code: int
    outputs: tuple[int, ...]
    stdout: str
    stderr: str
    source_path: Path
    exe_path: Path


@dataclass(frozen=True)
class TraceDistance:
    components: dict[str, float]


@dataclass(frozen=True)
class TraceDomain:
    arity: int
    all_positive: bool
    all_nonnegative: bool
    has_negative: bool
    has_zero: bool
    has_positive: bool


VALUE_POOL = (
    -16, -8, -5, -3, -2, -1, 0, 1, 2, 3, 4, 5, 7, 8, 9, 10,
    12, 14, 16, 17, 21, 25, 31, 63, 127, 128, 170, 255, 256, 300,
)
COMPACT_POOL_2 = (-8, -3, -1, 0, 1, 2, 3, 5, 8, 12, 17, 25, 255)
COMPACT_POOL_3 = (-8, -1, 0, 1, 2, 3, 5, 8, 17)
POSITIVE_COMPACT_POOL_2 = (1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 14, 15, 16, 17, 21, 25)
NONNEGATIVE_COMPACT_POOL_2 = (0, 1, 2, 3, 4, 5, 6, 8, 9, 10, 12, 14, 15, 16, 17, 21)
POSITIVE_COMPACT_POOL_3 = (1, 2, 3, 5, 8, 13, 21)
NONNEGATIVE_COMPACT_POOL_3 = (0, 1, 2, 3, 5, 8, 13)
BOUNDARY_VALUES = {-16, -8, -1, 0, 1, 8, 16, 127, 128, 255, 256, 300}


def generate_trace_inputs(
    case: fixtures.FunctionCase,
    max_inputs: int = 256,
    include_fixture_tests: bool = False,
) -> list[TraceInput]:
    if not case.tests:
        return []
    arity = len(case.tests[0].args)
    fixture_args = {test.args for test in case.tests}
    generated: dict[tuple[int, ...], str] = {}

    if arity == 1:
        for value in VALUE_POOL:
            generated[(value,)] = _bucket_for_args((value,))
    elif arity == 2:
        for left, right in itertools.product(COMPACT_POOL_2, repeat=2):
            generated[(left, right)] = _bucket_for_args((left, right))
        for value in COMPACT_POOL_2:
            generated[(value, value)] = "equal"
        for args in fixture_args:
            generated[tuple(reversed(args))] = "swapped_fixture_like"
    elif arity == 3:
        for value in COMPACT_POOL_3:
            generated[(value, value, value)] = "all_equal"
        for left, middle, right in itertools.product(COMPACT_POOL_3, repeat=3):
            if left <= middle <= right:
                generated[(left, middle, right)] = "ascending"
            if left >= middle >= right:
                generated[(left, middle, right)] = "descending"
            if 0 in (left, middle, right) or any(value in BOUNDARY_VALUES for value in (left, middle, right)):
                generated.setdefault((left, middle, right), _bucket_for_args((left, middle, right)))
    else:
        for args in itertools.product((-1, 0, 1), repeat=arity):
            generated[tuple(args)] = _bucket_for_args(tuple(args))

    if include_fixture_tests:
        for args in fixture_args:
            generated[args] = "fixture"
    else:
        for args in fixture_args:
            generated.pop(args, None)

    return [
        TraceInput(args=args, bucket=bucket)
        for args, bucket in sorted(generated.items(), key=lambda item: item[0])
    ][:max_inputs]


def infer_trace_domain(case: fixtures.FunctionCase) -> TraceDomain:
    if not case.tests:
        return TraceDomain(
            arity=0,
            all_positive=False,
            all_nonnegative=False,
            has_negative=False,
            has_zero=False,
            has_positive=False,
        )
    arity = len(case.tests[0].args)
    values = [value for test in case.tests for value in test.args]
    return TraceDomain(
        arity=arity,
        all_positive=bool(values) and all(value > 0 for value in values),
        all_nonnegative=bool(values) and all(value >= 0 for value in values),
        has_negative=any(value < 0 for value in values),
        has_zero=any(value == 0 for value in values),
        has_positive=any(value > 0 for value in values),
    )


def generate_domain_trace_inputs(
    case: fixtures.FunctionCase,
    max_inputs: int = 256,
    include_fixture_tests: bool = False,
) -> list[TraceInput]:
    domain = infer_trace_domain(case)
    if not domain.all_positive and not domain.all_nonnegative:
        return generate_trace_inputs(case, max_inputs, include_fixture_tests)

    fixture_args = {test.args for test in case.tests}
    generated: dict[tuple[int, ...], str] = {}
    if domain.all_positive:
        pool_1 = tuple(value for value in VALUE_POOL if value > 0)
        pool_2 = POSITIVE_COMPACT_POOL_2
        pool_3 = POSITIVE_COMPACT_POOL_3
        domain_bucket = "positive_domain"
    else:
        pool_1 = tuple(value for value in VALUE_POOL if value >= 0)
        pool_2 = NONNEGATIVE_COMPACT_POOL_2
        pool_3 = NONNEGATIVE_COMPACT_POOL_3
        domain_bucket = "nonnegative_domain"

    if domain.arity == 1:
        for value in pool_1:
            generated[(value,)] = _bucket_for_args((value,))
    elif domain.arity == 2:
        for left, right in itertools.product(pool_2, repeat=2):
            generated[(left, right)] = _bucket_for_args((left, right))
        for value in pool_2:
            generated[(value, value)] = "equal"
        for args in fixture_args:
            generated[tuple(reversed(args))] = "swapped_fixture_like"
    elif domain.arity == 3:
        for value in pool_3:
            generated[(value, value, value)] = "all_equal"
        for left, middle, right in itertools.product(pool_3, repeat=3):
            if left <= middle <= right:
                generated[(left, middle, right)] = "ascending"
            if left >= middle >= right:
                generated[(left, middle, right)] = "descending"
            if any(value in BOUNDARY_VALUES for value in (left, middle, right)):
                generated.setdefault((left, middle, right), _bucket_for_args((left, middle, right)))
    else:
        for args in itertools.product(pool_3[:3], repeat=domain.arity):
            generated[tuple(args)] = domain_bucket

    if include_fixture_tests:
        for args in fixture_args:
            generated[args] = "fixture"
    else:
        for args in fixture_args:
            generated.pop(args, None)

    return [
        TraceInput(args=args, bucket=bucket)
        for args, bucket in sorted(generated.items(), key=lambda item: item[0])
    ][:max_inputs]


def generate_boundary_trace_inputs(
    case: fixtures.FunctionCase,
    max_inputs: int = 256,
    include_fixture_tests: bool = False,
) -> list[TraceInput]:
    domain = infer_trace_domain(case)
    fixture_args = {test.args for test in case.tests}
    generated = {
        trace_input.args: trace_input.bucket
        for trace_input in generate_domain_trace_inputs(
            case,
            max_inputs=10_000,
            include_fixture_tests=include_fixture_tests,
        )
    }
    protected_boundary: set[tuple[int, ...]] = set()
    for args in _v3_boundary_args(domain):
        generated[args] = "v3_boundary"
        protected_boundary.add(args)

    if include_fixture_tests:
        for args in fixture_args:
            generated[args] = "fixture"
    else:
        for args in fixture_args:
            if args not in protected_boundary:
                generated.pop(args, None)

    boundary_inputs = [
        TraceInput(args=args, bucket=generated[args])
        for args in sorted(protected_boundary)
        if args in generated
    ]
    remaining_inputs = [
        TraceInput(args=args, bucket=bucket)
        for args, bucket in sorted(generated.items(), key=lambda item: item[0])
        if args not in protected_boundary
    ]
    return (boundary_inputs + remaining_inputs)[:max_inputs]


def render_trace_harness(
    case: fixtures.FunctionCase,
    function_source: str,
    inputs: list[TraceInput],
) -> str:
    lines = ["#include <stdio.h>", "", function_source.rstrip(), "", "int main(void) {"]
    for trace_input in inputs:
        args = ", ".join(str(arg) for arg in trace_input.args)
        lines.append(f'    printf("%d\\n", {case.function_name}({args}));')
    lines.append("    return 0;")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def parse_trace_stdout(stdout: str, expected_count: int) -> tuple[int, ...]:
    lines = [line.strip() for line in stdout.splitlines() if line.strip()]
    if len(lines) != expected_count:
        raise ValueError(f"expected {expected_count} trace outputs, got {len(lines)}")
    outputs: list[int] = []
    for line in lines:
        if not re.fullmatch(r"[-+]?\d+", line):
            raise ValueError(f"non-integer trace output: {line!r}")
        outputs.append(int(line))
    return tuple(outputs)


def run_trace(
    case: fixtures.FunctionCase,
    candidate_id: str,
    function_source: str,
    inputs: list[TraceInput],
    output_dir: Path,
    opt_level: str = "O0",
) -> TraceRun:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{case.case_id}__{_safe_name(candidate_id)}__trace__{opt_level}"
    source_path = output_dir / f"{stem}.trace.c"
    exe_path = output_dir / f"{stem}.trace.exe"
    source_path.write_text(render_trace_harness(case, function_source, inputs), encoding="utf-8")
    try:
        compile_result = ccompile.run_command(
            [
                "/usr/bin/gcc",
                "-std=c11",
                "-Wall",
                "-Wextra",
                "-Werror",
                f"-{opt_level}",
                str(source_path),
                "-o",
                str(exe_path),
            ]
        )
    except subprocess.TimeoutExpired as exc:
        return TraceRun(
            case.case_id,
            candidate_id,
            False,
            124,
            (),
            _timeout_stream(exc.stdout),
            _timeout_message(exc),
            source_path,
            exe_path,
        )
    if compile_result.returncode != 0:
        return TraceRun(
            case.case_id,
            candidate_id,
            False,
            compile_result.returncode,
            (),
            compile_result.stdout,
            compile_result.stderr,
            source_path,
            exe_path,
        )
    try:
        run_result = ccompile.run_command([str(exe_path)])
    except subprocess.TimeoutExpired as exc:
        return TraceRun(
            case.case_id,
            candidate_id,
            True,
            124,
            (),
            _timeout_stream(exc.stdout),
            _timeout_message(exc),
            source_path,
            exe_path,
        )
    outputs = parse_trace_stdout(run_result.stdout, len(inputs)) if run_result.returncode == 0 else ()
    return TraceRun(
        case.case_id,
        candidate_id,
        True,
        run_result.returncode,
        outputs,
        run_result.stdout,
        run_result.stderr,
        source_path,
        exe_path,
    )


def trace_distance(
    inputs: list[TraceInput],
    original_outputs: tuple[int, ...],
    candidate_outputs: tuple[int, ...],
) -> TraceDistance:
    if len(inputs) != len(original_outputs) or len(inputs) != len(candidate_outputs):
        raise ValueError("trace input/output lengths differ")
    count = len(inputs)
    mismatch = 0
    abs_errors: list[int] = []
    sign_mismatch = 0
    zero_mismatch = 0
    boundary_mismatch = 0
    boundary_count = 0
    for trace_input, left, right in zip(inputs, original_outputs, candidate_outputs):
        differs = left != right
        mismatch += int(differs)
        abs_errors.append(abs(left - right))
        sign_mismatch += int(_sign(left) != _sign(right))
        zero_mismatch += int((left == 0) != (right == 0))
        if trace_input.bucket == "boundary" or any(value in BOUNDARY_VALUES for value in trace_input.args):
            boundary_count += 1
            boundary_mismatch += int(differs)
    mismatch_rate = mismatch / count if count else 0.0
    abs_error_mean = sum(abs_errors) / count if count else 0.0
    sign_mismatch_rate = sign_mismatch / count if count else 0.0
    zero_mismatch_rate = zero_mismatch / count if count else 0.0
    boundary_mismatch_rate = boundary_mismatch / boundary_count if boundary_count else 0.0
    trace_total = (
        mismatch_rate
        + 0.25 * _squash(abs_error_mean)
        + 0.25 * sign_mismatch_rate
        + 0.25 * zero_mismatch_rate
        + 0.25 * boundary_mismatch_rate
    )
    return TraceDistance(
        {
            "trace_input_count": float(count),
            "trace_mismatch_count": float(mismatch),
            "trace_mismatch_rate": mismatch_rate,
            "trace_abs_error_mean": abs_error_mean,
            "trace_abs_error_max": float(max(abs_errors) if abs_errors else 0),
            "trace_sign_mismatch_rate": sign_mismatch_rate,
            "trace_zero_mismatch_rate": zero_mismatch_rate,
            "trace_boundary_mismatch_rate": boundary_mismatch_rate,
            "trace_total": trace_total,
        }
    )


def _bucket_for_args(args: tuple[int, ...]) -> str:
    if any(value in BOUNDARY_VALUES for value in args):
        return "boundary"
    if all(value == 0 for value in args):
        return "zero"
    if all(value < 0 for value in args):
        return "negative"
    if all(value > 0 for value in args):
        return "positive"
    return "mixed"


def _v3_boundary_args(domain: TraceDomain) -> set[tuple[int, ...]]:
    if domain.arity <= 0:
        return set()
    if domain.all_positive:
        pool = (1, 2)
    elif domain.all_nonnegative:
        pool = (0, 1, 2)
    else:
        pool = (-1, 0, 1)
    return {
        tuple(args)
        for args in itertools.product(pool, repeat=domain.arity)
    }


def _safe_name(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", value)
    return safe.strip("._") or "candidate"


def _sign(value: int) -> int:
    if value < 0:
        return -1
    if value > 0:
        return 1
    return 0


def _squash(value: float) -> float:
    return value / (1.0 + value) if value > 0.0 else 0.0


def _timeout_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _timeout_message(exc: subprocess.TimeoutExpired) -> str:
    stderr = _timeout_stream(exc.stderr)
    prefix = f"command timed out after {exc.timeout} seconds: {exc.cmd!r}"
    return f"{prefix}\n{stderr}" if stderr else prefix
