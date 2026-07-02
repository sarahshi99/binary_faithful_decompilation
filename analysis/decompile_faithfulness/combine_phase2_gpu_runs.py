from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from analysis.decompile_faithfulness import run_phase2_gpu_smoke as gpu_smoke


def main() -> None:
    args = parse_args()
    summary = combine_runs(
        run_dirs=args.run_dir,
        run_prefixes=args.run_prefix,
        output_dir=args.output_dir,
        output_json=args.output_json,
        output_md=args.output_md,
        output_zh=args.output_zh,
    )
    print(
        json.dumps(
            {
                "generation_count": summary["generation_count"],
                "candidate_count": summary["candidate_count"],
                "compile_pass_count": summary["compile_pass_count"],
                "behavior_label_counts": summary["behavior_label_counts"],
                "paired_case_count": summary["paired_case_count"],
                "trace_pairwise_auc": summary["trace_pairwise_auc"],
                "fixture_collapse": summary["fixture_collapse"],
            },
            sort_keys=True,
        )
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", action="append", type=Path, required=True)
    parser.add_argument("--run-prefix", action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-md", type=Path, required=True)
    parser.add_argument("--output-zh", type=Path, required=True)
    return parser.parse_args()


def combine_runs(
    run_dirs: list[Path],
    run_prefixes: list[str],
    output_dir: Path,
    output_json: Path,
    output_md: Path,
    output_zh: Path,
) -> dict[str, Any]:
    if len(run_dirs) != len(run_prefixes):
        raise ValueError("run-dir and run-prefix counts must match")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    generation_path = output_dir / "generation_metadata.jsonl"
    records_path = output_dir / "records.jsonl"

    by_case: dict[str, list[dict[str, Any]]] = {}
    generations: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for run_dir, prefix in zip(run_dirs, run_prefixes):
        manifest = _read_json(run_dir / "manifest.json")
        for entry in manifest:
            case_id = entry["case_id"]
            by_case.setdefault(case_id, []).extend(
                _rename_candidate(candidate, prefix)
                for candidate in entry["candidates"]
            )
        generations.extend(
            _rename_generation(row, prefix)
            for row in _read_jsonl(run_dir / "generation_metadata.jsonl")
        )
        records.extend(
            _rename_record(row, prefix, run_dir.name)
            for row in _read_jsonl(run_dir / "records.jsonl")
        )

    combined_manifest = [
        {"case_id": case_id, "candidates": candidates}
        for case_id, candidates in sorted(by_case.items())
    ]
    _write_json(manifest_path, combined_manifest)
    _write_jsonl(generation_path, generations)
    _write_jsonl(records_path, records)

    return gpu_smoke.summarize_gpu_smoke(
        output_dir=output_dir,
        output_json=output_json,
        output_md=output_md,
        output_zh=output_zh,
        manifest_path=manifest_path,
        generation_path=generation_path,
        records_path=records_path,
        generation_records=generations,
        records=records,
        model_info={
            "model_path": "Dream-Coder-v0-Instruct-7B local snapshots",
            "device": "combined",
            "torch_dtype": "auto",
            "max_new_tokens": 192,
            "steps": 32,
            "temperature": 0.2,
            "top_p": 0.95,
            "seed": 20260618,
            "model_loaded": True,
            "model_error": "",
            "model_load_seconds": None,
            "cuda_visible_devices_policy": (
                "not_set_by_script; model and tensors explicitly moved to requested device"
            ),
        },
    )


def _rename_candidate(candidate: dict[str, Any], prefix: str) -> dict[str, Any]:
    renamed = dict(candidate)
    renamed["candidate_id"] = f"{prefix}__{candidate['candidate_id']}"
    return renamed


def _rename_generation(row: dict[str, Any], prefix: str) -> dict[str, Any]:
    renamed = dict(row)
    renamed["candidate_id"] = f"{prefix}__{row['candidate_id']}"
    return renamed


def _rename_record(row: dict[str, Any], prefix: str, source_run: str) -> dict[str, Any]:
    renamed = dict(row)
    renamed["candidate_id"] = f"{prefix}__{row['candidate_id']}"
    metadata = dict(renamed.get("metadata", {}))
    metadata["source_run"] = source_run
    renamed["metadata"] = metadata
    return renamed


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(record, sort_keys=True) for record in records) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
