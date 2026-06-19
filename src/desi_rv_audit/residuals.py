from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import lsqr


DIMENSION_COLUMNS = {
    "PROGRAM": ("PROGRAM_1", "PROGRAM_2"),
    "NIGHT": ("NIGHT_1", "NIGHT_2"),
    "TILEID": ("TILEID_1", "TILEID_2"),
    "EXPID": ("EXPID_1", "EXPID_2"),
    "FIBER": ("FIBER_1", "FIBER_2"),
}


@dataclass(frozen=True)
class ZeroPointResult:
    summary: dict
    offsets: pd.DataFrame
    by_program: pd.DataFrame


def _hash_fraction(values: pd.Series) -> np.ndarray:
    hashed = pd.util.hash_pandas_object(values.astype("string"), index=False).to_numpy(
        dtype=np.uint64
    )
    return hashed.astype(np.float64) / float(np.iinfo(np.uint64).max)


def _as_label(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().fillna("")


def _summarize_z(values: np.ndarray) -> dict[str, float | int]:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {
            "N_PAIRS": 0,
            "MEDIAN_Z": np.nan,
            "ROBUST_WIDTH_Z": np.nan,
            "TAIL_GT_3": np.nan,
            "TAIL_GT_5": np.nan,
        }
    q16, q84 = np.quantile(values, [0.16, 0.84])
    return {
        "N_PAIRS": int(values.size),
        "MEDIAN_Z": float(np.median(values)),
        "ROBUST_WIDTH_Z": float((q84 - q16) / 2.0),
        "TAIL_GT_3": float(np.mean(np.abs(values) > 3.0)),
        "TAIL_GT_5": float(np.mean(np.abs(values) > 5.0)),
    }


def _select_base_pairs(
    pairs: pd.DataFrame,
    columns: tuple[str, str],
    interday_only: bool,
) -> pd.DataFrame:
    left, right = columns
    required = ["GROUP_ID", "DELTA_VRAD", "PAIR_ERROR", "PAIR_Z", left, right]
    missing = [column for column in required if column not in pairs.columns]
    if missing:
        return pd.DataFrame()

    result = pairs[required + (["PROGRAM_PAIR"] if "PROGRAM_PAIR" in pairs.columns else [])].copy()
    result[left] = _as_label(result[left])
    result[right] = _as_label(result[right])
    mask = (
        np.isfinite(pd.to_numeric(result["DELTA_VRAD"], errors="coerce"))
        & np.isfinite(pd.to_numeric(result["PAIR_ERROR"], errors="coerce"))
        & (pd.to_numeric(result["PAIR_ERROR"], errors="coerce") > 0)
        & result[left].ne("")
        & result[right].ne("")
    )
    if interday_only and "DELTA_DAYS" in pairs.columns:
        result["DELTA_DAYS"] = pairs["DELTA_DAYS"]
        mask &= pd.to_numeric(result["DELTA_DAYS"], errors="coerce") > 1.0
    return result.loc[mask].copy()


def estimate_zero_points(
    pairs: pd.DataFrame,
    dimension: str,
    train_fraction: float = 0.5,
    min_pairs_per_label: int = 200,
    max_abs_train_z: float = 5.0,
    interday_only: bool = True,
    damp: float = 0.05,
) -> ZeroPointResult:
    dimension = dimension.upper()
    columns = DIMENSION_COLUMNS[dimension]
    left, right = columns
    base = _select_base_pairs(pairs, columns, interday_only=interday_only)
    empty_summary = {
        "DIMENSION": dimension,
        "N_LABELS": 0,
        "N_TRAIN_PAIRS": 0,
        "N_HOLDOUT_PAIRS": 0,
        "TRAIN_FRACTION": train_fraction,
        "MIN_PAIRS_PER_LABEL": min_pairs_per_label,
        "MAX_ABS_TRAIN_Z": max_abs_train_z,
        "INTERDAY_ONLY": interday_only,
        "LSQR_ISTOP": np.nan,
        "LSQR_ITERS": 0,
        "MAX_ABS_OFFSET_KMS": np.nan,
    }
    if base.empty:
        return ZeroPointResult(empty_summary, pd.DataFrame(), pd.DataFrame())

    split = _hash_fraction(base["GROUP_ID"])
    train_mask = split < train_fraction
    holdout_mask = ~train_mask

    train = base.loc[train_mask].copy()
    train["PAIR_Z"] = pd.to_numeric(train["PAIR_Z"], errors="coerce")
    train = train[np.abs(train["PAIR_Z"]) <= max_abs_train_z]

    label_counts = pd.concat([train[left], train[right]], ignore_index=True).value_counts()
    kept_labels = label_counts[label_counts >= min_pairs_per_label].index
    train = train[
        train[left].isin(kept_labels)
        & train[right].isin(kept_labels)
        & train[left].ne(train[right])
    ]
    labels = pd.Index(sorted(kept_labels.astype(str)))
    label_index = {label: i for i, label in enumerate(labels)}

    if train.empty or len(labels) < 2:
        before = _summarize_z(pd.to_numeric(base.loc[holdout_mask, "PAIR_Z"], errors="coerce"))
        summary = {
            **empty_summary,
            "N_LABELS": int(len(labels)),
            "N_HOLDOUT_PAIRS": int(holdout_mask.sum()),
            **{f"BEFORE_{key}": value for key, value in before.items()},
            **{f"AFTER_{key}": value for key, value in before.items()},
        }
        summary["DELTA_WIDTH_Z"] = 0.0
        summary["DELTA_TAIL_GT_5"] = 0.0
        return ZeroPointResult(summary, pd.DataFrame(), pd.DataFrame())

    row_number = np.arange(len(train), dtype=np.int64)
    left_index = train[left].map(label_index).to_numpy(dtype=np.int64)
    right_index = train[right].map(label_index).to_numpy(dtype=np.int64)
    errors = pd.to_numeric(train["PAIR_ERROR"], errors="coerce").to_numpy(dtype=float)
    weights = 1.0 / errors
    deltas = pd.to_numeric(train["DELTA_VRAD"], errors="coerce").to_numpy(dtype=float)

    matrix = coo_matrix(
        (
            np.r_[weights, -weights],
            (np.r_[row_number, row_number], np.r_[left_index, right_index]),
        ),
        shape=(len(train), len(labels)),
    ).tocsr()
    solution = lsqr(matrix, deltas * weights, damp=damp, atol=1e-8, btol=1e-8, iter_lim=500)
    offsets = solution[0]
    offsets = offsets - np.nanmedian(offsets)
    offset_map = pd.Series(offsets, index=labels)

    holdout = base.loc[holdout_mask].copy()
    holdout_left = holdout[left].map(offset_map).fillna(0.0).to_numpy(dtype=float)
    holdout_right = holdout[right].map(offset_map).fillna(0.0).to_numpy(dtype=float)
    holdout_delta = pd.to_numeric(holdout["DELTA_VRAD"], errors="coerce").to_numpy(dtype=float)
    holdout_error = pd.to_numeric(holdout["PAIR_ERROR"], errors="coerce").to_numpy(dtype=float)
    before_z = pd.to_numeric(holdout["PAIR_Z"], errors="coerce").to_numpy(dtype=float)
    after_z = (holdout_delta - (holdout_left - holdout_right)) / holdout_error

    before = _summarize_z(before_z)
    after = _summarize_z(after_z)
    offset_table = pd.DataFrame(
        {
            "DIMENSION": dimension,
            "LABEL": labels.astype(str),
            "OFFSET_KMS": offsets,
            "N_LABEL_PAIR_ENDPOINTS": labels.map(label_counts).to_numpy(dtype=int),
        }
    ).sort_values("OFFSET_KMS", key=lambda values: np.abs(values), ascending=False)

    by_program = pd.DataFrame()
    if "PROGRAM_PAIR" in holdout.columns:
        records = []
        holdout = holdout.assign(_BEFORE_Z=before_z, _AFTER_Z=after_z)
        for program_pair, group in holdout.groupby("PROGRAM_PAIR", dropna=False, sort=True):
            before_group = _summarize_z(group["_BEFORE_Z"].to_numpy(dtype=float))
            after_group = _summarize_z(group["_AFTER_Z"].to_numpy(dtype=float))
            records.append(
                {
                    "DIMENSION": dimension,
                    "PROGRAM_PAIR": program_pair,
                    "N_HOLDOUT_PAIRS": before_group["N_PAIRS"],
                    "WIDTH_BEFORE": before_group["ROBUST_WIDTH_Z"],
                    "WIDTH_AFTER": after_group["ROBUST_WIDTH_Z"],
                    "TAIL_GT_5_BEFORE": before_group["TAIL_GT_5"],
                    "TAIL_GT_5_AFTER": after_group["TAIL_GT_5"],
                    "MEDIAN_BEFORE": before_group["MEDIAN_Z"],
                    "MEDIAN_AFTER": after_group["MEDIAN_Z"],
                }
            )
        by_program = pd.DataFrame.from_records(records)

    summary = {
        **empty_summary,
        "N_LABELS": int(len(labels)),
        "N_TRAIN_PAIRS": int(len(train)),
        "N_HOLDOUT_PAIRS": int(before["N_PAIRS"]),
        "LSQR_ISTOP": int(solution[1]),
        "LSQR_ITERS": int(solution[2]),
        "MAX_ABS_OFFSET_KMS": float(np.max(np.abs(offsets))) if offsets.size else np.nan,
    }
    summary.update({f"BEFORE_{key}": value for key, value in before.items()})
    summary.update({f"AFTER_{key}": value for key, value in after.items()})
    summary["DELTA_WIDTH_Z"] = summary["AFTER_ROBUST_WIDTH_Z"] - summary[
        "BEFORE_ROBUST_WIDTH_Z"
    ]
    summary["DELTA_TAIL_GT_5"] = summary["AFTER_TAIL_GT_5"] - summary["BEFORE_TAIL_GT_5"]
    return ZeroPointResult(summary, offset_table, by_program)


def run_residual_zero_point_calibration(
    pairs: pd.DataFrame,
    dimensions: list[str] | tuple[str, ...] = ("PROGRAM", "NIGHT", "TILEID", "EXPID", "FIBER"),
    train_fraction: float = 0.5,
    min_pairs_per_label: int = 200,
    max_abs_train_z: float = 5.0,
    interday_only: bool = True,
    damp: float = 0.05,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], pd.DataFrame]:
    summaries = []
    offsets: dict[str, pd.DataFrame] = {}
    by_program_frames = []
    for dimension in dimensions:
        dimension = dimension.upper()
        if dimension not in DIMENSION_COLUMNS:
            continue
        result = estimate_zero_points(
            pairs,
            dimension,
            train_fraction=train_fraction,
            min_pairs_per_label=min_pairs_per_label,
            max_abs_train_z=max_abs_train_z,
            interday_only=interday_only,
            damp=damp,
        )
        summaries.append(result.summary)
        if not result.offsets.empty:
            offsets[dimension] = result.offsets
        if not result.by_program.empty:
            by_program_frames.append(result.by_program)

    summary = pd.DataFrame.from_records(summaries)
    by_program = (
        pd.concat(by_program_frames, ignore_index=True, sort=False)
        if by_program_frames
        else pd.DataFrame()
    )
    return summary, offsets, by_program
