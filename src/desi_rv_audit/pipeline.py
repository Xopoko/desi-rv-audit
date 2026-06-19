from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .calibration import add_quantile_bin, summarize_pair_residuals
from .corrections import apply_velocity_calibration
from .io import load_many
from .manifest import build_manifest, write_manifest
from .pairs import build_pair_table
from .program_night import run_program_night_experiment
from .quality import QualityRules, quality_mask, rejection_reasons
from .stats import summarize_sources


@dataclass(frozen=True)
class AuditOutputs:
    source_summary: pd.DataFrame
    pairs: pd.DataFrame
    epoch_quality_by_program: pd.DataFrame
    calibration_overall: pd.DataFrame
    calibration_formal_overall: pd.DataFrame
    calibration_by_program: pd.DataFrame
    calibration_formal_by_program: pd.DataFrame
    calibration_interday_by_program: pd.DataFrame
    calibration_formal_interday_by_program: pd.DataFrame
    calibration_by_sn: pd.DataFrame
    rejection_counts: pd.DataFrame
    correction_summary: pd.DataFrame
    program_night_summary: pd.DataFrame
    program_night_by_program: pd.DataFrame
    program_night_offsets: pd.DataFrame
    program_night_reproducibility: pd.DataFrame
    program_night_permutation_summary: pd.DataFrame
    run_manifest: dict[str, object]


def summarize_epoch_quality(frame: pd.DataFrame, good_mask: pd.Series) -> pd.DataFrame:
    keys = [column for column in ("SURVEY", "PROGRAM") if column in frame.columns]
    if not keys:
        keys = ["_ALL"]
        frame = frame.assign(_ALL="ALL")

    raw = (
        frame.groupby(keys, dropna=False, sort=True)
        .agg(
            N_EPOCHS_RAW=("TARGETID", "size"),
            N_TARGETIDS_RAW=("TARGETID", "nunique"),
            N_GROUPS_RAW=("GROUP_ID", "nunique") if "GROUP_ID" in frame.columns else ("TARGETID", "nunique"),
        )
        .reset_index()
    )

    good = frame.loc[good_mask]
    good_summary = (
        good.groupby(keys, dropna=False, sort=True)
        .agg(
            N_EPOCHS_GOOD=("TARGETID", "size"),
            N_TARGETIDS_GOOD=("TARGETID", "nunique"),
            N_GROUPS_GOOD=("GROUP_ID", "nunique") if "GROUP_ID" in good.columns else ("TARGETID", "nunique"),
        )
        .reset_index()
    )

    repeat_key = "GROUP_ID" if "GROUP_ID" in good.columns else "TARGETID"
    repeat_summary = (
        good.groupby(keys + [repeat_key], dropna=False, sort=False)
        .size()
        .rename("N_GOOD_EPOCHS")
        .reset_index()
    )
    repeat_summary = (
        repeat_summary[repeat_summary["N_GOOD_EPOCHS"] >= 2]
        .groupby(keys, dropna=False, sort=True)
        .agg(N_GROUPS_2PLUS_GOOD_EPOCHS=(repeat_key, "nunique"))
        .reset_index()
    )

    result = raw.merge(good_summary, on=keys, how="left").merge(
        repeat_summary, on=keys, how="left"
    )
    count_columns = [
        "N_EPOCHS_GOOD",
        "N_TARGETIDS_GOOD",
        "N_GROUPS_GOOD",
        "N_GROUPS_2PLUS_GOOD_EPOCHS",
    ]
    for column in count_columns:
        result[column] = result[column].fillna(0).astype(int)
    result["GOOD_EPOCH_FRACTION"] = result["N_EPOCHS_GOOD"] / result["N_EPOCHS_RAW"].clip(lower=1)
    if "_ALL" in result.columns:
        result = result.drop(columns=["_ALL"])
    return result


def run_audit(
    frame: pd.DataFrame,
    rules: QualityRules = QualityRules(),
    max_pairs_per_source: int = 50,
    run_program_night: bool = False,
    program_night_folds: int = 5,
    program_night_min_pairs_per_label: int = 200,
    program_night_run_permutation: bool = True,
    program_night_permutations: int = 20,
    correction_summary: dict[str, object] | None = None,
    run_manifest: dict[str, object] | None = None,
) -> AuditOutputs:
    mask = quality_mask(frame, rules)
    source_summary = summarize_sources(frame, mask)
    pairs = build_pair_table(frame, mask, max_pairs_per_source=max_pairs_per_source)
    epoch_quality = summarize_epoch_quality(frame, mask)
    overall = summarize_pair_residuals(pairs)
    formal_overall = (
        summarize_pair_residuals(pairs, z_column="PAIR_Z_FORMAL")
        if "PAIR_Z_FORMAL" in pairs.columns
        else pd.DataFrame()
    )

    if "PROGRAM_PAIR" in pairs.columns and not pairs.empty:
        by_program = summarize_pair_residuals(pairs, "PROGRAM_PAIR", z_column="PROGRAM_PAIR_Z")
        formal_by_program = summarize_pair_residuals(
            pairs,
            "PROGRAM_PAIR",
            z_column="PROGRAM_PAIR_Z_FORMAL",
        )
        interday = pairs[pairs["DELTA_DAYS"] > 1.0]
        interday_by_program = summarize_pair_residuals(
            interday,
            "PROGRAM_PAIR",
            z_column="PROGRAM_PAIR_Z",
        )
        formal_interday_by_program = summarize_pair_residuals(
            interday,
            "PROGRAM_PAIR",
            z_column="PROGRAM_PAIR_Z_FORMAL",
        )
    else:
        by_program = pd.DataFrame()
        formal_by_program = pd.DataFrame()
        interday_by_program = pd.DataFrame()
        formal_interday_by_program = pd.DataFrame()

    if "SN_R_MIN" in pairs.columns and pairs["SN_R_MIN"].notna().sum() >= 10:
        pairs_with_bins = add_quantile_bin(pairs, "SN_R_MIN", bins=6)
        by_sn = summarize_pair_residuals(pairs_with_bins, "SN_R_MIN_BIN")
        by_sn["SN_R_MIN_BIN"] = by_sn["SN_R_MIN_BIN"].astype(str)
    else:
        by_sn = pd.DataFrame()

    reasons = rejection_reasons(frame, rules)
    rejection_counts = (
        reasons.sum(axis=0)
        .rename("N_REJECTED")
        .to_frame()
        .assign(FRACTION=lambda data: data["N_REJECTED"] / max(len(frame), 1))
        .reset_index(names="REASON")
    )
    correction_summary_frame = pd.DataFrame([correction_summary or {}])
    if run_program_night:
        program_night_result = run_program_night_experiment(
            pairs,
            n_folds=program_night_folds,
            min_pairs_per_label=program_night_min_pairs_per_label,
            run_permutation=program_night_run_permutation,
            n_permutations=program_night_permutations,
        )
        program_night_summary = program_night_result.summary
        program_night_by_program = program_night_result.by_program
        program_night_offsets = program_night_result.offsets
        program_night_reproducibility = program_night_result.reproducibility
        program_night_permutation_summary = program_night_result.permutation_summary
    else:
        program_night_summary = pd.DataFrame()
        program_night_by_program = pd.DataFrame()
        program_night_offsets = pd.DataFrame()
        program_night_reproducibility = pd.DataFrame()
        program_night_permutation_summary = pd.DataFrame()

    return AuditOutputs(
        source_summary=source_summary,
        pairs=pairs,
        epoch_quality_by_program=epoch_quality,
        calibration_overall=overall,
        calibration_formal_overall=formal_overall,
        calibration_by_program=by_program,
        calibration_formal_by_program=formal_by_program,
        calibration_interday_by_program=interday_by_program,
        calibration_formal_interday_by_program=formal_interday_by_program,
        calibration_by_sn=by_sn,
        rejection_counts=rejection_counts,
        correction_summary=correction_summary_frame,
        program_night_summary=program_night_summary,
        program_night_by_program=program_night_by_program,
        program_night_offsets=program_night_offsets,
        program_night_reproducibility=program_night_reproducibility,
        program_night_permutation_summary=program_night_permutation_summary,
        run_manifest=run_manifest or {},
    )


def save_outputs(
    outputs: AuditOutputs,
    output_dir: str | Path,
    write_heavy_outputs: bool = True,
) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if write_heavy_outputs:
        outputs.source_summary.to_csv(output_dir / "source_summary.csv", index=False)
        outputs.pairs.to_csv(output_dir / "pairs.csv", index=False)
    else:
        outputs.source_summary["classification"].value_counts().rename_axis(
            "classification"
        ).reset_index(name="N_SOURCES").to_csv(
            output_dir / "source_classification_counts.csv",
            index=False,
        )
        outputs.source_summary.loc[
            outputs.source_summary["classification"] == "candidate_variable"
        ].to_csv(output_dir / "candidate_sources.csv", index=False)
        strict = outputs.source_summary[
            (outputs.source_summary["classification"] == "candidate_variable")
            & (outputs.source_summary["n_epochs_good"] >= 3)
            & (outputs.source_summary["time_baseline_days"] > 1.0)
        ]
        strict.to_csv(output_dir / "candidate_sources_strict.csv", index=False)
    outputs.epoch_quality_by_program.to_csv(output_dir / "epoch_quality_by_program.csv", index=False)
    outputs.calibration_overall.to_csv(output_dir / "calibration_overall.csv", index=False)
    outputs.calibration_formal_overall.to_csv(
        output_dir / "calibration_formal_overall.csv",
        index=False,
    )
    outputs.calibration_by_program.to_csv(output_dir / "calibration_by_program.csv", index=False)
    outputs.calibration_formal_by_program.to_csv(
        output_dir / "calibration_formal_by_program.csv",
        index=False,
    )
    outputs.calibration_interday_by_program.to_csv(
        output_dir / "calibration_interday_by_program.csv",
        index=False,
    )
    outputs.calibration_formal_interday_by_program.to_csv(
        output_dir / "calibration_formal_interday_by_program.csv",
        index=False,
    )
    outputs.calibration_by_sn.to_csv(output_dir / "calibration_by_sn.csv", index=False)
    outputs.rejection_counts.to_csv(output_dir / "rejection_counts.csv", index=False)
    outputs.correction_summary.to_csv(output_dir / "correction_summary.csv", index=False)
    outputs.program_night_summary.to_csv(output_dir / "program_night_summary.csv", index=False)
    outputs.program_night_by_program.to_csv(
        output_dir / "program_night_by_program.csv",
        index=False,
    )
    outputs.program_night_offsets.to_csv(
        output_dir / "program_night_offsets.csv",
        index=False,
    )
    outputs.program_night_reproducibility.to_csv(
        output_dir / "program_night_reproducibility.csv",
        index=False,
    )
    outputs.program_night_permutation_summary.to_csv(
        output_dir / "program_night_permutation_summary.csv",
        index=False,
    )
    write_manifest(output_dir / "run_manifest.json", outputs.run_manifest)


def load_and_run(
    paths: list[str],
    output_dir: str | Path,
    max_rows_per_file: int | None = None,
    min_sn_r: float = 5.0,
    max_pairs_per_source: int = 50,
    write_heavy_outputs: bool = True,
    backup_correction_path: str | Path | None = None,
    backup_correction_md5: str | None = None,
    strict_desi_main: bool = False,
    run_program_night: bool = False,
    program_night_folds: int = 5,
    program_night_min_pairs_per_label: int = 200,
    program_night_run_permutation: bool = True,
    program_night_permutations: int = 20,
) -> AuditOutputs:
    frame = load_many(paths, max_rows_per_file=max_rows_per_file, strict_desi_main=strict_desi_main)
    frame = apply_velocity_calibration(
        frame,
        backup_correction_path=backup_correction_path,
        expected_backup_correction_md5=backup_correction_md5,
    )
    correction_summary = frame.attrs.get("backup_correction_summary", {})
    parameters = {
        "max_rows_per_file": max_rows_per_file,
        "min_sn_r": min_sn_r,
        "max_pairs_per_source": max_pairs_per_source,
        "write_heavy_outputs": write_heavy_outputs,
        "strict_desi_main": strict_desi_main,
        "backup_correction_md5": backup_correction_md5,
        "run_program_night": run_program_night,
        "program_night_folds": program_night_folds,
        "program_night_min_pairs_per_label": program_night_min_pairs_per_label,
        "program_night_run_permutation": program_night_run_permutation,
        "program_night_permutations": program_night_permutations,
    }
    manifest = build_manifest(paths, correction_summary, parameters)
    outputs = run_audit(
        frame,
        rules=QualityRules(min_sn_r=min_sn_r),
        max_pairs_per_source=max_pairs_per_source,
        run_program_night=run_program_night,
        program_night_folds=program_night_folds,
        program_night_min_pairs_per_label=program_night_min_pairs_per_label,
        program_night_run_permutation=program_night_run_permutation,
        program_night_permutations=program_night_permutations,
        correction_summary=correction_summary,
        run_manifest=manifest,
    )
    save_outputs(outputs, output_dir, write_heavy_outputs=write_heavy_outputs)
    return outputs
