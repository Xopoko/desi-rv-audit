"""Exploratory diagnostics for the preregistered E3 result.

These slices are explicitly secondary: they do not alter the E3 decision.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

import run_petal as core  # noqa: E402
from desi_rv_audit.hashing import stable_hash_mod  # noqa: E402
from desi_rv_audit.program_night import _robust_width  # noqa: E402


BY_PROGRAM_OUTPUT = EXPERIMENT_DIR / "petal_cv_by_program.csv"
INDEPENDENT_OFFSETS_OUTPUT = EXPERIMENT_DIR / "petal_independent_program_offsets.csv"
INDEPENDENT_SUMMARY_OUTPUT = EXPERIMENT_DIR / "petal_independent_program_summary.csv"
MANIFEST_OUTPUT = EXPERIMENT_DIR / "petal_diagnostics_manifest.json"


def _evaluate_by_program(
    pairs: pd.DataFrame,
    holdout: pd.DataFrame,
    nested: core.OffsetModel,
    fold: int,
) -> list[dict[str, object]]:
    offset_1 = holdout["LABEL_1"].map(nested.offsets)
    offset_2 = holdout["LABEL_2"].map(nested.offsets)
    component_1 = holdout["LABEL_1"].map(nested.components)
    component_2 = holdout["LABEL_2"].map(nested.components)
    supported = offset_1.notna() & offset_2.notna() & component_1.eq(component_2)
    scored = holdout.loc[supported].copy()
    scored["PROGRAM_PAIR"] = pairs.loc[scored.index, "PROGRAM_PAIR"].astype(str)
    scored["DELTA_NESTED"] = scored["DELTA_BASE"].to_numpy(dtype=float) - (
        offset_1.loc[supported].to_numpy(dtype=float) - offset_2.loc[supported].to_numpy(dtype=float)
    )
    records: list[dict[str, object]] = []
    for program_pair, group in scored.groupby("PROGRAM_PAIR", sort=True):
        raw_width = _robust_width(group["DELTA_RAW"].to_numpy(dtype=float))
        base_width = _robust_width(group["DELTA_BASE"].to_numpy(dtype=float))
        nested_width = _robust_width(group["DELTA_NESTED"].to_numpy(dtype=float))
        records.append(
            {
                "FOLD": fold,
                "PROGRAM_PAIR": program_pair,
                "N_COMMON_SUPPORT": int(len(group)),
                "RAW_WIDTH_UNCORRECTED_KMS": raw_width,
                "RAW_WIDTH_PROGRAM_NIGHT_KMS": base_width,
                "RAW_WIDTH_PROGRAM_NIGHT_PETAL_KMS": nested_width,
                "PROGRAM_NIGHT_GAIN_KMS": raw_width - base_width,
                "INCREMENTAL_PETAL_GAIN_KMS": base_width - nested_width,
            }
        )
    return records


def cv_program_slices(
    pairs: pd.DataFrame,
    fold_ids: np.ndarray,
    base_models: list[core.OffsetModel],
) -> pd.DataFrame:
    petal_1 = pairs["PETAL_1"].to_numpy(dtype=np.int8)
    petal_2 = pairs["PETAL_2"].to_numpy(dtype=np.int8)
    records: list[dict[str, object]] = []
    for fold, base in enumerate(base_models):
        train = core._residual_frame(pairs, fold_ids != fold, base, petal_1, petal_2)
        nested = core._fit_nested(train)
        holdout = core._residual_frame(pairs, fold_ids == fold, base, petal_1, petal_2)
        records.extend(_evaluate_by_program(pairs, holdout, nested, fold))
        print(f"DIAGNOSTIC_CV_FOLD {fold}", flush=True)
    result = pd.DataFrame.from_records(records)
    result.to_csv(BY_PROGRAM_OUTPUT, index=False, lineterminator="\n")
    return result


def independent_program_patterns(pairs: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    petal_1 = pairs["PETAL_1"].to_numpy(dtype=np.int8)
    petal_2 = pairs["PETAL_2"].to_numpy(dtype=np.int8)
    half_ids = stable_hash_mod(pairs["GROUP_ID"], 2)
    records: list[dict[str, object]] = []
    for program in ("BRIGHT", "DARK"):
        for half, value in (("A", 0), ("B", 1)):
            mask = (
                (half_ids == value)
                & pairs["PROGRAM_1"].astype(str).eq(program).to_numpy()
                & pairs["PROGRAM_2"].astype(str).eq(program).to_numpy()
            )
            model, _ = core._fit_nested_scope(
                pairs,
                mask,
                petal_1,
                petal_2,
                f"{program}_{half}_WITHIN_PROGRAM_ONLY",
            )
            table = pd.DataFrame(
                {
                    "LABEL": model.offsets.index.astype(str),
                    "OFFSET_KMS": model.offsets.to_numpy(dtype=float),
                    "COMPONENT": model.offsets.index.map(model.components),
                }
            )
            table["PETAL"] = table["LABEL"].str.rsplit(":P", n=1).str[1].astype(int)
            if table.empty:
                continue
            largest_component = int(table["COMPONENT"].value_counts().idxmax())
            table = table.loc[table["COMPONENT"] == largest_component]
            for petal, group in table.groupby("PETAL", sort=True):
                records.append(
                    {
                        "PROGRAM": program,
                        "HALF": half,
                        "PETAL": int(petal),
                        "N_NIGHTS": int(len(group)),
                        "MEDIAN_OFFSET_KMS": float(group["OFFSET_KMS"].median()),
                        "MEAN_OFFSET_KMS": float(group["OFFSET_KMS"].mean()),
                        "STD_OFFSET_KMS": float(group["OFFSET_KMS"].std()),
                        "COMPONENT": largest_component,
                    }
                )
            print(f"INDEPENDENT_PATTERN {program} {half}", flush=True)
    offsets = pd.DataFrame.from_records(records).sort_values(["PROGRAM", "HALF", "PETAL"])
    offsets.to_csv(INDEPENDENT_OFFSETS_OUTPUT, index=False, lineterminator="\n")

    summaries: list[dict[str, object]] = []
    for direction, p_program, p_half, q_program, q_half in (
        ("BRIGHT_A_DARK_B", "BRIGHT", "A", "DARK", "B"),
        ("BRIGHT_B_DARK_A", "BRIGHT", "B", "DARK", "A"),
    ):
        left = offsets.loc[
            offsets["PROGRAM"].eq(p_program) & offsets["HALF"].eq(p_half),
            ["PETAL", "MEDIAN_OFFSET_KMS"],
        ].rename(columns={"MEDIAN_OFFSET_KMS": "LEFT"})
        right = offsets.loc[
            offsets["PROGRAM"].eq(q_program) & offsets["HALF"].eq(q_half),
            ["PETAL", "MEDIAN_OFFSET_KMS"],
        ].rename(columns={"MEDIAN_OFFSET_KMS": "RIGHT"})
        merged = left.merge(right, on="PETAL", how="inner")
        x = merged["LEFT"].to_numpy(dtype=float)
        y = merged["RIGHT"].to_numpy(dtype=float)
        summaries.append(
            {
                "DIRECTION": direction,
                "N_PETALS": int(len(merged)),
                "PEARSON_R": float(np.corrcoef(x, y)[0, 1]) if len(merged) >= 3 else np.nan,
                "SPEARMAN_RHO": float(spearmanr(x, y).statistic) if len(merged) >= 3 else np.nan,
            }
        )
    summary = pd.DataFrame.from_records(summaries)
    summary.to_csv(INDEPENDENT_SUMMARY_OUTPUT, index=False, lineterminator="\n")
    return offsets, summary


def run() -> None:
    pairs = pd.read_pickle(core.CACHE)
    pairs["PN_1"] = pairs["PROGRAM_1"].astype(str) + ":" + pairs["NIGHT_1"].astype("int64").astype(str)
    pairs["PN_2"] = pairs["PROGRAM_2"].astype(str) + ":" + pairs["NIGHT_2"].astype("int64").astype(str)
    fold_ids = stable_hash_mod(pairs["GROUP_ID"], core.N_FOLDS)
    # Refit once here to normalize the transient cache away from the
    # ``__main__`` pickle identity created by the first direct script run.
    base_models = core.fit_or_load_outer_base_models(pairs, fold_ids, force=True)
    slices = cv_program_slices(pairs, fold_ids, base_models)
    _, independent = independent_program_patterns(pairs)
    manifest = {
        "schema": "desi_rv_audit.petal_diagnostics.v1",
        "status": "complete",
        "role": "exploratory_secondary_not_used_for_E3_decision",
        "program_pair_mean_gains_kms": (
            slices.groupby("PROGRAM_PAIR")["INCREMENTAL_PETAL_GAIN_KMS"].mean().to_dict()
        ),
        "independent_cross_program_patterns": independent.to_dict(orient="records"),
    }
    MANIFEST_OUTPUT.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(manifest, sort_keys=True), flush=True)


if __name__ == "__main__":
    run()
