#!/usr/bin/env python3
"""Plot the measured median and P05–P95 from a benchmark JSON report."""
import argparse
import json
from pathlib import Path

LABELS = {
    "cache-locality": "Cache locality",
    "matrix-traversal": "Matrix traversal",
    "false-sharing": "False sharing",
    "mutex-atomic": "Mutex vs atomic",
    "cpu-affinity": "CPU affinity",
    "memory-alignment": "Memory alignment",
    "simd": "SIMD vectorization",
    "memory-bandwidth": "Memory bandwidth",
    "branch-prediction": "Branch prediction",
    "context-switch": "Context switch",
}


def draw(report, destination):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    if report.get("schema_version") != 1:
        raise ValueError("unsupported benchmark report format")
    experiments = report["experiments"]
    columns = 2 if len(experiments) > 1 else 1
    rows = (len(experiments) + columns - 1) // columns
    figure, axes = plt.subplots(rows, columns, squeeze=False, figsize=(6.2 * columns, 2.5 * rows + 1.3))
    figure.patch.set_facecolor("#f6f8f6")
    environment = report["environment"]
    settings = report["settings"]
    figure.suptitle("Computer Systems Performance Lab", x=0.055, y=0.984,
                    ha="left", fontsize=23, fontweight="bold", color="#142a2c")
    figure.text(0.055, 0.94,
                f"{environment['cpu_model'] or 'Unknown CPU'}  |  {settings['environment_label']} "
                f"({environment['virtualization'] or 'unspecified'})  |  {settings['trials']} trials per variant\n"
                "Bars show medians. Whiskers span P05–P95 across trials. Each panel has its own scale.",
                va="top", fontsize=10, color="#405857")
    for axis, (name, experiment) in zip(axes.flat, experiments.items()):
        axis.set_facecolor("#f6f8f6")
        axis.set_title(LABELS.get(name, name), loc="left", fontsize=13, fontweight="bold")
        metric = experiment["primary_metric"]
        unit = "logical GiB/s" if metric == "logical_gib_per_sec" else "ns/" + experiment["operation"]
        scale = 1
        if name == "context-switch" and any(
                v["status"] == "ok" and v["summary"][metric]["median"] >= 1000
                for v in experiment["variants"].values()):
            unit, scale = "µs/handoff", 1000
        measured = [v["summary"][metric]["p95"] / scale for v in experiment["variants"].values()
                    if v["status"] == "ok"]
        limit = max(measured, default=1)
        variants = experiment["variants"]
        for index, (variant, series) in enumerate(variants.items()):
            if series["status"] != "ok":
                axis.text(0, index, "unavailable", va="center", color="#405857")
                continue
            quantiles = series["summary"][metric]
            median, low, high = (quantiles[key] / scale for key in ("median", "p05", "p95"))
            axis.barh(index, median, height=0.6, color="#198275", zorder=2)
            axis.errorbar(median, index, xerr=[[median - low], [high - median]], fmt="none",
                          ecolor="#142a2c", capsize=3, linewidth=1, zorder=3)
            axis.text(high + 0.025 * limit, index, f"{median:.4g}", va="center",
                      color="#142a2c", fontsize=9)
        axis.set_yticks(range(len(variants)), variants)
        axis.invert_yaxis()
        axis.set_xlim(0, limit * 1.24)
        axis.xaxis.set_major_locator(MaxNLocator(nbins=5))
        axis.set_xlabel(unit, loc="right", color="#405857")
        axis.grid(axis="x", linewidth=0.7, color="#d6dfda")
        for spine in axis.spines.values():
            spine.set_visible(False)
        axis.tick_params(length=0, pad=5, labelsize=9, colors="#142a2c")
    for axis in list(axes.flat)[len(experiments):]:
        axis.set_visible(False)
    figure.tight_layout(rect=(0.045, 0.02, 0.985, 0.88), h_pad=1.3, w_pad=2.8)
    figure.savefig(destination, dpi=160)
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    with args.report.open(encoding="utf-8") as source:
        draw(json.load(source), args.output)


if __name__ == "__main__":
    main()
