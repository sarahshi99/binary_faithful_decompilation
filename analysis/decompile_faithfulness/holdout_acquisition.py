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
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable


METHOD_FREEZE_COMMIT = "06dda89912103b94fc065d6f073581a7811154b1"
PHASE1B_CORRECTION_COMMIT = "a784d1c8195ae88a8b3233f8eef5cfd2c27d7b14"
PHASE1C_CENSUS_COMMIT = "4b4e552b2ea93f057c679a0eba662075e09203be"
PHASE1C_CENSUS_SEAL_HASH = "74b2168a7b9f4e924c521d37df16b48ee776b9562b9c2d1c674147be2e2127ba"
PHASE1D_AMENDMENT_COMMIT = "3a0a65ff6c38da9dbd9a9f620a6b434d7fb3e1fa"
ACQUISITION_SEED = 2026070301
FIXTURE_SEED = 2026070302
MUTATION_SEED = 2026070303
MIN_PROJECTS = 8
MIN_SELECTED_FUNCTIONS = 42
MAX_SELECTED_FUNCTIONS = 42
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
    source_file_sha256: str
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
    figure_out = repo_root / "figures/data"
    work = repo_root / "analysis_outputs/decompile_faithfulness/holdout_phase1d"
    project_root = repo_root / "external/holdout_projects"
    artifact_root = out / "holdout_candidate_artifacts"
    for path in [out, analysis_out, figure_out, work, project_root, artifact_root]:
        path.mkdir(parents=True, exist_ok=True)
    if artifact_root.exists():
        shutil.rmtree(artifact_root)
        artifact_root.mkdir(parents=True, exist_ok=True)
    command_log = work / "holdout_execution_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    update_dataset_provenance_table(repo_root)

    project_records, acquisition_errors = acquire_projects(repo_root, project_root, command_log)
    candidates, census_rows, exclusion_rows = run_eligibility_census(repo_root, project_records, work, command_log)
    write_project_manifest(repo_root, project_records, acquisition_errors)
    write_project_manifest_v2(repo_root, project_records, acquisition_errors)
    write_census(repo_root, census_rows)
    write_exclusions(repo_root, exclusion_rows)
    selection_metadata = deterministic_selection_metadata(candidates)
    write_sampling_frame(repo_root, candidates)
    write_sampling_frame_v2(repo_root, candidates, project_records, selection_metadata)

    gate = eligibility_gate(candidates)
    enough = gate["passed"]
    if enough:
        selected = deterministic_sample(candidates, selection_metadata=selection_metadata)
    else:
        selected = []
    selected_metadata = {function.function_id: selection_metadata[function.function_id] for function in selected}
    write_selected_functions(repo_root, selected, project_records, selected_metadata)

    fixture_rows: list[dict[str, Any]] = []
    natural_candidates: list[dict[str, Any]] = []
    controlled_candidates: list[dict[str, Any]] = []
    labels: list[dict[str, Any]] = []
    label_summary: list[dict[str, Any]] = []
    status = gate["status"]

    if enough:
        status = "sealed_after_exact_labeling"
        fixture_rows = generate_fixtures(selected, work, command_log)
        natural_candidates = generate_natural_ghidra_candidates(repo_root, selected, artifact_root / "natural_ghidra", command_log)
        controlled_candidates = generate_controlled_candidates(selected, fixture_rows, artifact_root / "controlled", command_log)
        labels = label_candidates(selected, natural_candidates + controlled_candidates, work, command_log)
        apply_label_outcomes(natural_candidates + controlled_candidates, labels)
        label_summary = summarize_labels(labels)

    write_jsonl(out / "holdout_fixtures.jsonl", fixture_rows)
    write_jsonl(out / "holdout_candidate_manifest.jsonl", natural_candidates + controlled_candidates)
    write_jsonl(out / "holdout_controlled_candidates.jsonl", controlled_candidates)
    write_jsonl(out / "holdout_exact_labels.jsonl", labels)
    write_label_summary(out / "holdout_label_summary.csv", label_summary)
    write_holdout_acquisition_table(repo_root, census_rows, selected, natural_candidates, controlled_candidates, labels)
    descriptive = descriptive_analysis(selected, natural_candidates, controlled_candidates, labels)
    write_json(out / "holdout_pre_auditor_descriptive_analysis.json", descriptive)
    write_dataset_flow(repo_root, census_rows, selected, natural_candidates, controlled_candidates, labels)
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
        selected_metadata=selected_metadata,
        fixture_rows=fixture_rows,
        natural_candidates=natural_candidates,
        controlled_candidates=controlled_candidates,
        labels=labels,
        command_log=submitted_command_log,
        descriptive=descriptive,
    )
    write_json(analysis_out / "holdout_sealed_manifest_v2.json", manifest)
    seal_hash = sha256_path(analysis_out / "holdout_sealed_manifest_v2.json")
    (analysis_out / "holdout_sealed_manifest_v2.sha256").write_text(
        f"{seal_hash}  holdout_sealed_manifest_v2.json\n",
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
            source_file_sha256 = sha256_path(source_path)
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
                    source_file_sha256=source_file_sha256,
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
    if project_count < MIN_PROJECTS:
        status = "stopped_before_candidate_generation_insufficient_project_count"
    elif capacity < MIN_SELECTED_FUNCTIONS:
        status = "stopped_before_candidate_generation_insufficient_eligible_functions"
    elif capacity != MIN_SELECTED_FUNCTIONS:
        status = "stopped_before_candidate_generation_unexpected_capped_sampling_capacity"
    else:
        status = "sealed_after_exact_labeling"
    return {
        "passed": status == "sealed_after_exact_labeling",
        "status": status,
        "eligible_function_count": len(candidates),
        "eligible_project_count": project_count,
        "sampling_capacity_under_project_cap": capacity,
    }


def legacy_phase1c_eligibility_gate(candidates: list[FunctionCandidate]) -> dict[str, Any]:
    projects = {item.project for item in candidates}
    project_count = len(projects)
    capacity = sum(min(PROJECT_CAP, sum(1 for item in candidates if item.project == project)) for project in projects)
    if len(candidates) < 48:
        status = "stopped_before_candidate_generation_insufficient_eligible_functions"
    elif project_count < MIN_PROJECTS:
        status = "stopped_before_candidate_generation_insufficient_project_count"
    elif capacity < 48:
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


def deterministic_selection_metadata(candidates: list[FunctionCandidate]) -> dict[str, dict[str, int]]:
    by_project: dict[str, list[FunctionCandidate]] = {}
    for item in candidates:
        by_project.setdefault(item.project, []).append(item)
    ordered_projects = [name for name, _url, _pool in PROJECT_POOL if name in by_project and by_project[name]]
    rng = random.Random(ACQUISITION_SEED)
    shuffled: dict[str, list[FunctionCandidate]] = {}
    for project in ordered_projects:
        items = sorted(by_project[project], key=lambda item: item.function_id)
        rng.shuffle(items)
        shuffled[project] = items
    selected: list[tuple[FunctionCandidate, int, int]] = []
    project_counts = {project: 0 for project in ordered_projects}
    round_index = 1
    while True:
        progressed = False
        for project in ordered_projects:
            if project_counts[project] >= PROJECT_CAP:
                continue
            items = shuffled[project]
            if project_counts[project] >= len(items):
                continue
            function = items[project_counts[project]]
            project_counts[project] += 1
            selected.append((function, project_counts[project], round_index))
            progressed = True
        if not progressed:
            break
        round_index += 1
    return {
        function.function_id: {
            "selection_rank_within_project": rank,
            "selection_round": round_number,
            "acquisition_seed": ACQUISITION_SEED,
        }
        for function, rank, round_number in selected[:MAX_SELECTED_FUNCTIONS]
    }


def deterministic_sample(
    candidates: list[FunctionCandidate],
    selection_metadata: dict[str, dict[str, int]] | None = None,
) -> list[FunctionCandidate]:
    if selection_metadata is None:
        selection_metadata = deterministic_selection_metadata(candidates)
    by_project: dict[str, list[FunctionCandidate]] = {}
    for item in candidates:
        by_project.setdefault(item.project, []).append(item)
    selected = [item for item in candidates if item.function_id in selection_metadata]
    return sorted(
        selected,
        key=lambda item: (
            selection_metadata[item.function_id]["selection_round"],
            project_order_index(item.project),
            selection_metadata[item.function_id]["selection_rank_within_project"],
            item.function_id,
        ),
    )


def project_order_index(project: str) -> int:
    for index, (name, _url, _pool) in enumerate(PROJECT_POOL):
        if name == project:
            return index
    return len(PROJECT_POOL)


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
                "candidate_class": "non_evaluable_decompilation_failure",
                "candidate_status": "non_evaluable_decompilation_failure",
                "compile_status": "ghidra_unavailable",
                "execution_status": "not_executed",
            }
            for function in selected
        ]
    for function in selected:
        for compiler_name, compiler, opt, flags in build_configurations():
            candidate_id = f"{function.function_id}::ghidra::{compiler_name}_{opt}"
            dirs = make_candidate_dirs(work, candidate_id)
            original_path = dirs["original"] / "source_function.c"
            original_path.write_text(function.source.rstrip() + "\n", encoding="utf-8")
            wrapper = wrapper_source(function)
            wrapper_path = dirs["wrapper"] / "wrapper.c"
            wrapper_path.write_text(wrapper, encoding="utf-8")
            object_path = dirs["binary"] / "function.bin"
            command = [str(compiler), "-std=c11", f"-{opt}", *flags, "-c", str(wrapper_path), "-o", str(object_path)]
            compile_result = run_command(command, repo_root, command_log, timeout_s=30)
            raw_dir = dirs["raw"]
            raw_path = raw_dir / "raw_decompiler_output.c"
            parsed_path = dirs["parsed"] / "parsed_function_extraction.c"
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
                rows.append(candidate_manifest_row(function, candidate_id, "natural_ghidra", "non_evaluable_compile_failure", compiler_name, opt, original_path, wrapper_path, object_path, raw_path, parsed_path, normalized_path, transform_log, "binary_compile_failed"))
                continue
            metadata_path = raw_dir / "metadata.json"
            log_path = dirs["logs"] / "ghidra.log"
            ghidra_result = run_ghidra(repo_root, object_path, function.function_name, raw_dir, metadata_path, log_path, command_log)
            raw_output = first_raw_ghidra_output(raw_dir, function.function_name)
            raw_path.write_text(raw_output, encoding="utf-8")
            parsed_path.write_text(raw_output, encoding="utf-8")
            normalized = normalize_ghidra_output(raw_output)
            normalized_path.write_text(normalized, encoding="utf-8")
            status = "natural_minimally_normalized_ghidra_output" if ghidra_result.returncode == 0 and normalized.strip() else "non_evaluable_decompilation_failure"
            rows.append(candidate_manifest_row(function, candidate_id, "natural_ghidra", status, compiler_name, opt, original_path, wrapper_path, object_path, raw_path, parsed_path, normalized_path, transform_log, "generated"))
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
            path = work / safe_name(candidate_id) / "candidate.c"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(mutation["source"], encoding="utf-8")
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "function_id": function.function_id,
                    "project": function.project,
                    "candidate_stratum": "controlled_stress",
                    "candidate_class": "controlled_stress_candidate",
                    "candidate_status": "controlled_stress_candidate",
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
    source_cache: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        function = functions[candidate["function_id"]]
        if str(candidate.get("candidate_status", candidate.get("candidate_class", ""))).startswith("non_evaluable_"):
            labels.append(label_row(candidate, function, "non_evaluable", candidate.get("candidate_status", candidate.get("compile_status", "non_evaluable")), [], 0))
            continue
        candidate_source_path = candidate.get("normalized_candidate_path") or candidate.get("candidate_source_path")
        if not candidate_source_path or not Path(candidate_source_path).exists():
            labels.append(label_row(candidate, function, "non_evaluable", "missing_candidate_source", [], 0))
            continue
        source_run = source_cache.get(function.function_id)
        if source_run is None:
            source_run = execute_function(function, list(function.domain), work / "exact_source", command_log)
            source_cache[function.function_id] = source_run
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
        confirmation = {"confirmed": False}
        if mismatches:
            first_args = [tuple(mismatches[0]["args"])]
            confirm_source = execute_function(function, first_args, work / "witness_confirm_source", command_log)
            confirm_candidate = execute_function(function, first_args, work / "witness_confirm_candidate", command_log, candidate_source=Path(candidate_source_path).read_text(encoding="utf-8"), candidate_id=candidate["candidate_id"])
            confirmation = {
                "confirmed": bool(
                    confirm_source["ok"]
                    and confirm_candidate["ok"]
                    and confirm_source["outputs"][0] == mismatches[0]["source_output"]
                    and confirm_candidate["outputs"][0] == mismatches[0]["candidate_output"]
                ),
                "source_ok": confirm_source["ok"],
                "candidate_ok": confirm_candidate["ok"],
            }
            if not confirmation["confirmed"]:
                label = "non_evaluable"
        labels.append(label_row(candidate, function, label, "exact_domain_exhaustive_comparison", mismatches[:MAX_STORED_MISMATCHES], len(mismatches), mismatch_digest=sha256_text(json.dumps(mismatches, sort_keys=True)), confirmation=confirmation))
    return labels


def apply_label_outcomes(candidates: list[dict[str, Any]], labels: list[dict[str, Any]]) -> None:
    by_candidate = {label["candidate_id"]: label for label in labels}
    for candidate in candidates:
        label = by_candidate.get(candidate["candidate_id"])
        if not label:
            continue
        candidate["label"] = label["label"]
        candidate["label_reason"] = label["reason"]
        candidate["exact_domain_size"] = label["exact_domain_size"]
        candidate["total_mismatching_input_count"] = label["total_mismatching_input_count"]
        candidate["label_record_sha256"] = label["label_record_sha256"]
        if label["label"] == "non_evaluable":
            candidate["compile_status"] = "non_evaluable"
            candidate["execution_status"] = label["reason"]
            if label["reason"] == "compile_failure":
                candidate["candidate_status"] = "non_evaluable_compile_failure"
            elif label["reason"].startswith("runtime_failure") or label["reason"] in {
                "harness_output_count_mismatch",
                "non_integer_output",
                "trusted_source_execution_failed",
                "missing_candidate_source",
            }:
                candidate["candidate_status"] = "non_evaluable_harness_failure"
        else:
            candidate["compile_status"] = "compile_ready"
            candidate["execution_status"] = "exact_domain_execution_complete"


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
    project_dir.mkdir(parents=True, exist_ok=True)
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


def label_row(
    candidate: dict[str, Any],
    function: FunctionCandidate,
    label: str,
    reason: str,
    mismatches: list[dict[str, Any]],
    mismatch_count: int,
    mismatch_digest: str | None = None,
    confirmation: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "complete_mismatch_set_sha256": mismatch_digest or sha256_text(json.dumps(mismatches, sort_keys=True)),
        "first_mismatch_confirmation": confirmation or {"confirmed": False},
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
    original_path: Path,
    wrapper_path: Path,
    object_path: Path,
    raw_path: Path,
    parsed_path: Path,
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
        "candidate_class": "natural_ghidra_output" if stratum == "natural_ghidra" else cls,
        "candidate_status": cls,
        "tool": "Ghidra 12.1.2 headless",
        "compiler": compiler_name,
        "optimization_level": opt,
        "original_source_function_path": str(original_path),
        "original_source_function_sha256": sha256_path(original_path) if original_path.exists() else "",
        "wrapper_source_path": str(wrapper_path),
        "wrapper_source_sha256": sha256_path(wrapper_path) if wrapper_path.exists() else "",
        "object_path": str(object_path),
        "object_sha256": sha256_path(object_path) if object_path.exists() else "",
        "raw_ghidra_output_path": str(raw_path),
        "raw_ghidra_sha256": sha256_path(raw_path) if raw_path.exists() else "",
        "parsed_function_extraction_path": str(parsed_path),
        "parsed_function_extraction_sha256": sha256_path(parsed_path) if parsed_path.exists() else "",
        "normalized_candidate_path": str(normalized_path),
        "normalized_candidate_sha256": sha256_path(normalized_path) if normalized_path.exists() else "",
        "transformation_log_path": str(transform_path),
        "compile_status": "compile_ready" if cls == "natural_minimally_normalized_ghidra_output" else status,
        "execution_status": "pending_exact_label",
    }


def make_candidate_dirs(work: Path, candidate_id: str) -> dict[str, Path]:
    root = work / safe_name(candidate_id)
    dirs = {name: root / name for name in ["original", "wrapper", "binary", "raw", "parsed", "normalized", "logs"]}
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
    selected_metadata: dict[str, dict[str, int]],
    fixture_rows: list[dict[str, Any]],
    natural_candidates: list[dict[str, Any]],
    controlled_candidates: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    command_log: Path,
    descriptive: dict[str, Any],
) -> dict[str, Any]:
    artifact_paths = [
        "docs/paper_agent/frozen_holdout_preregistration_v4.md",
        "docs/paper_agent/holdout_feasibility_amendment.md",
        "docs/paper_agent/holdout_mutation_grammar.md",
        "results/decompile_faithfulness/holdout_project_manifest.json",
        "results/decompile_faithfulness/holdout_project_manifest_v2.json",
        "results/decompile_faithfulness/holdout_eligibility_census.csv",
        "results/decompile_faithfulness/holdout_exclusions.jsonl",
        "results/decompile_faithfulness/holdout_sampling_frame.csv",
        "results/decompile_faithfulness/holdout_sampling_frame_v2.csv",
        "results/decompile_faithfulness/holdout_selected_functions.csv",
        "results/decompile_faithfulness/holdout_fixtures.jsonl",
        "results/decompile_faithfulness/holdout_candidate_manifest.jsonl",
        "results/decompile_faithfulness/holdout_controlled_candidates.jsonl",
        "results/decompile_faithfulness/holdout_exact_labels.jsonl",
        "results/decompile_faithfulness/holdout_label_summary.csv",
        "results/decompile_faithfulness/holdout_execution_log.jsonl",
        "results/decompile_faithfulness/holdout_pre_auditor_descriptive_analysis.json",
        "results/decompile_faithfulness/holdout_candidate_artifacts",
        "figures/data/holdout_dataset_flow.json",
        "paper/tables/holdout_acquisition.tex",
    ]
    log_text = command_log.read_text(encoding="utf-8") if command_log.exists() else ""
    method_hash_status = method_freeze_hash_status(repo_root)
    return {
        "schema_version": 2,
        "created_at_utc": now_utc(),
        "status": status,
        "method_freeze_commit": METHOD_FREEZE_COMMIT,
        "phase1b_correction_commit": PHASE1B_CORRECTION_COMMIT,
        "phase1c_census_commit": PHASE1C_CENSUS_COMMIT,
        "phase1c_census_seal_hash": PHASE1C_CENSUS_SEAL_HASH,
        "phase1d_amendment_commit": PHASE1D_AMENDMENT_COMMIT,
        "current_acquisition_commit_context": git_at(repo_root, ["rev-parse", "HEAD"]),
        "final_auditor_invoked": False,
        "prohibited_final_method_functions_confirmed_absent_from_execution_log": {
            name: name not in log_text for name in PROHIBITED_FINAL_METHOD_FUNCTIONS
        },
        "prohibited_final_method_imports_or_calls_absent_from_runner_ast": final_method_ast_guard(repo_root),
        "method_affecting_hashes_unchanged": method_hash_status,
        "natural_and_controlled_strata_separate": strata_separate(natural_candidates, controlled_candidates),
        "labels_produced_by_complete_exact_domain_enumeration": all(
            label["label"] == "non_evaluable" or label["reason"] == "exact_domain_exhaustive_comparison"
            for label in labels
        ),
        "project_repositories": project_records,
        "acquisition_errors": acquisition_errors,
        "sampling_seed": ACQUISITION_SEED,
        "fixture_seed": FIXTURE_SEED,
        "mutation_seed": MUTATION_SEED,
        "exact_domain_definitions": domain_definition_text(),
        "eligibility_counts_by_project": census_rows,
        "selected_functions": [
            selected_function_row_v2(function, project_records, selected_metadata) for function in selected
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
        "pre_auditor_descriptive_analysis": descriptive,
        "artifact_hashes": artifact_hashes(repo_root, artifact_paths),
        "execution_log_path": str(command_log),
        "execution_log_sha256": sha256_path(command_log) if command_log.exists() else "",
    }


def selected_function_row(function: FunctionCandidate) -> dict[str, Any]:
    return {
        "function_id": function.function_id,
        "project": function.project,
        "source_file": function.source_path,
        "function_name": function.function_name,
        "ordinal": function.ordinal,
        "signature": function_signature(function),
        "return_type": function.return_type,
        "argument_types": ";".join(param.type_text for param in function.params),
        "declared_exact_domain": json.dumps(domain_spec(function), sort_keys=True),
        "domain_size": function.domain_size,
        "source_file_sha256": function.source_file_sha256,
        "source_sha256": function.source_sha256,
    }


def selected_function_row_v2(
    function: FunctionCandidate,
    project_records: list[dict[str, Any]],
    selection_metadata: dict[str, dict[str, int]],
) -> dict[str, Any]:
    project_commits = {record["project"]: record.get("pinned_commit", "") for record in project_records}
    metadata = selection_metadata.get(function.function_id, {})
    row = selected_function_row(function)
    row.update(
        {
            "pinned_project_commit": project_commits.get(function.project, ""),
            "selection_rank_within_project": metadata.get("selection_rank_within_project", ""),
            "selection_round": metadata.get("selection_round", ""),
            "acquisition_seed": metadata.get("acquisition_seed", ACQUISITION_SEED),
        }
    )
    return row


def function_signature(function: FunctionCandidate) -> str:
    params = ", ".join(f"{param.type_text} {param.name}" for param in function.params)
    return f"{function.return_type} {function.function_name}({params})"


def domain_spec(function: FunctionCandidate) -> list[dict[str, Any]]:
    specs = []
    for param in function.params:
        domain = declared_domain(param.type_text)
        values = list(domain or [])
        specs.append(
            {
                "name": param.name,
                "type": param.type_text,
                "count": len(values),
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "values": values,
            }
        )
    return specs


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


def write_project_manifest_v2(repo_root: Path, records: list[dict[str, Any]], errors: list[dict[str, Any]]) -> None:
    write_json(
        repo_root / "results/decompile_faithfulness/holdout_project_manifest_v2.json",
        {
            "schema_version": 2,
            "created_at_utc": now_utc(),
            "method_freeze_commit": METHOD_FREEZE_COMMIT,
            "phase1b_correction_commit": PHASE1B_CORRECTION_COMMIT,
            "phase1c_census_commit": PHASE1C_CENSUS_COMMIT,
            "phase1c_census_seal_hash": PHASE1C_CENSUS_SEAL_HASH,
            "phase1d_amendment_commit": PHASE1D_AMENDMENT_COMMIT,
            "project_cap": PROJECT_CAP,
            "selected_function_target": MAX_SELECTED_FUNCTIONS,
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
        "function_id", "project", "source_file", "function_name", "ordinal", "signature", "return_type",
        "argument_types", "declared_exact_domain", "domain_size", "source_file_sha256", "source_sha256",
    ])


def write_sampling_frame_v2(
    repo_root: Path,
    candidates: list[FunctionCandidate],
    project_records: list[dict[str, Any]],
    selection_metadata: dict[str, dict[str, int]],
) -> None:
    rows = [selected_function_row_v2(item, project_records, selection_metadata) for item in candidates]
    write_csv(repo_root / "results/decompile_faithfulness/holdout_sampling_frame_v2.csv", rows, [
        "project", "pinned_project_commit", "source_file", "function_name", "function_id", "ordinal",
        "signature", "declared_exact_domain", "domain_size", "source_file_sha256", "source_sha256",
        "selection_rank_within_project", "selection_round", "acquisition_seed",
    ])


def write_selected_functions(
    repo_root: Path,
    selected: list[FunctionCandidate],
    project_records: list[dict[str, Any]],
    selection_metadata: dict[str, dict[str, int]],
) -> None:
    rows = [selected_function_row_v2(item, project_records, selection_metadata) for item in selected]
    write_csv(repo_root / "results/decompile_faithfulness/holdout_selected_functions.csv", rows, [
        "project", "pinned_project_commit", "source_file", "function_name", "function_id", "ordinal",
        "signature", "declared_exact_domain", "domain_size", "source_file_sha256", "source_sha256",
        "selection_rank_within_project", "selection_round", "acquisition_seed",
    ])


def write_label_summary(path: Path, rows: list[dict[str, Any]]) -> None:
    write_csv(path, rows, ["candidate_stratum", "label", "count"])


def label_counts_by_stratum(labels: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for row in labels:
        stratum = row["candidate_stratum"]
        result.setdefault(stratum, {})
        result[stratum][row["label"]] = result[stratum].get(row["label"], 0) + 1
    return result


def is_compile_ready(candidate: dict[str, Any], labels_by_candidate: dict[str, dict[str, Any]]) -> bool:
    if str(candidate.get("candidate_status", candidate.get("candidate_class", ""))).startswith("non_evaluable_"):
        return False
    label = labels_by_candidate.get(candidate["candidate_id"])
    if not label:
        return False
    return label["label"] != "non_evaluable"


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
    labels_by_candidate = {row["candidate_id"]: row for row in labels}
    natural_ready = sum(1 for row in natural_candidates if is_compile_ready(row, labels_by_candidate))
    controlled_ready = sum(1 for row in controlled_candidates if is_compile_ready(row, labels_by_candidate))
    counts = label_counts_by_stratum(labels)
    natural_counts = counts.get("natural_ghidra", {})
    controlled_counts = counts.get("controlled_stress", {})
    non_evaluable = sum(1 for row in labels if row["label"] == "non_evaluable")
    text = f"""\\begin{{tabular}}{{lrrrrrrrrrrrr}}
\\toprule
Status & Projects & Eligible functions & Selected functions & Natural attempts & Natural compile-ready & Natural semantic wrong & Natural no-mismatch & Controlled attempts & Controlled compile-ready & Controlled semantic wrong & Controlled no-mismatch & Non-evaluable \\\\
\\midrule
Sealed exact-domain holdout & {projects} & {eligible} & {len(selected)} & {len(natural_candidates)} & {natural_ready} & {natural_counts.get('semantic_wrong', 0)} & {natural_counts.get('no_mismatch_under_exact_holdout_domain', 0)} & {len(controlled_candidates)} & {controlled_ready} & {controlled_counts.get('semantic_wrong', 0)} & {controlled_counts.get('no_mismatch_under_exact_holdout_domain', 0)} & {non_evaluable} \\\\
\\bottomrule
\\end{{tabular}}
"""
    (repo_root / "paper/tables/holdout_acquisition.tex").write_text(text, encoding="utf-8")


def write_handoff(repo_root: Path, manifest: dict[str, Any], seal_hash: str, status: str) -> None:
    selected = manifest["selected_functions"]
    descriptive = manifest["pre_auditor_descriptive_analysis"]
    labels = manifest["pre_auditor_descriptive_analysis"]["labels_by_stratum"]
    natural_counts = labels.get("natural_ghidra", {})
    controlled_counts = labels.get("controlled_stress", {})
    exhaustive_execution_count = sum(
        int(row.get("exact_domain_size", 0))
        for row in read_jsonl(repo_root / "results/decompile_faithfulness/holdout_exact_labels.jsonl")
        if row.get("label") != "non_evaluable"
    )
    text = f"""# Holdout Generation Seal Handoff

## Git

- Branch: `{git_at(repo_root, ["branch", "--show-current"])}`
- HEAD at generation: `{git_at(repo_root, ["rev-parse", "HEAD"])}`
- Amendment commit: `{PHASE1D_AMENDMENT_COMMIT}`
- Method freeze commit: `{METHOD_FREEZE_COMMIT}`
- Phase 1b correction commit: `{PHASE1B_CORRECTION_COMMIT}`
- Phase 1c census commit: `{PHASE1C_CENSUS_COMMIT}`
- Phase 1c census seal hash: `{PHASE1C_CENSUS_SEAL_HASH}`
- Final holdout seal hash: `{seal_hash}`

## Seeds And Domains

- Sampling seed: `{ACQUISITION_SEED}`
- Fixture seed: `{FIXTURE_SEED}`
- Mutation seed: `{MUTATION_SEED}`
- Exact domains: `{json.dumps(domain_definition_text(), sort_keys=True)}`

## Selected Functions

- Selected-function count: `{len(selected)}`
- Selected-function counts by project: `{json.dumps(descriptive['selected_functions_by_project'], sort_keys=True)}`

## Candidate And Label Counts

- Natural candidate attempts: `{manifest['natural_candidate_count']}`
- Natural compile-ready yield: `{descriptive['natural_compile_ready_yield']}`
- Natural semantic-wrong count: `{natural_counts.get('semantic_wrong', 0)}`
- Controlled candidate attempts: `{manifest['controlled_candidate_count']}`
- Controlled compile-ready yield: `{descriptive['controlled_compile_ready_yield']}`
- Controlled semantic-wrong count: `{controlled_counts.get('semantic_wrong', 0)}`
- Natural exact-domain no-mismatch count: `{natural_counts.get('no_mismatch_under_exact_holdout_domain', 0)}`
- Controlled exact-domain no-mismatch count: `{controlled_counts.get('no_mismatch_under_exact_holdout_domain', 0)}`
- Exact-label count: `{manifest['label_count']}`
- Non-evaluable counts and reasons: `{json.dumps(descriptive['non_evaluable_counts_and_reasons'], sort_keys=True)}`
- Exclusion count: `{manifest['exclusion_count']}`
- Sampling capacity under project cap: `{manifest['sampling_capacity_under_project_cap']}`
- Exhaustive execution count: `{exhaustive_execution_count}`

## Source-Literal Prevalence

```json
{json.dumps(descriptive['source_character_literal_prevalence'], indent=2, sort_keys=True)}
```

## Seal

- Status: `{status}`
- Seal manifest hash: `{seal_hash}`
- Final auditor invoked: `False`
- Prohibited final-method functions absent from execution log: `{json.dumps(manifest['prohibited_final_method_functions_confirmed_absent_from_execution_log'], sort_keys=True)}`
- Final-method imports/calls absent from runner AST: `{json.dumps(manifest['prohibited_final_method_imports_or_calls_absent_from_runner_ast'], sort_keys=True)}`
- Method-affecting hashes unchanged: `{manifest['method_affecting_hashes_unchanged']['all_method_files_current_match_freeze']}`
- Natural and controlled strata separate: `{manifest['natural_and_controlled_strata_separate']}`
- Labels produced by complete exact-domain enumeration: `{manifest['labels_produced_by_complete_exact_domain_enumeration']}`

## Tests Run

- `python -m py_compile analysis/decompile_faithfulness/holdout_acquisition.py`
- `python -m unittest analysis.decompile_faithfulness.tests.test_probe_order_freeze analysis.decompile_faithfulness.tests.test_submission_evidence_corrections analysis.decompile_faithfulness.tests.test_holdout_acquisition`

## Review Readiness

The complete holdout is ready for independent seal review if status is `sealed_after_exact_labeling` and the seal confirmations above remain true. No final-auditor detection results are included.
"""
    (repo_root / "docs/paper_agent/holdout_generation_seal_handoff.md").write_text(text, encoding="utf-8")


def domain_definition_text() -> dict[str, str]:
    return {
        "char_signed_model": "[0, 127]",
        "unsigned_char": "[0, 127]",
        "bool": "{0, 1}",
        "signed_short_int_long_like": "[-32, 31]",
        "unsigned_short_int_long_like": "[0, 63]",
        "two_argument_rule": "complete Cartesian product",
    }


def descriptive_analysis(
    selected: list[FunctionCandidate],
    natural_candidates: list[dict[str, Any]],
    controlled_candidates: list[dict[str, Any]],
    labels: list[dict[str, Any]],
) -> dict[str, Any]:
    labels_by_candidate = {row["candidate_id"]: row for row in labels}
    counts = label_counts_by_stratum(labels)
    non_evaluable_reasons = count_by(row["reason"] for row in labels if row["label"] == "non_evaluable")
    densities = []
    for row in labels:
        if row["label"] == "non_evaluable":
            continue
        domain_size = int(row["exact_domain_size"])
        density = (int(row["total_mismatching_input_count"]) / domain_size) if domain_size else 0.0
        densities.append({"candidate_id": row["candidate_id"], "candidate_stratum": row["candidate_stratum"], "density": density})
    source_literal_counts = {
        function.function_id: count_c_char_literals(function.source)
        for function in selected
    }
    natural_wrong = counts.get("natural_ghidra", {}).get("semantic_wrong", 0)
    return {
        "selected_functions_by_project": count_by(function.project for function in selected),
        "signature_distribution": count_by(function_signature(function) for function in selected),
        "domain_size_distribution": count_by(str(function.domain_size) for function in selected),
        "argument_type_distribution": count_by(";".join(param.type_text for param in function.params) for function in selected),
        "natural_candidate_attempts": len(natural_candidates),
        "natural_compile_ready_yield": sum(1 for row in natural_candidates if is_compile_ready(row, labels_by_candidate)),
        "natural_semantic_wrong_yield": natural_wrong,
        "controlled_candidate_attempts": len(controlled_candidates),
        "controlled_compile_ready_yield": sum(1 for row in controlled_candidates if is_compile_ready(row, labels_by_candidate)),
        "controlled_semantic_wrong_yield": counts.get("controlled_stress", {}).get("semantic_wrong", 0),
        "no_mismatch_counts_by_stratum": {
            stratum: values.get("no_mismatch_under_exact_holdout_domain", 0)
            for stratum, values in counts.items()
        },
        "non_evaluable_counts_and_reasons": non_evaluable_reasons,
        "mismatch_domain_density_distribution": density_summary(densities),
        "source_character_literal_prevalence": {
            "selected_function_count": len(selected),
            "functions_with_char_literals": sum(1 for count in source_literal_counts.values() if count > 0),
            "total_char_literals": sum(source_literal_counts.values()),
            "per_function": source_literal_counts,
            "descriptive_only": True,
        },
        "natural_ghidra_semantic_errors_exist": natural_wrong > 0,
        "labels_by_stratum": counts,
    }


def density_summary(densities: list[dict[str, Any]]) -> dict[str, Any]:
    buckets = {
        "0": 0,
        "(0,0.01]": 0,
        "(0.01,0.10]": 0,
        "(0.10,0.50]": 0,
        "(0.50,1.0]": 0,
    }
    values = [float(item["density"]) for item in densities]
    for value in values:
        if value == 0:
            buckets["0"] += 1
        elif value <= 0.01:
            buckets["(0,0.01]"] += 1
        elif value <= 0.10:
            buckets["(0.01,0.10]"] += 1
        elif value <= 0.50:
            buckets["(0.10,0.50]"] += 1
        else:
            buckets["(0.50,1.0]"] += 1
    return {
        "count": len(values),
        "min": min(values) if values else None,
        "max": max(values) if values else None,
        "buckets": buckets,
    }


def count_c_char_literals(source: str) -> int:
    return len(re.findall(r"'(?:\\.|[^\\'\n])+'", source))


def write_dataset_flow(
    repo_root: Path,
    census_rows: list[dict[str, Any]],
    selected: list[FunctionCandidate],
    natural_candidates: list[dict[str, Any]],
    controlled_candidates: list[dict[str, Any]],
    labels: list[dict[str, Any]],
) -> None:
    labels_by_candidate = {row["candidate_id"]: row for row in labels}
    counts = label_counts_by_stratum(labels)
    payload = {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "phase": "phase1d_holdout_generation_and_seal",
        "projects_with_eligible_functions": sum(1 for row in census_rows if int(row["final_eligible_functions"]) > 0),
        "eligible_functions": sum(int(row["final_eligible_functions"]) for row in census_rows),
        "selected_functions": len(selected),
        "natural_candidate_attempts": len(natural_candidates),
        "natural_compile_ready": sum(1 for row in natural_candidates if is_compile_ready(row, labels_by_candidate)),
        "natural_semantic_wrong": counts.get("natural_ghidra", {}).get("semantic_wrong", 0),
        "natural_no_mismatch": counts.get("natural_ghidra", {}).get("no_mismatch_under_exact_holdout_domain", 0),
        "controlled_candidate_attempts": len(controlled_candidates),
        "controlled_compile_ready": sum(1 for row in controlled_candidates if is_compile_ready(row, labels_by_candidate)),
        "controlled_semantic_wrong": counts.get("controlled_stress", {}).get("semantic_wrong", 0),
        "controlled_no_mismatch": counts.get("controlled_stress", {}).get("no_mismatch_under_exact_holdout_domain", 0),
        "non_evaluable": sum(1 for row in labels if row["label"] == "non_evaluable"),
    }
    write_json(repo_root / "figures/data/holdout_dataset_flow.json", payload)


def artifact_hashes(repo_root: Path, artifact_paths: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for rel in artifact_paths:
        path = repo_root / rel
        if not path.exists():
            continue
        if path.is_dir():
            result[rel] = directory_hash(path)
        else:
            result[rel] = {"type": "file", "sha256": sha256_path(path)}
    return result


def directory_hash(path: Path) -> dict[str, Any]:
    files = []
    digest_lines = []
    for item in sorted(child for child in path.rglob("*") if child.is_file()):
        rel = item.relative_to(path).as_posix()
        digest = sha256_path(item)
        files.append({"path": rel, "sha256": digest})
        digest_lines.append(f"{rel}\0{digest}")
    return {
        "type": "directory",
        "file_count": len(files),
        "tree_sha256": sha256_text("\n".join(digest_lines)),
        "files": files,
    }


def method_freeze_hash_status(repo_root: Path) -> dict[str, Any]:
    integrity_path = repo_root / "analysis/decompile_faithfulness/method_freeze_integrity.json"
    if not integrity_path.exists():
        return {"available": False, "all_method_files_current_match_freeze": False, "sources": []}
    payload = json.loads(integrity_path.read_text(encoding="utf-8"))
    sources = []
    ok = True
    for item in payload.get("method_affecting_sources", []):
        path = repo_root / item["path"]
        current = sha256_path(path) if path.exists() else ""
        matches = bool(path.exists() and current == item.get("method_freeze_sha256"))
        ok = ok and matches
        sources.append(
            {
                "path": item["path"],
                "method_freeze_sha256": item.get("method_freeze_sha256", ""),
                "current_sha256": current,
                "unchanged": matches,
            }
        )
    return {
        "available": True,
        "all_method_files_current_match_freeze": ok,
        "sources": sources,
    }


def final_method_ast_guard(repo_root: Path) -> dict[str, bool]:
    path = repo_root / "analysis/decompile_faithfulness/holdout_acquisition.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    forbidden_modules = {
        "analysis.decompile_faithfulness.run_phase18_source_literal_char_policy",
        "analysis.decompile_faithfulness.run_phase11_input_ordering",
    }
    forbidden_calls = set(PROHIBITED_FINAL_METHOD_FUNCTIONS)
    module_absent = True
    call_absent = True
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module in forbidden_modules:
            module_absent = False
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in forbidden_modules:
                    module_absent = False
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in forbidden_calls:
                call_absent = False
            if isinstance(node.func, ast.Attribute) and node.func.attr in forbidden_calls:
                call_absent = False
    return {"forbidden_imports_absent": module_absent, "forbidden_calls_absent": call_absent}


def strata_separate(natural_candidates: list[dict[str, Any]], controlled_candidates: list[dict[str, Any]]) -> bool:
    return (
        all(row.get("candidate_stratum") == "natural_ghidra" for row in natural_candidates)
        and all(row.get("candidate_stratum") == "controlled_stress" for row in controlled_candidates)
        and not ({row["candidate_id"] for row in natural_candidates} & {row["candidate_id"] for row in controlled_candidates})
    )


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


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
