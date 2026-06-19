from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import rv_error_column, rv_value_column


def _clean_category(value) -> str:
    if pd.isna(value):
        return "UNKNOWN"
    text = str(value).strip().upper()
    return text if text and text != "NAN" else "UNKNOWN"


def _numeric_array(group: pd.DataFrame, column: str) -> np.ndarray:
    if column not in group.columns:
        return np.full(len(group), np.nan, dtype=float)
    return pd.to_numeric(group[column], errors="coerce").to_numpy(dtype=float)


def _int_array(group: pd.DataFrame, column: str) -> np.ndarray:
    if column not in group.columns:
        return np.full(len(group), 0, dtype=np.int64)
    return pd.to_numeric(group[column], errors="coerce").fillna(0).to_numpy(dtype=np.int64)


def _object_array(group: pd.DataFrame, column: str) -> np.ndarray:
    if column not in group.columns:
        return np.full(len(group), np.nan, dtype=object)
    return group[column].to_numpy(dtype=object)


def _category_array(group: pd.DataFrame, column: str) -> np.ndarray:
    if column not in group.columns:
        return np.full(len(group), "UNKNOWN", dtype=object)
    values = group[column].astype("string").str.strip().str.upper()
    values = values.mask(values.isna() | values.eq("") | values.eq("NAN"), "UNKNOWN")
    return values.to_numpy(dtype=object)


def _string_array(group: pd.DataFrame, column: str, default: str = "UNKNOWN") -> np.ndarray:
    if column not in group.columns:
        return np.full(len(group), default, dtype=object)
    values = group[column].astype("string").str.strip()
    values = values.mask(values.isna() | values.eq("") | values.eq("nan") | values.eq("<NA>"), default)
    return values.to_numpy(dtype=object)


def _join_key(*parts: np.ndarray) -> np.ndarray:
    if not parts:
        return np.asarray([], dtype=object)
    count = len(parts[0])
    return np.fromiter(
        ("|".join(items) for items in zip(*parts)),
        dtype=object,
        count=count,
    )


def _nanmin_pair(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    return np.where(
        np.isnan(first),
        second,
        np.where(np.isnan(second), first, np.minimum(first, second)),
    )


def _nanmedian_pair(first: np.ndarray, second: np.ndarray) -> np.ndarray:
    return np.where(
        np.isnan(first),
        second,
        np.where(np.isnan(second), first, (first + second) / 2.0),
    )


def _safe_divide(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    return np.divide(
        numerator,
        denominator,
        out=np.full(len(numerator), np.nan, dtype=float),
        where=denominator > 0,
    )


def _append_pair_chunk(
    data: dict[str, list[np.ndarray]],
    group_id: np.ndarray,
    group_kind: np.ndarray,
    targetid: np.ndarray,
    source_id: np.ndarray,
    expid: np.ndarray,
    expid_key: np.ndarray,
    mjd: np.ndarray,
    vrad: np.ndarray,
    vrad_err: np.ndarray,
    formal_vrad: np.ndarray,
    formal_vrad_err: np.ndarray,
    sn_r: np.ndarray,
    program: np.ndarray,
    survey: np.ndarray,
    fiber: np.ndarray,
    fiber_key: np.ndarray,
    targetid_key: np.ndarray,
    night: np.ndarray,
    tileid: np.ndarray,
    teff: np.ndarray,
    logg: np.ndarray,
    feh: np.ndarray,
    first_idx: np.ndarray,
    second_idx: np.ndarray,
) -> None:
    n_pairs = len(first_idx)
    if n_pairs == 0:
        return

    vrad1 = vrad[first_idx]
    vrad2 = vrad[second_idx]
    error = np.hypot(vrad_err[first_idx], vrad_err[second_idx])
    delta = vrad1 - vrad2
    pair_z = _safe_divide(delta, error)

    formal_vrad1 = formal_vrad[first_idx]
    formal_vrad2 = formal_vrad[second_idx]
    formal_error = np.hypot(formal_vrad_err[first_idx], formal_vrad_err[second_idx])
    formal_delta = formal_vrad1 - formal_vrad2
    formal_pair_z = _safe_divide(formal_delta, formal_error)

    program1 = program[first_idx]
    program2 = program[second_idx]
    first_is_low = program1 <= program2
    low_program = np.where(first_is_low, program1, program2)
    high_program = np.where(first_is_low, program2, program1)
    program_pair = np.fromiter(
        (f"{low} / {high}" for low, high in zip(low_program, high_program)),
        dtype=object,
        count=n_pairs,
    )
    program_delta = np.where(first_is_low, delta, -delta)
    formal_program_delta = np.where(first_is_low, formal_delta, -formal_delta)

    mjd1 = mjd[first_idx]
    mjd2 = mjd[second_idx]
    obs_key1 = _join_key(
        survey[first_idx],
        program1,
        expid_key[first_idx],
        fiber_key[first_idx],
        targetid_key[first_idx],
    )
    obs_key2 = _join_key(
        survey[second_idx],
        program2,
        expid_key[second_idx],
        fiber_key[second_idx],
        targetid_key[second_idx],
    )
    exposure_key1 = _join_key(survey[first_idx], program1, expid_key[first_idx])
    exposure_key2 = _join_key(survey[second_idx], program2, expid_key[second_idx])
    chunk = {
        "GROUP_ID": group_id[first_idx],
        "GROUP_KIND": group_kind[first_idx],
        "TARGETID_1": targetid[first_idx],
        "TARGETID_2": targetid[second_idx],
        "SOURCE_ID_1": source_id[first_idx],
        "SOURCE_ID_2": source_id[second_idx],
        "OBS_KEY_1": obs_key1,
        "OBS_KEY_2": obs_key2,
        "EXPOSURE_KEY_1": exposure_key1,
        "EXPOSURE_KEY_2": exposure_key2,
        "EXPID_1": expid[first_idx],
        "EXPID_2": expid[second_idx],
        "MJD_1": mjd1,
        "MJD_2": mjd2,
        "DELTA_DAYS": np.abs(mjd1 - mjd2),
        "VRAD_1": vrad1,
        "VRAD_2": vrad2,
        "DELTA_VRAD": delta,
        "PAIR_ERROR": error,
        "PAIR_Z": pair_z,
        "VRAD_FORMAL_1": formal_vrad1,
        "VRAD_FORMAL_2": formal_vrad2,
        "DELTA_VRAD_FORMAL": formal_delta,
        "PAIR_ERROR_FORMAL": formal_error,
        "PAIR_Z_FORMAL": formal_pair_z,
        "SN_R_MIN": _nanmin_pair(sn_r[first_idx], sn_r[second_idx]),
        "PROGRAM_1": program1,
        "PROGRAM_2": program2,
        "PROGRAM_PAIR": program_pair,
        "PROGRAM_DELTA_VRAD": program_delta,
        "PROGRAM_PAIR_Z": _safe_divide(program_delta, error),
        "PROGRAM_DELTA_VRAD_FORMAL": formal_program_delta,
        "PROGRAM_PAIR_Z_FORMAL": _safe_divide(formal_program_delta, formal_error),
        "SURVEY_1": survey[first_idx],
        "SURVEY_2": survey[second_idx],
        "FIBER_1": fiber[first_idx],
        "FIBER_2": fiber[second_idx],
        "NIGHT_1": night[first_idx],
        "NIGHT_2": night[second_idx],
        "TILEID_1": tileid[first_idx],
        "TILEID_2": tileid[second_idx],
        "TEFF_MEDIAN": _nanmedian_pair(teff[first_idx], teff[second_idx]),
        "LOGG_MEDIAN": _nanmedian_pair(logg[first_idx], logg[second_idx]),
        "FEH_MEDIAN": _nanmedian_pair(feh[first_idx], feh[second_idx]),
    }
    for column, values in chunk.items():
        data[column].append(np.asarray(values))


def build_pair_table(
    frame: pd.DataFrame,
    good_mask: pd.Series,
    max_pairs_per_source: int = 50,
) -> pd.DataFrame:
    """Build deterministic within-source pairs from quality-approved epochs."""
    columns = [
        "GROUP_ID",
        "GROUP_KIND",
        "TARGETID_1",
        "TARGETID_2",
        "SOURCE_ID_1",
        "SOURCE_ID_2",
        "OBS_KEY_1",
        "OBS_KEY_2",
        "EXPOSURE_KEY_1",
        "EXPOSURE_KEY_2",
        "EXPID_1",
        "EXPID_2",
        "MJD_1",
        "MJD_2",
        "DELTA_DAYS",
        "VRAD_1",
        "VRAD_2",
        "DELTA_VRAD",
        "PAIR_ERROR",
        "PAIR_Z",
        "VRAD_FORMAL_1",
        "VRAD_FORMAL_2",
        "DELTA_VRAD_FORMAL",
        "PAIR_ERROR_FORMAL",
        "PAIR_Z_FORMAL",
        "SN_R_MIN",
        "PROGRAM_1",
        "PROGRAM_2",
        "PROGRAM_PAIR",
        "PROGRAM_DELTA_VRAD",
        "PROGRAM_PAIR_Z",
        "PROGRAM_DELTA_VRAD_FORMAL",
        "PROGRAM_PAIR_Z_FORMAL",
        "SURVEY_1",
        "SURVEY_2",
        "FIBER_1",
        "FIBER_2",
        "NIGHT_1",
        "NIGHT_2",
        "TILEID_1",
        "TILEID_2",
        "TEFF_MEDIAN",
        "LOGG_MEDIAN",
        "FEH_MEDIAN",
    ]
    data: dict[str, list[np.ndarray]] = {column: [] for column in columns}
    if max_pairs_per_source < 1:
        return pd.DataFrame(columns=columns)

    good = frame.loc[good_mask].copy()
    if good.empty:
        return pd.DataFrame(columns=columns)

    group_column = "GROUP_ID" if "GROUP_ID" in good.columns else "TARGETID"
    value_column = rv_value_column(good)
    error_column = rv_error_column(good)
    sort_columns = [column for column in ("MJD", "EXPID") if column in good.columns]
    good = good.sort_values([group_column, *sort_columns], kind="mergesort")

    group_id = _int_array(good, group_column)
    group_kind = _category_array(good, "GROUP_KIND")
    targetid = _int_array(good, "TARGETID")
    source_id = _int_array(good, "SOURCE_ID")
    vrad = _numeric_array(good, value_column)
    vrad_err = _numeric_array(good, error_column)
    formal_vrad = _numeric_array(good, "VRAD")
    formal_vrad_err = _numeric_array(good, "VRAD_ERR")
    expid = _object_array(good, "EXPID")
    expid_key = _string_array(good, "EXPID", default="0")
    mjd = _numeric_array(good, "MJD")
    sn_r = _numeric_array(good, "SN_R")
    program = _category_array(good, "PROGRAM")
    survey = _category_array(good, "SURVEY")
    fiber = _object_array(good, "FIBER")
    fiber_key = _string_array(good, "FIBER", default="0")
    targetid_key = _string_array(good, "TARGETID", default="0")
    night = _object_array(good, "NIGHT")
    tileid = _object_array(good, "TILEID")
    teff = _numeric_array(good, "TEFF")
    logg = _numeric_array(good, "LOGG")
    feh = _numeric_array(good, "FEH")

    boundaries = np.flatnonzero(np.r_[True, group_id[1:] != group_id[:-1], True])
    starts = boundaries[:-1]
    lengths = np.diff(boundaries)

    two_starts = starts[lengths == 2]
    if len(two_starts):
        _append_pair_chunk(
            data,
            group_id,
            group_kind,
            targetid,
            source_id,
            expid,
            expid_key,
            mjd,
            vrad,
            vrad_err,
            formal_vrad,
            formal_vrad_err,
            sn_r,
            program,
            survey,
            fiber,
            fiber_key,
            targetid_key,
            night,
            tileid,
            teff,
            logg,
            feh,
            two_starts,
            two_starts + 1,
        )

    for start, n_epochs in zip(starts[lengths > 2], lengths[lengths > 2]):
        first_local, second_local = np.triu_indices(n_epochs, k=1)
        if len(first_local) > max_pairs_per_source:
            positions = np.linspace(
                0,
                len(first_local) - 1,
                max_pairs_per_source,
                dtype=int,
            )
            first_local = first_local[positions]
            second_local = second_local[positions]
        _append_pair_chunk(
            data,
            group_id,
            group_kind,
            targetid,
            source_id,
            expid,
            expid_key,
            mjd,
            vrad,
            vrad_err,
            formal_vrad,
            formal_vrad_err,
            sn_r,
            program,
            survey,
            fiber,
            fiber_key,
            targetid_key,
            night,
            tileid,
            teff,
            logg,
            feh,
            start + first_local,
            start + second_local,
        )

    result = {
        column: np.concatenate(chunks) if chunks else np.asarray([], dtype=object)
        for column, chunks in data.items()
    }
    frame = pd.DataFrame(result, columns=columns)
    for column in ("SOURCE_ID_1", "SOURCE_ID_2"):
        if column in frame.columns:
            values = pd.Series(frame[column], index=frame.index)
            frame[column] = values.mask(values <= 0).astype("Int64")
    return frame
