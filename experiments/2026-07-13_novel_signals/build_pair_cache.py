from __future__ import annotations

import argparse
import gc
import hashlib
import json
import platform
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from astropy.io import fits


EXPERIMENT_DIR = Path(__file__).resolve().parent
ROOT = EXPERIMENT_DIR.parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from desi_rv_audit.corrections import apply_velocity_calibration  # noqa: E402
from desi_rv_audit.downloads import BACKUP_CORRECTION_MD5  # noqa: E402
from desi_rv_audit.io import load_many  # noqa: E402
from desi_rv_audit.pairs import build_pair_table  # noqa: E402
from desi_rv_audit.quality import QualityRules, quality_mask  # noqa: E402


INPUTS = [
    ROOT / "data" / "desi_main" / "rvpix_exp-main-backup.fits",
    ROOT / "data" / "desi_main" / "rvpix_exp-main-bright.fits",
    ROOT / "data" / "desi_main" / "rvpix_exp-main-dark.fits",
]
CORRECTION = ROOT / "data" / "desi_corrections" / "backup_correction.fits"
CACHE = EXPERIMENT_DIR / "pair_cache.pkl"
MANIFEST = EXPERIMENT_DIR / "pair_cache_manifest.json"
PETAL_VALIDATION = EXPERIMENT_DIR / "petal_validation.csv"

PAIR_COLUMNS = [
    "GROUP_ID",
    "GROUP_KIND",
    "DELTA_VRAD",
    "PAIR_ERROR",
    "PAIR_ERROR_FORMAL",
    "PROGRAM_1",
    "PROGRAM_2",
    "PROGRAM_PAIR",
    "NIGHT_1",
    "NIGHT_2",
    "DELTA_DAYS",
    "OBS_KEY_1",
    "OBS_KEY_2",
    "EXPOSURE_KEY_1",
    "EXPOSURE_KEY_2",
    "EXPID_1",
    "EXPID_2",
    "FIBER_1",
    "FIBER_2",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def validate_petal_mapping() -> pd.DataFrame:
    records: list[dict[str, object]] = []
    for path in INPUTS:
        with fits.open(path, memmap=True) as hdul:
            rvtab = hdul["RVTAB"].data
            fibermap = hdul["FIBERMAP"].data
            if "PETAL_LOC" not in fibermap.names:
                raise ValueError(f"{path} FIBERMAP is missing PETAL_LOC")
            n_rows = len(rvtab)
            if len(fibermap) != n_rows:
                raise ValueError(f"{path} RVTAB/FIBERMAP row-count mismatch")
            mismatches = 0
            invalid = 0
            for start in range(0, n_rows, 500_000):
                stop = min(start + 500_000, n_rows)
                fiber = np.asarray(rvtab["FIBER"][start:stop], dtype=np.int64)
                petal = np.asarray(fibermap["PETAL_LOC"][start:stop], dtype=np.int64)
                mismatches += int(np.count_nonzero(fiber // 500 != petal))
                invalid += int(
                    np.count_nonzero((fiber < 0) | (fiber >= 5000) | (petal < 0) | (petal >= 10))
                )
            records.append(
                {
                    "INPUT_FILE": path.relative_to(ROOT).as_posix(),
                    "N_ROWS": n_rows,
                    "N_FIBER_PETAL_MISMATCH": mismatches,
                    "N_INVALID_FIBER_OR_PETAL": invalid,
                    "PASS": mismatches == 0 and invalid == 0,
                }
            )
    result = pd.DataFrame.from_records(records)
    result.to_csv(PETAL_VALIDATION, index=False, lineterminator="\n")
    if not bool(result["PASS"].all()):
        raise ValueError("FIBER // 500 != PETAL_LOC for at least one input row")
    return result


def _cache_is_current() -> bool:
    if not CACHE.exists() or not MANIFEST.exists():
        return False
    try:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    expected = {
        path.relative_to(ROOT).as_posix(): {"size": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns}
        for path in [*INPUTS, CORRECTION]
    }
    return manifest.get("input_fingerprint") == expected


def build_cache(force: bool = False) -> pd.DataFrame:
    if not force and _cache_is_current():
        print(f"CACHE_HIT {CACHE}", flush=True)
        return pd.read_pickle(CACHE)

    timings: list[dict[str, object]] = []
    total_started = perf_counter()
    started = total_started
    petal_validation = validate_petal_mapping()
    timings.append({"stage": "validate_petal", "elapsed_seconds": perf_counter() - started})

    started = perf_counter()
    frame = load_many(INPUTS, strict_desi_main=True)
    n_epochs_raw = len(frame)
    timings.append({"stage": "load_inputs", "elapsed_seconds": perf_counter() - started})

    started = perf_counter()
    frame = apply_velocity_calibration(
        frame,
        backup_correction_path=CORRECTION,
        expected_backup_correction_md5=BACKUP_CORRECTION_MD5,
    )
    timings.append({"stage": "apply_velocity_calibration", "elapsed_seconds": perf_counter() - started})

    started = perf_counter()
    good = quality_mask(frame, QualityRules(min_sn_r=5.0))
    n_epochs_good = int(good.sum())
    timings.append({"stage": "quality_mask", "elapsed_seconds": perf_counter() - started})

    started = perf_counter()
    pairs = build_pair_table(frame, good, max_pairs_per_source=20)
    n_pairs_all = len(pairs)
    timings.append({"stage": "build_pair_table", "elapsed_seconds": perf_counter() - started})
    del frame, good
    gc.collect()

    started = perf_counter()
    pairs = pairs.loc[pd.to_numeric(pairs["DELTA_DAYS"], errors="coerce") > 1.0, PAIR_COLUMNS].copy()
    numeric = [
        "GROUP_ID",
        "DELTA_VRAD",
        "PAIR_ERROR",
        "PAIR_ERROR_FORMAL",
        "NIGHT_1",
        "NIGHT_2",
        "DELTA_DAYS",
        "EXPID_1",
        "EXPID_2",
        "FIBER_1",
        "FIBER_2",
    ]
    for column in numeric:
        pairs[column] = pd.to_numeric(pairs[column], errors="coerce")
    valid = (
        pairs["GROUP_ID"].notna()
        & np.isfinite(pairs["DELTA_VRAD"])
        & np.isfinite(pairs["PAIR_ERROR"])
        & np.isfinite(pairs["PAIR_ERROR_FORMAL"])
        & (pairs["PAIR_ERROR"] > 0)
        & (pairs["PAIR_ERROR_FORMAL"] > 0)
        & pairs["FIBER_1"].between(0, 4999)
        & pairs["FIBER_2"].between(0, 4999)
    )
    pairs = pairs.loc[valid].copy()
    pairs["GROUP_ID"] = pairs["GROUP_ID"].astype("int64")
    for column in ("NIGHT_1", "NIGHT_2", "EXPID_1", "EXPID_2", "FIBER_1", "FIBER_2"):
        pairs[column] = pairs[column].astype("int64")
    pairs["PETAL_1"] = (pairs["FIBER_1"] // 500).astype("int8")
    pairs["PETAL_2"] = (pairs["FIBER_2"] // 500).astype("int8")
    pairs.to_pickle(CACHE)
    timings.append({"stage": "filter_and_write_cache", "elapsed_seconds": perf_counter() - started})

    input_fingerprint = {
        path.relative_to(ROOT).as_posix(): {"size": path.stat().st_size, "mtime_ns": path.stat().st_mtime_ns}
        for path in [*INPUTS, CORRECTION]
    }
    manifest = {
        "schema": "desi_rv_audit.discovery_pair_cache.v1",
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "input_fingerprint": input_fingerprint,
        "input_sha256": {
            item["name"]: item["sha256"]
            for item in json.loads(
                (ROOT / "reports" / "program_night_artifacts" / "run_manifest.json").read_text(
                    encoding="utf-8"
                )
            )["input_files"]
        },
        "backup_correction_md5": BACKUP_CORRECTION_MD5,
        "parameters": {
            "strict_desi_main": True,
            "min_sn_r": 5.0,
            "max_pairs_per_source": 20,
            "min_delta_days_exclusive": 1.0,
        },
        "counts": {
            "n_epochs_raw": n_epochs_raw,
            "n_epochs_good": n_epochs_good,
            "n_pairs_all": n_pairs_all,
            "n_pairs_interday": len(pairs),
            "n_sources_interday": int(pairs["GROUP_ID"].nunique()),
        },
        "petal_validation": petal_validation.to_dict(orient="records"),
        "cache": {
            "path": CACHE.name,
            "size": CACHE.stat().st_size,
            "sha256": _sha256(CACHE),
        },
        "timings": timings + [{"stage": "total", "elapsed_seconds": perf_counter() - total_started}],
    }
    _write_json(MANIFEST, manifest)
    print(json.dumps(manifest["counts"], sort_keys=True), flush=True)
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    build_cache(force=args.force)


if __name__ == "__main__":
    main()
