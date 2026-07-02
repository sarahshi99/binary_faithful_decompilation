from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import compile as ccompile
from analysis.decompile_faithfulness import dynamic_trace, fixtures
from analysis.decompile_faithfulness import run_phase5_source_preflight as phase5


DEFAULT_CODEFUSE_ROOT = Path("external/CodeFuse-DeBench-shallow")
DEFAULT_SOURCE_DIR = Path("analysis_inputs/decompile_faithfulness/phase7_codefuse_sources")
DEFAULT_OUTPUT_DIR = Path("analysis_outputs/decompile_faithfulness/phase7_codefuse_import")
DEFAULT_MANIFEST_JSON = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_function_manifest.json")
DEFAULT_PREFLIGHT_JSON = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_import_preflight.json")
DEFAULT_OUTPUT_ZH = Path("docs/paper_agent/decompile_faithfulness_phase7_codefuse_import_preflight.zh.md")


@dataclass(frozen=True)
class ScalarFunction:
    source_file: str
    name: str
    signature: str
    body: str
    arity: int


def main() -> None:
    args = parse_args()
    summary = run_import(
        repo_root=args.repo_root,
        codefuse_root=args.codefuse_root,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        manifest_json=args.manifest_json,
        preflight_json=args.preflight_json,
        output_zh=args.output_zh,
        max_functions=args.max_functions,
    )
    print(
        json.dumps(
            {
                "verdict": summary["preflight"]["verdict"],
                "source_file_count": summary["manifest"]["source_file_count"],
                "imported_function_count": summary["manifest"]["function_count"],
                "oracle_ready": summary["preflight"]["oracle_ready"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--codefuse-root", type=Path, default=DEFAULT_CODEFUSE_ROOT)
    parser.add_argument("--source-dir", type=Path, default=DEFAULT_SOURCE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST_JSON)
    parser.add_argument("--preflight-json", type=Path, default=DEFAULT_PREFLIGHT_JSON)
    parser.add_argument("--output-zh", type=Path, default=DEFAULT_OUTPUT_ZH)
    parser.add_argument("--max-functions", type=int, default=80)
    return parser.parse_args()


def run_import(
    repo_root: Path,
    codefuse_root: Path,
    source_dir: Path,
    output_dir: Path,
    manifest_json: Path,
    preflight_json: Path,
    output_zh: Path,
    max_functions: int,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    codefuse_root = _resolve(repo_root, codefuse_root)
    source_dir = _resolve(repo_root, source_dir)
    output_dir = _resolve(repo_root, output_dir)
    manifest_json = _resolve(repo_root, manifest_json)
    preflight_json = _resolve(repo_root, preflight_json)
    output_zh = _resolve(repo_root, output_zh)

    manifest = build_manifest(
        repo_root=repo_root,
        codefuse_root=codefuse_root,
        source_dir=source_dir,
        max_functions=max_functions,
    )
    preflight = run_preflight(repo_root=repo_root, manifest=manifest, output_dir=output_dir)
    _write_json(manifest_json, manifest)
    _write_json(preflight_json, preflight)
    _write_markdown(output_zh, manifest, preflight)
    return {"manifest": manifest, "preflight": preflight}


def build_manifest(
    repo_root: Path,
    codefuse_root: Path,
    source_dir: Path,
    max_functions: int,
) -> dict[str, Any]:
    source_dir.mkdir(parents=True, exist_ok=True)
    source_files = list_codefuse_source_files(codefuse_root)
    functions: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    seen_case_ids: set[str] = set()
    for source_file in source_files:
        try:
            text = read_codefuse_blob(codefuse_root, f"src/{source_file}")
        except Exception as exc:
            errors.append({"source_file": source_file, "reason": repr(exc)})
            continue
        for scalar in extract_scalar_functions(text, source_file):
            if len(functions) >= max_functions:
                break
            try:
                case_id = case_id_for_function(source_file, scalar.name)
                if case_id in seen_case_ids:
                    errors.append(
                        {
                            "source_file": source_file,
                            "function_name": scalar.name,
                            "reason": "duplicate_case_id_deferred",
                        }
                    )
                    continue
                seen_case_ids.add(case_id)
                source_path = source_dir / f"{case_id}.c"
                source_path.write_text(scalar.body.rstrip() + "\n", encoding="utf-8")
                tests = fixture_tests_from_oracle(scalar, source_path.parent / "oracle_fixtures")
                functions.append(manifest_entry(repo_root, codefuse_root, scalar, source_path, tests))
            except Exception as exc:
                errors.append(
                    {
                        "source_file": source_file,
                        "function_name": scalar.name,
                        "reason": repr(exc),
                    }
                )
        if len(functions) >= max_functions:
            break
    return {
        "phase": "phase7_codefuse_public_benchmark_import",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "benchmark": "CodeFuse-DeBench",
        "codefuse_root": str(codefuse_root),
        "import_mode": "partial_git_tree_src_scalar_integer_functions",
        "source_file_count": len(source_files),
        "function_count": len(functions),
        "minimum_required": {
            "imported_functions": 50,
            "oracle_ready": 30,
        },
        "functions": functions,
        "import_errors": errors,
        "verdict": "pending-preflight",
    }


def list_codefuse_source_files(codefuse_root: Path) -> list[str]:
    result = ccompile.run_command(
        ["git", "ls-tree", "-r", "--name-only", "HEAD:src"],
        cwd=codefuse_root,
        timeout_s=20,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip().endswith(".c")
    ]


def read_codefuse_blob(codefuse_root: Path, tree_path: str) -> str:
    result = ccompile.run_command(
        ["git", "show", f"HEAD:{tree_path}"],
        cwd=codefuse_root,
        timeout_s=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return result.stdout


FUNCTION_RE = re.compile(
    r"^[ \t]*(?P<ret>int|unsigned[ \t]+int|short|char|long|long[ \t]+long|_Bool)[ \t]+"
    r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)[ \t]*\((?P<params>[^;{}]*)\)[ \t]*\{",
    re.MULTILINE,
)


def extract_scalar_functions(source: str, source_file: str) -> list[ScalarFunction]:
    items: list[ScalarFunction] = []
    seen_names: set[str] = set()
    for match in FUNCTION_RE.finditer(source):
        name = match.group("name")
        if name.startswith("test_") or name == "main" or function_name_is_deferred(name):
            continue
        if name in seen_names:
            continue
        seen_names.add(name)
        params = match.group("params").strip()
        if not scalar_integer_params(params):
            continue
        close = find_matching_brace(source, match.end() - 1)
        if close is None:
            continue
        body = source[match.start(): close + 1]
        if not function_body_is_supported(body, name):
            continue
        signature = " ".join(source[match.start(): match.end() - 1].strip().split())
        items.append(
            ScalarFunction(
                source_file=source_file,
                name=name,
                signature=signature,
                body=body,
                arity=0 if params in {"", "void"} else len(split_params(params)),
            )
        )
    return items


def scalar_integer_params(params: str) -> bool:
    if params in {"", "void"}:
        return True
    for param in split_params(params):
        if "*" in param or "[" in param or "]" in param:
            return False
        normalized = " ".join(param.replace("const ", "").strip().split())
        if not re.fullmatch(
            r"(?:int|unsigned int|short|char|long|long long|_Bool)\s+[A-Za-z_][A-Za-z0-9_]*",
            normalized,
        ):
            return False
    return True


def split_params(params: str) -> list[str]:
    return [part.strip() for part in params.split(",") if part.strip()]


def function_body_is_supported(body: str, name: str) -> bool:
    unsupported = (
        "printf(",
        "scanf(",
        "malloc(",
        "calloc(",
        "free(",
        "alloca(",
        "longjmp(",
        "setjmp(",
    )
    if any(token in body for token in unsupported):
        return False
    if re.search(r"\b(?:float|double|long[ \t]+double)\b", body):
        return False
    if re.search(r"\b(?:static|__thread|thread_local|try|catch|throw|class|new|delete|this)\b", body):
        return False
    if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*[ \t]*\(", strip_signature_and_keywords(body, name)):
        return False
    return True


def function_name_is_deferred(name: str) -> bool:
    lowered = name.lower()
    deferred_fragments = (
        "cpp",
        "thiscall",
        "tls",
        "extern",
        "global",
        "static",
        "file_static",
    )
    return any(fragment in lowered for fragment in deferred_fragments)


def strip_signature_and_keywords(body: str, name: str) -> str:
    text = re.sub(rf"\b{name}[ \t]*\(", "", body, count=1)
    return re.sub(r"\b(?:if|for|while|switch|return|sizeof)\s*\(", "", text)


def find_matching_brace(text: str, open_index: int) -> int | None:
    depth = 0
    for index in range(open_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def fixture_args_for_arity(arity: int) -> tuple[tuple[int, ...], ...]:
    if arity == 0:
        return ((),)
    if arity == 1:
        return ((0,), (1,), (5,), (-3,))
    if arity == 2:
        return ((1, 2), (5, 3), (8, 4))
    if arity == 3:
        return ((1, 2, 3), (5, 3, 1), (8, 4, 2))
    return tuple(tuple(range(1, arity + 1)) for _ in range(3))


def fixture_tests_from_oracle(
    scalar: ScalarFunction,
    output_dir: Path,
) -> tuple[fixtures.FunctionTest, ...]:
    output_dir.mkdir(parents=True, exist_ok=True)
    case = fixtures.FunctionCase(
        case_id=case_id_for_function(scalar.source_file, scalar.name),
        function_name=scalar.name,
        function_source=scalar.body,
        tests=(),
    )
    inputs = [
        dynamic_trace.TraceInput(args=args, bucket="fixture")
        for args in fixture_args_for_arity(scalar.arity)
    ]
    trace_run = dynamic_trace.run_trace(
        case=case,
        candidate_id="oracle_fixture",
        function_source=scalar.body,
        inputs=inputs,
        output_dir=output_dir,
        opt_level="O0",
    )
    if not trace_run.compiled or trace_run.exit_code != 0:
        raise RuntimeError(trace_run.stderr)
    return tuple(
        fixtures.FunctionTest(args=item.args, expected=expected)
        for item, expected in zip(inputs, trace_run.outputs)
    )


def manifest_entry(
    repo_root: Path,
    codefuse_root: Path,
    scalar: ScalarFunction,
    source_path: Path,
    tests: tuple[fixtures.FunctionTest, ...],
) -> dict[str, Any]:
    eligibility = {
        "deterministic": True,
        "integer_only": True,
        "no_io": True,
        "no_heap": True,
        "no_external_state": True,
        "bounded_domain": True,
    }
    return {
        "case_id": case_id_for_function(scalar.source_file, scalar.name),
        "project": "CodeFuse-DeBench",
        "benchmark": "CodeFuse-DeBench",
        "source_path": path_for_manifest(repo_root, source_path),
        "original_source_path": f"{path_for_manifest(repo_root, codefuse_root)}/src/{scalar.source_file}",
        "function_name": scalar.name,
        "signature": scalar.signature,
        "risk_families": risk_families_for_function(scalar),
        "tags": ["codefuse_debench", "public_benchmark", "source_known"],
        "domain": {
            "arity": scalar.arity,
            "fixture_args": [list(test.args) for test in tests],
            "trace_generation": "bounded_cross_product_from_fixture_values",
            "note": "auto_generated_scalar_integer_fixtures",
        },
        "fixtures": [
            {"args": list(test.args), "expected": test.expected}
            for test in tests
        ],
        "eligibility": eligibility,
        "extraction_kind": "codefuse_src_scalar_integer_function",
        "counts_for_phase7_public_benchmark_gate": all(eligibility.values()),
    }


def risk_families_for_function(scalar: ScalarFunction) -> list[str]:
    body = scalar.body
    risks = ["public_benchmark"]
    if any(token in body for token in ("if ", "if(")):
        risks.append("branch")
    if any(token in body for token in ("for ", "for(", "while ", "while(")):
        risks.append("loop")
    if any(token in body for token in ("%", "/", "<<", ">>", "&", "|", "^")):
        risks.append("operator_boundary")
    if scalar.arity >= 2:
        risks.append("multi_arg")
    return risks


def case_id_for_function(source_file: str, function_name: str) -> str:
    stem = re.sub(r"\.[^.]+$", "", source_file)
    value = f"codefuse_{stem}_{function_name}"
    value = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_").lower()
    return value or "codefuse_function"


def run_preflight(repo_root: Path, manifest: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    records = []
    for entry in manifest["functions"]:
        case = case_from_manifest_entry(repo_root, entry)
        compile_result = ccompile.compile_candidate(
            case=case,
            candidate_id="original",
            function_source=case.function_source,
            output_dir=output_dir / "compile",
            opt_level="O0",
        )
        trace_inputs = phase5.phase5_bounded_trace_inputs(entry, max_inputs=128)
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
                "source_path": entry["source_path"],
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
    oracle_ready = sum(1 for record in records if record["oracle_ready"])
    imported = len(manifest["functions"])
    return {
        "phase": "phase7_codefuse_import_preflight",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "imported_functions": imported,
        "compile_pass": sum(1 for record in records if record["compiled"]),
        "fixture_pass": sum(1 for record in records if record["fixture_passed"]),
        "oracle_ready": oracle_ready,
        "records": records,
        "verdict": import_verdict(imported=imported, oracle_ready=oracle_ready),
    }


def import_verdict(imported: int, oracle_ready: int) -> str:
    if imported < 50:
        return "needs-more-codefuse-functions"
    if oracle_ready < 30:
        return "blocked-codefuse-oracle-preflight"
    return "pass-phase7-codefuse-import"


def case_from_manifest_entry(repo_root: Path, entry: dict[str, Any]) -> fixtures.FunctionCase:
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


def path_for_manifest(repo_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_markdown(path: Path, manifest: dict[str, Any], preflight: dict[str, Any]) -> None:
    rows = "\n".join(
        "| `{case_id}` | `{signature}` | `{ready}` | `{risks}` |".format(
            case_id=entry["case_id"],
            signature=entry["signature"],
            ready=next((r["oracle_ready"] for r in preflight["records"] if r["case_id"] == entry["case_id"]), False),
            risks=", ".join(entry["risk_families"]),
        )
        for entry in manifest["functions"][:80]
    )
    text = f"""# Decompilation Faithfulness Phase 7 CodeFuse-DeBench Import

- Verdict: `{preflight['verdict']}`
- Benchmark: `CodeFuse-DeBench`
- Import mode: `{manifest['import_mode']}`
- Source files discovered: `{manifest['source_file_count']}`
- Imported functions: `{manifest['function_count']}`
- Oracle ready: `{preflight['oracle_ready']}`
- Compile pass: `{preflight['compile_pass']}`
- Fixture pass: `{preflight['fixture_pass']}`

## Imported Functions

| Case | Signature | Oracle ready | Risks |
|---|---|---:|---|
{rows}

## Interpretation

This import uses CodeFuse-DeBench source files as a public source-known benchmark seed. It intentionally keeps only scalar integer C functions that fit the current bounded dynamic trace harness. Pointer, array, floating-point, C++ and helper-dependent functions are deferred to later adapters.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _resolve(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


if __name__ == "__main__":
    main()
