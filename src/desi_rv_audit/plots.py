from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .pipeline import AuditOutputs


def _finite_values(frame: pd.DataFrame, column: str) -> np.ndarray:
    if column not in frame.columns:
        return np.asarray([], dtype=float)
    values = pd.to_numeric(frame[column], errors="coerce").to_numpy(dtype=float)
    return values[np.isfinite(values)]


def write_plots(outputs: AuditOutputs, output_dir: str | Path) -> list[Path]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:  # pragma: no cover - optional plotting dependency
        return []

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    calibrated = _finite_values(outputs.pairs, "PAIR_Z")
    formal = _finite_values(outputs.pairs, "PAIR_Z_FORMAL")
    if calibrated.size and formal.size:
        fig, ax = plt.subplots(figsize=(8, 4.8), constrained_layout=True)
        bins = np.linspace(-8, 8, 129)
        ax.hist(
            formal[np.abs(formal) <= 8],
            bins=bins,
            density=True,
            histtype="step",
            linewidth=1.6,
            label=f"formal errors (N={formal.size:,})",
        )
        ax.hist(
            calibrated[np.abs(calibrated) <= 8],
            bins=bins,
            density=True,
            histtype="step",
            linewidth=1.8,
            label=f"calibrated errors (N={calibrated.size:,})",
        )
        x = np.linspace(-8, 8, 500)
        normal_pdf = np.exp(-0.5 * x * x) / np.sqrt(2 * np.pi)
        ax.plot(x, normal_pdf, color="black", linestyle="--", linewidth=1.0, label="N(0,1)")
        ax.set_title("Formal vs calibrated normalized RV residuals")
        ax.set_xlabel("pair residual z")
        ax.set_ylabel("density")
        ax.set_yscale("log")
        ax.set_ylim(bottom=1e-4)
        ax.legend(frameon=False)
        path = output_dir / "formal_vs_calibrated_residual_distribution.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        written.append(path)

    calibrated_width = outputs.calibration_interday_by_program
    formal_width = outputs.calibration_formal_interday_by_program
    if (
        not calibrated_width.empty
        and not formal_width.empty
        and {"PROGRAM_PAIR", "ROBUST_WIDTH_Z"}.issubset(calibrated_width.columns)
        and {"PROGRAM_PAIR", "ROBUST_WIDTH_Z"}.issubset(formal_width.columns)
    ):
        merged = calibrated_width[["PROGRAM_PAIR", "ROBUST_WIDTH_Z"]].merge(
            formal_width[["PROGRAM_PAIR", "ROBUST_WIDTH_Z"]],
            on="PROGRAM_PAIR",
            how="inner",
            suffixes=("_CALIBRATED", "_FORMAL"),
        )
        if not merged.empty:
            fig, ax = plt.subplots(figsize=(8.4, 4.8), constrained_layout=True)
            x = np.arange(len(merged))
            width = 0.38
            ax.bar(
                x - width / 2,
                merged["ROBUST_WIDTH_Z_FORMAL"],
                width,
                label="formal errors",
            )
            ax.bar(
                x + width / 2,
                merged["ROBUST_WIDTH_Z_CALIBRATED"],
                width,
                label="calibrated errors",
            )
            ax.axhline(1.0, color="black", linestyle="--", linewidth=1.0)
            ax.set_xticks(x, merged["PROGRAM_PAIR"], rotation=35, ha="right")
            ax.set_ylabel("central 16-84% half-width")
            ax.set_title("Inter-day residual width by program pair")
            ax.legend(frameon=False)
            path = output_dir / "interday_width_by_program_pair.png"
            fig.savefig(path, dpi=160)
            plt.close(fig)
            written.append(path)

    program_night = outputs.program_night_summary
    if not program_night.empty and {
        "FOLD",
        "BEFORE_WIDTH_Z",
        "AFTER_WIDTH_Z",
        "MACRO_WIDTH_BEFORE_Z",
        "MACRO_WIDTH_AFTER_Z",
    }.issubset(program_night.columns):
        plot_frame = program_night.dropna(
            subset=[
                "BEFORE_WIDTH_Z",
                "AFTER_WIDTH_Z",
                "MACRO_WIDTH_BEFORE_Z",
                "MACRO_WIDTH_AFTER_Z",
            ]
        )
        if not plot_frame.empty:
            fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), constrained_layout=True)
            x = np.arange(len(plot_frame))
            width = 0.38
            labels = plot_frame["FOLD"].astype(str).to_numpy()
            axes[0].bar(x - width / 2, plot_frame["BEFORE_WIDTH_Z"], width, label="before")
            axes[0].bar(x + width / 2, plot_frame["AFTER_WIDTH_Z"], width, label="after")
            axes[0].axhline(1.0, color="black", linestyle="--", linewidth=1.0)
            axes[0].set_xticks(x, labels)
            axes[0].set_xlabel("source-grouped fold")
            axes[0].set_ylabel("central 16-84% half-width")
            axes[0].set_title("Program-night aggregate holdout width")
            axes[0].legend(frameon=False)

            axes[1].bar(
                x - width / 2,
                plot_frame["MACRO_WIDTH_BEFORE_Z"],
                width,
                label="before",
            )
            axes[1].bar(
                x + width / 2,
                plot_frame["MACRO_WIDTH_AFTER_Z"],
                width,
                label="after",
            )
            axes[1].axhline(1.0, color="black", linestyle="--", linewidth=1.0)
            axes[1].set_xticks(x, labels)
            axes[1].set_xlabel("source-grouped fold")
            axes[1].set_title("Program-night macro-average by program pair")
            axes[1].legend(frameon=False)
            path = output_dir / "program_night_source_fold_widths.png"
            fig.savefig(path, dpi=160)
            plt.close(fig)
            written.append(path)

    return written
