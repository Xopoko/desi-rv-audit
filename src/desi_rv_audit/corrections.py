from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_RV_FLOORS = {
    "BRIGHT": 1.0,
    "BACKUP": 2.0,
    "DARK": 1.6,
}


def _native_array(values) -> np.ndarray:
    array = np.asarray(values)
    if array.dtype.byteorder not in ("=", "|"):
        array = array.byteswap().view(array.dtype.newbyteorder("="))
    return array


def _clean_program(values: pd.Series) -> pd.Series:
    return values.fillna("").astype(str).str.strip().str.upper()


def _clean_survey(values: pd.Series) -> pd.Series:
    return values.fillna("").astype(str).str.strip().str.upper()


def _file_digest(path: Path, algorithm: str) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_backup_correction(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    suffixes = "".join(path.suffixes).lower()
    if suffixes.endswith(".fits") or suffixes.endswith(".fits.gz"):
        try:
            from astropy.io import fits
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError(
                "FITS correction input requires astropy. Install with: pip install -e '.[fits]'"
            ) from exc
        with fits.open(path, memmap=True) as hdul:
            table = next(
                hdu.data
                for hdu in hdul
                if getattr(hdu, "data", None) is not None and hasattr(hdu.data, "names")
            )
            frame = pd.DataFrame({column: _native_array(table[column]) for column in table.names})
    elif suffixes.endswith(".csv") or suffixes.endswith(".csv.gz"):
        frame = pd.read_csv(path)
    elif suffixes.endswith(".parquet"):
        frame = pd.read_parquet(path)
    else:
        raise ValueError(f"Unsupported backup correction format: {path}")

    frame.columns = [str(column).strip().upper() for column in frame.columns]
    offset_column = None
    for candidate in ("VRAD_OFFSET", "VRAD_BIAS", "OFFSET", "BIAS"):
        if candidate in frame.columns:
            offset_column = candidate
            break
    if "TARGETID" not in frame.columns or offset_column is None:
        raise ValueError("Backup correction must contain TARGETID and VRAD_OFFSET/VRAD_BIAS")

    result = frame[["TARGETID", offset_column]].copy()
    result = result.rename(columns={offset_column: "VRAD_OFFSET"})
    result["TARGETID"] = pd.to_numeric(result["TARGETID"], errors="coerce").astype("Int64")
    result["VRAD_OFFSET"] = pd.to_numeric(result["VRAD_OFFSET"], errors="coerce")
    result = result.dropna(subset=["TARGETID", "VRAD_OFFSET"])
    result["TARGETID"] = result["TARGETID"].astype("int64")
    conflicting = (
        result.groupby("TARGETID", sort=False)["VRAD_OFFSET"]
        .nunique(dropna=False)
        .loc[lambda values: values > 1]
    )
    if not conflicting.empty:
        examples = ", ".join(map(str, conflicting.index[:5].tolist()))
        raise ValueError(
            "Backup correction contains conflicting offsets for "
            f"{len(conflicting)} TARGETID values; examples: {examples}"
        )
    return result.drop_duplicates("TARGETID", keep="first")


def backup_correction_file_summary(path: str | Path) -> dict[str, object]:
    path = Path(path)
    correction = load_backup_correction(path)
    return {
        "CORRECTION_PATH": path.as_posix(),
        "CORRECTION_MD5": _file_digest(path, "md5"),
        "CORRECTION_SHA256": _file_digest(path, "sha256"),
        "N_CORRECTION_ROWS": int(len(correction)),
        "N_CORRECTION_UNIQUE_TARGETIDS": int(correction["TARGETID"].nunique()),
    }


def apply_velocity_calibration(
    frame: pd.DataFrame,
    backup_correction_path: str | Path | None = None,
    floor_by_program: dict[str, float] | None = None,
    expected_backup_correction_md5: str | None = None,
) -> pd.DataFrame:
    result = frame.copy(deep=False)
    result["VRAD_OFFSET"] = 0.0
    summary: dict[str, object] = {
        "CORRECTION_PATH": "",
        "CORRECTION_MD5": "",
        "CORRECTION_SHA256": "",
        "N_CORRECTION_ROWS": 0,
        "N_CORRECTION_UNIQUE_TARGETIDS": 0,
        "N_BACKUP_EPOCHS": 0,
        "N_BACKUP_EPOCHS_MATCHED": 0,
        "N_BACKUP_EPOCHS_UNMATCHED": 0,
        "N_NON_BACKUP_TARGETID_MATCHES": 0,
        "CORRECTION_MD5_EXPECTED": expected_backup_correction_md5 or "",
        "CORRECTION_MD5_OK": "",
    }

    if backup_correction_path is not None:
        backup_correction_path = Path(backup_correction_path)
        correction = load_backup_correction(backup_correction_path)
        summary.update(backup_correction_file_summary(backup_correction_path))
        if expected_backup_correction_md5:
            md5_ok = summary["CORRECTION_MD5"] == expected_backup_correction_md5
            summary["CORRECTION_MD5_OK"] = bool(md5_ok)
            if not md5_ok:
                raise ValueError(
                    "Backup correction MD5 mismatch: "
                    f"expected {expected_backup_correction_md5}, got {summary['CORRECTION_MD5']}"
                )
        result = result.merge(
            correction,
            on="TARGETID",
            how="left",
            suffixes=("", "_CORRECTION"),
        )
        correction_column = (
            "VRAD_OFFSET_CORRECTION"
            if "VRAD_OFFSET_CORRECTION" in result.columns
            else "VRAD_OFFSET"
        )
        program = (
            _clean_program(result["PROGRAM"])
            if "PROGRAM" in result.columns
            else pd.Series("", index=result.index)
        )
        survey = (
            _clean_survey(result["SURVEY"])
            if "SURVEY" in result.columns
            else pd.Series("", index=result.index)
        )
        is_main_backup = survey.eq("MAIN") & program.eq("BACKUP")
        has_match = result[correction_column].notna()
        result["VRAD_OFFSET"] = np.where(
            is_main_backup & has_match,
            pd.to_numeric(result[correction_column], errors="coerce"),
            0.0,
        )
        if correction_column == "VRAD_OFFSET_CORRECTION":
            result = result.drop(columns=["VRAD_OFFSET_CORRECTION"])
        summary.update(
            {
                "N_BACKUP_EPOCHS": int(is_main_backup.sum()),
                "N_BACKUP_EPOCHS_MATCHED": int((is_main_backup & has_match).sum()),
                "N_BACKUP_EPOCHS_UNMATCHED": int((is_main_backup & ~has_match).sum()),
                "N_NON_BACKUP_TARGETID_MATCHES": int((~is_main_backup & has_match).sum()),
            }
        )

    result["VRAD_ADOPTED"] = pd.to_numeric(result["VRAD"], errors="coerce") - result[
        "VRAD_OFFSET"
    ]

    floor_by_program = floor_by_program or DEFAULT_RV_FLOORS
    if "PROGRAM" in result.columns:
        program = _clean_program(result["PROGRAM"])
        floor = program.map({key.upper(): value for key, value in floor_by_program.items()})
        floor = floor.fillna(0.0).to_numpy(dtype=float)
    else:
        floor = np.zeros(len(result), dtype=float)
    result["VRAD_FLOOR"] = floor
    formal_error = pd.to_numeric(result["VRAD_ERR"], errors="coerce").to_numpy(dtype=float)
    result["VRAD_ERR_ADOPTED"] = np.hypot(formal_error, floor)
    result.attrs["backup_correction_summary"] = summary
    return result
