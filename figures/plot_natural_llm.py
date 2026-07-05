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
    data = [row for row in rows("natural_llm_budget_curves.csv") if row["scope"] == "primary_fixture_passing_wrong"]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for policy in sorted({row["policy"] for row in data}):
        policy_rows = sorted([row for row in data if row["policy"] == policy], key=lambda row: int(row["budget"]))
        ax.plot([int(row["budget"]) for row in policy_rows], [float(row["detection_rate"]) for row in policy_rows], marker="o", linewidth=1.2, label=policy)
    ax.set_xlabel("Concrete-execution budget")
    ax.set_ylabel("Detection")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/natural_llm_budget_curves.pdf")


def plot_fuzzer() -> None:
    data = [row for row in rows("natural_llm_fuzzer_comparison.csv") if row["population"] == "primary_fixture_passing_wrong"]
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    labels = [row["mode"] + ":" + row["budget_or_time_limit"] for row in data]
    values = [float(row["mean_detection"]) for row in data]
    ax.bar(labels, values)
    ax.set_ylabel("Mean Detection")
    ax.set_ylim(0, 1.02)
    ax.tick_params(axis="x", labelrotation=25)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/natural_llm_fuzzer_comparison.pdf")


def plot_density() -> None:
    data = rows("natural_llm_density_results.csv")
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    ax.bar([row["density_bucket"] for row in data], [int(row["candidate_count"]) for row in data])
    ax.set_xlabel("Mismatch-density bucket")
    ax.set_ylabel("Natural LLM primary candidates")
    ax.tick_params(axis="x", labelrotation=20)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/natural_llm_density_results.pdf")


if __name__ == "__main__":
    plot_budget()
    plot_fuzzer()
    plot_density()
