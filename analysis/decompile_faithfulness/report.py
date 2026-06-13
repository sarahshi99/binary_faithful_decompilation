from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Decompilation Faithfulness Phase 1A Audit",
        "",
        "## Research Question",
        "",
        (
            "Can recompiled binary feature distance rank faithful C candidates "
            "above plausible-but-wrong C candidates in a controlled source-known benchmark?"
        ),
        "",
        "## Dataset",
        "",
        f"- Cases: `{payload['case_count']}`",
        f"- Ranking candidates: `{payload['candidate_count']}`",
        f"- Faithful candidates: `{payload['faithful_count']}`",
        f"- Plausible-wrong candidates: `{payload['plausible_wrong_count']}`",
        f"- Equivalent or weak mutations excluded from ranking: `{payload['equivalent_or_weak_count']}`",
        f"- Compile failures excluded from ranking: `{payload['excluded_compile_fail']}`",
        f"- Compiler optimization: `{payload['opt_level']}`",
        "",
        "## Metrics",
        "",
        f"- Top-1 faithful rate: `{payload['top1_faithful_rate']:.4f}`",
        f"- Pairwise AUC: `{payload['pairwise_auc']:.4f}`",
        f"- Verdict: `{payload['verdict']}`",
        "",
        "## Feature Set",
        "",
        (
            "Phase 1A.1 includes an operand-sensitive `instruction_signature_l1` component. "
            "This was added after the opcode/immediate/count-only metric missed the "
            "`return a - b` -> `return b - a` behavior-changing counterfactual."
        ),
        "",
        "## Mutation Buckets",
        "",
        "| Mutation type | Candidate count | Mean distance |",
        "|---|---:|---:|",
    ]
    by_mutation_type = payload.get("by_mutation_type", {})
    if isinstance(by_mutation_type, dict) and by_mutation_type:
        for mutation_type, bucket in sorted(by_mutation_type.items()):
            lines.append(
                f"| `{mutation_type}` | {bucket['candidate_count']} | {bucket['mean_distance']:.4f} |"
            )
    else:
        lines.append("| none | 0 | 0.0000 |")

    lines.extend(
        [
            "",
            "## Kill Criterion",
            "",
            "- Continue if `pairwise_auc >= 0.75` and `top1_faithful_rate >= 0.67`.",
            "- Kill core method if `pairwise_auc < 0.60` or `top1_faithful_rate < 0.50`.",
            "- Otherwise mark the signal inconclusive and add stronger candidates before method claims.",
            "",
            "## Interpretation",
            "",
            _interpret_verdict(str(payload["verdict"])),
            "",
        ]
    )
    zero_distance_buckets = _zero_distance_buckets(payload)
    if zero_distance_buckets:
        joined = ", ".join(f"`{bucket}`" for bucket in zero_distance_buckets)
        lines.extend(
            [
                "## Observed Blind Spots",
                "",
                (
                    f"The current feature set assigns zero mean distance to these wrong-candidate "
                    f"buckets: {joined}. This means opcode/immediate/count features miss at least "
                    "one semantic error family and should not be treated as a complete "
                    "binary-faithfulness metric."
                ),
                "",
            ]
        )
    lines.extend(
        [
            (
                "This is a controlled mutation-style audit, not a full decompilation system. "
                "It only tests whether the proposed binary feature distance contains enough "
                "faithfulness signal to justify the next experiment."
            ),
            "",
            "## Next Route",
            "",
            (
                "Phase 1B realistic negatives show that the naive global feature-distance "
                "ranker fails on behavior-preserving rewrites. Phase 1D slot calibration "
                "recovers signal at O0 but weakens at O2, so the next step is "
                "optimization-aware slot-local calibration before real-project transfer."
            ),
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _interpret_verdict(verdict: str) -> str:
    if verdict == "continue":
        return (
            "The controlled ranking signal passes the first gate. The next step is to add "
            "realistic LLM/decompiler negatives before making paper-level claims."
        )
    if verdict == "kill-core-method":
        return (
            "The controlled ranking signal failed the first gate. Do not center Paper A on "
            "recompile-guided binary feature feedback without redesigning the feature metric."
        )
    return (
        "The controlled ranking signal is inconclusive. Add more cases and harder negatives "
        "before deciding whether to keep or kill the method."
    )


def _zero_distance_buckets(payload: dict[str, Any]) -> list[str]:
    by_mutation_type = payload.get("by_mutation_type", {})
    if not isinstance(by_mutation_type, dict):
        return []
    buckets = []
    for mutation_type, bucket in sorted(by_mutation_type.items()):
        if isinstance(bucket, dict) and bucket.get("candidate_count", 0) and bucket.get("mean_distance") == 0.0:
            buckets.append(str(mutation_type))
    return buckets
