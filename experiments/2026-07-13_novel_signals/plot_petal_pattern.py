from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parent
INPUT = EXPERIMENT_DIR / "petal_independent_program_offsets.csv"
OUTPUT = EXPERIMENT_DIR / "petal_independent_pattern.png"


def run() -> None:
    data = pd.read_csv(INPUT)
    fig, ax = plt.subplots(figsize=(11, 6.2), constrained_layout=True)
    styles = {
        ("BRIGHT", "A"): ("#e69f00", "o", "-"),
        ("BRIGHT", "B"): ("#f0c45a", "s", "--"),
        ("DARK", "A"): ("#3b6fb6", "o", "-"),
        ("DARK", "B"): ("#75a5df", "s", "--"),
    }
    for (program, half), group in data.groupby(["PROGRAM", "HALF"], sort=True):
        color, marker, linestyle = styles[(program, half)]
        group = group.sort_values("PETAL")
        ax.plot(
            group["PETAL"],
            group["MEDIAN_OFFSET_KMS"],
            color=color,
            marker=marker,
            linestyle=linestyle,
            linewidth=2.0,
            markersize=6,
            label=f"{program}, source half {half}",
        )
    ax.axhline(0.0, color="#555555", linewidth=1.0)
    ax.set_xticks(range(10))
    ax.set_xlabel("DESI PETAL")
    ax.set_ylabel("Median zero-mean residual offset (km/s)")
    ax.set_title("Independent within-program fits reproduce the PETAL pattern")
    ax.grid(axis="y", color="#dddddd", linewidth=0.8)
    ax.legend(frameon=False, ncol=2)
    fig.savefig(OUTPUT, dpi=180)
    plt.close(fig)
    print(OUTPUT)


if __name__ == "__main__":
    run()
