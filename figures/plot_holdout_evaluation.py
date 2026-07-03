from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "figures/data"


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def plot_budget_curves() -> None:
    data = [row for row in rows("holdout_budget_curves.csv") if row["scope"] == "primary_fixture_passing_wrong"]
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for policy in sorted({row["policy"] for row in data}):
        policy_rows = sorted([row for row in data if row["policy"] == policy], key=lambda row: int(row["budget"]))
        ax.plot([int(row["budget"]) for row in policy_rows], [float(row["detection_rate"]) for row in policy_rows], marker="o", linewidth=1.3, label=policy)
    ax.set_xlabel("Budget")
    ax.set_ylabel("Detection rate")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/holdout_budget_curves.pdf")


def plot_ecdf() -> None:
    data = rows("holdout_first_witness_ecdf.csv")
    fig, ax = plt.subplots(figsize=(6.2, 4.0))
    for policy in sorted({row["policy"] for row in data}):
        policy_rows = sorted([row for row in data if row["policy"] == policy], key=lambda row: int(row["rank"]))
        ax.step([int(row["rank"]) for row in policy_rows], [float(row["detection_rate"]) for row in policy_rows], where="post", label=policy)
    ax.set_xlabel("First witness rank")
    ax.set_ylabel("Cumulative detected fraction")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/holdout_first_witness_ecdf.pdf")


def plot_density() -> None:
    data = [row for row in rows("holdout_density_results.csv") if row["policy"] == "source_literal_char_interleave"]
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    ax.bar([row["density_bucket"] for row in data], [float(row["detection_rate"]) for row in data])
    ax.set_xlabel("Mismatch-density bucket")
    ax.set_ylabel("Detection@8")
    ax.set_ylim(0, 1.02)
    ax.tick_params(axis="x", labelrotation=20)
    ax.grid(True, axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/holdout_density_results.pdf")


if __name__ == "__main__":
    plot_budget_curves()
    plot_ecdf()
    plot_density()
