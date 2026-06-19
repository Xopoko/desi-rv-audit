from __future__ import annotations

from dataclasses import dataclass
from math import log10

import numpy as np
import pandas as pd
from scipy.stats import chi2


def rv_value_column(frame: pd.DataFrame) -> str:
    return "VRAD_ADOPTED" if "VRAD_ADOPTED" in frame.columns else "VRAD"


def rv_error_column(frame: pd.DataFrame) -> str:
    return "VRAD_ERR_ADOPTED" if "VRAD_ERR_ADOPTED" in frame.columns else "VRAD_ERR"


@dataclass(frozen=True)
class SourceSummary:
    targetid: int
    n_epochs_raw: int
    n_epochs_good: int
    weighted_mean_vrad: float
    median_vrad: float
    robust_scatter: float
    chi2_const: float
    dof: int
    p_const: float
    max_pair_sigma: float
    time_baseline_days: float
    classification: str
    evidence_score: float


def robust_scale(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return float("nan")
    median = np.median(values)
    return float(1.4826 * np.median(np.abs(values - median)))


def weighted_mean(values: np.ndarray, errors: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    errors = np.asarray(errors, dtype=float)
    weights = 1.0 / np.square(errors)
    return float(np.sum(weights * values) / np.sum(weights))


def max_pair_sigma(values: np.ndarray, errors: np.ndarray) -> float:
    values = np.asarray(values, dtype=float)
    errors = np.asarray(errors, dtype=float)
    if values.size < 2:
        return float("nan")
    best = 0.0
    for i in range(values.size - 1):
        denom = np.hypot(errors[i], errors[i + 1 :])
        sigma = np.divide(
            np.abs(values[i] - values[i + 1 :]),
            denom,
            out=np.zeros_like(denom, dtype=float),
            where=denom > 0,
        )
        if sigma.size:
            best = max(best, float(np.max(sigma)))
    return float(best)


def _max_pair_sigma_by_target(
    good: pd.DataFrame,
    n_epochs_good: pd.Series,
    value_column: str,
    error_column: str,
) -> pd.Series:
    result = pd.Series(np.nan, index=n_epochs_good.index, dtype=float)
    if good.empty:
        return result

    counts_by_row = good["GROUP_ID"].map(n_epochs_good)

    two_epoch = good.loc[
        counts_by_row == 2,
        ["GROUP_ID", value_column, error_column],
    ]
    if not two_epoch.empty:
        two_summary = two_epoch.groupby("GROUP_ID", sort=False).agg(
            first_vrad=(value_column, "first"),
            last_vrad=(value_column, "last"),
            e1=(error_column, "first"),
            e2=(error_column, "last"),
        )
        denom = np.hypot(
            two_summary["e1"].to_numpy(dtype=float),
            two_summary["e2"].to_numpy(dtype=float),
        )
        sigma = np.divide(
            np.abs(
                two_summary["first_vrad"].to_numpy(dtype=float)
                - two_summary["last_vrad"].to_numpy(dtype=float)
            ),
            denom,
            out=np.full(len(two_summary), np.nan, dtype=float),
            where=denom > 0,
        )
        result.loc[two_summary.index] = sigma

    many_epoch = good.loc[counts_by_row > 2, ["GROUP_ID", value_column, error_column]]
    for group_id, group in many_epoch.groupby("GROUP_ID", sort=False):
        result.loc[group_id] = max_pair_sigma(
            group[value_column].to_numpy(dtype=float),
            group[error_column].to_numpy(dtype=float),
        )

    return result


def summarize_source(
    raw_group: pd.DataFrame,
    good_group: pd.DataFrame,
    p_threshold: float = 1e-6,
    pair_sigma_threshold: float = 5.0,
) -> SourceSummary:
    targetid = int(raw_group["TARGETID"].iloc[0])
    n_raw = int(len(raw_group))
    n_good = int(len(good_group))

    if n_good == 0:
        return SourceSummary(
            targetid=targetid,
            n_epochs_raw=n_raw,
            n_epochs_good=n_good,
            weighted_mean_vrad=float("nan"),
            median_vrad=float("nan"),
            robust_scatter=float("nan"),
            chi2_const=float("nan"),
            dof=0,
            p_const=float("nan"),
            max_pair_sigma=float("nan"),
            time_baseline_days=float("nan"),
            classification="quality_limited",
            evidence_score=0.0,
        )

    value_column = rv_value_column(good_group)
    error_column = rv_error_column(good_group)
    values = good_group[value_column].to_numpy(dtype=float)
    errors = good_group[error_column].to_numpy(dtype=float)
    mean = weighted_mean(values, errors)
    chi2_value = float(np.sum(np.square((values - mean) / errors))) if n_good > 1 else 0.0
    dof = max(n_good - 1, 0)
    p_value = float(chi2.sf(chi2_value, dof)) if dof > 0 else float("nan")
    pair_sigma = max_pair_sigma(values, errors)

    if "MJD" in good_group.columns and good_group["MJD"].notna().any():
        mjd = good_group["MJD"].dropna().to_numpy(dtype=float)
        baseline = float(np.max(mjd) - np.min(mjd)) if mjd.size > 1 else 0.0
    else:
        baseline = float("nan")

    if n_good < 2:
        classification = "insufficient_epochs"
    elif p_value < p_threshold and pair_sigma >= pair_sigma_threshold:
        classification = "candidate_variable"
    else:
        classification = "stable_like"

    evidence = 0.0
    if np.isfinite(p_value) and p_value > 0:
        evidence = min(300.0, -log10(p_value))

    return SourceSummary(
        targetid=targetid,
        n_epochs_raw=n_raw,
        n_epochs_good=n_good,
        weighted_mean_vrad=mean,
        median_vrad=float(np.median(values)),
        robust_scatter=robust_scale(values),
        chi2_const=chi2_value,
        dof=dof,
        p_const=p_value,
        max_pair_sigma=pair_sigma,
        time_baseline_days=baseline,
        classification=classification,
        evidence_score=evidence,
    )


def summarize_sources(frame: pd.DataFrame, good_mask: pd.Series) -> pd.DataFrame:
    group_column = "GROUP_ID" if "GROUP_ID" in frame.columns else "TARGETID"
    value_column = rv_value_column(frame)
    error_column = rv_error_column(frame)
    raw_grouped = frame.groupby(group_column, sort=False)
    raw = raw_grouped.size().rename("n_epochs_raw").reset_index()
    if "TARGETID" in frame.columns:
        raw["targetid"] = raw_grouped["TARGETID"].first().to_numpy()
    if "SOURCE_ID" in frame.columns:
        raw["source_id"] = raw_grouped["SOURCE_ID"].first().to_numpy()
    if "GROUP_KIND" in frame.columns:
        raw["group_kind"] = raw_grouped["GROUP_KIND"].first().to_numpy()

    good = frame.loc[good_mask].copy()
    if good.empty:
        result = raw.rename(columns={group_column: "group_id"})
        if group_column == "TARGETID":
            result["targetid"] = result["group_id"]
        result["n_epochs_good"] = 0
        result["weighted_mean_vrad"] = np.nan
        result["median_vrad"] = np.nan
        result["robust_scatter"] = np.nan
        result["chi2_const"] = np.nan
        result["dof"] = 0
        result["p_const"] = np.nan
        result["max_pair_sigma"] = np.nan
        result["time_baseline_days"] = np.nan
        result["classification"] = "quality_limited"
        result["evidence_score"] = 0.0
        return result

    good["_W"] = 1.0 / np.square(pd.to_numeric(good[error_column], errors="coerce"))
    good["_WV"] = good["_W"] * pd.to_numeric(good[value_column], errors="coerce")
    good["_W_V_SQUARED"] = good["_W"] * np.square(
        pd.to_numeric(good[value_column], errors="coerce")
    )

    grouped = good.groupby(group_column, sort=False)
    summary = grouped.agg(
        n_epochs_good=(value_column, "size"),
        sum_w=("_W", "sum"),
        sum_wv=("_WV", "sum"),
        sum_weighted_v_squared=("_W_V_SQUARED", "sum"),
        median_vrad=(value_column, "median"),
    )
    if "TARGETID" in good.columns:
        summary["targetid"] = grouped["TARGETID"].first()
    if "SOURCE_ID" in good.columns:
        summary["source_id"] = grouped["SOURCE_ID"].first()
    if "GROUP_KIND" in good.columns:
        summary["group_kind"] = grouped["GROUP_KIND"].first()
    median_by_row = good[group_column].map(summary["median_vrad"])
    good["_ABS_DEV"] = np.abs(pd.to_numeric(good[value_column], errors="coerce") - median_by_row)
    summary["robust_scatter"] = 1.4826 * grouped["_ABS_DEV"].median()

    if "MJD" in good.columns:
        mjd_summary = grouped["MJD"].agg(["min", "max", "count"])
        summary["time_baseline_days"] = np.where(
            mjd_summary["count"] > 1,
            mjd_summary["max"] - mjd_summary["min"],
            np.where(mjd_summary["count"] == 1, 0.0, np.nan),
        )
    else:
        summary["time_baseline_days"] = np.nan

    summary["max_pair_sigma"] = _max_pair_sigma_by_target(
        good.rename(columns={group_column: "GROUP_ID"}) if group_column != "GROUP_ID" else good,
        summary["n_epochs_good"],
        value_column,
        error_column,
    )

    summary["weighted_mean_vrad"] = summary["sum_wv"] / summary["sum_w"]
    chi2_values = summary["sum_weighted_v_squared"] - np.square(
        summary["weighted_mean_vrad"]
    ) * summary["sum_w"]
    summary["chi2_const"] = np.maximum(chi2_values, 0.0)
    summary["dof"] = (summary["n_epochs_good"] - 1).clip(lower=0).astype(int)
    p_values = np.full(len(summary), np.nan, dtype=float)
    log_p_values = np.full(len(summary), np.nan, dtype=float)
    has_dof = summary["dof"].to_numpy() > 0
    p_values[has_dof] = chi2.sf(
        summary.loc[has_dof, "chi2_const"].to_numpy(dtype=float),
        summary.loc[has_dof, "dof"].to_numpy(dtype=float),
    )
    log_p_values[has_dof] = chi2.logsf(
        summary.loc[has_dof, "chi2_const"].to_numpy(dtype=float),
        summary.loc[has_dof, "dof"].to_numpy(dtype=float),
    )
    summary["p_const"] = p_values
    summary["log_p_const"] = log_p_values

    result = raw.merge(summary, left_on=group_column, right_index=True, how="left")
    result["n_epochs_good"] = result["n_epochs_good"].fillna(0).astype(int)
    result["dof"] = result["dof"].fillna(0).astype(int)

    n_good = result["n_epochs_good"].to_numpy()
    p_const = result["p_const"].to_numpy(dtype=float)
    log_p_const = result["log_p_const"].to_numpy(dtype=float)
    pair_sigma = result["max_pair_sigma"].to_numpy(dtype=float)
    classification = np.full(len(result), "stable_like", dtype=object)
    classification[n_good == 0] = "quality_limited"
    classification[(n_good > 0) & (n_good < 2)] = "insufficient_epochs"
    classification[
        (n_good >= 2)
        & np.isfinite(p_const)
        & (p_const < 1e-6)
        & np.isfinite(pair_sigma)
        & (pair_sigma >= 5.0)
    ] = "candidate_variable"
    result["classification"] = classification

    evidence = np.zeros(len(result), dtype=float)
    valid_log_p = np.isfinite(log_p_const)
    evidence[valid_log_p] = np.minimum(300.0, -log_p_const[valid_log_p] / np.log(10.0))
    result["evidence_score"] = evidence

    result = result.rename(columns={group_column: "group_id"})
    for metadata_column in ("targetid", "source_id", "group_kind"):
        left = f"{metadata_column}_x"
        right = f"{metadata_column}_y"
        if left in result.columns and right in result.columns:
            result[metadata_column] = result[left]
            missing = result[metadata_column].isna()
            if missing.any():
                result.loc[missing, metadata_column] = result.loc[missing, right]
            result = result.drop(columns=[left, right])
        elif left in result.columns:
            result = result.rename(columns={left: metadata_column})
        elif right in result.columns:
            result = result.rename(columns={right: metadata_column})
    if "targetid" not in result.columns:
        result["targetid"] = result["group_id"]
    if "source_id" not in result.columns:
        result["source_id"] = np.nan
    if "group_kind" not in result.columns:
        result["group_kind"] = np.where(group_column == "GROUP_ID", "UNKNOWN", "TARGETID")
    for id_column in ("group_id", "source_id", "targetid"):
        if id_column in result.columns:
            result[id_column] = pd.to_numeric(result[id_column], errors="coerce").astype("Int64")
    result = result[
        [
            "group_id",
            "group_kind",
            "source_id",
            "targetid",
            "n_epochs_raw",
            "n_epochs_good",
            "weighted_mean_vrad",
            "median_vrad",
            "robust_scatter",
            "chi2_const",
            "dof",
            "p_const",
            "log_p_const",
            "max_pair_sigma",
            "time_baseline_days",
            "classification",
            "evidence_score",
        ]
    ]
    return result.sort_values(
        ["classification", "evidence_score", "max_pair_sigma"],
        ascending=[True, False, False],
        na_position="last",
    ).reset_index(drop=True)
