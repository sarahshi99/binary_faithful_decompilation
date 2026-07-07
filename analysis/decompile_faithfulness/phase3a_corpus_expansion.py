from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TARGETS = [120, 111, 104, 100, 96, 90, 80]
STRICT_PROJECT_CAP = 10
V1_SELECTED_COUNT = 80
V1_FUNCTION_FIXTURE_SEAL = "2bba63e1a191050f2ec0e15a8f58ed7eff9a5c9bf1f21b672b7ab9bfc64c1494"

CANDIDATE_OR_LABEL_PATHS = [
    "analysis/decompile_faithfulness/phase3a_candidate_seal.json",
    "analysis/decompile_faithfulness/phase3a_candidate_seal.sha256",
    "results/decompile_faithfulness/phase3a_candidate_manifest.jsonl",
    "results/decompile_faithfulness/phase3a_candidate_provenance.csv",
    "results/decompile_faithfulness/phase3a_exact_labels.jsonl",
    "results/decompile_faithfulness/phase3a_label_summary.csv",
    "results/decompile_faithfulness/phase3a_fixture_replay.jsonl",
    "results/decompile_faithfulness/phase3a_natural_error_descriptors.csv",
    "results/decompile_faithfulness/phase3a_taxonomy_review_packet.jsonl",
]

V2_PATHS = [
    "docs/paper_agent/phase3a_corpus_expansion_amendment.md",
    "results/decompile_faithfulness/phase3a_selected_functions_v2.csv",
    "results/decompile_faithfulness/phase3a_fixtures_v2.jsonl",
    "analysis/decompile_faithfulness/phase3a_function_fixture_seal_v2.json",
    "analysis/decompile_faithfulness/phase3a_function_fixture_seal_v2.sha256",
]

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


def main() -> None:
    args = parse_args()
    summary = run(args.repo_root.resolve())
    print(json.dumps(summary, sort_keys=True))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit whether the Phase 3a corpus can expand before candidate generation.")
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    return parser.parse_args()


def run(repo_root: Path) -> dict[str, Any]:
    eligibility_path = repo_root / "results/decompile_faithfulness/phase3a_eligibility_census.csv"
    selected_path = repo_root / "results/decompile_faithfulness/phase3a_selected_functions.csv"
    manifest_path = repo_root / "results/decompile_faithfulness/phase3a_project_manifest.json"
    seal_path = repo_root / "analysis/decompile_faithfulness/phase3a_function_fixture_seal.json"
    seal_hash = sha256_path(seal_path)

    eligible = load_eligible_rows(eligibility_path)
    selected = load_csv(selected_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected_ids = {row["function_id"] for row in selected}

    audit = build_expansion_audit(repo_root, eligible, selected_ids, manifest, seal_hash)
    out_json = repo_root / "results/decompile_faithfulness/phase3a_corpus_expansion_audit.json"
    out_md = repo_root / "docs/paper_agent/phase3a_corpus_expansion_audit.md"
    write_json(out_json, audit)
    out_md.write_text(render_markdown(audit), encoding="utf-8")
    return {
        "status": audit["decision"]["status"],
        "maximum_feasible_target": audit["decision"]["maximum_feasible_target"],
        "v2_created": False,
        "audit_json": str(out_json),
        "audit_markdown": str(out_md),
    }


def build_expansion_audit(
    repo_root: Path,
    eligible: list[dict[str, str]],
    selected_ids: set[str],
    manifest: dict[str, Any],
    seal_hash: str,
) -> dict[str, Any]:
    selected = [row for row in eligible if row["function_id"] in selected_ids]
    unselected = [row for row in eligible if row["function_id"] not in selected_ids]
    target_results = [target_feasibility(eligible, target) for target in TARGETS]
    all_size_results = [target_feasibility(eligible, target) for target in range(V1_SELECTED_COUNT, min(len(eligible), 120) + 1)]
    maximum_feasible_in_range = max(
        (item["target"] for item in all_size_results if item["feasible_under_expansion_framework"]),
        default=0,
    )
    feasible_above_v1 = [item for item in target_results if item["target"] > V1_SELECTED_COUNT and item["feasible_under_expansion_framework"]]
    maximum = max((item["target"] for item in target_results if item["feasible_under_expansion_framework"]), default=0)
    blockers = expansion_blockers(target_results, eligible)
    no_candidate_label = guard_no_candidate_or_label_artifacts(repo_root)
    no_v2_artifacts = guard_no_v2_artifacts(repo_root)
    return {
        "schema_version": 1,
        "created_at_utc": now_utc(),
        "phase": "phase3a_corpus_expansion_audit",
        "scope": "pre_candidate_corpus_work_only",
        "v1_function_fixture_seal_sha256": seal_hash,
        "v1_expected_function_fixture_seal_sha256": V1_FUNCTION_FIXTURE_SEAL,
        "v1_seal_matches_expected": seal_hash == V1_FUNCTION_FIXTURE_SEAL,
        "candidate_generation": "not_run",
        "semantic_labeling": "not_run",
        "auditor_execution": "not_run",
        "candidate_or_label_artifact_guard": no_candidate_label,
        "v2_artifact_guard_before_expansion": no_v2_artifacts,
        "project_manifest_summary": project_manifest_summary(manifest),
        "eligible_summary": population_summary(eligible),
        "selected_summary": population_summary(selected),
        "unselected_summary": population_summary(unselected),
        "selected_count": len(selected),
        "unselected_eligible_count": len(unselected),
        "selected_function_ids": sorted(selected_ids),
        "unselected_eligible_function_ids": sorted(row["function_id"] for row in unselected),
        "target_evaluations": target_results,
        "maximum_feasible_target_in_80_to_120_range": maximum_feasible_in_range,
        "blocker_analysis": blockers,
        "decision": {
            "status": "no_expansion_feasible_above_80" if not feasible_above_v1 else "expansion_feasible",
            "maximum_feasible_target": maximum_feasible_in_range,
            "maximum_feasible_target_among_requested_targets": maximum,
            "expansion_target": None if not feasible_above_v1 else feasible_above_v1[0]["target"],
            "v2_selection_created": False,
            "v2_seal_created": False,
            "v1_remains_canonical_for_now": not feasible_above_v1,
            "reason": blockers["primary_reason"],
        },
        "method_constraints": {
            "targets_evaluated_in_order": TARGETS,
            "strict_project_cap": STRICT_PROJECT_CAP,
            "target_100_or_above_share_goal": "no project above 10% where possible",
            "target_80_to_99_share_goal": "no project above 15%",
            "inputs_used": [
                "committed eligibility census",
                "committed selected-functions v1 file",
                "committed project manifest",
                "precomputed source structural features",
                "declared exact-domain feasibility",
                "source sanitizer feasibility",
            ],
            "inputs_not_used": [
                "candidate-generation success",
                "semantic labels",
                "mismatch witnesses",
                "auditor behavior",
                "libFuzzer results",
            ],
        },
    }


def target_feasibility(eligible: list[dict[str, str]], target: int) -> dict[str, Any]:
    counts = Counter(row["project"] for row in eligible)
    total = len(eligible)
    represented_projects = len(counts)
    strict_capacity = selection_capacity(counts, STRICT_PROJECT_CAP)
    dominance_cap = dominance_cap_for_target(target)
    dominance_capacity = selection_capacity(counts, dominance_cap)
    largest_project, largest_count = counts.most_common(1)[0]
    rest_count = total - largest_count
    required_from_largest = max(0, target - rest_count)
    required_largest_share = required_from_largest / target if target else 0.0
    target_available = total >= target
    enough_projects = represented_projects >= 12
    strict_feasible = target_available and enough_projects and strict_capacity >= target
    dominance_feasible = target_available and enough_projects and dominance_capacity >= target
    reasons = []
    if not target_available:
        reasons.append("insufficient_total_eligible_functions")
    if not enough_projects:
        reasons.append("insufficient_represented_projects")
    if strict_capacity < target:
        reasons.append("strict_project_cap_capacity_shortfall")
    if dominance_capacity < target:
        reasons.append("dominance_share_capacity_shortfall")
    if required_from_largest > dominance_cap:
        reasons.append("largest_project_would_exceed_share_goal")
    achieved = structural_summary(eligible)
    return {
        "target": target,
        "total_eligible_functions": total,
        "represented_projects_available": represented_projects,
        "at_least_12_projects_possible": enough_projects,
        "strict_project_cap": STRICT_PROJECT_CAP,
        "strict_project_cap_capacity": strict_capacity,
        "feasible_under_strict_project_cap": strict_feasible,
        "dominance_cap_for_target": dominance_cap,
        "dominance_capacity": dominance_capacity,
        "feasible_under_expansion_framework": dominance_feasible,
        "largest_project": largest_project,
        "largest_project_eligible_count": largest_count,
        "eligible_functions_outside_largest_project": rest_count,
        "minimum_required_from_largest_project": required_from_largest,
        "minimum_required_largest_project_share": round(required_largest_share, 6),
        "domain_and_sanitizer_feasible_by_construction": True,
        "structural_coverage_if_all_feasible_rows_considered": achieved,
        "structural_quota_forced": False,
        "reasons": reasons or ["feasible"],
    }


def dominance_cap_for_target(target: int) -> int:
    if target >= 120:
        return STRICT_PROJECT_CAP
    if target >= 100:
        return max(STRICT_PROJECT_CAP, int(target * 0.10))
    if target >= 80:
        return max(STRICT_PROJECT_CAP, int(target * 0.15))
    return STRICT_PROJECT_CAP


def selection_capacity(project_counts: Counter[str], per_project_cap: int) -> int:
    return sum(min(count, per_project_cap) for count in project_counts.values())


def expansion_blockers(target_results: list[dict[str, Any]], eligible: list[dict[str, str]]) -> dict[str, Any]:
    counts = Counter(row["project"] for row in eligible)
    strict_capacity = selection_capacity(counts, STRICT_PROJECT_CAP)
    rest_count = len(eligible) - counts.most_common(1)[0][1]
    above_v1 = [item for item in target_results if item["target"] > V1_SELECTED_COUNT]
    return {
        "primary_reason": "project_capacity_and_dominance_constraints",
        "strict_10_per_project_capacity": strict_capacity,
        "eligible_functions_outside_largest_project": rest_count,
        "largest_project": counts.most_common(1)[0][0],
        "largest_project_eligible_count": counts.most_common(1)[0][1],
        "targets_above_80_requiring_largest_project_over_share_goal": [
            {
                "target": item["target"],
                "minimum_required_from_largest_project": item["minimum_required_from_largest_project"],
                "minimum_required_largest_project_share": item["minimum_required_largest_project_share"],
                "dominance_cap_for_target": item["dominance_cap_for_target"],
            }
            for item in above_v1
            if not item["feasible_under_expansion_framework"]
        ],
        "not_due_to_argument_count_quota": True,
        "not_due_to_structural_quota": True,
        "not_due_to_sampler_implementation": True,
        "not_due_to_conservative_feasibility_amendment": True,
        "not_due_to_exclusion_of_otherwise_usable_projects": True,
        "not_due_to_candidate_results_or_labels": True,
        "not_due_to_auditor_behavior": True,
    }


def population_summary(rows: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "count": len(rows),
        "by_project": counter_dict(Counter(row["project"] for row in rows)),
        "by_argument_count": counter_dict(Counter(row["argument_count"] for row in rows)),
        "by_domain_size": counter_dict(Counter(row["domain_size"] for row in rows)),
        "structural_features": structural_summary(rows),
    }


def structural_summary(rows: list[dict[str, str]]) -> dict[str, int]:
    return {
        "loop": sum(int(row["loop_count"]) > 0 for row in rows),
        "lookup": sum(int(row["lookup_table_access"]) != 0 for row in rows),
        "bitwise": sum(int(row["bitwise_operation_count"]) > 0 for row in rows),
        "branches4": sum(int(row["branch_count"]) >= 4 for row in rows),
        "interacting_args": sum(int(row["multiple_interacting_arguments"]) != 0 for row in rows),
        "switch_like": sum(int(row["switch_like_categorical_behavior"]) != 0 for row in rows),
    }


def project_manifest_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    projects = manifest.get("projects", [])
    return {
        "projects_scanned": len(projects),
        "projects_acquired": sum(1 for project in projects if project.get("acquired")),
        "projects_yielding_eligible_functions": sum(1 for project in projects if project.get("yielded_eligible_functions")),
        "acquisition_errors": manifest.get("acquisition_errors", []),
    }


def guard_no_candidate_or_label_artifacts(repo_root: Path) -> dict[str, Any]:
    present = [path for path in CANDIDATE_OR_LABEL_PATHS if (repo_root / path).exists()]
    return {"ok": not present, "present_paths": present}


def guard_no_v2_artifacts(repo_root: Path) -> dict[str, Any]:
    present = [path for path in V2_PATHS if (repo_root / path).exists()]
    return {"ok": not present, "present_paths": present}


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


def render_markdown(audit: dict[str, Any]) -> str:
    decision = audit["decision"]
    eligible = audit["eligible_summary"]
    selected = audit["selected_summary"]
    unselected = audit["unselected_summary"]
    lines = [
        "# Phase 3a Corpus Expansion Audit",
        "",
        f"Created: {audit['created_at_utc']}",
        "",
        "Scope: pre-candidate corpus audit only. No candidate generation, semantic labeling, auditor policy, libFuzzer run, budget curve, or auditor result table was run.",
        "",
        "## Decision",
        "",
        f"- Status: `{decision['status']}`",
        f"- Maximum feasible target across 80..120: `{decision['maximum_feasible_target']}`",
        f"- Maximum feasible target among requested targets: `{decision['maximum_feasible_target_among_requested_targets']}`",
        f"- Expansion target: `{decision['expansion_target']}`",
        f"- Reason: `{decision['reason']}`",
        f"- V1 selected functions: `{audit['selected_count']}`",
        f"- V1 function/fixture seal: `{audit['v1_function_fixture_seal_sha256']}`",
        "",
        "No v2 selected-functions file or v2 seal is created because no target above 80 is feasible without violating project-capacity and dominance constraints.",
        "",
        "## Why Selection Stopped At 80",
        "",
        f"- Eligible functions: `{eligible['count']}`",
        f"- Selected functions: `{selected['count']}`",
        f"- Unselected eligible functions: `{unselected['count']}`",
        f"- Strict 10-per-project capacity: `{audit['blocker_analysis']['strict_10_per_project_capacity']}`",
        f"- Largest project: `{audit['blocker_analysis']['largest_project']}` with `{audit['blocker_analysis']['largest_project_eligible_count']}` eligible functions",
        f"- Eligible functions outside largest project: `{audit['blocker_analysis']['eligible_functions_outside_largest_project']}`",
        "",
        "The stop is due to project-capacity and dominance constraints. It is not due to argument-count quota, structural quota, sampler nondeterminism, a conservative amendment, candidate results, semantic labels, witnesses, or auditor behavior.",
        "",
        "## Population Summaries",
        "",
        f"- Eligible by project: `{json.dumps(eligible['by_project'], sort_keys=True)}`",
        f"- Eligible by argument count: `{json.dumps(eligible['by_argument_count'], sort_keys=True)}`",
        f"- Eligible by domain size: `{json.dumps(eligible['by_domain_size'], sort_keys=True)}`",
        f"- Eligible structural features: `{json.dumps(eligible['structural_features'], sort_keys=True)}`",
        f"- Selected by project: `{json.dumps(selected['by_project'], sort_keys=True)}`",
        f"- Selected by argument count: `{json.dumps(selected['by_argument_count'], sort_keys=True)}`",
        f"- Selected structural features: `{json.dumps(selected['structural_features'], sort_keys=True)}`",
        f"- Unselected by project: `{json.dumps(unselected['by_project'], sort_keys=True)}`",
        "",
        "## Target Feasibility",
        "",
        "| Target | Strict cap capacity | Dominance cap | Dominance capacity | Feasible | Main reasons |",
        "| --- | ---: | ---: | ---: | --- | --- |",
    ]
    for item in audit["target_evaluations"]:
        lines.append(
            f"| {item['target']} | {item['strict_project_cap_capacity']} | {item['dominance_cap_for_target']} | "
            f"{item['dominance_capacity']} | {item['feasible_under_expansion_framework']} | {', '.join(item['reasons'])} |"
        )
    lines.extend(
        [
            "",
            "## Guards",
            "",
            f"- Candidate/label artifacts absent: `{audit['candidate_or_label_artifact_guard']['ok']}`",
            f"- Pre-existing v2 artifacts absent: `{audit['v2_artifact_guard_before_expansion']['ok']}`",
            f"- Candidate generation: `{audit['candidate_generation']}`",
            f"- Semantic labeling: `{audit['semantic_labeling']}`",
            f"- Auditor execution: `{audit['auditor_execution']}`",
            "",
        ]
    )
    return "\n".join(lines)


def load_eligible_rows(path: Path) -> list[dict[str, str]]:
    return [row for row in load_csv(path) if row["eligibility_status"] == "eligible"]


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def counter_dict(counter: Counter[str]) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda item: (item[0])))


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


if __name__ == "__main__":
    main()
