from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class QualityRules:
    min_sn_r: float = 5.0
    require_success: bool = True
    require_rr_spectype_star: bool = True
    require_zero_rvs_warn: bool = True
    require_zero_fiberstatus: bool = True
    max_vsini: float | None = 30.0
    max_abs_vrad: float = 2000.0


def _is_star_spectype(values: pd.Series) -> pd.Series:
    return values.fillna("").astype(str).str.strip().str.upper().eq("STAR")


def quality_mask(frame: pd.DataFrame, rules: QualityRules = QualityRules()) -> pd.Series:
    mask = pd.Series(True, index=frame.index, dtype=bool)
    mask &= np.isfinite(frame["VRAD"])
    mask &= np.isfinite(frame["VRAD_ERR"])
    mask &= frame["VRAD_ERR"] > 0
    mask &= frame["VRAD"].abs() <= rules.max_abs_vrad

    if "SN_R" in frame.columns:
        mask &= np.isfinite(frame["SN_R"])
        mask &= frame["SN_R"] >= rules.min_sn_r

    if rules.require_success and "SUCCESS" in frame.columns:
        mask &= frame["SUCCESS"].fillna(False).astype(bool)

    if rules.require_rr_spectype_star and "RR_SPECTYPE" in frame.columns:
        mask &= _is_star_spectype(frame["RR_SPECTYPE"])

    if rules.require_zero_rvs_warn and "RVS_WARN" in frame.columns:
        mask &= frame["RVS_WARN"].fillna(-1).eq(0)

    if rules.require_zero_fiberstatus and "FIBERSTATUS" in frame.columns:
        mask &= frame["FIBERSTATUS"].fillna(-1).eq(0)

    if rules.max_vsini is not None and "VSINI" in frame.columns:
        mask &= np.isfinite(frame["VSINI"])
        mask &= frame["VSINI"] < rules.max_vsini

    return mask


def rejection_reasons(frame: pd.DataFrame, rules: QualityRules = QualityRules()) -> pd.DataFrame:
    """Return one boolean column per explicit rejection rule."""
    result = pd.DataFrame(index=frame.index)
    result["NONFINITE_RV"] = ~np.isfinite(frame["VRAD"])
    result["INVALID_RV_ERROR"] = ~np.isfinite(frame["VRAD_ERR"]) | (frame["VRAD_ERR"] <= 0)
    result["EXTREME_ABS_RV"] = frame["VRAD"].abs() > rules.max_abs_vrad
    if "SN_R" in frame.columns:
        result["LOW_SN_R"] = ~np.isfinite(frame["SN_R"]) | (frame["SN_R"] < rules.min_sn_r)
    if rules.require_success and "SUCCESS" in frame.columns:
        result["FIT_NOT_SUCCESSFUL"] = ~frame["SUCCESS"].fillna(False).astype(bool)
    if rules.require_rr_spectype_star and "RR_SPECTYPE" in frame.columns:
        result["NON_STELLAR_RR_SPECTYPE"] = ~_is_star_spectype(frame["RR_SPECTYPE"])
    if rules.require_zero_rvs_warn and "RVS_WARN" in frame.columns:
        result["RVS_WARNING"] = ~frame["RVS_WARN"].fillna(-1).eq(0)
    if rules.require_zero_fiberstatus and "FIBERSTATUS" in frame.columns:
        result["FIBER_WARNING"] = ~frame["FIBERSTATUS"].fillna(-1).eq(0)
    if rules.max_vsini is not None and "VSINI" in frame.columns:
        result["MISSING_VSINI"] = ~np.isfinite(frame["VSINI"])
        result["HIGH_VSINI"] = np.isfinite(frame["VSINI"]) & (frame["VSINI"] >= rules.max_vsini)
    return result
