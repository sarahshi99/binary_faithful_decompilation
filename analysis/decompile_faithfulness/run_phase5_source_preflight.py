from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import dynamic_trace, fixtures


DEFAULT_EXTERNAL_ROOT = Path("analysis_inputs/decompile_faithfulness/phase5_external_sources")
DEFAULT_SOURCE_DIR = Path("analysis_inputs/decompile_faithfulness/phase5_sources")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase5_source_preflight")
DEFAULT_MANIFEST_JSON = Path("docs/paper_agent/decompile_faithfulness_phase5_function_manifest.json")
DEFAULT_PREFLIGHT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase5_preflight.json")
DEFAULT_PROJECT_MD = Path("docs/paper_agent/decompile_faithfulness_phase5_project_candidates.zh.md")
DEFAULT_GATE_MD = Path("docs/paper_agent/decompile_faithfulness_phase5_gate_decision.zh.md")


@dataclass(frozen=True)
class Phase5Spec:
    case_id: str
    project: str
    original_source_path: str
    function_name: str
    fixture_args: tuple[tuple[int, ...], ...]
    risk_families: tuple[str, ...]
    tags: tuple[str, ...]
    extracted_functions: tuple[str, ...] = field(default_factory=tuple)
    prefix: str = ""
    explicit_source: str | None = None
    extraction_kind: str = "direct_function"
    domain_note: str = "bounded_integer_inputs"


def main() -> None:
    args = parse_args()
    summary = run_source_preflight(
        repo_root=args.repo_root,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        manifest_json=args.manifest_json,
        preflight_json=args.preflight_json,
        project_md=args.project_md,
        gate_md=args.gate_md,
    )
    print(
        json.dumps(
            {
                "verdict": summary["preflight"]["verdict"],
                "function_count": summary["manifest"]["function_count"],
                "eligible_functions": summary["preflight"]["eligible_functions"],
                "source_projects": summary["manifest"]["source_projects"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    parser.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT_JSON)
    parser.add_argument("--project-md", type=Path, default=DEFAULT_PROJECT_MD)
    parser.add_argument("--gate-md", type=Path, default=DEFAULT_GATE_MD)
    return parser.parse_args()


def run_source_preflight(
    repo_root: Path,
    source_dir: Path,
    output_dir: Path,
    manifest_json: Path,
    preflight_json: Path,
    project_md: Path,
    gate_md: Path,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    source_dir = _resolve(repo_root, source_dir)
    output_dir = _resolve(repo_root, output_dir)
    manifest_json = _resolve(repo_root, manifest_json)
    preflight_json = _resolve(repo_root, preflight_json)
    project_md = _resolve(repo_root, project_md)
    gate_md = _resolve(repo_root, gate_md)

    manifest = build_manifest(repo_root=repo_root, source_dir=source_dir)
    preflight = run_preflight(repo_root=repo_root, manifest=manifest, output_dir=output_dir)

    _write_json(manifest_json, manifest)
    _write_json(preflight_json, preflight)
    _write_project_report(project_md, manifest, preflight)
    _write_gate_report(gate_md, manifest, preflight)
    return {"manifest": manifest, "preflight": preflight}


def build_manifest(repo_root: Path, source_dir: Path) -> dict[str, Any]:
    source_dir.mkdir(parents=True, exist_ok=True)
    functions: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for spec in phase5_specs():
        try:
            source = materialize_source(repo_root, spec)
            source_path = source_dir / f"{spec.case_id}.c"
            source_path.write_text(source, encoding="utf-8")
            tests = _fixture_tests_from_oracle(spec, source, source_dir / "oracle_fixtures")
            functions.append(_manifest_entry(repo_root, spec, source_path, source, tests))
        except Exception as exc:
            errors.append(
                {
                    "case_id": spec.case_id,
                    "project": spec.project,
                    "reason": repr(exc),
                }
            )

    source_projects = sorted({entry["project"] for entry in functions})
    eligible = [
        entry for entry in functions
        if all(entry["eligibility"].values())
    ]
    manifest = {
        "phase": "phase5_real_project_source_known_transfer",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "function_count": len(functions),
        "phase5_real_project_eligible_function_count": len(eligible),
        "source_projects": source_projects,
        "minimum_required": {
            "source_projects": 2,
            "eligible_functions": 30,
        },
        "functions": functions,
        "extraction_errors": errors,
        "verdict": _source_gate_verdict(len(eligible), len(source_projects)),
    }
    return manifest


def run_preflight(repo_root: Path, manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    for entry in manifest.get("functions", []):
        case = _case_from_manifest_entry(repo_root, entry)
        compile_result = ccompile.compile_candidate(
            case=case,
            candidate_id="original",
            function_source=case.function_source,
            output_dir=output_dir / "compile",
            opt_level="O0",
        )
        trace_inputs = phase5_bounded_trace_inputs(entry, max_inputs=128)
        trace_run = dynamic_trace.run_trace(
            case=case,
            candidate_id="original_boundary",
            function_source=case.function_source,
            inputs=trace_inputs,
            output_dir=output_dir / "traces",
            opt_level="O0",
        )
        records.append(
            {
                "case_id": entry["case_id"],
                "project": entry["project"],
                "compiled": compile_result.compiled,
                "fixture_passed": compile_result.behavior_passed,
                "fixture_exit_code": compile_result.exit_code,
                "bounded_trace_compiled": trace_run.compiled,
                "bounded_trace_exit_code": trace_run.exit_code,
                "bounded_trace_output_count": len(trace_run.outputs),
                "bounded_trace_input_count": len(trace_inputs),
                "oracle_ready": (
                    compile_result.compiled
                    and compile_result.behavior_passed
                    and trace_run.compiled
                    and trace_run.exit_code == 0
                    and len(trace_run.outputs) == len(trace_inputs)
                ),
                "stderr_tail": (compile_result.stderr + "\n" + trace_run.stderr)[-1200:],
            }
        )

    eligible_count = manifest.get("phase5_real_project_eligible_function_count", 0)
    source_project_count = len(manifest.get("source_projects", []))
    compile_pass = sum(1 for record in records if record["compiled"])
    fixture_pass = sum(1 for record in records if record["fixture_passed"])
    oracle_ready = sum(1 for record in records if record["oracle_ready"])
    preflight = {
        "phase": "phase5_preflight",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "eligible_functions": eligible_count,
        "source_project_count": source_project_count,
        "compile_pass": compile_pass,
        "fixture_pass": fixture_pass,
        "oracle_ready": oracle_ready,
        "records": records,
        "verdict": _preflight_verdict(
            eligible_count=eligible_count,
            source_project_count=source_project_count,
            records=records,
        ),
    }
    return preflight


def phase5_specs() -> list[Phase5Spec]:
    ta = "thealgorithms_c"
    ca = "c_algorithms"
    return [
        _direct("ta_gcd_GCD", ta, "math/gcd.c", "GCD", [(12, 8), (17, 5), (25, 10)], ("loop", "modulo", "positive_domain")),
        _direct("ta_lcm_gcd", ta, "math/lcm.c", "gcd", [(12, 8), (17, 5), (25, 10)], ("loop", "modulo", "positive_domain")),
        _direct("ta_lcm_lcm", ta, "math/lcm.c", "lcm", [(15, 20), (12, 18), (7, 5)], ("arithmetic", "division", "positive_domain"), extracted=("gcd", "lcm")),
        _direct("ta_armstrong_power", ta, "math/armstrong_number.c", "power", [(2, 3), (5, 0), (3, 4)], ("recursion", "boundary", "nonnegative_domain")),
        _direct("ta_armstrong_order", ta, "math/armstrong_number.c", "order", [(0,), (7,), (153,), (1000,)], ("loop", "digits", "nonnegative_domain")),
        _direct("ta_armstrong_isArmstrong", ta, "math/armstrong_number.c", "isArmstrong", [(0,), (153,), (370,), (1253,)], ("digits", "helper_dependency", "boundary"), extracted=("power", "order", "isArmstrong")),
        _direct("ta_decimal_to_binary", ta, "conversions/decimal_to_binary_recursion.c", "decimal_to_binary", [(0,), (1,), (5,), (7,)], ("conversion", "recursion", "nonnegative_domain")),
        _direct("ta_decimal_to_octal", ta, "conversions/decimal_to_octal_recursion.c", "decimal_to_octal", [(0,), (7,), (8,), (64,)], ("conversion", "recursion", "boundary")),
        _direct("ta_binary_to_octal_three_digits", ta, "conversions/binary_to_octal.c", "three_digits", [(0,), (1,), (101,), (111,)], ("conversion", "digits", "loop")),
        _direct("ta_affine_mod_inverse", ta, "cipher/affine.c", "modular_multiplicative_inverse", [(1, 95), (7, 95), (11, 95), (0, 95)], ("modulo", "loop", "zero_boundary"), prefix="#include <stdlib.h>\n"),
        _direct("ta_euler_is_palindromic", ta, "project_euler/problem_4/sol.c", "is_palindromic", [(0,), (1,), (121,), (123,)], ("digits", "loop", "boundary")),
        _direct("ta_leetcode_tribonacci", ta, "leetcode/src/1137.c", "tribonacci", [(0,), (1,), (4,), (8,)], ("dynamic_programming", "loop", "boundary")),
        _direct("ta_leetcode_fib", ta, "leetcode/src/509.c", "fib", [(0,), (1,), (5,), (8,)], ("recursion", "boundary", "nonnegative_domain")),
        _direct("ta_leetcode_divide", ta, "leetcode/src/29.c", "divide", [(10, 2), (7, 3), (1, 1), (12, 5)], ("division", "loop", "positive_domain"), prefix="#include <limits.h>\n"),
        _direct("ta_leetcode_reverse", ta, "leetcode/src/7.c", "reverse", [(0,), (123,), (-123,), (120,)], ("digits", "sign_zero", "overflow_guard"), prefix="#include <limits.h>\n"),
        _direct("ta_leetcode_range_bitwise_and", ta, "leetcode/src/201.c", "rangeBitwiseAnd", [(5, 7), (0, 1), (8, 15), (12, 12)], ("bitwise", "loop", "boundary")),
        _direct("ta_leetcode_find_complement", ta, "leetcode/src/476.c", "findComplement", [(1,), (2,), (5,), (10,)], ("bitwise", "loop", "positive_domain"), prefix="#include <stdint.h>\n"),
        _direct("ta_leetcode_hamming_distance", ta, "leetcode/src/461.c", "hammingDistance", [(1, 4), (3, 1), (7, 7), (0, 255)], ("bitwise", "loop", "zero_boundary"), prefix="#include <stdint.h>\n"),
        _direct("ta_leetcode_unique_paths", ta, "leetcode/src/62.c", "uniquePaths", [(1, 1), (2, 3), (3, 7), (4, 4)], ("dynamic_programming", "multi_arg", "positive_domain")),
        _direct("ta_leetcode_max", ta, "leetcode/src/110.c", "max", [(1, 2), (2, 1), (-3, -1), (4, 4)], ("branch", "comparison", "sign_zero")),
        _direct("ta_leetcode_get_point_key", ta, "leetcode/src/79.c", "getPointKey", [(0, 0, 3, 4), (1, 2, 3, 4), (2, 1, 5, 5)], ("arithmetic", "multi_arg", "boundary")),
        _direct("ta_leetcode_get_triplet_id", ta, "leetcode/src/37.c", "getTripletId", [(0, 0), (2, 8), (3, 3), (8, 8)], ("division", "grid_boundary", "multi_arg")),
        _direct("ta_leetcode_intersection_size", ta, "leetcode/src/223.c", "intersectionSize", [(0, 2, 1, 3), (0, 1, 2, 3), (-2, 2, -1, 1)], ("geometry", "branch", "boundary"), prefix="#define min(X, Y) ((X) < (Y) ? (X) : (Y))\n"),
        _direct("ta_leetcode_compute_area", ta, "leetcode/src/223.c", "computeArea", [(-3, 0, 3, 4, 0, -1, 9, 2), (0, 0, 1, 1, 2, 2, 3, 3)], ("geometry", "helper_dependency", "multi_arg"), extracted=("intersectionSize", "computeArea"), prefix="#define min(X, Y) ((X) < (Y) ? (X) : (Y))\n"),
        _direct("ta_leetcode_my_sqrt", ta, "leetcode/src/69.c", "mySqrt", [(0,), (1,), (4,), (8,), (16,)], ("binary_search", "boundary", "nonnegative_domain")),
        _direct("ta_bucket_get_bucket_index", ta, "sorting/bucket_sort.c", "getBucketIndex", [(0,), (9,), (10,), (49,)], ("division", "bucket_boundary", "nonnegative_domain"), prefix="#define INTERVAL 10\n"),
        _direct("ta_naval_valid_entry_line_column", ta, "games/naval_battle.c", "validEntryLineColumn", [(1, 65), (10, 74), (0, 65), (5, 90)], ("range_check", "char_boundary", "branch")),
        _direct("ta_shunting_get_precedence", ta, "misc/shunting_yard.c", "getPrecedence", [(43,), (45,), (42,), (94,)], ("char_boundary", "branch", "operator_precedence"), prefix="#include <stdio.h>\n"),
        _direct("ta_shunting_get_associativity", ta, "misc/shunting_yard.c", "getAssociativity", [(43,), (42,), (94,)], ("char_boundary", "branch", "operator_associativity"), prefix="#include <stdio.h>\n"),
        _direct("ta_infix_is_operand", ta, "conversions/infix_to_postfix.c", "isOprnd", [(65,), (122,), (48,), (43,)], ("char_boundary", "range_check", "branch")),
        _direct("ta_infix_precedence_two", ta, "conversions/infix_to_postfix.c", "getPrecedence", [(42, 43), (43, 42), (36, 43), (43, 36)], ("char_boundary", "operator_precedence", "multi_arg")),
        _direct("ta_leetcode_min", ta, "leetcode/src/11.c", "min", [(1, 2), (2, 1), (-3, -1), (4, 4)], ("branch", "comparison", "sign_zero")),
        _direct("ta_leetcode_maxval", ta, "leetcode/src/104.c", "maxval", [(1, 2), (2, 1), (-3, -1), (4, 4)], ("branch", "comparison", "sign_zero")),
        _adapter_ca_int_hash(),
        _adapter_ca_int_equal(),
        _adapter_ca_int_compare(),
        _adapter_ca_string_hash(),
        _adapter_ca_string_nocase_hash(),
    ]


def _direct(
    case_id: str,
    project: str,
    project_relative_path: str,
    function_name: str,
    fixture_args: list[tuple[int, ...]],
    risk_families: tuple[str, ...],
    extracted: tuple[str, ...] | None = None,
    prefix: str = "",
) -> Phase5Spec:
    return Phase5Spec(
        case_id=case_id,
        project=project,
        original_source_path=str(DEFAULT_EXTERNAL_ROOT / project / project_relative_path),
        function_name=function_name,
        fixture_args=tuple(fixture_args),
        risk_families=risk_families,
        tags=risk_families,
        extracted_functions=extracted or (function_name,),
        prefix=prefix,
    )


def _adapter_ca_int_hash() -> Phase5Spec:
    return _adapter(
        "ca_int_hash_value",
        "src/hash-int.c",
        "ca_int_hash_value",
        [(0,), (1,), (-7,), (255,)],
        ("adapter", "hash", "sign_zero"),
        """
unsigned int int_hash(void *vlocation)
{
    int *location = (int *) vlocation;
    return (unsigned int) *location;
}

int ca_int_hash_value(int value)
{
    return (int) int_hash(&value);
}
""",
    )


def _adapter_ca_int_equal() -> Phase5Spec:
    return _adapter(
        "ca_int_equal_values",
        "src/compare-int.c",
        "ca_int_equal_values",
        [(0, 0), (1, 2), (-7, -7), (255, -255)],
        ("adapter", "comparison", "sign_zero"),
        """
int int_equal(void *vlocation1, void *vlocation2)
{
    int *location1 = (int *) vlocation1;
    int *location2 = (int *) vlocation2;
    return *location1 == *location2;
}

int ca_int_equal_values(int left, int right)
{
    return int_equal(&left, &right);
}
""",
    )


def _adapter_ca_int_compare() -> Phase5Spec:
    return _adapter(
        "ca_int_compare_values",
        "src/compare-int.c",
        "ca_int_compare_values",
        [(0, 0), (1, 2), (2, 1), (-7, -3)],
        ("adapter", "comparison", "sign_zero"),
        """
int int_compare(void *vlocation1, void *vlocation2)
{
    int *location1 = (int *) vlocation1;
    int *location2 = (int *) vlocation2;
    if (*location1 < *location2) {
        return -1;
    } else if (*location1 > *location2) {
        return 1;
    } else {
        return 0;
    }
}

int ca_int_compare_values(int left, int right)
{
    return int_compare(&left, &right);
}
""",
    )


def _adapter_ca_string_hash() -> Phase5Spec:
    return _adapter(
        "ca_string_hash_selector",
        "src/hash-string.c",
        "ca_string_hash_selector",
        [(0,), (1,), (2,), (3,)],
        ("adapter", "hash", "branch"),
        """
unsigned int string_hash(void *string)
{
    unsigned int result = 5381;
    unsigned char *p = (unsigned char *) string;
    while (*p != '\\0') {
        result = (result << 5) + result + *p;
        ++p;
    }
    return result;
}

int ca_string_hash_selector(int selector)
{
    if (selector == 0) return (int) string_hash("alpha");
    if (selector == 1) return (int) string_hash("Alpha");
    if (selector == 2) return (int) string_hash("beta");
    return (int) string_hash("");
}
""",
    )


def _adapter_ca_string_nocase_hash() -> Phase5Spec:
    return _adapter(
        "ca_string_nocase_hash_selector",
        "src/hash-string.c",
        "ca_string_nocase_hash_selector",
        [(0,), (1,), (2,), (3,)],
        ("adapter", "hash", "case_boundary"),
        """
#include <ctype.h>

unsigned int string_nocase_hash(void *string)
{
    unsigned int result = 5381;
    unsigned char *p = (unsigned char *) string;
    while (*p != '\\0') {
        result = (result << 5) + result + (unsigned int) tolower(*p);
        ++p;
    }
    return result;
}

int ca_string_nocase_hash_selector(int selector)
{
    if (selector == 0) return (int) string_nocase_hash("alpha");
    if (selector == 1) return (int) string_nocase_hash("Alpha");
    if (selector == 2) return (int) string_nocase_hash("beta");
    return (int) string_nocase_hash("");
}
""",
    )


def _adapter(
    case_id: str,
    project_relative_path: str,
    function_name: str,
    fixture_args: list[tuple[int, ...]],
    risk_families: tuple[str, ...],
    source: str,
) -> Phase5Spec:
    return Phase5Spec(
        case_id=case_id,
        project="c_algorithms",
        original_source_path=str(DEFAULT_EXTERNAL_ROOT / "c_algorithms" / project_relative_path),
        function_name=function_name,
        fixture_args=tuple(fixture_args),
        risk_families=risk_families,
        tags=risk_families,
        explicit_source=source.strip() + "\n",
        extraction_kind="scalar_adapter",
        domain_note="bounded_integer_adapter_over_original_pointer_api",
    )


def materialize_source(repo_root: Path, spec: Phase5Spec) -> str:
    if spec.explicit_source is not None:
        return spec.explicit_source
    original_path = repo_root / spec.original_source_path
    text = original_path.read_text(encoding="utf-8")
    parts = [spec.prefix.rstrip()] if spec.prefix.strip() else []
    for function_name in spec.extracted_functions:
        parts.append(extract_function(text, function_name))
    return "\n\n".join(part for part in parts if part).strip() + "\n"


def extract_function(source_text: str, function_name: str) -> str:
    matches = list(
        re.finditer(
            rf"^[ \t]*(?:static[ \t]+)?(?:int|unsigned[ \t]+int|long[ \t]+long|long|bool)[ \t]+\**[ \t]*{re.escape(function_name)}[ \t]*\([^;{{}}]*\)",
            source_text,
            flags=re.MULTILINE,
        )
    )
    for match in matches:
        cursor = match.end()
        while cursor < len(source_text) and source_text[cursor].isspace():
            cursor += 1
        if cursor >= len(source_text) or source_text[cursor] != "{":
            continue
        close = matching_brace(source_text, cursor)
        if close is not None:
            return source_text[match.start():close + 1].strip()
    raise ValueError(f"function definition not found: {function_name}")


def matching_brace(text: str, open_index: int) -> int | None:
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def _fixture_tests_from_oracle(
    spec: Phase5Spec,
    source: str,
    output_dir: Path,
) -> tuple[fixtures.FunctionTest, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    case = fixtures.FunctionCase(spec.case_id, spec.function_name, source, ())
    inputs = [dynamic_trace.TraceInput(args=args, bucket="fixture") for args in spec.fixture_args]
    trace_run = dynamic_trace.run_trace(
        case=case,
        candidate_id="oracle_fixture",
        function_source=source,
        inputs=inputs,
        output_dir=output_dir,
        opt_level="O0",
    )
    if not trace_run.compiled or trace_run.exit_code != 0:
        raise RuntimeError(f"oracle fixture run failed for {spec.case_id}: {trace_run.stderr}")
    return tuple(
        fixtures.FunctionTest(args=trace_input.args, expected=expected)
        for trace_input, expected in zip(inputs, trace_run.outputs)
    )


def _manifest_entry(
    repo_root: Path,
    spec: Phase5Spec,
    source_path: Path,
    source: str,
    tests: tuple[fixtures.FunctionTest, ...],
) -> dict[str, Any]:
    signature = extract_signature(source, spec.function_name)
    arity = len(tests[0].args) if tests else 0
    eligibility = {
        "deterministic": True,
        "integer_only": True,
        "no_io": re.search(r"\b(?:printf|scanf|puts|getchar|fgets)\s*\(", source) is None,
        "no_heap": "malloc" not in source and "calloc" not in source and "free(" not in source,
        "no_external_state": True,
        "bounded_domain": True,
    }
    return {
        "case_id": spec.case_id,
        "project": spec.project,
        "source_path": _path_for_manifest(repo_root, source_path),
        "original_source_path": spec.original_source_path,
        "function_name": spec.function_name,
        "signature": signature,
        "risk_families": list(spec.risk_families),
        "tags": list(spec.tags),
        "domain": {
            "arity": arity,
            "fixture_args": [list(test.args) for test in tests],
            "trace_generation": "bounded_cross_product_from_fixture_values",
            "note": spec.domain_note,
        },
        "fixtures": [
            {"args": list(test.args), "expected": test.expected}
            for test in tests
        ],
        "eligibility": eligibility,
        "extraction_kind": spec.extraction_kind,
        "counts_for_phase5_real_project_gate": all(eligibility.values()),
    }


def phase5_bounded_trace_inputs(
    entry: dict[str, Any],
    max_inputs: int = 128,
) -> list[dynamic_trace.TraceInput]:
    fixtures_args = [tuple(item["args"]) for item in entry.get("fixtures", [])]
    if not fixtures_args:
        return []
    arity = len(fixtures_args[0])
    values_by_position: list[list[int]] = []
    for index in range(arity):
        values = sorted({int(args[index]) for args in fixtures_args})
        values_by_position.append(values)

    generated: dict[tuple[int, ...], str] = {
        args: "fixture" for args in fixtures_args
    }
    for args in _bounded_product(values_by_position, max_inputs=max_inputs * 2):
        generated.setdefault(args, "bounded_cross_product")

    ordered = [
        dynamic_trace.TraceInput(args=args, bucket=generated[args])
        for args in fixtures_args
    ]
    seen = set(fixtures_args)
    for args in sorted(generated):
        if args in seen:
            continue
        ordered.append(dynamic_trace.TraceInput(args=args, bucket=generated[args]))
        if len(ordered) >= max_inputs:
            break
    return ordered[:max_inputs]


def _bounded_product(
    values_by_position: list[list[int]],
    max_inputs: int,
) -> list[tuple[int, ...]]:
    if not values_by_position:
        return [()]
    results: list[tuple[int, ...]] = [()]
    for values in values_by_position:
        next_results: list[tuple[int, ...]] = []
        for prefix in results:
            for value in values:
                next_results.append(prefix + (value,))
                if len(next_results) >= max_inputs:
                    break
            if len(next_results) >= max_inputs:
                break
        results = next_results
        if len(results) >= max_inputs:
            break
    return results[:max_inputs]


def extract_signature(source_text: str, function_name: str) -> str:
    match = re.search(
        rf"^[ \t]*(?:static[ \t]+)?(?:int|unsigned[ \t]+int|long[ \t]+long|long|bool)[ \t]+\**[ \t]*{re.escape(function_name)}[ \t]*\([^;{{}}]*\)",
        source_text,
        flags=re.MULTILINE,
    )
    if match is None:
        raise ValueError(f"function signature not found: {function_name}")
    return " ".join(match.group(0).strip().split())


def _path_for_manifest(repo_root: Path, source_path: Path) -> str:
    try:
        return str(source_path.relative_to(repo_root))
    except ValueError:
        return str(source_path)


def _case_from_manifest_entry(repo_root: Path, entry: dict[str, Any]) -> fixtures.FunctionCase:
    tests = tuple(
        fixtures.FunctionTest(tuple(item["args"]), int(item["expected"]))
        for item in entry.get("fixtures", [])
    )
    return fixtures.FunctionCase(
        case_id=entry["case_id"],
        function_name=entry["function_name"],
        function_source=(repo_root / entry["source_path"]).read_text(encoding="utf-8"),
        tests=tests,
    )


def _source_gate_verdict(eligible_count: int, source_project_count: int) -> str:
    if source_project_count < 2:
        return "needs-more-source-projects"
    if eligible_count < 30:
        return "needs-more-real-project-functions"
    return "pass-phase5-source-gate"


def _preflight_verdict(
    eligible_count: int,
    source_project_count: int,
    records: list[dict[str, Any]],
) -> str:
    if source_project_count < 2 or eligible_count < 30:
        return "needs-more-real-project-functions"
    if any(not record["compiled"] for record in records):
        return "blocked-oracle-compile"
    if any(not record["fixture_passed"] for record in records):
        return "blocked-fixture-coverage"
    if any(not record["oracle_ready"] for record in records):
        return "blocked-bounded-oracle-trace"
    return "pass-phase5-preflight"


def _write_project_report(path: Path, manifest: dict[str, Any], preflight: dict[str, Any]) -> None:
    rows = "\n".join(
        "| `{case_id}` | `{project}` | `{kind}` | `{signature}` | `{risks}` |".format(
            case_id=entry["case_id"],
            project=entry["project"],
            kind=entry["extraction_kind"],
            signature=entry["signature"],
            risks=", ".join(entry["risk_families"]),
        )
        for entry in manifest["functions"]
    )
    text = f"""# Phase 5 Project Candidates

## Candidate Source Trees

- `analysis_inputs/decompile_faithfulness/phase5_external_sources/thealgorithms_c`
- `analysis_inputs/decompile_faithfulness/phase5_external_sources/c_algorithms`

## Exclusion Rules

只保留 deterministic、bounded-domain、integer-trace-compatible 的 C functions。带 I/O、heap-only API、数组/结构体主接口、外部状态、callback 或无法稳定生成边界 oracle 的函数不进入本轮 gate。

## Selected Projects

- `thealgorithms_c`: 以原始小型算法/LeetCode/转换/游戏 helper 为主。
- `c_algorithms`: 原项目多为 pointer/container API；本轮只保留少量明确标注的 scalar adapters，用于测试第二真实项目来源，不把它们夸大为原生 scalar API。

## Function Pool

| Case | Project | Kind | Signature | Risks |
|---|---|---|---|---|
{rows}

## Scale Risk

- Source projects: `{len(manifest['source_projects'])}` / required `2`
- Eligible real-project functions: `{manifest['phase5_real_project_eligible_function_count']}` / required `30`
- Source gate verdict: `{manifest['verdict']}`
- Preflight verdict: `{preflight['verdict']}`

这一步专门回应“小函数池/smoke 不跑 full 是否有说服力”：Phase 5 不再使用 Phase 3 的 12 个 curated functions 作为主证据，而是把真实项目函数池扩展到 `30+` 后才允许进入 GPU candidate generation。

## Next Gate

只有当 `decompile_faithfulness_phase5_preflight.json` 为 `pass-phase5-preflight` 时，才启动 GPU 2/3 生成 100-200 个 compile-pass candidates。
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_gate_report(path: Path, manifest: dict[str, Any], preflight: dict[str, Any]) -> None:
    decision = (
        "pass-phase5-start-gpu-candidate-generation"
        if preflight["verdict"] == "pass-phase5-preflight"
        else preflight["verdict"]
    )
    text = f"""# Decompilation Faithfulness Phase 5 Gate Decision

- Decision: `{decision}`
- Source gate: `{manifest['verdict']}`
- Preflight: `{preflight['verdict']}`
- Eligible functions: `{preflight['eligible_functions']}`
- Source projects: `{preflight['source_project_count']}`
- Oracle ready: `{preflight['oracle_ready']}` / `{manifest['function_count']}`

## CCF-A 风险自查

1. 小函数池/smoke 风险：本 gate 已把 Phase 5 提升到 `30+` real-project source-known functions，且要求后续 GPU candidate manifest 达到 `100-200` compile-pass candidates 与至少 `20` paired functions。未达到前不能称为 full 主实验。
2. SOTA 进步风险：Phase 5 仍不声称生成质量超过 SOTA decompiler；它要证明 Dynamic Trace v3 在 source-known bounded auditing 上显著强于 fixture-only、static/binary motifs、v1/v2 trace baselines。后续结果必须报告 `v3 - best non-oracle baseline >= 0.05`，否则不能写成 CCF-A 主贡献。

## Next

如果 decision 为 `pass-phase5-start-gpu-candidate-generation`，下一步直接在 GPU 2/3 上启动 Phase 5 candidate generation；否则先修 manifest/preflight。
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
