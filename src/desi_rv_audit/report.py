from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


def _fmt(value, digits: int = 3) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if value is None or not np.isfinite(number):
        return "n/a"
    return f"{number:.{digits}f}"


def _read_sidecar(source_summary_path: Path, filename: str) -> pd.DataFrame | None:
    path = source_summary_path.parent / filename
    if not path.exists():
        return None
    return pd.read_csv(path)


def _format_table(frame: pd.DataFrame | None, empty_message: str, max_rows: int = 12) -> str:
    if frame is None or frame.empty:
        return empty_message

    display = frame.head(max_rows).copy()
    for column in display.columns:
        if pd.api.types.is_numeric_dtype(display[column]):
            if column.startswith("N_"):
                display[column] = display[column].map(
                    lambda value: "n/a" if pd.isna(value) else f"{int(value):,}"
                )
            elif column in {"FRACTION", "GOOD_EPOCH_FRACTION", "TAIL_GT_3", "TAIL_GT_5"}:
                display[column] = display[column].map(lambda value: _fmt(value, 5))
            else:
                display[column] = display[column].map(lambda value: _fmt(value, 3))
    return display.to_markdown(index=False)


def _program_pair_counts(
    pairs: pd.DataFrame,
    calibration_by_program: pd.DataFrame | None,
) -> tuple[int, int]:
    if calibration_by_program is not None and {
        "PROGRAM_PAIR",
        "N_PAIRS",
    }.issubset(calibration_by_program.columns):
        labels = calibration_by_program["PROGRAM_PAIR"].fillna("").astype(str)
        counts = pd.to_numeric(calibration_by_program["N_PAIRS"], errors="coerce").fillna(0)
    elif "PROGRAM_PAIR" in pairs.columns:
        value_counts = pairs["PROGRAM_PAIR"].dropna().astype(str).value_counts()
        labels = pd.Series(value_counts.index, dtype=str)
        counts = pd.Series(value_counts.to_numpy(dtype=int))
    else:
        return 0, 0

    backup_total = 0
    backup_cross_program = 0
    for label, count_value in zip(labels, counts):
        count = int(count_value)
        parts = [part.strip().upper() for part in str(label).split("/")]
        if "BACKUP" not in parts:
            continue
        backup_total += count
        if any(part != "BACKUP" for part in parts):
            backup_cross_program += count
    return backup_total, backup_cross_program


def build_report(
    source_summary: pd.DataFrame,
    pairs: pd.DataFrame,
    epoch_quality_by_program: pd.DataFrame | None = None,
    calibration_overall: pd.DataFrame | None = None,
    calibration_formal_overall: pd.DataFrame | None = None,
    calibration_by_program: pd.DataFrame | None = None,
    calibration_formal_by_program: pd.DataFrame | None = None,
    calibration_interday_by_program: pd.DataFrame | None = None,
    calibration_formal_interday_by_program: pd.DataFrame | None = None,
    calibration_by_sn: pd.DataFrame | None = None,
    rejection_counts: pd.DataFrame | None = None,
    correction_summary: pd.DataFrame | None = None,
    program_night_summary: pd.DataFrame | None = None,
    program_night_by_program: pd.DataFrame | None = None,
    program_night_reproducibility: pd.DataFrame | None = None,
    program_night_permutation_summary: pd.DataFrame | None = None,
) -> str:
    n_sources = int(len(source_summary))
    n_candidates = int((source_summary["classification"] == "candidate_variable").sum())
    strict_mask = (
        (source_summary["classification"] == "candidate_variable")
        & (source_summary["n_epochs_good"] >= 3)
        & (source_summary["time_baseline_days"] > 1.0)
    )
    n_strict_candidates = int(strict_mask.sum())
    n_pairs = int(len(pairs))
    if n_pairs:
        z = pd.to_numeric(pairs["PAIR_Z"], errors="coerce").dropna().to_numpy()
        median_z = float(np.median(z)) if z.size else np.nan
        q16, q84 = np.quantile(z, [0.16, 0.84]) if z.size else (np.nan, np.nan)
        central_width = float((q84 - q16) / 2.0)
        tail5 = float(np.mean(np.abs(z) > 5.0)) if z.size else np.nan
    else:
        median_z = central_width = tail5 = np.nan

    classification_counts = (
        source_summary["classification"]
        .value_counts()
        .rename_axis("classification")
        .reset_index(name="N_SOURCES")
    )
    classification_counts["classification"] = classification_counts["classification"].replace(
        {"candidate_variable": "constant_rv_outlier"}
    )

    backup_total, backup_cross_program = _program_pair_counts(pairs, calibration_by_program)
    if backup_total == 0:
        backup_pair_note = (
            "No `BACKUP` epoch pairs survived into the pair table, so this run does not "
            "test the documented backup-program zero-point issue."
        )
    elif backup_cross_program < 30:
        backup_pair_note = (
            f"`BACKUP` pairs survived ({backup_total:,} total), but only "
            f"{backup_cross_program:,} cross-program `BACKUP`/non-`BACKUP` pairs are present. "
            "Treat this as underpowered for reproducing the documented backup-program "
            "zero-point issue."
        )
    else:
        backup_pair_note = (
            f"`BACKUP` cross-program pairs are present ({backup_cross_program:,}); inspect "
            "the program-pair table before treating this as a positive-control reproduction."
        )

    top_columns = [
        column
        for column in (
            "group_id",
            "group_kind",
            "source_id",
            "targetid",
            "n_epochs_good",
            "weighted_mean_vrad",
            "p_const",
            "max_pair_sigma",
            "time_baseline_days",
        )
        if column in source_summary.columns
    ]
    top = source_summary.loc[
        source_summary["classification"] == "candidate_variable",
        top_columns,
    ].head(10)

    if top.empty:
        top_table = "No sources crossed the configured screening thresholds."
    else:
        display = top.copy()
        for column in ("weighted_mean_vrad", "max_pair_sigma", "time_baseline_days"):
            display[column] = display[column].map(lambda value: _fmt(value, 2))
        display["p_const"] = display["p_const"].map(lambda value: f"{value:.2e}")
        top_table = display.to_markdown(index=False)

    strict_top = source_summary.loc[strict_mask, top_columns].head(10)
    if strict_top.empty:
        strict_top_table = "No sources crossed the stricter display thresholds."
    else:
        display = strict_top.copy()
        for column in ("weighted_mean_vrad", "max_pair_sigma", "time_baseline_days"):
            display[column] = display[column].map(lambda value: _fmt(value, 2))
        display["p_const"] = display["p_const"].map(lambda value: f"{value:.2e}")
        strict_top_table = display.to_markdown(index=False)

    classification_table = _format_table(
        classification_counts,
        "No source classifications were generated.",
    )
    epoch_quality_table = _format_table(
        epoch_quality_by_program,
        "Epoch-quality sidecar table was not available.",
    )
    rejection_table = _format_table(
        rejection_counts,
        "Rejection-count sidecar table was not available.",
    )
    correction_table = _format_table(
        correction_summary,
        "Correction-coverage sidecar table was not available.",
    )
    fiber_note = ""
    if rejection_counts is not None and not rejection_counts.empty:
        fiber_rows = rejection_counts[rejection_counts["REASON"] == "FIBER_WARNING"]
        if not fiber_rows.empty:
            fiber_rejections = int(pd.to_numeric(fiber_rows["N_REJECTED"], errors="coerce").iloc[0])
            if fiber_rejections == 0:
                fiber_note = (
                    "\nFor the local `MAIN` FITS files, `FIBERSTATUS` is zero for every loaded row, "
                    "so `FIBER_WARNING=0` is expected rather than evidence that this check is disabled."
                )
            else:
                fiber_note = (
                    f"\n`FIBER_WARNING` reflects {fiber_rejections:,} rows with nonzero or missing "
                    "`FIBERSTATUS`."
                )
    overall_table = _format_table(
        calibration_overall,
        "Overall calibrated-error calibration sidecar table was not available.",
    )
    formal_overall_table = _format_table(
        calibration_formal_overall,
        "Overall formal-error calibration sidecar table was not available.",
    )
    program_table = _format_table(
        calibration_by_program,
        "Program-pair calibrated-error sidecar table was not available or no program pairs were produced.",
    )
    formal_program_table = _format_table(
        calibration_formal_by_program,
        "Program-pair formal-error sidecar table was not available or no program pairs were produced.",
    )
    interday_program_table = _format_table(
        calibration_interday_by_program,
        "Inter-day calibrated-error sidecar table was not available or no inter-day pairs were produced.",
    )
    formal_interday_program_table = _format_table(
        calibration_formal_interday_by_program,
        "Inter-day formal-error sidecar table was not available or no inter-day pairs were produced.",
    )
    sn_table = _format_table(
        calibration_by_sn,
        "S/N calibration sidecar table was not available or too few S/N-tagged pairs were produced.",
    )
    program_night_table = _format_table(
        program_night_summary,
        "Source-grouped PROGRAM:NIGHT diagnostics were not run.",
        max_rows=10,
    )
    program_night_program_table = _format_table(
        program_night_by_program,
        "PROGRAM:NIGHT holdout diagnostics by program pair were not run.",
        max_rows=36,
    )
    program_night_repro_table = _format_table(
        program_night_reproducibility,
        "Independent-half offset reproducibility was not run.",
    )
    program_night_permutation_table = _format_table(
        program_night_permutation_summary,
        "Shuffled-night control was not run.",
        max_rows=10,
    )

    return f"""# DESI radial-velocity audit report

## Scope

This report is a **screening and quality-control artifact**, not an astrophysical discovery claim.

## Summary

- Sources summarized: **{n_sources:,}**
- Quality-approved epoch pairs: **{n_pairs:,}**
- Sources inconsistent with a constant-RV model under configured thresholds: **{n_candidates:,}**
- Strict constant-RV screening outliers with `n_epochs_good >= 3` and baseline > 1 day: **{n_strict_candidates:,}**
- Median normalized pair residual: **{_fmt(median_z)}**
- Central 16–84% normalized-residual half-width: **{_fmt(central_width)}**
- Fraction of pairs with |z| > 5: **{_fmt(tail5, 5)}**

For perfectly calibrated independent Gaussian errors and non-variable sources, the central width should be near one. Departures can arise from uncertainty miscalibration, zero-point systematics, real stellar variability, correlations, selection effects, or pipeline failures.

## Source classifications

{classification_table}

## Quality filtering

{epoch_quality_table}

{rejection_table}

Rejection reasons are **not mutually exclusive**; their counts should not be summed.
{fiber_note}

## Published Backup Correction

The backup-program velocity correction is applied only to rows where
`SURVEY == MAIN` and `PROGRAM == BACKUP`. TARGETID matches in other programs are
counted for auditability but are not corrected.

{correction_table}

## Calibration diagnostics

Overall normalized pair residuals using calibrated errors:

{overall_table}

Overall normalized pair residuals using formal catalogue errors:

{formal_overall_table}

By canonical program pair using calibrated errors. Cross-program `PROGRAM_PAIR_Z`
is oriented lexicographically so a zero-point offset does not cancel when epoch
order changes. Same-program pairs have no cross-program orientation; their sign
follows the sorted epoch order and their median should be interpreted as a
within-program residual diagnostic, not a program zero-point estimate.

{program_table}

By canonical program pair using formal catalogue errors:

{formal_program_table}

By canonical program pair using calibrated errors and only pairs separated by more than one day:

{interday_program_table}

By canonical program pair using formal catalogue errors and only pairs separated by more than one day:

{formal_interday_program_table}

By minimum pair `SN_R` quantile:

{sn_table}

Positive-control status: {backup_pair_note}

## Source-Grouped Program-Night Residual Diagnostics

This experiment estimates residual offsets for `PROGRAM:NIGHT` labels after the
published backup correction and program-level uncertainty floors. Folds are
assigned by `GROUP_ID`, so no source group contributes pairs to both train and
holdout within a fold. The fit uses train-only robust clipping, source-balanced
pair weights, train-estimated post-correction floors, and only holdout pairs
whose two labels are in the same train graph component. These offsets are
diagnostics, not official catalogue corrections.

Fold-level holdout diagnostics:

{program_night_table}

Fold-level holdout diagnostics by program pair:

{program_night_program_table}

Independent source-half reproducibility for nightly offsets:

{program_night_repro_table}

Deterministic shuffled-exposure-night-within-program control:

{program_night_permutation_table}

## Highest-ranked constant-RV screening outliers

{top_table}

## Highest-ranked strict constant-RV screening outliers

{strict_top_table}

## Required checks before interpretation

1. Reproduce documented DESI program-level radial-velocity systematics.
2. Inspect warning flags, S/N, posterior skewness/kurtosis, model residuals, and individual spectra.
3. Check whether screening outliers concentrate by night, exposure, fiber, survey, or program.
4. Compare against known variable/binary catalogues and published controls.
5. Have a domain expert review all selection assumptions and any physical interpretation.
"""


def write_report(source_summary_path: str, pairs_path: str, output_path: str) -> None:
    source_summary_file = Path(source_summary_path)
    source_summary = pd.read_csv(source_summary_file)
    pairs = pd.read_csv(pairs_path)
    text = build_report(
        source_summary,
        pairs,
        epoch_quality_by_program=_read_sidecar(source_summary_file, "epoch_quality_by_program.csv"),
        calibration_overall=_read_sidecar(source_summary_file, "calibration_overall.csv"),
        calibration_formal_overall=_read_sidecar(
            source_summary_file,
            "calibration_formal_overall.csv",
        ),
        calibration_by_program=_read_sidecar(source_summary_file, "calibration_by_program.csv"),
        calibration_formal_by_program=_read_sidecar(
            source_summary_file,
            "calibration_formal_by_program.csv",
        ),
        calibration_interday_by_program=_read_sidecar(
            source_summary_file,
            "calibration_interday_by_program.csv",
        ),
        calibration_formal_interday_by_program=_read_sidecar(
            source_summary_file,
            "calibration_formal_interday_by_program.csv",
        ),
        calibration_by_sn=_read_sidecar(source_summary_file, "calibration_by_sn.csv"),
        rejection_counts=_read_sidecar(source_summary_file, "rejection_counts.csv"),
        correction_summary=_read_sidecar(source_summary_file, "correction_summary.csv"),
        program_night_summary=_read_sidecar(source_summary_file, "program_night_summary.csv"),
        program_night_by_program=_read_sidecar(
            source_summary_file,
            "program_night_by_program.csv",
        ),
        program_night_reproducibility=_read_sidecar(
            source_summary_file,
            "program_night_reproducibility.csv",
        ),
        program_night_permutation_summary=_read_sidecar(
            source_summary_file,
            "program_night_permutation_summary.csv",
        ),
    )
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
