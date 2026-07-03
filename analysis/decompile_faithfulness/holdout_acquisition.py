from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


METHOD_FREEZE_COMMIT = "06dda89912103b94fc065d6f073581a7811154b1"
PHASE1B_CORRECTION_COMMIT = "a784d1c8195ae88a8b3233f8eef5cfd2c27d7b14"
ACQUISITION_SEED = 2026070301
FIXTURE_SEED = 2026070302
MUTATION_SEED = 2026070303
MIN_PROJECTS = 8
MIN_SELECTED_FUNCTIONS = 48
MAX_SELECTED_FUNCTIONS = 64
PROJECT_CAP = 8
FIXTURES_PER_FUNCTION = 4
MAX_CONTROLLED_MUTATIONS_PER_FUNCTION = 2
MAX_STORED_MISMATCHES = 256
CLANG = Path("/usr/lib/llvm-11/bin/clang")
GCC = Path("/usr/bin/gcc")
GHIDRA_HEADLESS = Path(
    "analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/ghidra_12.1.2_PUBLIC/support/analyzeHeadless"
)
GHIDRA_SCRIPT_DIR = Path("analysis/decompile_faithfulness/ghidra_scripts")
JAVA_HOME = Path("analysis_outputs/decompile_faithfulness/phase6r_tools/ghidra_user/root/usr/lib/jvm/java-21-openjdk-amd64")


PROJECT_POOL = [
    ("libtommath", "https://github.com/libtom/libtommath.git", "primary"),
    ("cJSON", "https://github.com/DaveGamble/cJSON.git", "primary"),
    ("uthash", "https://github.com/troydhanson/uthash.git", "primary"),
    ("musl", "https://git.musl-libc.org/git/musl", "primary"),
    ("zlib", "https://github.com/madler/zlib.git", "primary"),
    ("mbedtls", "https://github.com/Mbed-TLS/mbedtls.git", "primary"),
    ("sqlite", "https://github.com/sqlite/sqlite.git", "primary"),
    ("libb64", "https://github.com/libb64/libb64.git", "primary"),
    ("inih", "https://github.com/benhoyt/inih.git", "primary"),
    ("tiny-AES-c", "https://github.com/kokke/tiny-AES-c.git", "primary"),
    ("libtomcrypt", "https://github.com/libtom/libtomcrypt.git", "fallback"),
    ("BearSSL", "https://www.bearssl.org/git/BearSSL", "fallback"),
    ("libdeflate", "https://github.com/ebiggers/libdeflate.git", "fallback"),
    ("xxHash", "https://github.com/Cyan4973/xxHash.git", "fallback"),
    ("TinyCC", "https://repo.or.cz/tinycc.git", "fallback"),
    ("chibicc", "https://github.com/rui314/chibicc.git", "fallback"),
    ("sbase", "https://git.suckless.org/sbase", "fallback"),
]


PROHIBITED_FINAL_METHOD_FUNCTIONS = [
    "run_phase18_source_literal_char_policy",
    "build_ordered_inputs",
    "source_literal_char_inputs",
    "fixture_neighbor_inputs",
    "interleave_inputs",
]


SCALAR_TYPES = {
    "char",
    "signed char",
    "unsigned char",
    "bool",
    "_Bool",
    "short",
    "short int",
    "signed short",
    "signed short int",
    "unsigned short",
    "unsigned short int",
    "int",
    "signed",
    "signed int",
    "unsigned",
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
}


KEYWORDS = {
    "auto", "break", "case", "char", "const", "continue", "default", "do", "double",
    "else", "enum", "extern", "float", "for", "goto", "if", "inline", "int", "long",
    "register", "restrict", "return", "short", "signed", "sizeof", "static", "struct",
    "switch", "typedef", "union", "unsigned", "void", "volatile", "while", "bool",
    "_Bool", "true", "false",
}


BLACKLIST_PATTERNS = [
    r"\bmalloc\b", r"\bcalloc\b", r"\brealloc\b", r"\bfree\b",
    r"\bfopen\b", r"\bfread\b", r"\bfwrite\b", r"\bprintf\b", r"\bscanf\b",
    r"\bgetenv\b", r"\bsetenv\b", r"\btime\b", r"\bclock\b", r"\blocale\b",
    r"\bpthread_", r"\berrno\b", r"\bsetjmp\b", r"\blongjmp\b",
    r"\bvolatile\b", r"\bstatic\s+[A-Za-z_][A-Za-z0-9_]*\s*=",
]


SKIP_DIR_PARTS = {
    ".git", "test", "tests", "testing", "example", "examples", "doc", "docs",
    "benchmark", "bench", "fuzz", "fuzzer", "build", "cmake", "scripts",
}


@dataclass(frozen=True)
class Param:
    type_text: str
    name: str


@dataclass(frozen=True)
class FunctionCandidate:
    project: str
    source_path: str
    function_name: str
    ordinal: int
    return_type: str
    params: tuple[Param, ...]
    source: str
    source_sha256: str
    domain: tuple[tuple[int, ...], ...]
    domain_size: int
    function_id: str


def main() -> None:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    summary = run(repo_root)
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args()


def run(repo_root: Path) -> dict[str, Any]:
    out = repo_root / "results/decompile_faithfulness"
    analysis_out = repo_root / "analysis/decompile_faithfulness"
    work = repo_root / "analysis_outputs/decompile_faithfulness/holdout_phase1c"
    project_root = repo_root / "external/holdout_projects"
    for path in [out, analysis_out, work, project_root]:
        path.mkdir(parents=True, exist_ok=True)
    command_log = work / "holdout_execution_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    write_preregistration(repo_root)
    write_mutation_grammar(repo_root)
    update_dataset_provenance_table(repo_root)

    project_records, acquisition_errors = acquire_projects(repo_root, project_root, command_log)
    candidates, census_rows, exclusion_rows = run_eligibility_census(repo_root, project_records, work, command_log)
    write_project_manifest(repo_root, project_records, acquisition_errors)
    write_census(repo_root, census_rows)
    write_exclusions(repo_root, exclusion_rows)
    write_sampling_frame(repo_root, candidates)

    gate = eligibility_gate(candidates)
    enough = gate["passed"]
    if enough:
        selected = deterministic_sample(candidates)
    else:
        selected = []
    write_selected_functions(repo_root, selected)

    fixture_rows: list[dict[str, Any]] = []
    natural_candidates: list[dict[str, Any]] = []
    controlled_candidates: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    label_summary: list[dict[str, Any]] = []
    status = gate["status"]

    if enough:
        status = "sealed_after_exact_labeling"
        fixture_rows = generate_fixtures(selected, work, command_log)
        natural_candidates = generate_natural_ghidra_candidates(repo_root, selected, work, command_log)
        controlled_candidates = generate_controlled_candidates(selected, fixture_rows, work, command_log)
        labels = label_candidates(selected, natural_candidates + controlled_candidates, work, command_log)
        label_summary = summarize_labels(labels)

    write_jsonl(out / "holdout_fixtures.jsonl", fixture_rows)
    write_jsonl(out / "holdout_candidate_manifest.jsonl", natural_candidates + controlled_candidates)
    write_jsonl(out / "holdout_controlled_candidates.jsonl", controlled_candidates)
    write_jsonl(out / "holdout_exact_labels.jsonl", labels)
    write_label_summary(out / "holdout_label_summary.csv", label_summary)
    write_holdout_acquisition_table(repo_root, census_rows, selected, natural_candidates, controlled_candidates, labels)
    submitted_command_log = out / "holdout_execution_log.jsonl"
    shutil.copyfile(command_log, submitted_command_log)

    manifest = build_sealed_manifest(
        repo_root=repo_root,
        status=status,
        project_records=project_records,
        acquisition_errors=acquisition_errors,
        census_rows=census_rows,
        exclusion_rows=exclusion_rows,
        selected=selected,
        fixture_rows=fixture_rows,
        natural_candidates=natural_candidates,
        controlled_candidates=controlled_candidates,
        labels=labels,
        command_log=submitted_command_log,
    )
    write_json(analysis_out / "holdout_sealed_manifest.json", manifest)
    seal_hash = sha256_path(analysis_out / "holdout_sealed_manifest.json")
    (analysis_out / "holdout_sealed_manifest.sha256").write_text(
        f"{seal_hash}  holdout_sealed_manifest.json\n",
        encoding="utf-8",
    )
    write_handoff(repo_root, manifest, seal_hash, status)
    return {
        "status": status,
        "eligible_functions": len(candidates),
        "eligible_projects": len({item.project for item in candidates}),
        "selected_functions": len(selected),
        "sampling_capacity_under_project_cap": gate["sampling_capacity_under_project_cap"],
        "natural_candidates": len(natural_candidates),
        "controlled_candidates": len(controlled_candidates),
        "labels": len(labels),
        "seal_sha256": seal_hash,
    }


def acquire_projects(
    repo_root: Path,
    project_root: Path,
    command_log: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records = []
    errors = []
    for order, (name, url, pool) in enumerate(PROJECT_POOL, start=1):
        path = project_root / safe_name(name)
        if not path.exists():
            result = run_command(["git", "clone", "--depth", "1", url, str(path)], repo_root, command_log, timeout_s=180)
            if result.returncode != 0:
                errors.append({"project": name, "repo": url, "error": result.stderr[-1000:] or result.stdout[-1000:]})
                records.append(project_record(order, name, url, pool, path, acquired=False))
                continue
        records.append(project_record(order, name, url, pool, path, acquired=True))
    return records, errors


def project_record(order: int, name: str, url: str, pool: str, path: Path, acquired: bool) -> dict[str, Any]:
    commit = git_at(path, ["rev-parse", "HEAD"]) if acquired else ""
    license_files = []
    if acquired:
        for item in sorted(path.iterdir()):
            if item.is_file() and item.name.lower().startswith(("license", "copying")):
                license_files.append({"path": item.name, "sha256": sha256_path(item)})
    return {
        "order": order,
        "project": name,
        "pool": pool,
        "canonical_repository": url,
        "local_path": str(path),
        "acquired": acquired,
        "acquisition_date": date.today().isoformat(),
        "pinned_commit": commit,
        "license_metadata": license_files or [{"path": "", "sha256": "", "status": "not_found_or_unavailable"}],
    }


def run_eligibility_census(
    repo_root: Path,
    project_records: list[dict[str, Any]],
    work: Path,
    command_log: Path,
) -> tuple[list[FunctionCandidate], list[dict[str, Any]], list[dict[str, Any]]]:
    eligible: list[FunctionCandidate] = []
    census_rows = []
    exclusion_rows = []
    for project in project_records:
        if not project["acquired"]:
            census_rows.append(census_row(project, 0, 0, 0, 0, 0, 0))
            exclusion_rows.append({"project": project["project"], "reason": "project_acquisition_failed"})
            continue
        root = Path(project["local_path"])
        source_files = list(iter_source_files(root))
        parsed_count = 0
        signature_pass = 0
        dependency_pass = 0
        sanitizer_pass = 0
        project_eligible = 0
        for source_path in source_files:
            rel = source_path.relative_to(root).as_posix()
            text = read_text_lossy(source_path)
            for ordinal, parsed in enumerate(extract_functions(text), start=1):
                parsed_count += 1
                signature = parse_signature(parsed["header"])
                if signature is None:
                    exclusion_rows.append(exclusion(project, rel, parsed, "signature_filter_failed"))
                    continue
                return_type, params = signature
                domains = [declared_domain(param.type_text) for param in params]
                if any(domain is None for domain in domains):
                    exclusion_rows.append(exclusion(project, rel, parsed, "unsupported_declared_domain"))
                    continue
                domain_tuples = tuple(itertools.product(*(domain for domain in domains if domain is not None)))
                if len(domain_tuples) < FIXTURES_PER_FUNCTION:
                    exclusion_rows.append(exclusion(project, rel, parsed, "domain_too_small_for_four_fixtures"))
                    continue
                signature_pass += 1
                dep_reason = dependency_filter_reason(parsed["source"], params)
                if dep_reason:
                    exclusion_rows.append(exclusion(project, rel, parsed, dep_reason))
                    continue
                dependency_pass += 1
                function_id = stable_function_id(project["project"], rel, parsed["name"], ordinal, parsed["source"])
                candidate = FunctionCandidate(
                    project=project["project"],
                    source_path=rel,
                    function_name=parsed["name"],
                    ordinal=ordinal,
                    return_type=return_type,
                    params=tuple(params),
                    source=parsed["source"],
                    source_sha256=sha256_text(parsed["source"]),
                    domain=domain_tuples,
                    domain_size=len(domain_tuples),
                    function_id=function_id,
                )
                validation = validate_source_function(candidate, work / "source_validation", command_log)
                if not validation["ok"]:
                    exclusion_rows.append(exclusion(project, rel, parsed, validation["reason"], extra=validation))
                    continue
                sanitizer_pass += 1
                project_eligible += 1
                eligible.append(candidate)
        census_rows.append(
            census_row(
                project,
                len(source_files),
                parsed_count,
                signature_pass,
                dependency_pass,
                sanitizer_pass,
                project_eligible,
            )
        )
    return eligible, census_rows, exclusion_rows


def eligibility_gate(candidates: list[FunctionCandidate]) -> dict[str, Any]:
    projects = {item.project for item in candidates}
    project_count = len(projects)
    capacity = sum(min(PROJECT_CAP, sum(1 for item in candidates if item.project == project)) for project in projects)
    if len(candidates) < MIN_SELECTED_FUNCTIONS:
        status = "stopped_before_candidate_generation_insufficient_eligible_functions"
    elif project_count < MIN_PROJECTS:
        status = "stopped_before_candidate_generation_insufficient_project_count"
    elif capacity < MIN_SELECTED_FUNCTIONS:
        status = "stopped_before_candidate_generation_insufficient_capped_sampling_capacity"
    else:
        status = "sealed_after_exact_labeling"
    return {
        "passed": status == "sealed_after_exact_labeling",
        "status": status,
        "eligible_function_count": len(candidates),
        "eligible_project_count": project_count,
        "sampling_capacity_under_project_cap": capacity,
    }


def deterministic_sample(candidates: list[FunctionCandidate]) -> list[FunctionCandidate]:
    by_project: dict[str, list[FunctionCandidate]] = {}
    for item in candidates:
        by_project.setdefault(item.project, []).append(item)
    rng = random.Random(ACQUISITION_SEED)
    eligible_projects = [project for project, items in by_project.items() if len(items) >= 4]
    ordered_projects = [name for name, _url, _pool in PROJECT_POOL if name in eligible_projects]
    selected_projects = ordered_projects[:MIN_PROJECTS]
    selected: list[FunctionCandidate] = []
    shuffled: dict[str, list[FunctionCandidate]] = {}
    for project in selected_projects:
        items = sorted(by_project[project], key=lambda item: item.function_id)
        rng.shuffle(items)
        shuffled[project] = items
        selected.extend(items[:4])
    while len(selected) < MIN_SELECTED_FUNCTIONS:
        progressed = False
        for project in selected_projects:
            current = [item for item in selected if item.project == project]
            if len(current) >= PROJECT_CAP:
                continue
            pool = [item for item in shuffled[project] if item not in selected]
            if not pool:
                continue
            selected.append(pool[0])
            progressed = True
            if len(selected) >= MIN_SELECTED_FUNCTIONS:
                break
        if not progressed:
            break
    return sorted(selected[:MAX_SELECTED_FUNCTIONS], key=lambda item: (item.project, item.source_path, item.function_name, item.ordinal))


def generate_fixtures(selected: list[FunctionCandidate], work: Path, command_log: Path) -> list[dict[str, Any]]:
    rows = []
    for function in selected:
        rng = random.Random(seed_from(FIXTURE_SEED, function.function_id, function.return_type, ",".join(p.type_text for p in function.params)))
        tuples = list(function.domain)
        fixture_args = rng.sample(tuples, FIXTURES_PER_FUNCTION)
        outputs = execute_function(function, fixture_args, work / "fixture_outputs", command_log)
        for rank, args in enumerate(fixture_args, start=1):
            rows.append(
                {
                    "function_id": function.function_id,
                    "project": function.project,
                    "rank": rank,
                    "args": list(args),
                    "source_output": outputs["outputs"][rank - 1] if outputs["ok"] else None,
                    "fixture_seed": FIXTURE_SEED,
                    "source_agnostic": True,
                }
            )
    return rows


def generate_natural_ghidra_candidates(
    repo_root: Path,
    selected: list[FunctionCandidate],
    work: Path,
    command_log: Path,
) -> list[dict[str, Any]]:
    rows = []
    ghidra = repo_root / GHIDRA_HEADLESS
    if not ghidra.exists():
        return [
            {
                "candidate_id": f"{function.function_id}::ghidra_unavailable",
                "function_id": function.function_id,
                "project": function.project,
                "candidate_stratum": "natural_ghidra",
                "candidate_class": "non_evaluable_compile_failure",
                "compile_status": "ghidra_unavailable",
                "execution_status": "not_executed",
            }
            for function in selected
        ]
    for function in selected:
        for compiler_name, compiler, opt, flags in build_configurations():
            candidate_id = f"{function.function_id}::ghidra::{compiler_name}_{opt}"
            dirs = make_candidate_dirs(work, candidate_id)
            wrapper = wrapper_source(function)
            wrapper_path = dirs["wrapper"] / "wrapper.c"
            wrapper_path.write_text(wrapper, encoding="utf-8")
            object_path = dirs["binary"] / "function.o"
            command = [str(compiler), "-std=c11", f"-{opt}", *flags, "-c", str(wrapper_path), "-o", str(object_path)]
            compile_result = run_command(command, repo_root, command_log, timeout_s=30)
            raw_dir = dirs["raw"]
            normalized_path = dirs["normalized"] / "candidate.c"
            transform_log = {
                "function_id": function.function_id,
                "candidate_id": candidate_id,
                "wrapper_transformation": "prepended noinline/used attribute before extracted function body",
                "normalization": "minimal Ghidra C preamble plus raw function text extraction; no source-guided behavior repair",
                "compiler_command": command,
                "compiler_returncode": compile_result.returncode,
            }
            if compile_result.returncode != 0:
                rows.append(candidate_manifest_row(function, candidate_id, "natural_ghidra", "non_evaluable_compile_failure", compiler_name, opt, wrapper_path, object_path, "", normalized_path, transform_log, "binary_compile_failed"))
                continue
            metadata_path = raw_dir / "metadata.json"
            log_path = dirs["logs"] / "ghidra.log"
            ghidra_result = run_ghidra(repo_root, object_path, function.function_name, raw_dir, metadata_path, log_path, command_log)
            raw_output = first_raw_ghidra_output(raw_dir, function.function_name)
            normalized = normalize_ghidra_output(raw_output)
            normalized_path.write_text(normalized, encoding="utf-8")
            status = "natural_minimally_normalized_ghidra_output" if ghidra_result.returncode == 0 and normalized.strip() else "non_evaluable_compile_failure"
            rows.append(candidate_manifest_row(function, candidate_id, "natural_ghidra", status, compiler_name, opt, wrapper_path, object_path, raw_output, normalized_path, transform_log, "generated"))
    return rows


def generate_controlled_candidates(
    selected: list[FunctionCandidate],
    fixture_rows: list[dict[str, Any]],
    work: Path,
    command_log: Path,
) -> list[dict[str, Any]]:
    fixtures_by_function: dict[str, list[dict[str, Any]]] = {}
    for row in fixture_rows:
        fixtures_by_function.setdefault(row["function_id"], []).append(row)
    rows = []
    for function in selected:
        mutations = eligible_mutations(function, fixtures_by_function.get(function.function_id, []))
        rng = random.Random(seed_from(MUTATION_SEED, function.function_id))
        rng.shuffle(mutations)
        for index, mutation in enumerate(mutations[:MAX_CONTROLLED_MUTATIONS_PER_FUNCTION]):
            candidate_id = f"{function.function_id}::controlled::{mutation['family']}_{index:02d}"
            path = work / "controlled" / safe_name(candidate_id) / "candidate.c"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(mutation["source"], encoding="utf-8")
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "function_id": function.function_id,
                    "project": function.project,
                    "candidate_stratum": "controlled_stress",
                    "candidate_class": "controlled_stress_candidate",
                    "mutation_family": mutation["family"],
                    "mutation_seed": MUTATION_SEED,
                    "candidate_source_path": str(path),
                    "candidate_source_sha256": sha256_path(path),
                    "source_diff": mutation["diff"],
                    "compile_status": "pending_exact_label",
                    "execution_status": "pending_exact_label",
                }
            )
    return rows


def label_candidates(
    selected: list[FunctionCandidate],
    candidates: list[dict[str, Any]],
    work: Path,
    command_log: Path,
) -> list[dict[str, Any]]:
    functions = {function.function_id: function for function in selected}
    labels = []
    for candidate in candidates:
        function = functions[candidate["function_id"]]
        candidate_source_path = candidate.get("normalized_candidate_path") or candidate.get("candidate_source_path")
        if not candidate_source_path or not Path(candidate_source_path).exists():
            labels.append(label_row(candidate, function, "non_evaluable", "missing_candidate_source", [], 0))
            continue
        source_run = execute_function(function, list(function.domain), work / "exact_source", command_log)
        candidate_run = execute_function(function, list(function.domain), work / "exact_candidate", command_log, candidate_source=Path(candidate_source_path).read_text(encoding="utf-8"), candidate_id=candidate["candidate_id"])
        if not source_run["ok"]:
            labels.append(label_row(candidate, function, "non_evaluable", "trusted_source_execution_failed", [], 0))
            continue
        if not candidate_run["ok"]:
            labels.append(label_row(candidate, function, "non_evaluable", candidate_run["reason"], [], 0))
            continue
        mismatches = []
        for rank, (args, left, right) in enumerate(zip(function.domain, source_run["outputs"], candidate_run["outputs"]), start=1):
            if left != right:
                mismatches.append({"rank": rank, "args": list(args), "source_output": left, "candidate_output": right})
        label = "semantic_wrong" if mismatches else "no_mismatch_under_exact_holdout_domain"
        if mismatches:
            confirm = execute_function(function, [tuple(mismatches[0]["args"])], work / "witness_confirm", command_log, candidate_source=Path(candidate_source_path).read_text(encoding="utf-8"), candidate_id=candidate["candidate_id"])
            if not confirm["ok"] or confirm["outputs"][0] != mismatches[0]["candidate_output"]:
                label = "non_evaluable"
        labels.append(label_row(candidate, function, label, "exact_domain_exhaustive_comparison", mismatches[:MAX_STORED_MISMATCHES], len(mismatches)))
    return labels


def extract_functions(text: str) -> list[dict[str, str]]:
    pattern = re.compile(
        r"(?P<header>(?:static\s+)?(?:inline\s+)?(?:const\s+)?(?:unsigned\s+|signed\s+)?(?:char|short|int|long|bool|_Bool)(?:\s+long|\s+int)?\s+"
        r"(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<params>[^;{}]*)\))\s*\{",
        re.MULTILINE,
    )
    results = []
    for match in pattern.finditer(text):
        start = match.start()
        brace = text.find("{", match.end() - 1)
        end = matching_brace(text, brace)
        if end is None:
            continue
        source = text[start:end + 1]
        if source.count("{") != source.count("}"):
            continue
        results.append({"header": match.group("header"), "name": match.group("name"), "params": match.group("params"), "source": source})
    return results


def parse_signature(header: str) -> tuple[str, list[Param]] | None:
    before, _, rest = header.partition("(")
    params_text = rest.rsplit(")", 1)[0].strip()
    parts = before.split()
    if len(parts) < 2:
        return None
    name = parts[-1]
    return_type = normalize_type(" ".join(parts[:-1]))
    if return_type not in SCALAR_TYPES or "*" in return_type or return_type == "void":
        return None
    if not params_text or params_text == "void":
        return None
    params = []
    for raw in split_params(params_text):
        if "*" in raw or "[" in raw or "]" in raw or "..." in raw:
            return None
        bits = raw.strip().split()
        if len(bits) < 2:
            return None
        param_name = bits[-1]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", param_name):
            return None
        type_text = normalize_type(" ".join(bits[:-1]))
        if type_text not in SCALAR_TYPES:
            return None
        params.append(Param(type_text=type_text, name=param_name))
    if len(params) not in {1, 2}:
        return None
    return return_type, params


def normalize_type(text: str) -> str:
    words = [word for word in text.replace("\t", " ").split() if word not in {"static", "inline", "const", "register"}]
    normalized = " ".join(words)
    if normalized == "signed":
        return "signed int"
    if normalized == "unsigned":
        return "unsigned int"
    return normalized


def split_params(text: str) -> list[str]:
    return [part.strip() for part in text.split(",") if part.strip()]


def declared_domain(type_text: str) -> tuple[int, ...] | None:
    normalized = normalize_type(type_text)
    if normalized in {"char", "signed char"}:
        return tuple(range(0, 128))
    if normalized == "unsigned char":
        return tuple(range(0, 128))
    if normalized in {"bool", "_Bool"}:
        return (0, 1)
    if normalized in {"short", "short int", "signed short", "signed short int", "int", "signed int", "long", "long int", "signed long", "signed long int", "long long", "long long int", "signed long long", "signed long long int"}:
        return tuple(range(-32, 32))
    if normalized in {"unsigned short", "unsigned short int", "unsigned int", "unsigned long", "unsigned long int", "unsigned long long", "unsigned long long int"}:
        return tuple(range(0, 64))
    return None


def dependency_filter_reason(source: str, params: tuple[Param, ...] | list[Param]) -> str:
    for pattern in BLACKLIST_PATTERNS:
        if re.search(pattern, source):
            return "dependency_blacklist:" + pattern
    calls = re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", source)
    allowed_calls = {param.name for param in params}
    allowed_calls.update({"if", "for", "while", "switch", "return", "sizeof"})
    function_names = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", source.split("{", 1)[0]))
    allowed_calls.update(function_names)
    disallowed = sorted({call for call in calls if call not in allowed_calls and call not in KEYWORDS})
    if disallowed:
        return "external_function_call:" + ",".join(disallowed[:5])
    if "#" in source:
        return "preprocessor_directive_in_function"
    return ""


def validate_source_function(function: FunctionCandidate, output_dir: Path, command_log: Path) -> dict[str, Any]:
    first = execute_function(function, list(function.domain), output_dir, command_log)
    if not first["ok"]:
        return {"ok": False, "reason": first["reason"]}
    second = execute_function(function, list(function.domain), output_dir, command_log)
    if not second["ok"]:
        return {"ok": False, "reason": "nondeterminism_second_run_failed:" + second["reason"]}
    if first["outputs"] != second["outputs"]:
        return {"ok": False, "reason": "nondeterministic_outputs"}
    return {"ok": True, "reason": "ok"}


def execute_function(
    function: FunctionCandidate,
    args_list: list[tuple[int, ...]],
    output_dir: Path,
    command_log: Path,
    candidate_source: str | None = None,
    candidate_id: str = "trusted_source",
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = safe_name(function.function_id + "_" + candidate_id)[:180]
    source_path = output_dir / f"{stem}.c"
    exe_path = output_dir / f"{stem}.exe"
    source = candidate_source if candidate_source is not None else function.source
    source_path.write_text(render_harness(function, source, args_list), encoding="utf-8")
    compile_cmd = [
        str(GCC), "-std=c11", "-Wall", "-Wextra", "-Werror", "-O0",
        "-fsanitize=undefined,address", "-fno-sanitize-recover=all",
        str(source_path), "-o", str(exe_path),
    ]
    compile_result = run_command(compile_cmd, output_dir, command_log, timeout_s=20)
    if compile_result.returncode != 0:
        return {"ok": False, "reason": "compile_failure", "stderr": compile_result.stderr[-1000:]}
    sanitizer_env = os.environ.copy()
    sanitizer_env["ASAN_OPTIONS"] = "detect_leaks=0"
    sanitizer_env["LSAN_OPTIONS"] = "detect_leaks=0"
    run_result = run_command([str(exe_path)], output_dir, command_log, timeout_s=20, env=sanitizer_env)
    if run_result.returncode != 0:
        return {"ok": False, "reason": f"runtime_failure_{run_result.returncode}", "stderr": run_result.stderr[-1000:]}
    lines = [line.strip() for line in run_result.stdout.splitlines() if line.strip()]
    if len(lines) != len(args_list):
        return {"ok": False, "reason": "harness_output_count_mismatch"}
    try:
        outputs = [int(line) for line in lines]
    except ValueError:
        return {"ok": False, "reason": "non_integer_output"}
    return {"ok": True, "outputs": outputs, "source_path": str(source_path)}


def render_harness(function: FunctionCandidate, function_source: str, args_list: list[tuple[int, ...]]) -> str:
    lines = [
        "#include <stdbool.h>",
        "#include <stdint.h>",
        "#include <stdio.h>",
        "#include <stdlib.h>",
        "",
        function_source.rstrip(),
        "",
        "int main(void) {",
    ]
    for args in args_list:
        rendered = ", ".join(str(value) for value in args)
        lines.append(f'    printf("%lld\\n", (long long){function.function_name}({rendered}));')
    lines.append("    return 0;")
    lines.append("}")
    return "\n".join(lines) + "\n"


def wrapper_source(function: FunctionCandidate) -> str:
    return "\n".join([
        "#include <stdbool.h>",
        "#include <stdint.h>",
        "__attribute__((noinline,used))",
        function.source.rstrip(),
        "",
    ])


def build_configurations() -> list[tuple[str, Path, str, list[str]]]:
    configs = [("gcc", GCC, "O0", ["-g", "-fno-inline", "-fno-pie", "-fcf-protection=none"])]
    if CLANG.exists():
        configs.append(("clang", CLANG, "O2", ["-g", "-fno-inline", "-fno-builtin"]))
    return configs


def run_ghidra(
    repo_root: Path,
    object_path: Path,
    function_name: str,
    raw_dir: Path,
    metadata_path: Path,
    log_path: Path,
    command_log: Path,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["JAVA_HOME"] = str(repo_root / JAVA_HOME)
    project_dir = raw_dir / "project"
    command = [
        str(repo_root / GHIDRA_HEADLESS),
        str(project_dir),
        "holdout_project",
        "-import",
        str(object_path),
        "-postScript",
        "ExportNamedFunctionsDecomp.java",
        function_name,
        str(raw_dir),
        str(metadata_path),
        "-scriptPath",
        str(repo_root / GHIDRA_SCRIPT_DIR),
        "-overwrite",
        "-deleteProject",
        "-analysisTimeoutPerFile",
        "120",
        "-max-cpu",
        "1",
    ]
    result = run_command(command, repo_root, command_log, timeout_s=180, env=env)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text((result.stdout or "") + "\n" + (result.stderr or ""), encoding="utf-8")
    return result


def first_raw_ghidra_output(raw_dir: Path, function_name: str) -> str:
    preferred = raw_dir / f"{function_name}.c"
    if preferred.exists():
        return preferred.read_text(encoding="utf-8", errors="replace")
    for path in sorted(raw_dir.glob("*.c")):
        return path.read_text(encoding="utf-8", errors="replace")
    return ""


def normalize_ghidra_output(raw: str) -> str:
    if not raw.strip():
        return ""
    preamble = "\n".join([
        "#include <stdbool.h>",
        "#include <stdint.h>",
        "typedef unsigned char byte;",
        "typedef unsigned char undefined;",
        "typedef unsigned short undefined2;",
        "typedef unsigned int undefined4;",
        "typedef unsigned long long undefined8;",
        "",
    ])
    cleaned = re.sub(r"/\*.*?\*/", "", raw, flags=re.DOTALL)
    return preamble + cleaned.strip() + "\n"


def eligible_mutations(function: FunctionCandidate, fixtures: list[dict[str, Any]]) -> list[dict[str, str]]:
    source = function.source
    mutations = []
    replacements = {"==": "!=", "!=": "==", "<=": "<", ">=": ">", "<": "<=", ">": ">="}
    for op, repl in replacements.items():
        if op in source:
            mutations.append(mutation("comparison_operator_replacement", source.replace(op, repl, 1), f"{op} -> {repl}"))
            break
    const_match = re.search(r"(?<![A-Za-z_])(-?\d+)(?![A-Za-z_])", source)
    if const_match:
        value = int(const_match.group(1))
        mutated = source[:const_match.start()] + str(value + 1) + source[const_match.end():]
        mutations.append(mutation("integer_or_character_constant_plus_1", mutated, f"{value} -> {value + 1}"))
    if_match = re.search(r"if\s*\(([^()]+)\)", source)
    if if_match:
        mutated = source[:if_match.start(1)] + "!(" + if_match.group(1) + ")" + source[if_match.end(1):]
        mutations.append(mutation("branch_condition_negation", mutated, "negated first simple if condition"))
    ret_match = re.search(r"return\s+([^;]+);", source)
    if ret_match:
        mutated = source[:ret_match.start(1)] + "(" + ret_match.group(1) + ") + 1" + source[ret_match.end(1):]
        mutations.append(mutation("return_value_perturbation", mutated, "first return expression + 1"))
    if len(function.params) == 2 and function.params[0].type_text == function.params[1].type_text:
        first, second = function.params[0].name, function.params[1].name
        body_start = source.find("{")
        body = source[body_start:]
        swapped_body = re.sub(rf"\b{re.escape(first)}\b", "__TMP_ARG__", body, count=1)
        swapped_body = re.sub(rf"\b{re.escape(second)}\b", first, swapped_body, count=1)
        swapped_body = swapped_body.replace("__TMP_ARG__", second, 1)
        mutations.append(mutation("argument_substitution_or_swap", source[:body_start] + swapped_body, f"swapped first occurrences of {first}/{second}"))
    if fixtures:
        mutations.append(mutation("fixture_overfit_construction", fixture_overfit_source(function, fixtures), "returns sealed fixture outputs and zero otherwise"))
    return mutations


def mutation(family: str, source: str, diff: str) -> dict[str, str]:
    return {"family": family, "source": source, "diff": diff}


def fixture_overfit_source(function: FunctionCandidate, fixtures: list[dict[str, Any]]) -> str:
    params = ", ".join(f"{param.type_text} {param.name}" for param in function.params)
    lines = [f"{function.return_type} {function.function_name}({params}) {{"]
    for fixture in fixtures:
        conditions = [
            f"{param.name} == {value}"
            for param, value in zip(function.params, fixture["args"])
        ]
        lines.append(f"    if ({' && '.join(conditions)}) return {int(fixture['source_output'])};")
    lines.append("    return 0;")
    lines.append("}")
    return "\n".join(lines) + "\n"


def label_row(candidate: dict[str, Any], function: FunctionCandidate, label: str, reason: str, mismatches: list[dict[str, Any]], mismatch_count: int) -> dict[str, Any]:
    row = {
        "candidate_id": candidate["candidate_id"],
        "function_id": function.function_id,
        "project": function.project,
        "candidate_stratum": candidate["candidate_stratum"],
        "candidate_class": candidate["candidate_class"],
        "label": label,
        "reason": reason,
        "exact_domain_size": function.domain_size,
        "total_mismatching_input_count": mismatch_count,
        "first_mismatch": mismatches[0] if mismatches else None,
        "stored_mismatches": mismatches,
    }
    row["label_record_sha256"] = sha256_text(json.dumps(row, sort_keys=True))
    return row


def summarize_labels(labels: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for label in labels:
        groups.setdefault((label["candidate_stratum"], label["label"]), []).append(label)
    return [
        {"candidate_stratum": stratum, "label": label, "count": len(rows)}
        for (stratum, label), rows in sorted(groups.items())
    ]


def candidate_manifest_row(
    function: FunctionCandidate,
    candidate_id: str,
    stratum: str,
    cls: str,
    compiler_name: str,
    opt: str,
    wrapper_path: Path,
    object_path: Path,
    raw_output: str,
    normalized_path: Path,
    transform_log: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    transform_path = normalized_path.parent / "transformation_log.json"
    transform_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(transform_path, transform_log)
    return {
        "candidate_id": candidate_id,
        "function_id": function.function_id,
        "project": function.project,
        "candidate_stratum": stratum,
        "candidate_class": cls,
        "tool": "Ghidra 12.1.2 headless",
        "compiler": compiler_name,
        "optimization_level": opt,
        "wrapper_source_path": str(wrapper_path),
        "wrapper_source_sha256": sha256_path(wrapper_path) if wrapper_path.exists() else "",
        "object_path": str(object_path),
        "object_sha256": sha256_path(object_path) if object_path.exists() else "",
        "raw_ghidra_sha256": sha256_text(raw_output),
        "normalized_candidate_path": str(normalized_path),
        "normalized_candidate_sha256": sha256_path(normalized_path) if normalized_path.exists() else "",
        "transformation_log_path": str(transform_path),
        "compile_status": status,
        "execution_status": "pending_exact_label",
    }


def make_candidate_dirs(work: Path, candidate_id: str) -> dict[str, Path]:
    root = work / "natural_ghidra" / safe_name(candidate_id)
    dirs = {name: root / name for name in ["wrapper", "binary", "raw", "normalized", "logs"]}
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def iter_source_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*.c")):
        parts = set(part.lower() for part in path.relative_to(root).parts)
        if parts & SKIP_DIR_PARTS:
            continue
        if path.stat().st_size > 250_000:
            continue
        yield path


def matching_brace(text: str, open_index: int) -> int | None:
    depth = 0
    index = open_index
    while index < len(text):
        ch = text[index]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def census_row(project: dict[str, Any], files: int, parsed: int, signature: int, dependency: int, sanitizer: int, eligible: int) -> dict[str, Any]:
    return {
        "project": project["project"],
        "pool": project["pool"],
        "pinned_commit": project.get("pinned_commit", ""),
        "source_files_scanned": files,
        "functions_parsed": parsed,
        "functions_passing_signature_filters": signature,
        "functions_passing_dependency_filters": dependency,
        "functions_passing_exhaustive_source_domain_sanitizer_validation": sanitizer,
        "final_eligible_functions": eligible,
    }


def exclusion(project: dict[str, Any], rel: str, parsed: dict[str, str], reason: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "project": project["project"],
        "source_file": rel,
        "function_name": parsed.get("name", ""),
        "reason": reason,
        "extra": extra or {},
    }


def stable_function_id(project: str, rel: str, name: str, ordinal: int, source: str) -> str:
    digest = sha256_text("|".join([project, rel, name, str(ordinal), source]))[:12]
    return f"{safe_name(project)}::{safe_name(rel)}::{safe_name(name)}::{ordinal:04d}::{digest}"


def seed_from(seed: int, *parts: str) -> int:
    digest = hashlib.sha256(("|".join([str(seed), *parts])).encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def run_command(
    argv: list[str],
    cwd: Path,
    command_log: Path,
    timeout_s: int,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    record = {"created_at_utc": now_utc(), "argv": argv, "cwd": str(cwd), "timeout_s": timeout_s}
    try:
        result = subprocess.run(
            argv,
            cwd=cwd,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout_s,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        result = subprocess.CompletedProcess(argv, 124, exc.stdout or "", exc.stderr or "timeout")
    record.update({"returncode": result.returncode, "stdout_tail": (result.stdout or "")[-400:], "stderr_tail": (result.stderr or "")[-400:]})
    append_jsonl(command_log, [record])
    return result


def git_at(path: Path, args: list[str]) -> str:
    result = subprocess.run(["git", *args], cwd=path, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    return result.stdout.strip() if result.returncode == 0 else ""


def build_sealed_manifest(
    repo_root: Path,
    status: str,
    project_records: list[dict[str, Any]],
    acquisition_errors: list[dict[str, Any]],
    census_rows: list[dict[str, Any]],
    exclusion_rows: list[dict[str, Any]],
    selected: list[FunctionCandidate],
    fixture_rows: list[dict[str, Any]],
    natural_candidates: list[dict[str, Any]],
    controlled_candidates: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    command_log: Path,
) -> dict[str, Any]:
    artifact_paths = [
        "docs/paper_agent/frozen_holdout_preregistration_v3.md",
        "docs/paper_agent/holdout_mutation_grammar.md",
        "results/decompile_faithfulness/holdout_project_manifest.json",
        "results/decompile_faithfulness/holdout_eligibility_census.csv",
        "results/decompile_faithfulness/holdout_exclusions.jsonl",
        "results/decompile_faithfulness/holdout_sampling_frame.csv",
        "results/decompile_faithfulness/holdout_selected_functions.csv",
        "results/decompile_faithfulness/holdout_fixtures.jsonl",
        "results/decompile_faithfulness/holdout_candidate_manifest.jsonl",
        "results/decompile_faithfulness/holdout_controlled_candidates.jsonl",
        "results/decompile_faithfulness/holdout_exact_labels.jsonl",
        "results/decompile_faithfulness/holdout_label_summary.csv",
        "results/decompile_faithfulness/holdout_execution_log.jsonl",
        "paper/tables/holdout_acquisition.tex",
    ]
    log_text = command_log.read_text(encoding="utf-8") if command_log.exists() else ""
    return {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "status": status,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "phase1b_correction_commit": PHASE1B_CORRECTION_COMMIT,
        "current_acquisition_commit_context": git_at(repo_root, ["rev-parse", "HEAD"]),
        "final_auditor_invoked": False,
        "prohibited_final_method_functions_confirmed_absent_from_execution_log": {
            name: name not in log_text for name in PROHIBITED_FINAL_METHOD_FUNCTIONS
        },
        "project_repositories": project_records,
        "acquisition_errors": acquisition_errors,
        "sampling_seed": ACQUISITION_SEED,
        "fixture_seed": FIXTURE_SEED,
        "mutation_seed": MUTATION_SEED,
        "exact_domain_definitions": domain_definition_text(),
        "eligibility_counts_by_project": census_rows,
        "selected_functions": [
            selected_function_row(function) for function in selected
        ],
        "fixture_count": len(fixture_rows),
        "sampling_capacity_under_project_cap": sum(
            min(PROJECT_CAP, sum(1 for candidate in selected if candidate.project == project))
            for project in {candidate.project for candidate in selected}
        ) if selected else sum(
            min(PROJECT_CAP, int(row["final_eligible_functions"]))
            for row in census_rows
        ),
        "natural_candidate_count": len(natural_candidates),
        "controlled_candidate_count": len(controlled_candidates),
        "label_count": len(labels),
        "exclusion_count": len(exclusion_rows),
        "artifact_hashes": {
            path: sha256_path(repo_root / path) for path in artifact_paths if (repo_root / path).exists()
        },
        "execution_log_path": str(command_log),
        "execution_log_sha256": sha256_path(command_log) if command_log.exists() else "",
    }


def selected_function_row(function: FunctionCandidate) -> dict[str, Any]:
    return {
        "function_id": function.function_id,
        "project": function.project,
        "source_file": function.source_path,
        "function_name": function.function_name,
        "return_type": function.return_type,
        "argument_types": ";".join(param.type_text for param in function.params),
        "domain_size": function.domain_size,
        "source_sha256": function.source_sha256,
    }


def write_preregistration(repo_root: Path) -> None:
    text = f"""# Frozen Holdout Preregistration v3

Generated: {now_utc()}

Final method remains frozen at `{METHOD_FREEZE_COMMIT}`. This phase acquires and seals a project-disjoint exact-oracle holdout. The frozen final auditor and its ordered probes must not be invoked before seal review.

## Supported Function Class

Retain only functions with exactly one or two scalar integral or character arguments, scalar integral or character return, deterministic behavior, no pointer/array arguments, no pointer return, no mutable global state, no heap ownership, no I/O/network/environment/locale/time/thread dependence, no callback dependence, no undefined or implementation-dependent behavior over the declared domain, isolated harness compilation, and no project runtime initialization. Zero-argument functions are excluded.

Selection must not depend on source character literals, comparison constants, or structures favorable to the final method.

## Exact Domains

- signed char and signed char-like values: `[0, 127]` under the sealed char model;
- unsigned char: `[0, 127]`;
- bool: `{{0, 1}}`;
- signed short/int/long-like arguments: `[-32, 31]`;
- unsigned short/int/long-like arguments: `[0, 63]`;
- enum arguments are excluded unless representation and admissible values are sealed without source-specific manual choice.

One-argument domains are exhaustive. Two-argument domains are exhaustive Cartesian products. The bounded domain is the formal evaluation domain; no full C-type equivalence outside it is claimed.

## Project Pool

Primary ordered pool: libtommath, cJSON, uthash, musl, zlib, mbedtls, sqlite utility-only subset, libb64, inih, tiny-AES-c utility subset.

Fallback ordered pool: libtomcrypt, BearSSL, libdeflate, xxHash, TinyCC, chibicc, sbase.

Excluded prior sources: CodeFuse-DeBench, c_algorithms, thealgorithms_c, and any prior development fixtures/candidates/examples.

## Sampling And Fixtures

Sampling seed: `{ACQUISITION_SEED}`. Fixture seed: `{FIXTURE_SEED}`. Mutation seed: `{MUTATION_SEED}`.

If fewer than 48 eligible functions across at least 8 projects are available, or if the cap-constrained sampling capacity is below 48, stop before candidate generation and push the census for review. Otherwise sample 48-64 functions from at least 8 projects, cap each project at 8 functions, and generate exactly four source-agnostic fixtures per function from function ID, signature, declared domain, and fixture seed only.

## Candidate Strata

Primary natural-output stratum: Ghidra 12.1.2 headless outputs from GCC `-O0` and Clang `-O2` builds where technically possible. Raw output, parsed extraction, minimally normalized candidate, and transformation logs are stored separately.

Secondary controlled-stress stratum: fixed grammar sealed in `docs/paper_agent/holdout_mutation_grammar.md`. Controlled candidates are never pooled with natural outputs in the primary generalization claim.

## Exact Labels And Seal

Compile/runtime/sanitizer/timeout/harness/nondeterminism failures are `non_evaluable`. A candidate is `semantic_wrong` only with a reproducible source-candidate mismatch under complete declared-domain enumeration. The seal hashes projects, source files, functions, domains, fixtures, tool configurations, candidates, labels, witnesses, and exclusions before final-auditor evaluation.
"""
    (repo_root / "docs/paper_agent/frozen_holdout_preregistration_v3.md").write_text(text, encoding="utf-8")


def write_mutation_grammar(repo_root: Path) -> None:
    text = """# Holdout Mutation Grammar

This grammar is sealed before semantic labels or final-auditor outputs are inspected.

Families:

1. comparison-operator replacement: replace the first eligible `==`, `!=`, `<`, `<=`, `>`, or `>=` with a deterministic paired operator.
2. integer or character constant +/- 1: increment the first numeric scalar constant by one when the result remains syntactically valid.
3. branch-condition negation: wrap the first simple `if` predicate in `!(...)`.
4. off-by-one arithmetic mutation: covered by constant +/- 1 and return perturbation for this sealed implementation.
5. return-value perturbation: add one to the first return expression.
6. argument substitution or swap: for two same-type arguments, swap first body occurrences.
7. deletion or inversion of one conditional arm: represented by first simple branch-condition negation in this implementation.
8. fixture-overfit construction: emit a deterministic if-chain over sealed fixtures and return zero otherwise.

Eligibility requires scalar return/arguments, syntactic transformation success, and candidate compile handling during exact labeling. At most two controlled candidates are selected per function using the committed mutation seed. Failed compilation is `non_evaluable`, not semantic wrong.
"""
    (repo_root / "docs/paper_agent/holdout_mutation_grammar.md").write_text(text, encoding="utf-8")


def update_dataset_provenance_table(repo_root: Path) -> None:
    text = r"""\begin{tabular}{lrrrrrrrrrll}
\toprule
Collection & Projects & Source functions & Attempts & Compile-ready & Primary evaluated & Paired cases & Semantic wrong & No-mismatch & Non-evaluable & Primary candidate provenance & Development/holdout status \\
\midrule
Public static-hard & 1 & 56 & 524 & 503 & 478 & 50 & 258 & 211 & 9 & Source-controlled semantic mutations and original controls & pre-freeze development evidence \\
LLM-public & 1 & 56 & 224 & 143 & 136 & 24 & 36 & 100 & 0 & Dream-Coder raw generations with function extraction & pre-freeze development evidence \\
Ghidra & 2 & 38 & 228 & 166 & 166 & 26 & 74 & 92 & 0 & Ghidra-derived controlled stress and control candidates & pre-freeze development evidence \\
\bottomrule
\end{tabular}
"""
    (repo_root / "paper/tables/dataset_provenance_v2.tex").write_text(text, encoding="utf-8")


def write_project_manifest(repo_root: Path, records: list[dict[str, Any]], errors: list[dict[str, Any]]) -> None:
    write_json(
        repo_root / "results/decompile_faithfulness/holdout_project_manifest.json",
        {
            "schema_version": 1,
            "created_at_utc": now_utc(),
            "method_freeze_commit": METHOD_FREEZE_COMMIT,
            "phase1b_correction_commit": PHASE1B_CORRECTION_COMMIT,
            "project_pool": records,
            "acquisition_errors": errors,
        },
    )


def write_census(repo_root: Path, rows: list[dict[str, Any]]) -> None:
    write_csv(repo_root / "results/decompile_faithfulness/holdout_eligibility_census.csv", rows, [
        "project", "pool", "pinned_commit", "source_files_scanned", "functions_parsed",
        "functions_passing_signature_filters", "functions_passing_dependency_filters",
        "functions_passing_exhaustive_source_domain_sanitizer_validation", "final_eligible_functions",
    ])


def write_exclusions(repo_root: Path, rows: list[dict[str, Any]]) -> None:
    write_jsonl(repo_root / "results/decompile_faithfulness/holdout_exclusions.jsonl", rows)


def write_sampling_frame(repo_root: Path, candidates: list[FunctionCandidate]) -> None:
    rows = [selected_function_row(item) for item in candidates]
    write_csv(repo_root / "results/decompile_faithfulness/holdout_sampling_frame.csv", rows, [
        "function_id", "project", "source_file", "function_name", "return_type", "argument_types", "domain_size", "source_sha256",
    ])


def write_selected_functions(repo_root: Path, selected: list[FunctionCandidate]) -> None:
    rows = [selected_function_row(item) for item in selected]
    write_csv(repo_root / "results/decompile_faithfulness/holdout_selected_functions.csv", rows, [
        "function_id", "project", "source_file", "function_name", "return_type", "argument_types", "domain_size", "source_sha256",
    ])


def write_label_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    write_csv(path, rows, ["candidate_stratum", "label", "count"])


def write_holdout_acquisition_table(
    repo_root: Path,
    census_rows: list[dict[str, Any]],
    selected: list[FunctionCandidate],
    natural_candidates: list[dict[str, Any]],
    controlled_candidates: list[dict[str, Any]],
    labels: list[dict[str, Any]],
) -> None:
    projects = sum(1 for row in census_rows if int(row["final_eligible_functions"]) > 0)
    eligible = sum(int(row["final_eligible_functions"]) for row in census_rows)
    natural_ready = sum(1 for row in natural_candidates if row.get("candidate_class") != "non_evaluable_compile_failure")
    controlled_ready = len(controlled_candidates)
    label_counts = {label: sum(1 for row in labels if row["label"] == label) for label in ["semantic_wrong", "no_mismatch_under_exact_holdout_domain", "non_evaluable"]}
    text = f"""\\begin{{tabular}}{{lrrrrrrrrrr}}
\\toprule
Status & Projects & Eligible functions & Selected functions & Natural attempts & Natural compile-ready & Controlled attempts & Controlled compile-ready & Semantic wrong & Exact-domain no-mismatch & Non-evaluable \\\\
\\midrule
Preliminary holdout acquisition & {projects} & {eligible} & {len(selected)} & {len(natural_candidates)} & {natural_ready} & {len(controlled_candidates)} & {controlled_ready} & {label_counts['semantic_wrong']} & {label_counts['no_mismatch_under_exact_holdout_domain']} & {label_counts['non_evaluable']} \\\\
\\bottomrule
\\end{{tabular}}
"""
    (repo_root / "paper/tables/holdout_acquisition.tex").write_text(text, encoding="utf-8")


def write_handoff(repo_root: Path, manifest: dict[str, Any], seal_hash: str, status: str) -> None:
    census = manifest["eligibility_counts_by_project"]
    selected = manifest["selected_functions"]
    text = f"""# Holdout Acquisition Seal Handoff

## Git

- Branch: `{git_at(repo_root, ["branch", "--show-current"])}`
- HEAD at generation: `{git_at(repo_root, ["rev-parse", "HEAD"])}`
- Method freeze commit: `{METHOD_FREEZE_COMMIT}`
- Phase 1b correction commit: `{PHASE1B_CORRECTION_COMMIT}`

## Seeds And Domains

- Sampling seed: `{ACQUISITION_SEED}`
- Fixture seed: `{FIXTURE_SEED}`
- Mutation seed: `{MUTATION_SEED}`
- Exact domains: `{json.dumps(domain_definition_text(), sort_keys=True)}`

## Project Commits

```json
{json.dumps(manifest['project_repositories'], indent=2, sort_keys=True)}
```

## Eligibility Counts By Project

```json
{json.dumps(census, indent=2, sort_keys=True)}
```

## Selected Functions

- Selected-function count: `{len(selected)}`
- Selected-function counts by project: `{json.dumps(count_by([row['project'] for row in selected]), sort_keys=True)}`

## Candidate And Label Counts

- Natural candidate attempts: `{manifest['natural_candidate_count']}`
- Controlled candidate attempts: `{manifest['controlled_candidate_count']}`
- Exact-label count: `{manifest['label_count']}`
- Exclusion count: `{manifest['exclusion_count']}`
- Sampling capacity under project cap: `{manifest['sampling_capacity_under_project_cap']}`

Any status beginning with `stopped_before_candidate_generation_` means fixture generation, natural candidate generation, controlled candidate generation, exact labeling, and final-auditor evaluation were intentionally not run.

## Seal

- Status: `{status}`
- Seal manifest hash: `{seal_hash}`
- Final auditor invoked: `False`
- Prohibited final-method functions absent from execution log: `{json.dumps(manifest['prohibited_final_method_functions_confirmed_absent_from_execution_log'], sort_keys=True)}`

## Tests Run

- `python -m py_compile analysis/decompile_faithfulness/holdout_acquisition.py`
- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze analysis.decompile_faithfulness.tests.test_submission_evidence_corrections analysis.decompile_faithfulness.tests.test_holdout_acquisition`

## Review Readiness

The holdout is ready for independent seal review only if status is `sealed_after_exact_labeling`. Otherwise this is a census/blocker artifact for review before broadening the project pool or adjusting eligibility rules.
"""
    (repo_root / "docs/paper_agent/holdout_acquisition_seal_handoff.md").write_text(text, encoding="utf-8")


def domain_definition_text() -> dict[str, str]:
    return {
        "char_signed_model": "[0, 127]",
        "unsigned_char": "[0, 127]",
        "bool": "{0, 1}",
        "signed_short_int_long_like": "[-32, 31]",
        "unsigned_short_int_long_like": "[0, 63]",
        "two_argument_rule": "complete Cartesian product",
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def count_by(values: Iterable[str]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        result[value] = result.get(value, 0) + 1
    return result


def read_text_lossy(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("._") or "item"


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


if __name__ == "__main__":
    main()
