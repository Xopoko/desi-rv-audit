from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable

import numpy as np
import pandas as pd


ALIASES = {
    "target_id": "TARGETID",
    "targetid": "TARGETID",
    "source_id": "SOURCE_ID",
    "sourceid": "SOURCE_ID",
    "vrad": "VRAD",
    "radial_velocity": "VRAD",
    "vrad_err": "VRAD_ERR",
    "radial_velocity_error": "VRAD_ERR",
    "sn_r": "SN_R",
    "sn_b": "SN_B",
    "sn_z": "SN_Z",
    "snr_r": "SN_R",
    "rvs_warn": "RVS_WARN",
    "success": "SUCCESS",
    "expid": "EXPID",
    "mjd": "MJD",
    "night": "NIGHT",
    "fiber": "FIBER",
    "survey": "SURVEY",
    "program": "PROGRAM",
    "teff": "TEFF",
    "logg": "LOGG",
    "feh": "FEH",
    "vsini": "VSINI",
    "rr_spectype": "RR_SPECTYPE",
    "tileid": "TILEID",
    "vrad_skew": "VRAD_SKEW",
    "vrad_kurt": "VRAD_KURT",
    "chisq_tot": "CHISQ_TOT",
    "chisq_c_tot": "CHISQ_C_TOT",
}

REQUIRED = ("TARGETID", "VRAD", "VRAD_ERR")


@dataclass(frozen=True)
class InferredContext:
    survey: str | None = None
    program: str | None = None


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize common lower-case aliases to the DESI column names."""
    rename: dict[str, str] = {}
    upper_existing = {str(column).upper() for column in frame.columns}
    for column in frame.columns:
        key = str(column).strip().lower()
        target = ALIASES.get(key)
        if target and target not in upper_existing:
            rename[column] = target
    result = frame.rename(columns=rename).copy()
    result.columns = [str(column).strip().upper() for column in result.columns]
    return result


def infer_context_from_path(path: str | Path) -> InferredContext:
    name = Path(path).name.lower()
    match = re.search(
        r"rvpix_exp-(?P<survey>[^-]+)-(?P<program>[^.]+)\.fits(?:\.gz)?$",
        name,
    )
    if not match:
        return InferredContext()
    return InferredContext(
        survey=match.group("survey").upper(),
        program=match.group("program").upper(),
    )


def validate_columns(frame: pd.DataFrame, required: Iterable[str] = REQUIRED) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")


def coerce_types(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    integer = [
        "TARGETID",
        "SOURCE_ID",
        "GROUP_ID",
        "EXPID",
        "NIGHT",
        "FIBER",
        "TILEID",
    ]
    for column in integer:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce").astype("Int64")

    numeric = [
        "VRAD",
        "VRAD_ERR",
        "VRAD_ADOPTED",
        "VRAD_ERR_ADOPTED",
        "VRAD_OFFSET",
        "SN_R",
        "SN_B",
        "SN_Z",
        "RVS_WARN",
        "MJD",
        "TEFF",
        "LOGG",
        "FEH",
        "VSINI",
        "VRAD_SKEW",
        "VRAD_KURT",
        "CHISQ_TOT",
        "CHISQ_C_TOT",
    ]
    for column in numeric:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce")

    if "SUCCESS" in result.columns:
        values = result["SUCCESS"]
        if values.dtype != bool:
            truthy = {"true", "1", "yes", "y", "t"}
            result["SUCCESS"] = values.map(
                lambda value: (
                    bool(value)
                    if isinstance(value, (bool, np.bool_))
                    else (
                        bool(float(value))
                        if isinstance(value, (int, float, np.integer, np.floating))
                        and np.isfinite(value)
                        else str(value).strip().lower() in truthy
                        or str(value).strip().lower() == "1.0"
                    )
                )
            )
    return result


def add_group_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    targetid = pd.to_numeric(result["TARGETID"], errors="coerce").fillna(0).astype("int64")
    if "SOURCE_ID" in result.columns:
        source_id = pd.to_numeric(result["SOURCE_ID"], errors="coerce")
        has_source = source_id.notna() & (source_id > 0)
        source_int = source_id.fillna(0).astype("int64")
        result["GROUP_ID"] = np.where(has_source, source_int, -targetid).astype("int64")
        result["GROUP_KIND"] = np.where(has_source, "GAIA_SOURCE_ID", "TARGETID_FALLBACK")
    else:
        result["GROUP_ID"] = (-targetid).astype("int64")
        result["GROUP_KIND"] = "TARGETID_FALLBACK"
    return result
