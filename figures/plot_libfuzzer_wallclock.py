from __future__ import annotations

import csv
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "figures/data"


def rows(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def plot_detection() -> None:
    data = [row for row in rows("libfuzzer_wallclock_detection.csv") if row["population"] in {"primary_fixture_passing_wrong", "low_density_fixture_passing_wrong", "non_fixture_overfit_fixture_passing_wrong"}]
    fig, ax = plt.subplots(figsize=(6.2, 3.9))
    labels = {
        "primary_fixture_passing_wrong": "Primary",
        "low_density_fixture_passing_wrong": "Low density",
        "non_fixture_overfit_fixture_passing_wrong": "Non-overfit",
    }
    for population in labels:
        items = sorted([row for row in data if row["population"] == population], key=lambda row: float(row["wall_clock_budget_s"]))
        ax.plot([float(row["wall_clock_budget_s"]) for row in items], [float(row["mean_detection"]) for row in items], marker="o", linewidth=1.4, label=labels[population])
    if not data:
        raise RuntimeError("libfuzzer_wallclock_detection.csv has no rows")
    final_ref = float(data[0]["frozen_final_detection_at_b8"])
    ax.axhline(final_ref, color="black", linestyle="--", linewidth=1.0, label="Frozen final Detection@8")
    ax.set_xscale("log")
    ax.set_xlabel("libFuzzer end-to-end wall-clock budget (s)")
    ax.set_ylabel("Detection")
    ax.set_ylim(0, 1.02)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/libfuzzer_wallclock_detection.pdf")


def plot_time_to_witness() -> None:
    data = [row for row in rows("libfuzzer_wallclock_time_to_witness.csv") if row["population"] == "primary_fixture_passing_wrong"]
    items = sorted(data, key=lambda row: float(row["wall_clock_budget_s"]))
    fig, ax1 = plt.subplots(figsize=(6.1, 3.8))
    budgets = [float(row["wall_clock_budget_s"]) for row in items]
    e2e = [float(row["median_end_to_end_time_to_witness_s"] or 0.0) for row in items]
    proc = [float(row["median_in_process_time_to_witness_s"] or 0.0) for row in items]
    ax1.plot(budgets, e2e, marker="o", linewidth=1.4, label="End-to-end")
    ax1.plot(budgets, proc, marker="s", linewidth=1.4, label="In-process")
    ax1.set_xscale("log")
    ax1.set_xlabel("libFuzzer wall-clock budget (s)")
    ax1.set_ylabel("Median time to witness (s)")
    ax1.grid(True, alpha=0.25)
    ax1.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "figures/libfuzzer_wallclock_time_to_witness.pdf")


if __name__ == "__main__":
    plot_detection()
    plot_time_to_witness()
