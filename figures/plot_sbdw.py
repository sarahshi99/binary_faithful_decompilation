from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "figures/data"


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def plot_budget() -> None:
    data = [row for row in rows("sbdw_budget_curves.csv") if row["scope"] in {"controlled_primary_fixture_passing_wrong", "natural_llm_primary_fixture_passing_wrong"} and row["policy"] in {"source_behavioral_diversity", "source_literal_char_interleave", "generic_type_boundaries"}]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for key in sorted({(row["scope"], row["policy"]) for row in data}):
        series = sorted([row for row in data if (row["scope"], row["policy"]) == key], key=lambda row: int(row["budget"]))
        ax.plot([int(row["budget"]) for row in series], [float(row["detection_rate"]) for row in series], marker="o", linewidth=1.2, label=key[0].replace("_fixture_passing_wrong", "") + ":" + key[1])
    ax.set_xlabel("Budget")
    ax.set_ylabel("Detection")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/sbdw_budget_curves.pdf")


def plot_cost() -> None:
    data = rows("sbdw_cost_amortization.csv")
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    ax.plot([int(row["candidate_count_per_source"]) for row in data], [float(row["elapsed_s"]) for row in data], marker="o")
    ax.set_xlabel("Candidates per source")
    ax.set_ylabel("Amortized seconds")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/sbdw_cost_amortization.pdf")


def plot_behavior() -> None:
    data = [row for row in rows("sbdw_behavior_selection.csv") if row["policy"] == "source_behavioral_diversity"]
    counts = {}
    for row in data:
        key = str(row["normalized_output"])
        counts[key] = counts.get(key, 0) + 1
    top = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:20]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    ax.bar([item[0] for item in top], [item[1] for item in top])
    ax.set_xlabel("Selected source output class")
    ax.set_ylabel("Selected probes")
    ax.tick_params(axis="x", labelrotation=45)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/sbdw_behavior_selection.pdf")


if __name__ == "__main__":
    plot_budget()
    plot_cost()
    plot_behavior()
