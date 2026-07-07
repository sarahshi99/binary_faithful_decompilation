from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import itertools
import json
import os
import random
import re
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


PHASE3A_BRANCH = "phase3a-prospective-natural-error-census"
PHASE3A_BASE_HEAD = "a2c975609aed5975431ec1a770c9cd92c37c2b1f"
PREREGISTRATION_COMMIT = "2b0e62472b3ee766bba9f64a440d52f0f53bedf9"
PRODUCER_SETUP_COMMIT = "5532b6d"
SAMPLING_SEED = 2026070701
FIXTURE_SEED = 2026070702
TARGET_FUNCTIONS = 120
MIN_FEASIBLE_FUNCTIONS = 80
MIN_PROJECTS = 12
PROJECT_CAP = 10
FIXTURES_PER_FUNCTION = 4
MAX_DOMAIN_SIZE = 32768

GCC = Path("/usr/bin/gcc")

PRIMARY_PROJECT_POOL = [
    ("libyaml", "https://github.com/yaml/libyaml.git"),
    ("jansson", "https://github.com/akheron/jansson.git"),
    ("expat", "https://github.com/libexpat/libexpat.git"),
    ("lz4", "https://github.com/lz4/lz4.git"),
    ("zstd", "https://github.com/facebook/zstd.git"),
    ("libpng", "https://github.com/pnggroup/libpng.git"),
    ("libjpeg-turbo", "https://github.com/libjpeg-turbo/libjpeg-turbo.git"),
    ("utf8proc", "https://github.com/JuliaStrings/utf8proc.git"),
    ("cmark", "https://github.com/commonmark/cmark.git"),
    ("miniz", "https://github.com/richgel999/miniz.git"),
    ("mpack", "https://github.com/ludocode/mpack.git"),
    ("parson", "https://github.com/kgabis/parson.git"),
    ("picohttpparser", "https://github.com/h2o/picohttpparser.git"),
    ("klib", "https://github.com/attractivechaos/klib.git"),
    ("bstrlib", "https://github.com/websnarf/bstrlib.git"),
    ("libcsv", "https://github.com/rgamble/libcsv.git"),
    ("nanoprintf", "https://github.com/charlesnicholson/nanoprintf.git"),
    ("sds", "https://github.com/antirez/sds.git"),
    ("libconfuse", "https://github.com/libconfuse/libconfuse.git"),
    ("libucl", "https://github.com/vstakhov/libucl.git"),
]

FALLBACK_PROJECT_POOL = [
    ("json-c", "https://github.com/json-c/json-c.git"),
    ("yyjson", "https://github.com/ibireme/yyjson.git"),
    ("qbe", "https://c9x.me/git/qbe.git"),
    ("htslib", "https://github.com/samtools/htslib.git"),
    ("libevent", "https://github.com/libevent/libevent.git"),
    ("libuv", "https://github.com/libuv/libuv.git"),
    ("brotli", "https://github.com/google/brotli.git"),
    ("nghttp2", "https://github.com/nghttp2/nghttp2.git"),
    ("c-ares", "https://github.com/c-ares/c-ares.git"),
    ("cwalk", "https://github.com/likle/cwalk.git"),
    ("mxml", "https://github.com/michaelrsweet/mxml.git"),
    ("libxdiff", "https://github.com/libgit2/xdiff.git"),
    ("ccan", "https://github.com/rustyrussell/ccan.git"),
    ("open62541", "https://github.com/open62541/open62541.git"),
    ("pcre2", "https://github.com/PCRE2Project/pcre2.git"),
    ("libunistring", "https://git.savannah.gnu.org/git/libunistring.git"),
    ("libidn2", "https://gitlab.com/libidn/libidn2.git"),
    ("freetype", "https://gitlab.freedesktop.org/freetype/freetype.git"),
    ("harfbuzz", "https://github.com/harfbuzz/harfbuzz.git"),
]

FORBIDDEN_PRIOR_PROJECTS = {
    "CodeFuse-DeBench",
    "c_algorithms",
    "thealgorithms_c",
    "libtommath",
    "cJSON",
    "uthash",
    "musl",
    "zlib",
    "mbedtls",
    "sqlite",
    "libb64",
    "inih",
    "tiny-AES-c",
    "libtomcrypt",
    "BearSSL",
    "libdeflate",
    "xxHash",
    "TinyCC",
    "chibicc",
    "sbase",
}

FORBIDDEN_SOURCE_PATH_TOKENS = {
    "bearssl",
    "c_algorithms",
    "chibicc",
    "codefuse",
    "cjson",
    "inih",
    "libb64",
    "libdeflate",
    "libtomcrypt",
    "libtommath",
    "mbedtls",
    "musl",
    "sbase",
    "sqlite",
    "thealgorithms",
    "tiny-aes",
    "tiny_aes",
    "tinycc",
    "uthash",
    "xxhash",
    "zlib",
}

SCALAR_TYPES = {
    "char",
    "signed char",
    "unsigned char",
    "_Bool",
    "bool",
    "short",
    "short int",
    "signed short",
    "signed short int",
    "unsigned short",
    "unsigned short int",
    "int",
    "signed int",
    "unsigned int",
    "long",
    "long int",
    "signed long",
    "signed long int",
    "unsigned long",
    "unsigned long int",
    "long long",
    "long long int",
    "signed long long",
    "signed long long int",
    "unsigned long long",
    "unsigned long long int",
    "int8_t",
    "uint8_t",
    "int16_t",
    "uint16_t",
    "int32_t",
    "uint32_t",
    "int64_t",
    "uint64_t",
    "size_t",
}

SIGNED_TYPES = {
    "char",
    "signed char",
    "short",
    "short int",
    "signed short",
    "signed short int",
    "int",
    "signed int",
    "long",
    "long int",
    "signed long",
    "signed long int",
    "long long",
    "long long int",
    "signed long long",
    "signed long long int",
    "int8_t",
    "int16_t",
    "int32_t",
    "int64_t",
}

UNSIGNED_TYPES = {
    "unsigned char",
    "_Bool",
    "bool",
    "unsigned short",
    "unsigned short int",
    "unsigned int",
    "unsigned long",
    "unsigned long int",
    "unsigned long long",
    "unsigned long long int",
    "uint8_t",
    "uint16_t",
    "uint32_t",
    "uint64_t",
    "size_t",
}

CHAR_LIKE_TYPES = {"char", "signed char", "unsigned char", "int8_t", "uint8_t"}

KEYWORDS = {
    "if",
    "for",
    "while",
    "switch",
    "return",
    "sizeof",
    "do",
    "case",
}

BLACKLIST_PATTERNS = [
    r"\bmalloc\b",
    r"\bcalloc\b",
    r"\brealloc\b",
    r"\bfree\b",
    r"\bfopen\b",
    r"\bfclose\b",
    r"\bfread\b",
    r"\bfwrite\b",
    r"\bprintf\b",
    r"\bfprintf\b",
    r"\bsprintf\b",
    r"\bsnprintf\b",
    r"\bscanf\b",
    r"\bgetenv\b",
    r"\bsetenv\b",
    r"\btime\b",
    r"\bclock\b",
    r"\blocale\b",
    r"\bpthread_",
    r"\berrno\b",
    r"\bsetjmp\b",
    r"\blongjmp\b",
    r"\bvolatile\b",
]

SKIP_DIR_PARTS = {
    ".git",
    "test",
    "tests",
    "testing",
    "example",
    "examples",
    "doc",
    "docs",
    "benchmark",
    "bench",
    "fuzz",
    "fuzzer",
    "build",
    "cmake",
    "script",
    "scripts",
    "contrib",
    "third_party",
}

FORBIDDEN_AUDITOR_IMPORTS = {
    "analysis.decompile_faithfulness.holdout_evaluation",
    "analysis.decompile_faithfulness.libfuzzer_wallclock",
    "analysis.decompile_faithfulness.source_behavioral_diversity",
    "analysis.decompile_faithfulness.strong_baselines_and_mechanism",
    "analysis.decompile_faithfulness.run_phase18_source_literal_char_policy",
    "analysis.decompile_faithfulness.run_phase11_input_ordering",
}

FORBIDDEN_AUDITOR_CALLS = {
    "build_ordered_inputs",
    "source_literal_char_inputs",
    "fixture_neighbor_inputs",
    "interleave_inputs",
    "run_policy",
    "run_trace",
    "build_libfuzzer_harness",
}


@dataclass(frozen=True)
class Param:
    type_text: str
    name: str


@dataclass(frozen=True)
class FunctionRecord:
    project: str
    pool: str
    project_order: int
    source_file: str
    function_name: str
    ordinal: int
    return_type: str
    params: tuple[Param, ...]
    source: str
    support_source: str
    source_sha256: str
    source_file_sha256: str
    function_id: str
    domain_values: tuple[tuple[int, ...], ...]
    domain: tuple[tuple[int, ...], ...]
    domain_size: int
    features: dict[str, Any]
    validation_reason: str = "ok"


def main() -> None:
    args = parse_args()
    summary = run(args.repo_root.resolve())
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build and seal Phase 3a function corpus and fixtures.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args()


def run(repo_root: Path) -> dict[str, Any]:
    out = repo_root / "results/decompile_faithfulness"
    analysis_out = repo_root / "analysis/decompile_faithfulness"
    work = repo_root / "analysis_outputs/decompile_faithfulness/phase3a_corpus"
    project_root = repo_root / "external/phase3a_projects"
    for path in [out, analysis_out, work, project_root]:
        path.mkdir(parents=True, exist_ok=True)
    command_log = out / "phase3a_corpus_execution_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    project_records: list[dict[str, Any]] = []
    all_rows: list[dict[str, Any]] = []
    eligible: list[FunctionRecord] = []
    acquisition_errors: list[dict[str, Any]] = []

    primary_records, primary_rows, primary_eligible, primary_errors = acquire_and_scan_pool(
        repo_root, project_root, command_log, "primary", PRIMARY_PROJECT_POOL, start_order=1
    )
    project_records.extend(primary_records)
    all_rows.extend(primary_rows)
    eligible.extend(primary_eligible)
    acquisition_errors.extend(primary_errors)

    fallback_used = False
    if not primary_satisfies_full_target(primary_eligible):
        fallback_used = True
        fallback_records, fallback_rows, fallback_eligible, fallback_errors = acquire_and_scan_pool(
            repo_root,
            project_root,
            command_log,
            "fallback",
            FALLBACK_PROJECT_POOL,
            start_order=len(PRIMARY_PROJECT_POOL) + 1,
        )
        project_records.extend(fallback_records)
        all_rows.extend(fallback_rows)
        eligible.extend(fallback_eligible)
        acquisition_errors.extend(fallback_errors)

    write_json(out / "phase3a_project_manifest.json", build_project_manifest(project_records, acquisition_errors))
    write_csv(out / "phase3a_eligibility_census.csv", all_rows, eligibility_fieldnames())
    write_jsonl(out / "phase3a_exclusions.jsonl", [row for row in all_rows if row["eligibility_status"] != "eligible"])

    gate = corpus_gate(eligible)
    selected: list[FunctionRecord] = []
    fixtures: list[dict[str, Any]] = []
    seal_hash = ""
    feasibility_amendment_needed = False
    feasibility_amendment_path = repo_root / "docs/paper_agent/phase3a_function_corpus_feasibility_amendment.md"

    if gate["status"] in {"target_120_available", "reduced_feasible"}:
        target = int(gate["target_selected_functions"])
        feasibility_amendment_needed = gate["status"] == "reduced_feasible"
        if feasibility_amendment_needed:
            write_feasibility_amendment(feasibility_amendment_path, gate, eligible)
        selected = select_functions(eligible, target)
        write_csv(out / "phase3a_selected_functions.csv", [selected_row(item, index) for index, item in enumerate(selected, start=1)], selected_fieldnames())
        fixtures = generate_fixtures(selected, work, command_log)
        write_jsonl(out / "phase3a_fixtures.jsonl", fixtures)
        seal = build_function_fixture_seal(repo_root, selected, fixtures, gate, fallback_used)
        seal_path = analysis_out / "phase3a_function_fixture_seal.json"
        write_json(seal_path, seal)
        seal_hash = sha256_path(seal_path)
        (analysis_out / "phase3a_function_fixture_seal.sha256").write_text(
            f"{seal_hash}  phase3a_function_fixture_seal.json\n",
            encoding="utf-8",
        )
    else:
        write_csv(out / "phase3a_selected_functions.csv", [], selected_fieldnames())
        write_jsonl(out / "phase3a_fixtures.jsonl", [])

    update_handoff(repo_root, project_records, eligible, selected, fixtures, gate, fallback_used, feasibility_amendment_needed, seal_hash)
    return {
        "status": gate["status"],
        "projects_scanned": len(project_records),
        "eligible_projects": len({item.project for item in eligible}),
        "eligible_functions": len(eligible),
        "selected_functions": len(selected),
        "fixtures": len(fixtures),
        "fallback_used": fallback_used,
        "seal_sha256": seal_hash,
    }


def acquire_and_scan_pool(
    repo_root: Path,
    project_root: Path,
    command_log: Path,
    pool_name: str,
    pool: list[tuple[str, str]],
    start_order: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[FunctionRecord], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    eligible: list[FunctionRecord] = []
    errors: list[dict[str, Any]] = []
    for offset, (name, url) in enumerate(pool):
        order = start_order + offset
        if name in FORBIDDEN_PRIOR_PROJECTS:
            errors.append({"project": name, "reason": "forbidden_prior_phase_project"})
            continue
        path = project_root / safe_name(name)
        acquired = acquire_project(repo_root, path, url, command_log)
        if not acquired["ok"]:
            errors.append({"project": name, "repository": url, "reason": acquired["reason"]})
        record = project_record(order, name, url, pool_name, path, acquired["ok"])
        project_rows, project_eligible = scan_project(record, command_log, repo_root / "analysis_outputs/decompile_faithfulness/phase3a_corpus/source_validation")
        if not acquired["ok"]:
            project_rows.append(project_exclusion_row(record, "project_acquisition_failed:" + acquired["reason"][:500]))
        record["source_files_scanned"] = len(record.get("source_file_hashes", []))
        record["yielded_eligible_functions"] = bool(project_eligible)
        record["eligible_function_count"] = len(project_eligible)
        records.append(record)
        rows.extend(project_rows)
        eligible.extend(project_eligible)
    return records, rows, eligible, errors


def acquire_project(repo_root: Path, path: Path, url: str, command_log: Path) -> dict[str, Any]:
    if path.exists() and (path / ".git").exists():
        if not git_at(path, ["rev-parse", "HEAD"]):
            return {"ok": False, "reason": "existing_checkout_without_resolved_head"}
        return {"ok": True, "reason": "existing_checkout"}
    path.parent.mkdir(parents=True, exist_ok=True)
    result = run_command(["git", "clone", "--depth", "1", url, str(path)], repo_root, command_log, timeout_s=240)
    if result.returncode != 0:
        return {"ok": False, "reason": (result.stderr or result.stdout)[-1000:]}
    if not git_at(path, ["rev-parse", "HEAD"]):
        return {"ok": False, "reason": "clone_without_resolved_head"}
    return {"ok": True, "reason": "cloned"}


def project_record(order: int, name: str, url: str, pool: str, path: Path, acquired: bool) -> dict[str, Any]:
    source_hashes = []
    license_files = []
    if acquired:
        for source in iter_source_files(path):
            source_hashes.append({"path": source.relative_to(path).as_posix(), "sha256": sha256_path(source)})
        for item in sorted(path.iterdir()):
            if item.is_file() and item.name.lower().startswith(("license", "copying", "copyright")):
                license_files.append({"path": item.name, "sha256": sha256_path(item)})
    return {
        "order": order,
        "project": name,
        "pool": pool,
        "canonical_repository": url,
        "local_path": str(path),
        "acquired": acquired,
        "acquisition_date": date.today().isoformat(),
        "pinned_commit": git_at(path, ["rev-parse", "HEAD"]) if acquired else "",
        "resolved_commit": git_at(path, ["rev-parse", "HEAD"]) if acquired else "",
        "license_metadata": license_files or [{"path": "", "sha256": "", "status": "not_found_or_unavailable"}],
        "source_file_hashes": source_hashes,
        "source_files_scanned": len(source_hashes),
        "yielded_eligible_functions": False,
        "eligible_function_count": 0,
    }


def scan_project(record: dict[str, Any], command_log: Path, validation_root: Path) -> tuple[list[dict[str, Any]], list[FunctionRecord]]:
    if not record["acquired"]:
        return [], []
    root = Path(record["local_path"])
    rows: list[dict[str, Any]] = []
    eligible: list[FunctionRecord] = []
    for source_file in iter_source_files(root):
        rel = source_file.relative_to(root).as_posix()
        text = read_text_lossy(source_file)
        enum_values = extract_enum_values(text)
        support_source = extract_support_source(text)
        for ordinal, parsed in enumerate(extract_functions(text, enum_values), start=1):
            signature = parse_signature(parsed["header"], enum_values)
            if signature is None:
                rows.append(census_row(record, rel, parsed, "not_eligible", "signature_filter_failed"))
                continue
            return_type, params = signature
            domain_values = declared_domain_values(params, enum_values)
            if domain_values is None:
                rows.append(census_row(record, rel, parsed, "not_eligible", "unsupported_or_oversized_domain"))
                continue
            dep_reason = dependency_filter_reason(parsed["source"], params, support_source)
            if dep_reason:
                rows.append(census_row(record, rel, parsed, "not_eligible", dep_reason, return_type, params, domain_values))
                continue
            function_id = stable_function_id(record["project"], rel, parsed["name"], ordinal, parsed["source"])
            domain = tuple(itertools.product(*domain_values))
            features = structural_features(parsed["source"], params)
            candidate = FunctionRecord(
                project=record["project"],
                pool=record["pool"],
                project_order=int(record["order"]),
                source_file=rel,
                function_name=parsed["name"],
                ordinal=ordinal,
                return_type=return_type,
                params=tuple(params),
                source=parsed["source"],
                support_source=support_source,
                source_sha256=sha256_text(parsed["source"]),
                source_file_sha256=sha256_path(source_file),
                function_id=function_id,
                domain_values=tuple(domain_values),
                domain=domain,
                domain_size=len(domain),
                features=features,
            )
            validation = validate_source_function(candidate, validation_root / safe_name(function_id), command_log)
            if not validation["ok"]:
                rows.append(census_row(record, rel, parsed, "not_eligible", validation["reason"], return_type, params, domain_values, features))
                continue
            eligible.append(candidate)
            rows.append(census_row(record, rel, parsed, "eligible", "ok", return_type, params, domain_values, features, function_id))
    return rows, eligible


def extract_functions(text: str, enum_values: dict[str, tuple[int, ...]] | None = None) -> list[dict[str, str]]:
    enum_values = enum_values or {}
    clean = strip_comments(text)
    type_names = sorted(set(SCALAR_TYPES) | set(enum_values) | {f"enum {name}" for name in enum_values})
    type_pattern = "|".join(re.escape(name).replace(r"\ ", r"\s+") for name in sorted(type_names, key=len, reverse=True))
    pattern = re.compile(
        rf"(?m)^[ \t]*(?P<header>(?:(?:static|inline|extern|const|__inline|__inline__)\s+)*(?:{type_pattern})\s+"
        rf"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<params>[^;{{}}]*)\))\s*(?:__attribute__\s*\(\([^)]*\)\)\s*)?\{{"
    )
    results = []
    for match in pattern.finditer(clean):
        brace = clean.find("{", match.end() - 1)
        end = matching_brace(clean, brace)
        if end is None:
            continue
        source = clean[match.start() : end + 1].strip()
        if source.count("{") != source.count("}"):
            continue
        results.append({"header": match.group("header"), "name": match.group("name"), "params": match.group("params"), "source": source})
    return results


def parse_signature(header: str, enum_values: dict[str, tuple[int, ...]] | None = None) -> tuple[str, list[Param]] | None:
    enum_values = enum_values or {}
    before, _, rest = header.partition("(")
    params_text = rest.rsplit(")", 1)[0].strip()
    before = normalize_ws(re.sub(r"\b(static|inline|extern|const|__inline|__inline__)\b", " ", before))
    parts = before.split()
    if len(parts) < 2:
        return None
    name = parts[-1]
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        return None
    return_type = normalize_type(" ".join(parts[:-1]))
    if not is_supported_scalar_type(return_type, enum_values):
        return None
    if "*" in return_type or not params_text or params_text == "void":
        return None
    params: list[Param] = []
    for raw in split_params(params_text):
        if "*" in raw or "[" in raw or "]" in raw or "..." in raw:
            return None
        raw = normalize_ws(re.sub(r"\b(const|register|restrict)\b", " ", raw))
        bits = raw.split()
        if len(bits) < 2:
            return None
        param_name = bits[-1]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", param_name):
            return None
        type_text = normalize_type(" ".join(bits[:-1]))
        if not is_supported_scalar_type(type_text, enum_values):
            return None
        params.append(Param(type_text=type_text, name=param_name))
    if len(params) not in {1, 2, 3}:
        return None
    return return_type, params


def normalize_type(text: str) -> str:
    text = normalize_ws(text)
    aliases = {
        "signed": "signed int",
        "unsigned": "unsigned int",
        "short signed": "signed short",
        "long signed": "signed long",
        "long long signed": "signed long long",
    }
    return aliases.get(text, text)


def is_supported_scalar_type(type_text: str, enum_values: dict[str, tuple[int, ...]]) -> bool:
    return type_text in SCALAR_TYPES or type_text in enum_values or type_text.startswith("enum ")


def split_params(params_text: str) -> list[str]:
    return [part.strip() for part in params_text.split(",") if part.strip()]


def declared_domain_values(params: list[Param], enum_values: dict[str, tuple[int, ...]]) -> tuple[tuple[int, ...], ...] | None:
    arity = len(params)
    domains = []
    for param in params:
        values = type_domain(param.type_text, arity, enum_values)
        if not values:
            return None
        domains.append(tuple(values))
    size = 1
    for values in domains:
        size *= len(values)
    if size > MAX_DOMAIN_SIZE:
        return None
    return tuple(domains)


def type_domain(type_text: str, arity: int, enum_values: dict[str, tuple[int, ...]]) -> tuple[int, ...]:
    if type_text in enum_values:
        return enum_domain(enum_values[type_text], arity)
    if type_text.startswith("enum ") and type_text[5:] in enum_values:
        return enum_domain(enum_values[type_text[5:]], arity)
    if type_text in {"bool", "_Bool"}:
        return (0, 1)
    if arity == 1:
        if type_text in CHAR_LIKE_TYPES:
            return tuple(range(0, 128))
        if type_text in UNSIGNED_TYPES:
            return tuple(range(0, 128))
        if type_text in SIGNED_TYPES:
            return tuple(range(-64, 64))
    if arity == 2:
        if type_text in SIGNED_TYPES:
            return tuple(range(-32, 32))
        if type_text in UNSIGNED_TYPES or type_text in CHAR_LIKE_TYPES:
            return tuple(range(0, 64))
    if arity == 3:
        if type_text in SIGNED_TYPES:
            return tuple(range(-8, 8))
        if type_text in UNSIGNED_TYPES or type_text in CHAR_LIKE_TYPES:
            return tuple(range(0, 16))
    return ()


def enum_domain(values: tuple[int, ...], arity: int) -> tuple[int, ...]:
    if not values:
        return ()
    base = sorted(set(values) | {min(values) - 1, max(values) + 1})
    limit = 128 if arity == 1 else 64 if arity == 2 else 16
    return tuple(base[:limit])


def dependency_filter_reason(source: str, params: list[Param], support_source: str) -> str:
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, source):
            return "dependency_blacklist:" + pattern
    calls = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)
    header = source.split("{", 1)[0]
    function_names = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", header))
    allowed = set(KEYWORDS) | function_names | {param.name for param in params}
    disallowed = sorted({call for call in calls if call not in allowed})
    if disallowed:
        return "external_function_call:" + ",".join(disallowed[:5])
    support_names = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\[", support_source))
    identifiers = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", source.split("{", 1)[1]))
    known = allowed | support_names | set(SCALAR_TYPES) | {"return", "else", "case", "default", "break", "continue", "true", "false"}
    unknown_upper = sorted(name for name in identifiers if name.isupper() and name not in known)
    if unknown_upper:
        return "macro_or_external_identifier:" + ",".join(unknown_upper[:5])
    return ""


def structural_features(source: str, params: list[Param]) -> dict[str, Any]:
    body = source.split("{", 1)[1].rsplit("}", 1)[0]
    arg_names = [param.name for param in params]
    loop_count = len(re.findall(r"\b(for|while|do)\b", body))
    switch_count = len(re.findall(r"\bswitch\b", body))
    case_count = len(re.findall(r"\bcase\b|\bdefault\b", body))
    if_count = len(re.findall(r"\bif\b", body))
    ternary_count = body.count("?")
    bitwise_count = len(re.findall(r"<<|>>|(?<![&])&(?!&)|(?<![|])\|(?![|])|\^|~", body))
    comparison_count = len(re.findall(r"==|!=|<=|>=|(?<!<)<(?!<)|(?<!>)>(?!>)", body))
    char_literal_count = len(re.findall(r"'(?:\\.|[^'\\])+'", body))
    integer_literal_count = len(re.findall(r"(?<![A-Za-z_])(?:0x[0-9A-Fa-f]+|\d+)(?:[uUlL]*)", body))
    lookup_table_access = bool(re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\[[^\]]+\]", body))
    interacting = False
    for statement in re.split(r"[;\n{}]", body):
        if sum(1 for name in arg_names if re.search(rf"\b{re.escape(name)}\b", statement)) >= 2:
            interacting = True
            break
    branch_count = if_count + case_count + ternary_count
    return {
        "argument_count": len(params),
        "argument_types": ";".join(param.type_text for param in params),
        "ast_node_count": ast_node_count(source),
        "cyclomatic_complexity": 1 + if_count + loop_count + case_count + ternary_count + len(re.findall(r"&&|\|\|", body)),
        "branch_count": branch_count,
        "loop_count": loop_count,
        "switch_presence": switch_count > 0,
        "lookup_table_access": lookup_table_access,
        "bitwise_operation_count": bitwise_count,
        "comparison_count": comparison_count,
        "character_literal_count": char_literal_count,
        "integer_literal_count": integer_literal_count,
        "multiple_interacting_arguments": interacting,
        "switch_like_categorical_behavior": switch_count > 0 or case_count >= 3,
    }


def ast_node_count(source: str) -> int:
    try:
        from pycparser import c_parser

        parser = c_parser.CParser()
        prefix = "\n".join(
            [
                "typedef int bool;",
                "typedef signed char int8_t;",
                "typedef unsigned char uint8_t;",
                "typedef short int16_t;",
                "typedef unsigned short uint16_t;",
                "typedef int int32_t;",
                "typedef unsigned int uint32_t;",
                "typedef long long int64_t;",
                "typedef unsigned long long uint64_t;",
                "typedef unsigned long size_t;",
            ]
        )
        tree = parser.parse(prefix + "\n" + source)
        return sum(1 for _ in tree)
    except Exception:
        return len(re.findall(r"[A-Za-z_][A-Za-z0-9_]*|==|!=|<=|>=|<<|>>|[{}();,+\-*/%&|^~<>?=:]", source))


def validate_source_function(function: FunctionRecord, output_dir: Path, command_log: Path) -> dict[str, Any]:
    first = execute_function(function, list(function.domain), output_dir, command_log)
    if not first["ok"]:
        return {"ok": False, "reason": first["reason"]}
    second = execute_function(function, list(function.domain), output_dir, command_log)
    if not second["ok"]:
        return {"ok": False, "reason": "nondeterminism_second_run_failed:" + second["reason"]}
    if first["outputs"] != second["outputs"]:
        return {"ok": False, "reason": "nondeterministic_outputs"}
    return {"ok": True, "reason": "ok"}


def execute_function(function: FunctionRecord, args_list: list[tuple[int, ...]], output_dir: Path, command_log: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    source_path = output_dir / "harness.c"
    exe_path = output_dir / "harness.exe"
    source_path.write_text(render_harness(function, args_list), encoding="utf-8")
    compile_cmd = [
        str(GCC),
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Wno-unused-const-variable",
        "-O0",
        "-fsanitize=undefined,address",
        "-fno-sanitize-recover=all",
        str(source_path),
        "-o",
        str(exe_path),
    ]
    compile_result = run_command(compile_cmd, output_dir, command_log, timeout_s=30)
    if compile_result.returncode != 0:
        return {"ok": False, "reason": "compile_failure", "stderr": compile_result.stderr[-1000:]}
    env = os.environ.copy()
    env["ASAN_OPTIONS"] = "detect_leaks=0"
    env["LSAN_OPTIONS"] = "detect_leaks=0"
    run_result = run_command([str(exe_path)], output_dir, command_log, timeout_s=30, env=env)
    if run_result.returncode != 0:
        return {"ok": False, "reason": f"runtime_failure_{run_result.returncode}", "stderr": run_result.stderr[-1000:]}
    lines = [line.strip() for line in run_result.stdout.splitlines() if line.strip()]
    if len(lines) != len(args_list):
        return {"ok": False, "reason": "harness_output_count_mismatch"}
    try:
        outputs = [int(line) for line in lines]
    except ValueError:
        return {"ok": False, "reason": "non_integer_output"}
    return {"ok": True, "outputs": outputs}


def render_harness(function: FunctionRecord, args_list: list[tuple[int, ...]]) -> str:
    arity = len(function.params)
    rows = ",\n".join("    {" + ", ".join(str(int(value)) for value in args) + "}" for args in args_list)
    call_args = ", ".join(f"({param.type_text})inputs[i][{index}]" for index, param in enumerate(function.params))
    support = function.support_source.strip()
    return "\n".join(
        [
            "#include <stdbool.h>",
            "#include <stddef.h>",
            "#include <stdint.h>",
            "#include <stdio.h>",
            "",
            support,
            "",
            function.source.rstrip(),
            "",
            f"static const long long inputs[{len(args_list)}][{arity}] = {{",
            rows,
            "};",
            "int main(void) {",
            f"    for (size_t i = 0; i < {len(args_list)}; ++i) {{",
            f'        printf("%lld\\n", (long long){function.function_name}({call_args}));',
            "    }",
            "    return 0;",
            "}",
            "",
        ]
    )


def primary_satisfies_full_target(eligible: list[FunctionRecord]) -> bool:
    return len({item.project for item in eligible}) >= MIN_PROJECTS and sampling_capacity(eligible) >= TARGET_FUNCTIONS


def corpus_gate(eligible: list[FunctionRecord]) -> dict[str, Any]:
    projects = {item.project for item in eligible}
    capacity = sampling_capacity(eligible)
    if len(projects) < MIN_PROJECTS:
        status = "stopped_before_fixture_generation_insufficient_project_count"
        target = 0
    elif capacity >= TARGET_FUNCTIONS:
        status = "target_120_available"
        target = TARGET_FUNCTIONS
    elif len(eligible) >= MIN_FEASIBLE_FUNCTIONS and capacity >= MIN_FEASIBLE_FUNCTIONS:
        status = "reduced_feasible"
        target = min(capacity, len(eligible))
    else:
        status = "stopped_before_fixture_generation_insufficient_eligible_functions"
        target = 0
    return {
        "status": status,
        "eligible_function_count": len(eligible),
        "eligible_project_count": len(projects),
        "sampling_capacity_under_project_cap": capacity,
        "target_selected_functions": target,
    }


def sampling_capacity(eligible: list[FunctionRecord]) -> int:
    counts = Counter(item.project for item in eligible)
    return sum(min(PROJECT_CAP, count) for count in counts.values())


def select_functions(eligible: list[FunctionRecord], target: int) -> list[FunctionRecord]:
    by_project: dict[str, list[FunctionRecord]] = {}
    for item in eligible:
        by_project.setdefault(item.project, []).append(item)
    project_order = sorted(by_project, key=lambda name: min(item.project_order for item in by_project[name]))
    rng = random.Random(SAMPLING_SEED)
    for project in project_order:
        by_project[project].sort(key=lambda item: (stable_random_key(item.function_id, SAMPLING_SEED), item.function_id))
    selected: list[FunctionRecord] = []
    selected_ids: set[str] = set()
    project_counts = Counter()
    represented = choose_represented_projects(by_project, project_order, target)
    min_each = 5 if target >= MIN_PROJECTS * 5 else 1
    for project in represented:
        for _ in range(min(min_each, len(by_project[project]), PROJECT_CAP)):
            pick = best_candidate(by_project[project], selected_ids, selected, project_counts, target)
            if pick is None:
                break
            selected.append(pick)
            selected_ids.add(pick.function_id)
            project_counts[pick.project] += 1
    while len(selected) < target:
        choices = []
        for project in represented:
            if project_counts[project] >= PROJECT_CAP:
                continue
            pick = best_candidate(by_project[project], selected_ids, selected, project_counts, target)
            if pick is not None:
                choices.append(pick)
        if not choices:
            break
        choices.sort(key=lambda item: (-selection_gain(item, selected, target), stable_random_key(item.function_id, SAMPLING_SEED), item.function_id))
        pick = choices[0]
        selected.append(pick)
        selected_ids.add(pick.function_id)
        project_counts[pick.project] += 1
    rng.shuffle(selected)
    selected.sort(key=lambda item: (min_project_order(item.project, by_project), project_counts[item.project], stable_random_key(item.function_id, SAMPLING_SEED), item.function_id))
    return selected[:target]


def choose_represented_projects(by_project: dict[str, list[FunctionRecord]], project_order: list[str], target: int) -> list[str]:
    max_projects_by_min = max(MIN_PROJECTS, target // 5)
    represented = []
    capacity = 0
    for project in project_order:
        if len(represented) >= max_projects_by_min and capacity >= target:
            break
        represented.append(project)
        capacity += min(PROJECT_CAP, len(by_project[project]))
        if len(represented) >= MIN_PROJECTS and capacity >= target and len(represented) * 5 >= target:
            break
    return represented


def best_candidate(
    candidates: list[FunctionRecord],
    selected_ids: set[str],
    selected: list[FunctionRecord],
    project_counts: Counter[str],
    target: int,
) -> FunctionRecord | None:
    available = [item for item in candidates if item.function_id not in selected_ids and project_counts[item.project] < PROJECT_CAP]
    if not available:
        return None
    available.sort(key=lambda item: (-selection_gain(item, selected, target), stable_random_key(item.function_id, SAMPLING_SEED), item.function_id))
    return available[0]


def selection_gain(item: FunctionRecord, selected: list[FunctionRecord], target: int) -> int:
    counts = selection_feature_counts(selected)
    quotas = selection_quotas(target)
    gain = 0
    arg_key = f"arity_{len(item.params)}"
    if counts[arg_key] < quotas.get(arg_key, 0):
        gain += 100
    feature_map = {
        "loop_count": "loop",
        "lookup_table_access": "lookup",
        "bitwise_operation_count": "bitwise",
        "branch_count": "branches4",
        "multiple_interacting_arguments": "interacting_args",
        "switch_like_categorical_behavior": "switch_like",
    }
    for feature, quota_name in feature_map.items():
        value = item.features[feature]
        present = value >= 4 if feature == "branch_count" else bool(value)
        if present and counts[quota_name] < quotas.get(quota_name, 0):
            gain += 20
    return gain


def selection_feature_counts(selected: list[FunctionRecord]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in selected:
        counts[f"arity_{len(item.params)}"] += 1
        if item.features["loop_count"]:
            counts["loop"] += 1
        if item.features["lookup_table_access"]:
            counts["lookup"] += 1
        if item.features["bitwise_operation_count"]:
            counts["bitwise"] += 1
        if item.features["branch_count"] >= 4:
            counts["branches4"] += 1
        if item.features["multiple_interacting_arguments"]:
            counts["interacting_args"] += 1
        if item.features["switch_like_categorical_behavior"]:
            counts["switch_like"] += 1
    return counts


def selection_quotas(target: int) -> dict[str, int]:
    scale = target / TARGET_FUNCTIONS
    return {
        "arity_1": min(30, round(30 * scale)),
        "arity_2": min(50, round(50 * scale)),
        "arity_3": min(20, round(20 * scale)),
        "loop": min(25, round(25 * scale)),
        "lookup": min(25, round(25 * scale)),
        "bitwise": min(30, round(30 * scale)),
        "branches4": min(30, round(30 * scale)),
        "interacting_args": min(30, round(30 * scale)),
        "switch_like": min(20, round(20 * scale)),
    }


def generate_fixtures(selected: list[FunctionRecord], work: Path, command_log: Path) -> list[dict[str, Any]]:
    rows = []
    for function in selected:
        rng = random.Random(seed_from(FIXTURE_SEED, function.function_id, signature(function), domain_digest(function)))
        domain = list(function.domain)
        indices = sorted(rng.sample(range(len(domain)), FIXTURES_PER_FUNCTION))
        fixture_args = [domain[index] for index in indices]
        outputs = execute_function(function, fixture_args, work / "fixture_outputs" / safe_name(function.function_id), command_log)
        if not outputs["ok"]:
            raise RuntimeError(f"trusted source fixture output failed for {function.function_id}: {outputs['reason']}")
        for rank, (index, args) in enumerate(zip(indices, fixture_args), start=1):
            rows.append(
                {
                    "function_id": function.function_id,
                    "project": function.project,
                    "function_name": function.function_name,
                    "rank": rank,
                    "domain_index": index,
                    "args": list(args),
                    "source_output": outputs["outputs"][rank - 1],
                    "fixture_seed": FIXTURE_SEED,
                    "source_agnostic_inputs": True,
                    "generation_inputs": ["function_id", "signature", "declared_audit_domain", "fixture_seed"],
                }
            )
    return rows


def build_function_fixture_seal(
    repo_root: Path,
    selected: list[FunctionRecord],
    fixtures: list[dict[str, Any]],
    gate: dict[str, Any],
    fallback_used: bool,
) -> dict[str, Any]:
    paths = [
        "docs/paper_agent/phase3a_natural_error_census_preregistration.md",
        "docs/paper_agent/phase3a_producer_setup_log.md",
        "results/decompile_faithfulness/phase3a_producer_availability.json",
        "results/decompile_faithfulness/phase3a_project_manifest.json",
        "results/decompile_faithfulness/phase3a_eligibility_census.csv",
        "results/decompile_faithfulness/phase3a_exclusions.jsonl",
        "results/decompile_faithfulness/phase3a_selected_functions.csv",
        "results/decompile_faithfulness/phase3a_fixtures.jsonl",
        "results/decompile_faithfulness/phase3a_corpus_execution_log.jsonl",
        "analysis/decompile_faithfulness/phase3a_corpus.py",
    ]
    amendment = "docs/paper_agent/phase3a_function_corpus_feasibility_amendment.md"
    if (repo_root / amendment).exists():
        paths.append(amendment)
    return {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "branch": git_at(repo_root, ["branch", "--show-current"]),
        "head": git_at(repo_root, ["rev-parse", "HEAD"]),
        "base_head": PHASE3A_BASE_HEAD,
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "producer_setup_commit": PRODUCER_SETUP_COMMIT,
        "sampling_seed": SAMPLING_SEED,
        "fixture_seed": FIXTURE_SEED,
        "fallback_used": fallback_used,
        "gate": gate,
        "selected_function_count": len(selected),
        "fixture_count": len(fixtures),
        "selected_function_ids": [item.function_id for item in selected],
        "fixture_records_sha256": sha256_text(canonical_json(fixtures)),
        "declared_domains_sha256": sha256_text(canonical_json({item.function_id: domain_spec(item) for item in selected})),
        "source_file_hashes": source_hashes_from_manifest(repo_root / "results/decompile_faithfulness/phase3a_project_manifest.json"),
        "artifact_hashes": artifact_hashes(repo_root, paths),
        "auditor_execution": "not_run",
        "candidate_generation": "not_run",
        "semantic_labeling": "not_run",
    }


def build_project_manifest(records: list[dict[str, Any]], acquisition_errors: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "branch": PHASE3A_BRANCH,
        "preregistration_commit": PREREGISTRATION_COMMIT,
        "producer_setup_commit": PRODUCER_SETUP_COMMIT,
        "forbidden_prior_projects": sorted(FORBIDDEN_PRIOR_PROJECTS),
        "projects": records,
        "acquisition_errors": acquisition_errors,
    }


def write_feasibility_amendment(path: Path, gate: dict[str, Any], eligible: list[FunctionRecord]) -> None:
    if path.exists():
        return
    counts = Counter(item.project for item in eligible)
    max_project = max(counts.values()) if counts else 0
    path.write_text(
        "\n".join(
            [
                "# Phase 3a Function Corpus Feasibility Amendment",
                "",
                f"Created: {now_utc()}",
                "",
                "This amendment is created before candidate generation, before semantic labels, and before any auditor execution.",
                "",
                f"The original 120-function target is infeasible under the preregistered project cap. The cap-constrained sampling capacity is {gate['sampling_capacity_under_project_cap']} across {gate['eligible_project_count']} eligible projects.",
                "",
                f"The reduced corpus size is {gate['target_selected_functions']} selected functions.",
                "",
                "Project diversity remains preserved by retaining at least 12 represented projects where available, preserving the maximum 10 functions per project, and preventing any single project from dominating the corpus.",
                "",
                f"The largest eligible project contributes {max_project} eligible functions before cap enforcement; selected functions remain capped at {PROJECT_CAP} per project.",
                "",
                "Structural-feature reporting and complete exact-domain labeling remain unchanged.",
                "",
                "No candidate-generation result, semantic label, mismatch witness, or auditor behavior was inspected when applying this amendment.",
                "",
            ]
        ),
        encoding="utf-8",
    )


def update_handoff(
    repo_root: Path,
    project_records: list[dict[str, Any]],
    eligible: list[FunctionRecord],
    selected: list[FunctionRecord],
    fixtures: list[dict[str, Any]],
    gate: dict[str, Any],
    fallback_used: bool,
    amendment_needed: bool,
    seal_hash: str,
) -> None:
    handoff = repo_root / "docs/paper_agent/phase3a_natural_error_census_handoff.md"
    text = handoff.read_text(encoding="utf-8") if handoff.exists() else ""
    marker = "## Function Corpus And Fixture Seal Milestone"
    text = text.split(marker)[0].rstrip()
    selected_by_project = Counter(item.project for item in selected)
    selected_by_arity = Counter(str(len(item.params)) for item in selected)
    feature_counts = selection_feature_counts(selected)
    domain_sizes = Counter(str(item.domain_size) for item in selected)
    exclusions = Counter(
        summarize_exclusion_reason(row["exclusion_reason"])
        for row in read_csv_rows(repo_root / "results/decompile_faithfulness/phase3a_eligibility_census.csv")
        if row.get("eligibility_status") != "eligible"
    )
    section = f"""

{marker}

Updated: {now_utc()}

- Branch: `{git_at(repo_root, ["branch", "--show-current"])}`
- Current HEAD: `{git_at(repo_root, ["rev-parse", "HEAD"])}`
- Producer setup commit: `{PRODUCER_SETUP_COMMIT}`
- Projects scanned: `{len(project_records)}`
- Projects represented: `{len({item.project for item in selected})}`
- Primary projects used: `{sum(1 for record in project_records if record["pool"] == "primary" and record["acquired"])}`
- Fallback projects used: `{sum(1 for record in project_records if record["pool"] == "fallback" and record["acquired"])}`
- Fallback needed: `{fallback_used}`
- Eligible function count: `{len(eligible)}`
- Selected function count: `{len(selected)}`
- Selected functions by project: `{json.dumps(dict(sorted(selected_by_project.items())), sort_keys=True)}`
- Selected functions by argument count: `{json.dumps(dict(sorted(selected_by_arity.items())), sort_keys=True)}`
- Structural-feature coverage: `{json.dumps(dict(sorted(feature_counts.items())), sort_keys=True)}`
- Exact-domain size distribution: `{json.dumps(dict(sorted(domain_sizes.items())), sort_keys=True)}`
- Exclusion counts and reasons: `{json.dumps(dict(exclusions.most_common()), sort_keys=True)}`
- Feasibility amendment needed: `{amendment_needed}`
- Fixture count: `{len(fixtures)}`
- Function/fixture seal hash: `{seal_hash}`
- Tests run: pending final milestone test run.

Gate status: `{gate['status']}`.

No candidate generation occurred in this milestone.

No semantic labeling occurred in this milestone.

No auditor was run in this milestone.
"""
    handoff.write_text(text + section + "\n", encoding="utf-8")


def census_row(
    record: dict[str, Any],
    rel: str,
    parsed: dict[str, str],
    status: str,
    reason: str,
    return_type: str = "",
    params: list[Param] | None = None,
    domain_values: tuple[tuple[int, ...], ...] | None = None,
    features: dict[str, Any] | None = None,
    function_id: str = "",
) -> dict[str, Any]:
    params = params or []
    features = features or {}
    domain_values = domain_values or tuple()
    size = 1
    for values in domain_values:
        size *= len(values)
    return {
        "project": record["project"],
        "pool": record["pool"],
        "project_order": record["order"],
        "pinned_commit": record.get("pinned_commit", ""),
        "source_file": rel,
        "source_file_sha256": next((item["sha256"] for item in record.get("source_file_hashes", []) if item["path"] == rel), ""),
        "function_id": function_id,
        "function_name": parsed.get("name", ""),
        "ordinal": parsed.get("ordinal", ""),
        "eligibility_status": status,
        "exclusion_reason": reason,
        "return_type": return_type,
        "argument_count": len(params),
        "argument_types": ";".join(param.type_text for param in params),
        "signature": signature_from_parts(return_type, parsed.get("name", ""), params) if params else "",
        "declared_audit_domain": json.dumps(domain_spec_from_values(params, domain_values), sort_keys=True),
        "domain_size": size if domain_values else 0,
        "source_sha256": sha256_text(parsed.get("source", "")) if parsed.get("source") else "",
        "ast_node_count": features.get("ast_node_count", 0),
        "cyclomatic_complexity": features.get("cyclomatic_complexity", 0),
        "branch_count": features.get("branch_count", 0),
        "loop_count": features.get("loop_count", 0),
        "switch_presence": int(bool(features.get("switch_presence", False))),
        "lookup_table_access": int(bool(features.get("lookup_table_access", False))),
        "bitwise_operation_count": features.get("bitwise_operation_count", 0),
        "comparison_count": features.get("comparison_count", 0),
        "character_literal_count": features.get("character_literal_count", 0),
        "integer_literal_count": features.get("integer_literal_count", 0),
        "multiple_interacting_arguments": int(bool(features.get("multiple_interacting_arguments", False))),
        "switch_like_categorical_behavior": int(bool(features.get("switch_like_categorical_behavior", False))),
    }


def project_exclusion_row(record: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "project": record["project"],
        "pool": record["pool"],
        "project_order": record["order"],
        "pinned_commit": "",
        "source_file": "",
        "source_file_sha256": "",
        "function_id": "",
        "function_name": "",
        "ordinal": "",
        "eligibility_status": "not_eligible",
        "exclusion_reason": reason,
        "return_type": "",
        "argument_count": 0,
        "argument_types": "",
        "signature": "",
        "declared_audit_domain": "",
        "domain_size": 0,
        "source_sha256": "",
        "ast_node_count": 0,
        "cyclomatic_complexity": 0,
        "branch_count": 0,
        "loop_count": 0,
        "switch_presence": 0,
        "lookup_table_access": 0,
        "bitwise_operation_count": 0,
        "comparison_count": 0,
        "character_literal_count": 0,
        "integer_literal_count": 0,
        "multiple_interacting_arguments": 0,
        "switch_like_categorical_behavior": 0,
    }


def summarize_exclusion_reason(reason: str) -> str:
    if reason.startswith("project_acquisition_failed:"):
        if "Couldn't connect to server" in reason:
            return "project_acquisition_failed:couldnt_connect_to_server"
        return "project_acquisition_failed"
    if reason.startswith("dependency_blacklist:"):
        return "dependency_blacklist"
    if reason.startswith("external_function_call:"):
        return "external_function_call"
    if reason.startswith("macro_or_external_identifier:"):
        return "macro_or_external_identifier"
    return reason


def selected_row(function: FunctionRecord, selection_rank: int) -> dict[str, Any]:
    row = census_row(
        {
            "project": function.project,
            "pool": function.pool,
            "order": function.project_order,
            "pinned_commit": "",
            "source_file_hashes": [{"path": function.source_file, "sha256": function.source_file_sha256}],
        },
        function.source_file,
        {"name": function.function_name, "source": function.source, "ordinal": function.ordinal},
        "selected",
        "selected",
        function.return_type,
        list(function.params),
        function.domain_values,
        function.features,
        function.function_id,
    )
    row["selection_rank"] = selection_rank
    row["sampling_seed"] = SAMPLING_SEED
    return row


def eligibility_fieldnames() -> list[str]:
    return [
        "project",
        "pool",
        "project_order",
        "pinned_commit",
        "source_file",
        "source_file_sha256",
        "function_id",
        "function_name",
        "ordinal",
        "eligibility_status",
        "exclusion_reason",
        "return_type",
        "argument_count",
        "argument_types",
        "signature",
        "declared_audit_domain",
        "domain_size",
        "source_sha256",
        "ast_node_count",
        "cyclomatic_complexity",
        "branch_count",
        "loop_count",
        "switch_presence",
        "lookup_table_access",
        "bitwise_operation_count",
        "comparison_count",
        "character_literal_count",
        "integer_literal_count",
        "multiple_interacting_arguments",
        "switch_like_categorical_behavior",
    ]


def selected_fieldnames() -> list[str]:
    return ["selection_rank", "sampling_seed", *eligibility_fieldnames()]


def exact_domain_complete(function: FunctionRecord) -> bool:
    return function.domain_size == len(function.domain) and function.domain_size <= MAX_DOMAIN_SIZE


def guard_against_auditor_imports() -> dict[str, bool]:
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    imports_ok = True
    calls_ok = True
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in FORBIDDEN_AUDITOR_IMPORTS:
            imports_ok = False
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in FORBIDDEN_AUDITOR_IMPORTS:
                    imports_ok = False
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_AUDITOR_CALLS:
                calls_ok = False
            if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_AUDITOR_CALLS:
                calls_ok = False
    return {"imports_ok": imports_ok, "calls_ok": calls_ok}


def iter_source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".c", ".h"}:
            continue
        rel = path.relative_to(root)
        parts = {part.lower() for part in rel.parts[:-1]}
        if parts & SKIP_DIR_PARTS:
            continue
        rel_text = rel.as_posix().lower()
        if any(token in rel_text for token in FORBIDDEN_SOURCE_PATH_TOKENS):
            continue
        yield path


def extract_enum_values(text: str) -> dict[str, tuple[int, ...]]:
    clean = strip_comments(text)
    enums: dict[str, tuple[int, ...]] = {}
    for match in re.finditer(r"typedef\s+enum(?:\s+[A-Za-z_][A-Za-z0-9_]*)?\s*\{(?P<body>.*?)\}\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*;", clean, re.S):
        enums[match.group("name")] = parse_enum_body(match.group("body"))
    for match in re.finditer(r"enum\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\{(?P<body>.*?)\}\s*;", clean, re.S):
        enums[match.group("name")] = parse_enum_body(match.group("body"))
    return enums


def parse_enum_body(body: str) -> tuple[int, ...]:
    values = []
    current = 0
    for raw in body.split(","):
        item = raw.strip()
        if not item:
            continue
        if "=" in item:
            _name, value = item.split("=", 1)
            try:
                current = int(value.strip(), 0)
            except ValueError:
                continue
        values.append(current)
        current += 1
    return tuple(values)


def extract_support_source(text: str) -> str:
    clean = strip_comments(text)
    decls = []
    for pattern in [
        r"typedef\s+enum(?:\s+[A-Za-z_][A-Za-z0-9_]*)?\s*\{.*?\}\s*[A-Za-z_][A-Za-z0-9_]*\s*;",
        r"enum\s+[A-Za-z_][A-Za-z0-9_]*\s*\{.*?\}\s*;",
        r"static\s+const\s+(?:unsigned\s+|signed\s+)?(?:char|short|int|long|uint8_t|int8_t|uint16_t|int16_t|uint32_t|int32_t|uint64_t|int64_t)\s+[A-Za-z_][A-Za-z0-9_]*\s*\[[^\]]*\]\s*=\s*\{.*?\}\s*;",
    ]:
        decls.extend(match.group(0) for match in re.finditer(pattern, clean, re.S))
    return "\n".join(dict.fromkeys(decls))


def strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.S)
    text = re.sub(r"//.*", " ", text)
    return text


def matching_brace(text: str, brace_index: int) -> int | None:
    if brace_index < 0:
        return None
    depth = 0
    in_string = False
    in_char = False
    escape = False
    for index in range(brace_index, len(text)):
        char = text[index]
        if escape:
            escape = False
            continue
        if char == "\\" and (in_string or in_char):
            escape = True
            continue
        if char == '"' and not in_char:
            in_string = not in_string
            continue
        if char == "'" and not in_string:
            in_char = not in_char
            continue
        if in_string or in_char:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
    return None


def domain_spec(function: FunctionRecord) -> list[dict[str, Any]]:
    return domain_spec_from_values(list(function.params), function.domain_values)


def domain_spec_from_values(params: list[Param], values: tuple[tuple[int, ...], ...]) -> list[dict[str, Any]]:
    return [
        {
            "name": param.name,
            "type": param.type_text,
            "count": len(domain),
            "values": list(domain),
            "min": min(domain) if domain else None,
            "max": max(domain) if domain else None,
        }
        for param, domain in zip(params, values)
    ]


def signature(function: FunctionRecord) -> str:
    return signature_from_parts(function.return_type, function.function_name, list(function.params))


def signature_from_parts(return_type: str, function_name: str, params: list[Param]) -> str:
    return f"{return_type} {function_name}({', '.join(f'{param.type_text} {param.name}' for param in params)})"


def stable_function_id(project: str, rel: str, name: str, ordinal: int, source: str) -> str:
    digest = sha256_text("|".join([project, rel, name, str(ordinal), source]))[:12]
    return f"{safe_name(project)}::{safe_name(rel)}::{safe_name(name)}::{ordinal:04d}::{digest}"


def stable_random_key(value: str, seed: int) -> str:
    return hashlib.sha256(f"{seed}|{value}".encode("utf-8")).hexdigest()


def seed_from(seed: int, *parts: str) -> int:
    return int(hashlib.sha256("|".join([str(seed), *parts]).encode("utf-8")).hexdigest()[:16], 16)


def domain_digest(function: FunctionRecord) -> str:
    return sha256_text(canonical_json(domain_spec(function)))


def min_project_order(project: str, by_project: dict[str, list[FunctionRecord]]) -> int:
    return min(item.project_order for item in by_project[project])


def source_hashes_from_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = []
    for project in payload.get("projects", []):
        for item in project.get("source_file_hashes", []):
            rows.append({"project": project["project"], "path": item["path"], "sha256": item["sha256"]})
    return rows


def artifact_hashes(repo_root: Path, paths: list[str]) -> dict[str, str]:
    hashes = {}
    for rel in paths:
        path = repo_root / rel
        if path.exists() and path.is_file():
            hashes[rel] = sha256_path(path)
    return hashes


def run_command(argv: list[str], cwd: Path, command_log: Path, timeout_s: int, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    record = {"created_at_utc": now_utc(), "argv": argv, "cwd": str(cwd), "timeout_s": timeout_s}
    try:
        result = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_s, check=False, env=env)
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(argv, 124, exc.stdout or "", exc.stderr or "timeout")
    record.update({"returncode": result.returncode, "stdout_tail": (result.stdout or "")[-500:], "stderr_tail": (result.stderr or "")[-500:]})
    append_jsonl(command_log, [record])
    return result


def git_at(path: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=path, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def safe_name(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", text)[:180]


def normalize_ws(text: str) -> str:
    return " ".join(text.replace("\t", " ").split())


def read_text_lossy(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    main()
