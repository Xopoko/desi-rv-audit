from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import lsqr


@dataclass(frozen=True)
class ProgramNightResult:
    summary: pd.DataFrame
    by_program: pd.DataFrame
    offsets: pd.DataFrame
    reproducibility: pd.DataFrame
    permutation_summary: pd.DataFrame


DEFAULT_MAX_ABS_Z = 5.0
DEFAULT_CLIP_SIGMA = 3.5
DEFAULT_CLIP_ITERATIONS = 3
DEFAULT_DAMP = 0.2
DEFAULT_MIN_DELTA_DAYS = 1.0


class _DisjointSet:
    def __init__(self, n: int) -> None:
        self.parent = np.arange(n, dtype=np.int64)
        self.size = np.ones(n, dtype=np.int64)

    def find(self, value: int) -> int:
        root = value
        while self.parent[root] != root:
            root = int(self.parent[root])
        while self.parent[value] != value:
            parent = int(self.parent[value])
            self.parent[value] = root
            value = parent
        return root

    def union(self, first: int, second: int) -> None:
        root_first = self.find(first)
        root_second = self.find(second)
        if root_first == root_second:
            return
        if self.size[root_first] < self.size[root_second]:
            root_first, root_second = root_second, root_first
        self.parent[root_second] = root_first
        self.size[root_first] += self.size[root_second]


def _hash_mod(values: pd.Series, modulo: int) -> np.ndarray:
    hashed = pd.util.hash_pandas_object(values.astype("string"), index=False).to_numpy(
        dtype=np.uint64
    )
    return (hashed % np.uint64(modulo)).astype(np.int64)


def _program_night_label(program: pd.Series, night: pd.Series) -> pd.Series:
    return (
        program.astype("string").str.strip().str.upper().fillna("UNKNOWN")
        + ":"
        + night.astype("string").str.strip().fillna("UNKNOWN")
    )


def _seed_for(label: str) -> int:
    return int(
        pd.util.hash_pandas_object(pd.Series([label]), index=False).iloc[0]
        % np.uint64(2**32)
    )


def _exposure_night_map(pairs: pd.DataFrame, permutation_index: int) -> pd.Series:
    first = pairs[["PROGRAM_1", "NIGHT_1", "EXPOSURE_KEY_1"]].rename(
        columns={"PROGRAM_1": "PROGRAM", "NIGHT_1": "NIGHT", "EXPOSURE_KEY_1": "EXPOSURE_KEY"}
    )
    second = pairs[["PROGRAM_2", "NIGHT_2", "EXPOSURE_KEY_2"]].rename(
        columns={"PROGRAM_2": "PROGRAM", "NIGHT_2": "NIGHT", "EXPOSURE_KEY_2": "EXPOSURE_KEY"}
    )
    exposures = pd.concat([first, second], ignore_index=True)
    exposures["PROGRAM"] = exposures["PROGRAM"].astype("string").str.strip().str.upper()
    exposures["NIGHT"] = exposures["NIGHT"].astype("string").str.strip()
    exposures["EXPOSURE_KEY"] = exposures["EXPOSURE_KEY"].astype("string").str.strip()
    conflicts = (
        exposures.groupby("EXPOSURE_KEY", dropna=False)["NIGHT"]
        .nunique(dropna=False)
        .loc[lambda values: values > 1]
    )
    if not conflicts.empty:
        examples = ", ".join(map(str, conflicts.index[:5].tolist()))
        raise ValueError(
            "One exposure key maps to multiple nights; examples: "
            f"{examples}"
        )
    exposures = exposures.drop_duplicates("EXPOSURE_KEY", keep="first")
    shuffled = pd.Series(index=exposures.index, dtype="string")
    for program_label, group in exposures.groupby("PROGRAM", sort=True):
        values = group["NIGHT"].to_numpy(dtype=object)
        if len(values) < 2:
            permuted = values
        else:
            rng = np.random.default_rng(_seed_for(f"{program_label}:{permutation_index}"))
            permutation = rng.permutation(len(values))
            if np.array_equal(permutation, np.arange(len(values))):
                permutation = np.roll(permutation, 1)
            permuted = values[permutation]
        shuffled.loc[group.index] = pd.Series(permuted, index=group.index, dtype="string")
    return pd.Series(shuffled.to_numpy(), index=exposures["EXPOSURE_KEY"].astype(str), dtype="string")


def _robust_width(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan")
    q16, q84 = np.quantile(values, [0.16, 0.84])
    return float((q84 - q16) / 2.0)


def _metrics(residual: np.ndarray, formal_error: np.ndarray, floor: np.ndarray) -> dict[str, float | int]:
    residual = np.asarray(residual, dtype=float)
    formal_error = np.asarray(formal_error, dtype=float)
    floor = np.asarray(floor, dtype=float)
    variance = np.square(formal_error) + np.square(floor)
    valid = np.isfinite(residual) & np.isfinite(variance) & (variance > 0)
    if not np.any(valid):
        return {
            "N_PAIRS": 0,
            "RAW_WIDTH_KMS": np.nan,
            "MEDIAN_KMS": np.nan,
            "WIDTH_Z": np.nan,
            "TAIL_GT_3": np.nan,
            "TAIL_GT_5": np.nan,
            "MEAN_GAUSSIAN_PAIR_LOSS": np.nan,
        }
    residual = residual[valid]
    variance = variance[valid]
    z = residual / np.sqrt(variance)
    return {
        "N_PAIRS": int(residual.size),
        "RAW_WIDTH_KMS": _robust_width(residual),
        "MEDIAN_KMS": float(np.median(residual)),
        "WIDTH_Z": _robust_width(z),
        "TAIL_GT_3": float(np.mean(np.abs(z) > 3.0)),
        "TAIL_GT_5": float(np.mean(np.abs(z) > 5.0)),
        "MEAN_GAUSSIAN_PAIR_LOSS": float(
            np.mean(0.5 * (np.square(z) + np.log(2.0 * np.pi * variance)))
        ),
    }


def _estimate_pair_floors(
    train: pd.DataFrame,
    residual_column: str,
    min_pairs: int,
) -> pd.Series:
    floors: dict[str, float] = {}
    global_width = _robust_width(train[residual_column].to_numpy(dtype=float))
    global_formal2 = np.nanmedian(np.square(train["PAIR_ERROR_FORMAL"].to_numpy(dtype=float)))
    global_floor = float(np.sqrt(max(global_width * global_width - global_formal2, 0.0)))
    for program_pair, group in train.groupby("PROGRAM_PAIR", dropna=False, sort=True):
        if len(group) < min_pairs:
            floors[str(program_pair)] = global_floor
            continue
        width = _robust_width(group[residual_column].to_numpy(dtype=float))
        formal2 = np.nanmedian(np.square(group["PAIR_ERROR_FORMAL"].to_numpy(dtype=float)))
        floors[str(program_pair)] = float(np.sqrt(max(width * width - formal2, 0.0)))
    return pd.Series(floors, dtype=float)


def _prepare_pairs(
    pairs: pd.DataFrame,
    shuffled: bool = False,
    permutation_index: int = 0,
    min_delta_days: float = DEFAULT_MIN_DELTA_DAYS,
) -> pd.DataFrame:
    required = [
        "GROUP_ID",
        "DELTA_VRAD",
        "PAIR_ERROR",
        "PAIR_ERROR_FORMAL",
        "PROGRAM_1",
        "PROGRAM_2",
        "NIGHT_1",
        "NIGHT_2",
        "PROGRAM_PAIR",
        "DELTA_DAYS",
        "EXPOSURE_KEY_1",
        "EXPOSURE_KEY_2",
    ]
    missing = [column for column in required if column not in pairs.columns]
    if missing:
        return pd.DataFrame()
    optional = [column for column in ("GROUP_KIND",) if column in pairs.columns]
    data = pairs[required + optional].copy()
    if shuffled:
        exposure_nights = _exposure_night_map(data, permutation_index=permutation_index)
        night1 = data["EXPOSURE_KEY_1"].astype(str).map(exposure_nights)
        night2 = data["EXPOSURE_KEY_2"].astype(str).map(exposure_nights)
    else:
        night1 = data["NIGHT_1"]
        night2 = data["NIGHT_2"]
    data["LABEL_1"] = _program_night_label(data["PROGRAM_1"], night1)
    data["LABEL_2"] = _program_night_label(data["PROGRAM_2"], night2)
    data["GROUP_ID"] = pd.to_numeric(data["GROUP_ID"], errors="coerce").astype("Int64")
    numeric = ["DELTA_VRAD", "PAIR_ERROR", "PAIR_ERROR_FORMAL", "DELTA_DAYS"]
    for column in numeric:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    mask = (
        data["GROUP_ID"].notna()
        & np.isfinite(data["DELTA_VRAD"])
        & np.isfinite(data["PAIR_ERROR"])
        & np.isfinite(data["PAIR_ERROR_FORMAL"])
        & (data["PAIR_ERROR"] > 0)
        & (data["PAIR_ERROR_FORMAL"] > 0)
        & (data["DELTA_DAYS"] > min_delta_days)
        & data["LABEL_1"].ne(data["LABEL_2"])
    )
    return data.loc[mask].copy()


def _fit_offsets(
    train: pd.DataFrame,
    min_pairs_per_label: int,
    max_abs_z: float,
    clip_sigma: float,
    n_clip_iterations: int,
    damp: float,
) -> tuple[pd.Series, pd.Series, dict]:
    endpoint_counts = pd.concat([train["LABEL_1"], train["LABEL_2"]], ignore_index=True).value_counts()
    kept = endpoint_counts[endpoint_counts >= min_pairs_per_label].index
    work = train[train["LABEL_1"].isin(kept) & train["LABEL_2"].isin(kept)].copy()
    work["_Z0"] = work["DELTA_VRAD"] / work["PAIR_ERROR"]
    work = work[np.abs(work["_Z0"]) <= max_abs_z]
    labels = pd.Index(sorted(pd.unique(pd.concat([work["LABEL_1"], work["LABEL_2"]]))))
    if len(work) == 0 or len(labels) < 2:
        return pd.Series(dtype=float), pd.Series(dtype=int), {
            "N_LABELS": int(len(labels)),
            "N_TRAIN_PAIRS": 0,
            "N_CONNECTED_COMPONENTS": 0,
            "LARGEST_COMPONENT_LABEL_FRACTION": np.nan,
            "LARGEST_COMPONENT_PAIR_FRACTION": np.nan,
            "LSQR_ISTOP": np.nan,
            "LSQR_ITERS": 0,
            "LSQR_ACOND": np.nan,
            "LSQR_R1NORM": np.nan,
            "LSQR_ARNORM": np.nan,
        }

    label_index = {label: idx for idx, label in enumerate(labels)}
    dsu = _DisjointSet(len(labels))
    left_idx = work["LABEL_1"].map(label_index).to_numpy(dtype=np.int64)
    right_idx = work["LABEL_2"].map(label_index).to_numpy(dtype=np.int64)
    for left, right in zip(left_idx, right_idx):
        dsu.union(int(left), int(right))
    component_roots = np.asarray([dsu.find(idx) for idx in range(len(labels))], dtype=np.int64)
    roots, component_ids = np.unique(component_roots, return_inverse=True)
    label_components = pd.Series(component_ids, index=labels, dtype=int)
    component_pair_counts = pd.Series(component_ids[left_idx]).value_counts()

    def solve(current: pd.DataFrame):
        row = np.arange(len(current), dtype=np.int64)
        current_left_idx = current["LABEL_1"].map(label_index).to_numpy(dtype=np.int64)
        current_right_idx = current["LABEL_2"].map(label_index).to_numpy(dtype=np.int64)
        source_counts = current["GROUP_ID"].value_counts()
        source_scale = current["GROUP_ID"].map(source_counts).to_numpy(dtype=float)
        row_weight = (1.0 / current["PAIR_ERROR"].to_numpy(dtype=float)) / np.sqrt(source_scale)
        matrix = coo_matrix(
            (
                np.r_[row_weight, -row_weight],
                (np.r_[row, row], np.r_[current_left_idx, current_right_idx]),
            ),
            shape=(len(current), len(labels)),
        ).tocsr()
        y = current["DELTA_VRAD"].to_numpy(dtype=float) * row_weight
        fit = lsqr(matrix, y, damp=damp, atol=1e-8, btol=1e-8, iter_lim=500)
        fit_offsets = fit[0]
        for component in np.unique(component_ids):
            component_mask = component_ids == component
            fit_offsets[component_mask] -= np.mean(fit_offsets[component_mask])
        return fit, fit_offsets

    keep_mask = np.ones(len(work), dtype=bool)
    solution = None
    offsets = np.zeros(len(labels), dtype=float)
    for _ in range(max(n_clip_iterations, 1)):
        current = work.loc[keep_mask].copy()
        if current.empty:
            break
        solution, offsets = solve(current)
        predicted = (
            work["LABEL_1"].map(pd.Series(offsets, index=labels)).to_numpy(dtype=float)
            - work["LABEL_2"].map(pd.Series(offsets, index=labels)).to_numpy(dtype=float)
        )
        z = (work["DELTA_VRAD"].to_numpy(dtype=float) - predicted) / work[
            "PAIR_ERROR"
        ].to_numpy(dtype=float)
        keep_mask = np.abs(z) <= clip_sigma
    final_current = work.loc[keep_mask].copy()
    if not final_current.empty:
        solution, offsets = solve(final_current)

    label_component_sizes = pd.Series(component_ids).value_counts()
    stats = {
        "N_LABELS": int(len(labels)),
        "N_TRAIN_PAIRS": int(len(final_current)),
        "N_CONNECTED_COMPONENTS": int(len(roots)),
        "LARGEST_COMPONENT_LABEL_FRACTION": float(label_component_sizes.max() / len(labels)),
        "LARGEST_COMPONENT_PAIR_FRACTION": float(component_pair_counts.max() / max(len(work), 1)),
        "LSQR_ISTOP": int(solution[1]) if solution is not None else np.nan,
        "LSQR_ITERS": int(solution[2]) if solution is not None else 0,
        "LSQR_ACOND": float(solution[6]) if solution is not None else np.nan,
        "LSQR_R1NORM": float(solution[3]) if solution is not None else np.nan,
        "LSQR_ARNORM": float(solution[7]) if solution is not None else np.nan,
    }
    return pd.Series(offsets, index=labels), label_components, stats


def _evaluate_fold(
    fold: int,
    train: pd.DataFrame,
    holdout: pd.DataFrame,
    min_pairs_per_label: int,
    max_abs_z: float,
    clip_sigma: float,
    n_clip_iterations: int,
    damp: float,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    offsets, components, stats = _fit_offsets(
        train,
        min_pairs_per_label=min_pairs_per_label,
        max_abs_z=max_abs_z,
        clip_sigma=clip_sigma,
        n_clip_iterations=n_clip_iterations,
        damp=damp,
    )
    holdout = holdout.copy()
    holdout["_OFFSET_1"] = holdout["LABEL_1"].map(offsets)
    holdout["_OFFSET_2"] = holdout["LABEL_2"].map(offsets)
    holdout["_COMP_1"] = holdout["LABEL_1"].map(components)
    holdout["_COMP_2"] = holdout["LABEL_2"].map(components)
    same_component = (
        holdout["_OFFSET_1"].notna()
        & holdout["_OFFSET_2"].notna()
        & holdout["_COMP_1"].eq(holdout["_COMP_2"])
    )
    holdout_same = holdout.loc[same_component].copy()
    if holdout_same.empty:
        summary = {
            "FOLD": fold,
            **stats,
            "N_HOLDOUT_PAIRS": int(len(holdout)),
            "N_HOLDOUT_SAME_COMPONENT": 0,
            "N_HOLDOUT_CROSS_COMPONENT": int(len(holdout)),
        }
        return summary, pd.DataFrame(), pd.DataFrame()

    train = train.copy()
    train["_OFFSET_1"] = train["LABEL_1"].map(offsets)
    train["_OFFSET_2"] = train["LABEL_2"].map(offsets)
    train["_RESID_AFTER"] = train["DELTA_VRAD"] - (train["_OFFSET_1"] - train["_OFFSET_2"])
    train = train[np.isfinite(train["_RESID_AFTER"])]
    floors = _estimate_pair_floors(train, "_RESID_AFTER", min_pairs=min_pairs_per_label)
    fallback_floor = float(floors.median()) if not floors.empty else 0.0

    holdout_same["_RESID_BEFORE"] = holdout_same["DELTA_VRAD"]
    holdout_same["_RESID_AFTER"] = holdout_same["DELTA_VRAD"] - (
        holdout_same["_OFFSET_1"] - holdout_same["_OFFSET_2"]
    )
    holdout_same["_PAIR_FLOOR"] = (
        holdout_same["PROGRAM_PAIR"].astype(str).map(floors).fillna(fallback_floor)
    )

    before = _metrics(
        holdout_same["_RESID_BEFORE"].to_numpy(dtype=float),
        holdout_same["PAIR_ERROR_FORMAL"].to_numpy(dtype=float),
        holdout_same["_PAIR_FLOOR"].to_numpy(dtype=float),
    )
    after = _metrics(
        holdout_same["_RESID_AFTER"].to_numpy(dtype=float),
        holdout_same["PAIR_ERROR_FORMAL"].to_numpy(dtype=float),
        holdout_same["_PAIR_FLOOR"].to_numpy(dtype=float),
    )
    by_program_records = []
    for program_pair, group in holdout_same.groupby("PROGRAM_PAIR", dropna=False, sort=True):
        before_program = _metrics(
            group["_RESID_BEFORE"].to_numpy(dtype=float),
            group["PAIR_ERROR_FORMAL"].to_numpy(dtype=float),
            group["_PAIR_FLOOR"].to_numpy(dtype=float),
        )
        after_program = _metrics(
            group["_RESID_AFTER"].to_numpy(dtype=float),
            group["PAIR_ERROR_FORMAL"].to_numpy(dtype=float),
            group["_PAIR_FLOOR"].to_numpy(dtype=float),
        )
        by_program_records.append(
            {
                "FOLD": fold,
                "PROGRAM_PAIR": program_pair,
                "N_HOLDOUT_PAIRS": before_program["N_PAIRS"],
                "RAW_WIDTH_BEFORE_KMS": before_program["RAW_WIDTH_KMS"],
                "RAW_WIDTH_AFTER_KMS": after_program["RAW_WIDTH_KMS"],
                "WIDTH_BEFORE_Z": before_program["WIDTH_Z"],
                "WIDTH_AFTER_Z": after_program["WIDTH_Z"],
                "TAIL_GT_3_BEFORE": before_program["TAIL_GT_3"],
                "TAIL_GT_3_AFTER": after_program["TAIL_GT_3"],
                "TAIL_GT_5_BEFORE": before_program["TAIL_GT_5"],
                "TAIL_GT_5_AFTER": after_program["TAIL_GT_5"],
                "GAUSSIAN_PAIR_LOSS_BEFORE": before_program["MEAN_GAUSSIAN_PAIR_LOSS"],
                "GAUSSIAN_PAIR_LOSS_AFTER": after_program["MEAN_GAUSSIAN_PAIR_LOSS"],
                "TRAIN_PAIR_FLOOR_KMS": float(floors.get(str(program_pair), fallback_floor)),
            }
        )
    by_program = pd.DataFrame.from_records(by_program_records)
    macro_width_before = float(by_program["WIDTH_BEFORE_Z"].mean()) if not by_program.empty else np.nan
    macro_width_after = float(by_program["WIDTH_AFTER_Z"].mean()) if not by_program.empty else np.nan
    macro_loss_before = (
        float(by_program["GAUSSIAN_PAIR_LOSS_BEFORE"].mean()) if not by_program.empty else np.nan
    )
    macro_loss_after = (
        float(by_program["GAUSSIAN_PAIR_LOSS_AFTER"].mean()) if not by_program.empty else np.nan
    )
    summary = {
        "FOLD": fold,
        **stats,
        "N_HOLDOUT_PAIRS": int(len(holdout)),
        "N_HOLDOUT_SAME_COMPONENT": int(len(holdout_same)),
        "N_HOLDOUT_CROSS_COMPONENT": int(len(holdout) - len(holdout_same)),
        "BEFORE_RAW_WIDTH_KMS": before["RAW_WIDTH_KMS"],
        "AFTER_RAW_WIDTH_KMS": after["RAW_WIDTH_KMS"],
        "BEFORE_WIDTH_Z": before["WIDTH_Z"],
        "AFTER_WIDTH_Z": after["WIDTH_Z"],
        "BEFORE_TAIL_GT_3": before["TAIL_GT_3"],
        "AFTER_TAIL_GT_3": after["TAIL_GT_3"],
        "BEFORE_TAIL_GT_5": before["TAIL_GT_5"],
        "AFTER_TAIL_GT_5": after["TAIL_GT_5"],
        "BEFORE_MEAN_GAUSSIAN_PAIR_LOSS": before["MEAN_GAUSSIAN_PAIR_LOSS"],
        "AFTER_MEAN_GAUSSIAN_PAIR_LOSS": after["MEAN_GAUSSIAN_PAIR_LOSS"],
        "MACRO_WIDTH_BEFORE_Z": macro_width_before,
        "MACRO_WIDTH_AFTER_Z": macro_width_after,
        "MACRO_GAUSSIAN_PAIR_LOSS_BEFORE": macro_loss_before,
        "MACRO_GAUSSIAN_PAIR_LOSS_AFTER": macro_loss_after,
    }
    offsets_table = pd.DataFrame(
        {
            "FOLD": fold,
            "LABEL": offsets.index.astype(str),
            "OFFSET_KMS": offsets.to_numpy(dtype=float),
            "COMPONENT": offsets.index.map(components).to_numpy(dtype=int),
        }
    )
    return summary, by_program, offsets_table


def _run_folds(
    base: pd.DataFrame,
    n_folds: int,
    min_pairs_per_label: int,
    max_abs_z: float,
    clip_sigma: float,
    n_clip_iterations: int,
    damp: float,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fold_ids = _hash_mod(base["GROUP_ID"], n_folds)
    summaries = []
    by_program = []
    offsets = []
    for fold in range(n_folds):
        holdout = base.loc[fold_ids == fold].copy()
        train = base.loc[fold_ids != fold].copy()
        summary, fold_by_program, fold_offsets = _evaluate_fold(
            fold,
            train,
            holdout,
            min_pairs_per_label=min_pairs_per_label,
            max_abs_z=max_abs_z,
            clip_sigma=clip_sigma,
            n_clip_iterations=n_clip_iterations,
            damp=damp,
        )
        summaries.append(summary)
        if not fold_by_program.empty:
            by_program.append(fold_by_program)
        if not fold_offsets.empty:
            offsets.append(fold_offsets)
    return (
        pd.DataFrame.from_records(summaries),
        pd.concat(by_program, ignore_index=True, sort=False) if by_program else pd.DataFrame(),
        pd.concat(offsets, ignore_index=True, sort=False) if offsets else pd.DataFrame(),
    )


def _reproducibility(
    base: pd.DataFrame,
    min_pairs_per_label: int,
    max_abs_z: float,
    clip_sigma: float,
    n_clip_iterations: int,
    damp: float,
) -> pd.DataFrame:
    half = _hash_mod(base["GROUP_ID"], 2)
    offsets = []
    for label, mask_value in (("A", 0), ("B", 1)):
        offset, components, stats = _fit_offsets(
            base.loc[half == mask_value].copy(),
            min_pairs_per_label=min_pairs_per_label,
            max_abs_z=max_abs_z,
            clip_sigma=clip_sigma,
            n_clip_iterations=n_clip_iterations,
            damp=damp,
        )
        frame = pd.DataFrame(
            {
                "LABEL": offset.index.astype(str),
                f"OFFSET_{label}_KMS": offset.to_numpy(dtype=float),
                f"COMPONENT_{label}": offset.index.map(components).to_numpy(dtype=int),
            }
        )
        for key, value in stats.items():
            frame[f"{label}_{key}"] = value
        offsets.append(frame)
    if len(offsets) != 2:
        return pd.DataFrame()
    merged = offsets[0].merge(offsets[1], on="LABEL", how="inner")
    if merged.empty:
        return pd.DataFrame()
    merged["_COMPONENT_PAIR"] = (
        merged["COMPONENT_A"].astype(str) + "/" + merged["COMPONENT_B"].astype(str)
    )
    largest_component_pair = merged["_COMPONENT_PAIR"].value_counts().idxmax()
    merged = merged[merged["_COMPONENT_PAIR"] == largest_component_pair]
    x = merged["OFFSET_A_KMS"].to_numpy(dtype=float)
    y = merged["OFFSET_B_KMS"].to_numpy(dtype=float)
    valid = np.isfinite(x) & np.isfinite(y)
    x = x[valid]
    y = y[valid]
    gauge_shift = float(np.median(y - x)) if x.size else np.nan
    if x.size:
        y = y - gauge_shift
    if x.size < 2:
        corr = np.nan
        slope = np.nan
    else:
        corr = float(np.corrcoef(x, y)[0, 1])
        slope = float(np.dot(x, y) / max(np.dot(x, x), 1e-12))
    return pd.DataFrame(
        [
            {
                "N_COMMON_LABELS": int(x.size),
                "COMMON_COMPONENT_PAIR": str(largest_component_pair),
                "GAUGE_SHIFT_B_MINUS_A_KMS": gauge_shift,
                "OFFSET_CORRELATION": corr,
                "OFFSET_SLOPE_B_ON_A": slope,
                "MEDIAN_ABS_DIFF_KMS": float(np.median(np.abs(x - y))) if x.size else np.nan,
                "ROBUST_WIDTH_DIFF_KMS": _robust_width(x - y) if x.size else np.nan,
            }
        ]
    )


def run_program_night_experiment(
    pairs: pd.DataFrame,
    n_folds: int = 5,
    min_pairs_per_label: int = 200,
    max_abs_z: float = DEFAULT_MAX_ABS_Z,
    clip_sigma: float = DEFAULT_CLIP_SIGMA,
    n_clip_iterations: int = DEFAULT_CLIP_ITERATIONS,
    damp: float = DEFAULT_DAMP,
    min_delta_days: float = DEFAULT_MIN_DELTA_DAYS,
    run_permutation: bool = True,
    n_permutations: int = 20,
) -> ProgramNightResult:
    base = _prepare_pairs(pairs, shuffled=False, min_delta_days=min_delta_days)
    if base.empty:
        return ProgramNightResult(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )
    summary, by_program, offsets = _run_folds(
        base,
        n_folds=n_folds,
        min_pairs_per_label=min_pairs_per_label,
        max_abs_z=max_abs_z,
        clip_sigma=clip_sigma,
        n_clip_iterations=n_clip_iterations,
        damp=damp,
    )
    summary["N_PROGRAM_NIGHT_PAIRS"] = int(len(base))
    if "GROUP_KIND" in base.columns:
        gaia_pairs = int(base["GROUP_KIND"].astype(str).eq("GAIA_SOURCE_ID").sum())
        summary["N_GAIA_GROUP_PAIRS"] = gaia_pairs
        summary["GAIA_GROUP_PAIR_FRACTION"] = gaia_pairs / max(len(base), 1)
    reproducibility = _reproducibility(
        base,
        min_pairs_per_label=min_pairs_per_label,
        max_abs_z=max_abs_z,
        clip_sigma=clip_sigma,
        n_clip_iterations=n_clip_iterations,
        damp=damp,
    )
    permutation_summary = pd.DataFrame()
    if run_permutation:
        permutation_frames = []
        for permutation_index in range(n_permutations):
            shuffled = _prepare_pairs(
                pairs,
                shuffled=True,
                permutation_index=permutation_index,
                min_delta_days=min_delta_days,
            )
            if shuffled.empty:
                continue
            permutation_frame, _, _ = _run_folds(
                shuffled,
                n_folds=n_folds,
                min_pairs_per_label=min_pairs_per_label,
                max_abs_z=max_abs_z,
                clip_sigma=clip_sigma,
                n_clip_iterations=n_clip_iterations,
                damp=damp,
            )
            permutation_frame["PERMUTATION"] = permutation_index
            permutation_frame["CONTROL"] = "SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM"
            permutation_frames.append(permutation_frame)
        if permutation_frames:
            permutation_summary = pd.concat(permutation_frames, ignore_index=True, sort=False)
    return ProgramNightResult(summary, by_program, offsets, reproducibility, permutation_summary)
