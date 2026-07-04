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
    data = rows("strong_baseline_budget_curves.csv")
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for baseline in sorted({row["baseline"] for row in data}):
        items = sorted([row for row in data if row["baseline"] == baseline], key=lambda row: float(row["budget"]))
        ax.plot([float(row["budget"]) for row in items], [float(row["detection_rate"]) for row in items], marker="o", linewidth=1.3, label=baseline)
    ax.set_xlabel("Completed evaluations")
    ax.set_ylabel("Detection rate")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/strong_baseline_budget_curves.pdf")


def plot_time_curves() -> None:
    data = rows("strong_baseline_time_curves.csv")
    fig, ax = plt.subplots(figsize=(6.0, 3.8))
    for baseline in sorted({row["baseline"] for row in data}):
        items = sorted([row for row in data if row["baseline"] == baseline], key=lambda row: float(row["time_s"]))
        ax.plot([float(row["time_s"]) for row in items], [float(row["detection_rate"]) for row in items], marker="o", linewidth=1.3, label=baseline)
    ax.set_xlabel("Wall-clock limit (s)")
    ax.set_ylabel("Detection rate")
    ax.set_xscale("log")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/strong_baseline_time_curves.pdf")


def plot_upsets() -> None:
    data = [row for row in rows("paired_policy_upset.csv") if row["budget"] == "8"]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    labels = [row["comparator_policy"] for row in data]
    final = [int(row["final_only"]) for row in data]
    comp = [int(row["comparator_only"]) for row in data]
    x = range(len(labels))
    ax.bar([v - 0.18 for v in x], final, width=0.36, label="Final only")
    ax.bar([v + 0.18 for v in x], comp, width=0.36, label="Comparator only")
    ax.set_xticks(list(x), labels, rotation=20, ha="right")
    ax.set_ylabel("Discordant candidates")
    ax.grid(True, axis="y", alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/paired_policy_upset.pdf")


if __name__ == "__main__":
    plot_budget_curves()
    plot_time_curves()
    plot_upsets()
