from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from .schema import (
    add_group_columns,
    coerce_types,
    infer_context_from_path,
    normalize_columns,
    validate_columns,
)


RVTAB_COLUMNS = [
    "TARGETID",
    "VRAD",
    "VRAD_ERR",
    "SN_R",
    "SN_B",
    "SN_Z",
    "RVS_WARN",
    "SUCCESS",
    "EXPID",
    "FIBER",
    "TEFF",
    "LOGG",
    "FEH",
    "VSINI",
    "RR_SPECTYPE",
    "VRAD_SKEW",
    "VRAD_KURT",
    "CHISQ_TOT",
    "CHISQ_C_TOT",
    "CHISQ_B",
    "CHISQ_C_B",
    "CHISQ_R",
    "CHISQ_C_R",
    "CHISQ_Z",
    "CHISQ_C_Z",
]

FIBERMAP_COLUMNS = [
    "TARGETID",
    "EXPID",
    "MJD",
    "NIGHT",
    "FIBER",
    "FIBERSTATUS",
    "EXPTIME",
    "TARGET_RA",
    "TARGET_DEC",
    "GAIA_PHOT_G_MEAN_MAG",
    "PARALLAX",
    "TILEID",
]

GAIA_COLUMNS = [
    "SOURCE_ID",
    "RADIAL_VELOCITY",
    "RADIAL_VELOCITY_ERROR",
]

STRICT_RVTAB_COLUMNS = [
    "TARGETID",
    "VRAD",
    "VRAD_ERR",
    "SN_R",
    "RVS_WARN",
    "SUCCESS",
    "EXPID",
    "FIBER",
    "VSINI",
    "RR_SPECTYPE",
]

STRICT_FIBERMAP_COLUMNS = ["TARGETID", "EXPID", "FIBER", "MJD", "NIGHT", "FIBERSTATUS", "TILEID"]
STRICT_GAIA_COLUMNS = ["SOURCE_ID"]


def _decode_object_columns(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.select_dtypes(include=["object"]).columns:
        result[column] = result[column].map(
            lambda value: value.decode("utf-8", errors="replace").strip()
            if isinstance(value, (bytes, bytearray))
            else value
        )
    return result


def _native_array(values) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype.byteorder not in ("=", "|"):
        array = array.byteswap().view(array.dtype.newbyteorder("="))
    return array


def _fits_table_to_frame(data, columns: list[str], stop: int) -> pd.DataFrame:
    available = [column for column in columns if column in data.names]
    return pd.DataFrame({column: _native_array(data[column][:stop]) for column in available})


def _require_columns(path: Path, extension: str, names: list[str], required: list[str]) -> None:
    missing = [column for column in required if column not in names]
    if missing:
        raise ValueError(
            f"{path} {extension} extension is missing required columns: {', '.join(missing)}"
        )


def _assert_same_values(path: Path, first, second, column: str) -> None:
    left = _native_array(first[column])
    right = _native_array(second[column])
    if len(left) != len(right) or not np.array_equal(left, right):
        raise ValueError(f"{path} has row-alignment mismatch for {column}")


def _load_fits(
    path: Path,
    max_rows: int | None = None,
    strict_desi_main: bool = False,
) -> pd.DataFrame:
    try:
        from astropy.io import fits
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError(
            "FITS input requires astropy. Install with: pip install -e '.[fits]'"
        ) from exc

    with fits.open(path, memmap=True) as hdul:
        if "RVTAB" not in hdul:
            raise ValueError(f"{path} does not contain an RVTAB extension")
        if strict_desi_main:
            for extension in ("FIBERMAP", "GAIA"):
                if extension not in hdul:
                    raise ValueError(f"{path} does not contain required {extension} extension")
        rv_data = hdul["RVTAB"].data
        if strict_desi_main:
            _require_columns(path, "RVTAB", rv_data.names, STRICT_RVTAB_COLUMNS)
        stop = len(rv_data) if max_rows is None else min(max_rows, len(rv_data))
        frame = _fits_table_to_frame(rv_data, RVTAB_COLUMNS, stop)

        # DESI files keep row-aligned observing metadata in FIBERMAP.
        if "FIBERMAP" in hdul:
            fib_full = hdul["FIBERMAP"].data
            if len(fib_full) < stop:
                raise ValueError(f"{path} FIBERMAP has fewer rows than RVTAB")
            if strict_desi_main:
                _require_columns(path, "FIBERMAP", fib_full.names, STRICT_FIBERMAP_COLUMNS)
            for column in ("TARGETID", "EXPID", "FIBER"):
                if column in rv_data.names and column in fib_full.names:
                    _assert_same_values(path, rv_data[:stop], fib_full[:stop], column)
            fib_data = fib_full[:stop]
            fib_frame = _fits_table_to_frame(fib_data, FIBERMAP_COLUMNS, stop)
            for column in fib_frame.columns:
                if column not in frame.columns:
                    frame[column] = fib_frame[column].to_numpy()
        if "GAIA" in hdul:
            gaia_full = hdul["GAIA"].data
            if len(gaia_full) < stop:
                raise ValueError(f"{path} GAIA has fewer rows than RVTAB")
            if strict_desi_main:
                _require_columns(path, "GAIA", gaia_full.names, STRICT_GAIA_COLUMNS)
            gaia_data = gaia_full[:stop]
            gaia_frame = _fits_table_to_frame(gaia_data, GAIA_COLUMNS, stop)
            for column in gaia_frame.columns:
                if column not in frame.columns:
                    frame[column] = gaia_frame[column].to_numpy()

    context = infer_context_from_path(path)
    if context.survey and "SURVEY" not in frame.columns:
        frame["SURVEY"] = context.survey
    if context.program and "PROGRAM" not in frame.columns:
        frame["PROGRAM"] = context.program
    return _decode_object_columns(frame)


def load_one(
    path: str | Path,
    max_rows: int | None = None,
    strict_desi_main: bool = False,
) -> pd.DataFrame:
    path = Path(path)
    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith(".fits") or suffixes.endswith(".fits.gz"):
        frame = _load_fits(path, max_rows=max_rows, strict_desi_main=strict_desi_main)
    elif suffixes.endswith(".parquet"):
        frame = pd.read_parquet(path)
        if max_rows is not None:
            frame = frame.head(max_rows)
    elif suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
        frame = pd.read_csv(path, nrows=max_rows)
    else:
        raise ValueError(f"Unsupported input format: {path}")

    frame = add_group_columns(coerce_types(normalize_columns(frame)))
    validate_columns(frame)
    frame["_INPUT_FILE"] = str(path)
    return frame


def load_many(
    paths: Iterable[str | Path],
    max_rows_per_file: int | None = None,
    strict_desi_main: bool = False,
) -> pd.DataFrame:
    frames = [
        load_one(path, max_rows=max_rows_per_file, strict_desi_main=strict_desi_main)
        for path in paths
    ]
    if not frames:
        raise ValueError("At least one input file is required")
    return pd.concat(frames, ignore_index=True, sort=False)
