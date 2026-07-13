from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import shutil
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import rankdata


EXPERIMENT_ID = "E1_temporal_persistence"
N_OFFSET_PERMUTATIONS = 9_999
MIN_ADJACENT_PAIRS = 20
MIN_ABS_PEARSON_R = 0.25
MAX_CORRECTED_P = 0.01
MIN_LOO_SAME_SIGN = 4
MIN_GAP_DAYS = 1
MAX_GAP_DAYS = 7
RELEASE_TAG = "v0.3.0"
RELEASE_BASE_URL = (
    "https://github.com/Xopoko/desi-rv-audit/releases/download/"
    f"{RELEASE_TAG}/"
)

ASSETS = {
    "program_night_permutation_offsets.csv.gz": {
        "gzip_sha256": "38bb2f2d3905482591b7638717a498da80a14c3408c4b15d23f0e36dd71db13d",
        "csv_sha256": "910aed945056010bac4b424697fe8dc9b1fff195108736bdad852442d6c1fb44",
    },
    "program_night_bootstrap_offsets.csv.gz": {
        "gzip_sha256": "72544b6d11dbc9edd7cfa76173f61f5692199a669f4a7b3d437d64ce8874a12d",
        "csv_sha256": "744bdd5433d93695949678346dfe596456edfb4493befbcd60d095fe3045aa47",
    },
}

PERSISTENCE_FIELDS = (
    "PEARSON_R_1_7D",
    "SPEARMAN_RHO_1_7D",
    "PEARSON_R_EXACT_1D",
    "SPEARMAN_RHO_EXACT_1D",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_seed(label: str) -> int:
    digest = hashlib.blake2b(
        label.encode("utf-8"),
        digest_size=8,
        person=b"desi-rv-fold-v1",
    ).digest()
    return int.from_bytes(digest, byteorder="little", signed=False) % (2**32)


def _download_asset(output_dir: Path, name: str, expected_sha256: str) -> Path:
    destination = output_dir / name
    if destination.exists() and _sha256_path(destination) == expected_sha256:
        return destination

    temporary = output_dir / f"{name}.part"
    request = urllib.request.Request(
        RELEASE_BASE_URL + name,
        headers={"User-Agent": "desi-rv-audit-e1-temporal/1"},
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            with temporary.open("wb") as handle:
                shutil.copyfileobj(response, handle)
        actual = _sha256_path(temporary)
        if actual != expected_sha256:
            raise ValueError(
                f"Downloaded {name} SHA-256 mismatch: {actual} != {expected_sha256}"
            )
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return destination


def _read_verified_gzip_csv(path: Path, expected_csv_sha256: str) -> pd.DataFrame:
    with gzip.open(path, "rb") as handle:
        payload = handle.read()
    actual = _sha256_bytes(payload)
    if actual != expected_csv_sha256:
        raise ValueError(
            f"Uncompressed {path.name} SHA-256 mismatch: "
            f"{actual} != {expected_csv_sha256}"
        )
    return pd.read_csv(io.BytesIO(payload))


def _write_csv_lf(frame: pd.DataFrame, path: Path) -> None:
    payload = frame.to_csv(index=False, lineterminator="\n").encode("utf-8")
    path.write_bytes(payload)
    if b"\r\n" in payload:
        raise AssertionError(f"CRLF found in {path}")


def _validate_observed_artifact(repo_root: Path, path: Path) -> dict:
    manifest_path = repo_root / "reports" / "program_night_artifacts" / "run_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [
        item
        for item in manifest["output_files"]
        if item["name"] == "diagnostic_offsets_program_night.csv"
    ]
    if len(matches) != 1:
        raise ValueError("run_manifest.json does not identify exactly one diagnostic offset file")
    expected = matches[0]["sha256"]
    payload = path.read_bytes()
    raw_sha = _sha256_bytes(payload)
    normalized_sha = _sha256_bytes(payload.replace(b"\r\n", b"\n"))
    if expected not in {raw_sha, normalized_sha}:
        raise ValueError(
            "diagnostic offset SHA-256 does not match run manifest, including LF normalization"
        )
    return {
        "git_commit": manifest["git_commit"],
        "release_tag": manifest["release_tag"],
        "expected_sha256": expected,
        "raw_sha256": raw_sha,
        "lf_normalized_sha256": normalized_sha,
    }


def _annotate_labels(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"FOLD", "LABEL", "OFFSET_KMS", "COMPONENT"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"Offset table is missing columns: {missing}")
    output = frame.copy()
    parts = output["LABEL"].astype("string").str.rsplit(":", n=1, expand=True)
    if parts.shape[1] != 2:
        raise ValueError("LABEL must have PROGRAM:YYYYMMDD form")
    output["PROGRAM"] = parts[0].str.strip().str.upper()
    output["NIGHT"] = parts[1].str.strip()
    output["DATE"] = pd.to_datetime(output["NIGHT"], format="%Y%m%d", errors="raise")
    if output[list(required)].isna().any().any():
        raise ValueError("Offset table contains nulls in required columns")
    return output


def _prepare_fold_offsets(
    frame: pd.DataFrame,
    ensemble_column: str | None = None,
) -> tuple[pd.DataFrame, int]:
    work = _annotate_labels(frame)
    fold_keys = ([ensemble_column] if ensemble_column else []) + ["FOLD"]
    component_keys = fold_keys + ["COMPONENT"]
    sizes = work.groupby(component_keys, sort=True).size().rename("COMPONENT_SIZE").reset_index()
    ascending = [True] * len(fold_keys) + [False, True]
    largest = (
        sizes.sort_values(fold_keys + ["COMPONENT_SIZE", "COMPONENT"], ascending=ascending)
        .drop_duplicates(fold_keys, keep="first")
        [fold_keys + ["COMPONENT"]]
    )
    selected = work.merge(largest, on=fold_keys + ["COMPONENT"], how="inner")
    excluded = int(len(work) - len(selected))

    duplicate_keys = fold_keys + ["LABEL"]
    if selected.duplicated(duplicate_keys).any():
        raise ValueError(f"Duplicate rows at grain {duplicate_keys}")
    gauge_keys = fold_keys + ["PROGRAM"]
    selected["PROGRAM_GAUGE_OFFSET_KMS"] = selected["OFFSET_KMS"] - selected.groupby(
        gauge_keys, sort=False
    )["OFFSET_KMS"].transform("mean")
    return selected, excluded


def _aggregate_fold_offsets(
    frame: pd.DataFrame,
    ensemble_column: str | None = None,
) -> pd.DataFrame:
    keys = ([ensemble_column] if ensemble_column else []) + [
        "LABEL",
        "PROGRAM",
        "NIGHT",
        "DATE",
    ]
    return (
        frame.groupby(keys, as_index=False, sort=True)
        .agg(
            PROGRAM_GAUGE_OFFSET_KMS=("PROGRAM_GAUGE_OFFSET_KMS", "median"),
            N_FOLDS=("FOLD", "nunique"),
            FOLD_OFFSET_STD_KMS=("PROGRAM_GAUGE_OFFSET_KMS", "std"),
        )
        .sort_values(([ensemble_column] if ensemble_column else []) + ["PROGRAM", "DATE"])
        .reset_index(drop=True)
    )


def _corr(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) < 2 or len(right) < 2:
        return float("nan")
    left_centered = left - np.mean(left)
    right_centered = right - np.mean(right)
    denominator = np.sqrt(
        np.sum(np.square(left_centered)) * np.sum(np.square(right_centered))
    )
    if not np.isfinite(denominator) or denominator <= 0:
        return float("nan")
    return float(np.sum(left_centered * right_centered) / denominator)


def _adjacent_pair_arrays(
    values: np.ndarray,
    dates: np.ndarray,
    exact_one_day: bool,
) -> tuple[np.ndarray, np.ndarray]:
    days = dates.astype("datetime64[D]").astype(np.int64)
    gaps = np.diff(days)
    if exact_one_day:
        keep = gaps == 1
    else:
        keep = (gaps >= MIN_GAP_DAYS) & (gaps <= MAX_GAP_DAYS)
    return values[:-1][keep], values[1:][keep]


def _pair_metrics(left: np.ndarray, right: np.ndarray) -> tuple[int, float, float]:
    return (
        int(len(left)),
        _corr(left, right),
        _corr(rankdata(left), rankdata(right)) if len(left) >= 2 else float("nan"),
    )


def _series_map(frame: pd.DataFrame) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    output: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for program, group in frame.groupby("PROGRAM", sort=True):
        ordered = group.sort_values("DATE")
        output[str(program)] = (
            ordered["PROGRAM_GAUGE_OFFSET_KMS"].to_numpy(dtype=float),
            ordered["DATE"].to_numpy(dtype="datetime64[ns]"),
        )
    return output


def _persistence_metrics(
    series: dict[str, tuple[np.ndarray, np.ndarray]],
) -> dict[str, dict[str, float | int]]:
    results: dict[str, dict[str, float | int]] = {}
    pooled_left: list[np.ndarray] = []
    pooled_right: list[np.ndarray] = []
    pooled_exact_left: list[np.ndarray] = []
    pooled_exact_right: list[np.ndarray] = []
    pooled_nights = 0

    for program in sorted(series):
        values, dates = series[program]
        left, right = _adjacent_pair_arrays(values, dates, exact_one_day=False)
        exact_left, exact_right = _adjacent_pair_arrays(values, dates, exact_one_day=True)
        n_pairs, pearson, spearman = _pair_metrics(left, right)
        n_exact, pearson_exact, spearman_exact = _pair_metrics(exact_left, exact_right)
        results[program] = {
            "N_NIGHTS": int(len(values)),
            "N_ADJACENT_PAIRS_1_7D": n_pairs,
            "N_ADJACENT_PAIRS_EXACT_1D": n_exact,
            "PEARSON_R_1_7D": pearson,
            "SPEARMAN_RHO_1_7D": spearman,
            "PEARSON_R_EXACT_1D": pearson_exact,
            "SPEARMAN_RHO_EXACT_1D": spearman_exact,
        }

        standard_deviation = np.std(values, ddof=1)
        standardized = (values - np.mean(values)) / standard_deviation
        pair_left, pair_right = _adjacent_pair_arrays(standardized, dates, False)
        one_left, one_right = _adjacent_pair_arrays(standardized, dates, True)
        pooled_left.append(pair_left)
        pooled_right.append(pair_right)
        pooled_exact_left.append(one_left)
        pooled_exact_right.append(one_right)
        pooled_nights += len(values)

    left = np.concatenate(pooled_left)
    right = np.concatenate(pooled_right)
    exact_left = np.concatenate(pooled_exact_left)
    exact_right = np.concatenate(pooled_exact_right)
    n_pairs, pearson, spearman = _pair_metrics(left, right)
    n_exact, pearson_exact, spearman_exact = _pair_metrics(exact_left, exact_right)
    results["POOLED"] = {
        "N_NIGHTS": int(pooled_nights),
        "N_ADJACENT_PAIRS_1_7D": n_pairs,
        "N_ADJACENT_PAIRS_EXACT_1D": n_exact,
        "PEARSON_R_1_7D": pearson,
        "SPEARMAN_RHO_1_7D": spearman,
        "PEARSON_R_EXACT_1D": pearson_exact,
        "SPEARMAN_RHO_EXACT_1D": spearman_exact,
    }
    return results


def _change_point(values: np.ndarray, dates: np.ndarray) -> dict[str, float | int | str]:
    n_values = len(values)
    minimum_segment = max(10, int(np.ceil(0.15 * n_values)))
    split_sizes = np.arange(1, n_values)
    valid = (split_sizes >= minimum_segment) & (
        n_values - split_sizes >= minimum_segment
    )
    cumulative = np.cumsum(values)
    pre_mean = cumulative[:-1] / split_sizes
    post_mean = (cumulative[-1] - cumulative[:-1]) / (n_values - split_sizes)
    scale = np.sqrt(split_sizes * (n_values - split_sizes) / n_values)
    scale /= np.std(values, ddof=1)
    scores = np.abs(post_mean - pre_mean) * scale
    scores[~valid] = -np.inf
    index = int(np.argmax(scores))
    split = int(split_sizes[index])
    return {
        "N_NIGHTS": n_values,
        "MIN_SEGMENT_N": minimum_segment,
        "CHANGE_AFTER_NIGHT": str(pd.Timestamp(dates[split - 1]).date()),
        "CHANGE_NEXT_NIGHT": str(pd.Timestamp(dates[split]).date()),
        "PRE_MEAN_KMS": float(np.mean(values[:split])),
        "POST_MEAN_KMS": float(np.mean(values[split:])),
        "DELTA_POST_MINUS_PRE_KMS": float(np.mean(values[split:]) - np.mean(values[:split])),
        "CUSUM_SCORE": float(scores[index]),
    }


def _change_point_metrics(
    series: dict[str, tuple[np.ndarray, np.ndarray]],
) -> dict[str, dict[str, float | int | str]]:
    return {
        program: _change_point(values, dates)
        for program, (values, dates) in sorted(series.items())
    }


def _offset_permutation_controls(
    observed_series: dict[str, tuple[np.ndarray, np.ndarray]],
    scopes: list[str],
    programs: list[str],
) -> tuple[dict[str, np.ndarray], np.ndarray]:
    nulls = {
        field: np.full((N_OFFSET_PERMUTATIONS, len(scopes)), np.nan, dtype=float)
        for field in PERSISTENCE_FIELDS
    }
    change_null = np.full((N_OFFSET_PERMUTATIONS, len(programs)), np.nan, dtype=float)
    random_generators = {
        program: np.random.default_rng(
            _stable_seed(f"{EXPERIMENT_ID}:offset-permutations-v1:{program}")
        )
        for program in programs
    }

    for permutation_index in range(N_OFFSET_PERMUTATIONS):
        permuted: dict[str, tuple[np.ndarray, np.ndarray]] = {}
        for program in programs:
            values, dates = observed_series[program]
            order = random_generators[program].permutation(len(values))
            permuted[program] = (values[order], dates)
        persistence = _persistence_metrics(permuted)
        change_points = _change_point_metrics(permuted)
        for scope_index, scope in enumerate(scopes):
            for field in PERSISTENCE_FIELDS:
                nulls[field][permutation_index, scope_index] = float(
                    persistence[scope][field]
                )
        for program_index, program in enumerate(programs):
            change_null[permutation_index, program_index] = float(
                change_points[program]["CUSUM_SCORE"]
            )
    return nulls, change_null


def _ensemble_controls(
    aggregate: pd.DataFrame,
    ensemble_column: str,
    scopes: list[str],
    programs: list[str],
) -> tuple[dict[str, np.ndarray], np.ndarray, dict[str, list[dict]]]:
    ensemble_ids = sorted(aggregate[ensemble_column].unique().tolist())
    metrics = {
        field: np.full((len(ensemble_ids), len(scopes)), np.nan, dtype=float)
        for field in PERSISTENCE_FIELDS
    }
    change_scores = np.full((len(ensemble_ids), len(programs)), np.nan, dtype=float)
    change_records: dict[str, list[dict]] = {program: [] for program in programs}
    for row_index, ensemble_id in enumerate(ensemble_ids):
        group = aggregate.loc[aggregate[ensemble_column].eq(ensemble_id)]
        series = _series_map(group)
        persistence = _persistence_metrics(series)
        change_points = _change_point_metrics(series)
        for scope_index, scope in enumerate(scopes):
            for field in PERSISTENCE_FIELDS:
                metrics[field][row_index, scope_index] = float(persistence[scope][field])
        for program_index, program in enumerate(programs):
            change_scores[row_index, program_index] = float(
                change_points[program]["CUSUM_SCORE"]
            )
            change_records[program].append(change_points[program])
    return metrics, change_scores, change_records


def _empirical_p(observed: float, null: np.ndarray, absolute: bool = True) -> tuple[int, float]:
    valid = null[np.isfinite(null)]
    if absolute:
        exceed = int(np.count_nonzero(np.abs(valid) >= abs(observed)))
    else:
        exceed = int(np.count_nonzero(valid >= observed))
    return exceed, float((exceed + 1) / (len(valid) + 1))


def _holm_adjust(raw_p: list[float]) -> list[float]:
    values = np.asarray(raw_p, dtype=float)
    order = np.argsort(values)
    adjusted = np.empty(len(values), dtype=float)
    running = 0.0
    for rank, index in enumerate(order):
        candidate = min(1.0, (len(values) - rank) * values[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted.tolist()


def _quantiles(values: list[float] | np.ndarray) -> tuple[float, float, float]:
    array = np.asarray(values, dtype=float)
    array = array[np.isfinite(array)]
    if not len(array):
        return float("nan"), float("nan"), float("nan")
    q025, median, q975 = np.quantile(array, [0.025, 0.5, 0.975])
    return float(q025), float(median), float(q975)


def _leave_one_fold_out(
    selected_observed: pd.DataFrame,
    observed_metrics: dict[str, dict[str, float | int]],
    scopes: list[str],
) -> dict[str, dict[str, float | int]]:
    folds = sorted(selected_observed["FOLD"].unique().tolist())
    correlations = {scope: [] for scope in scopes}
    for fold in folds:
        aggregate = _aggregate_fold_offsets(
            selected_observed.loc[selected_observed["FOLD"].ne(fold)]
        )
        metrics = _persistence_metrics(_series_map(aggregate))
        for scope in scopes:
            correlations[scope].append(float(metrics[scope]["PEARSON_R_1_7D"]))
    output = {}
    for scope in scopes:
        observed_sign = np.sign(float(observed_metrics[scope]["PEARSON_R_1_7D"]))
        values = np.asarray(correlations[scope], dtype=float)
        output[scope] = {
            "LOO_N": len(values),
            "LOO_SAME_SIGN": int(np.count_nonzero(np.sign(values) == observed_sign)),
            "LOO_PEARSON_MIN": float(np.nanmin(values)),
            "LOO_PEARSON_MAX": float(np.nanmax(values)),
        }
    return output


def _bootstrap_offset_summary(bootstrap_aggregate: pd.DataFrame) -> pd.DataFrame:
    return (
        bootstrap_aggregate.groupby("LABEL", as_index=False)
        .agg(
            BOOTSTRAP_N=("BOOTSTRAP", "nunique"),
            BOOTSTRAP_OFFSET_MEDIAN_KMS=("PROGRAM_GAUGE_OFFSET_KMS", "median"),
            BOOTSTRAP_OFFSET_Q025_KMS=(
                "PROGRAM_GAUGE_OFFSET_KMS",
                lambda values: values.quantile(0.025),
            ),
            BOOTSTRAP_OFFSET_Q975_KMS=(
                "PROGRAM_GAUGE_OFFSET_KMS",
                lambda values: values.quantile(0.975),
            ),
        )
    )


def main() -> None:
    experiment_dir = Path(__file__).resolve().parent
    repo_root = experiment_dir.parents[1]
    observed_path = (
        repo_root
        / "reports"
        / "program_night_artifacts"
        / "diagnostic_offsets_program_night.csv"
    )
    provenance = _validate_observed_artifact(repo_root, observed_path)

    asset_paths = {}
    for name, metadata in ASSETS.items():
        asset_paths[name] = _download_asset(
            experiment_dir,
            name,
            metadata["gzip_sha256"],
        )
    permutation_frame = _read_verified_gzip_csv(
        asset_paths["program_night_permutation_offsets.csv.gz"],
        ASSETS["program_night_permutation_offsets.csv.gz"]["csv_sha256"],
    )
    bootstrap_frame = _read_verified_gzip_csv(
        asset_paths["program_night_bootstrap_offsets.csv.gz"],
        ASSETS["program_night_bootstrap_offsets.csv.gz"]["csv_sha256"],
    )
    observed_frame = pd.read_csv(observed_path)

    selected_observed, observed_excluded = _prepare_fold_offsets(observed_frame)
    selected_permutation, permutation_excluded = _prepare_fold_offsets(
        permutation_frame,
        "PERMUTATION",
    )
    selected_bootstrap, bootstrap_excluded = _prepare_fold_offsets(
        bootstrap_frame,
        "BOOTSTRAP",
    )
    observed_aggregate = _aggregate_fold_offsets(selected_observed)
    permutation_aggregate = _aggregate_fold_offsets(
        selected_permutation,
        "PERMUTATION",
    )
    bootstrap_aggregate = _aggregate_fold_offsets(selected_bootstrap, "BOOTSTRAP")

    programs = sorted(observed_aggregate["PROGRAM"].unique().tolist())
    scopes = programs + ["POOLED"]
    observed_series = _series_map(observed_aggregate)
    observed_persistence = _persistence_metrics(observed_series)
    observed_change_points = _change_point_metrics(observed_series)
    loo = _leave_one_fold_out(selected_observed, observed_persistence, scopes)

    offset_null, offset_change_null = _offset_permutation_controls(
        observed_series,
        scopes,
        programs,
    )
    full_null, full_change_null, _ = _ensemble_controls(
        permutation_aggregate,
        "PERMUTATION",
        scopes,
        programs,
    )
    bootstrap_metrics, bootstrap_change_scores, bootstrap_change_records = _ensemble_controls(
        bootstrap_aggregate,
        "BOOTSTRAP",
        scopes,
        programs,
    )

    raw_offset_primary_p = []
    raw_full_primary_p = []
    offset_primary_exceed = []
    full_primary_exceed = []
    for scope_index, scope in enumerate(scopes):
        observed = float(observed_persistence[scope]["PEARSON_R_1_7D"])
        exceed, p_value = _empirical_p(
            observed,
            offset_null["PEARSON_R_1_7D"][:, scope_index],
        )
        offset_primary_exceed.append(exceed)
        raw_offset_primary_p.append(p_value)
        exceed, p_value = _empirical_p(
            observed,
            full_null["PEARSON_R_1_7D"][:, scope_index],
        )
        full_primary_exceed.append(exceed)
        raw_full_primary_p.append(p_value)
    offset_holm = _holm_adjust(raw_offset_primary_p)
    full_holm = _holm_adjust(raw_full_primary_p)
    offset_max = np.nanmax(np.abs(offset_null["PEARSON_R_1_7D"]), axis=1)
    full_max = np.nanmax(np.abs(full_null["PEARSON_R_1_7D"]), axis=1)

    persistence_rows = []
    for scope_index, scope in enumerate(scopes):
        observed = observed_persistence[scope]
        observed_r = float(observed["PEARSON_R_1_7D"])
        offset_max_exceed, offset_max_p = _empirical_p(observed_r, offset_max)
        full_max_exceed, full_max_p = _empirical_p(observed_r, full_max)
        spearman_exceed, spearman_p = _empirical_p(
            float(observed["SPEARMAN_RHO_1_7D"]),
            offset_null["SPEARMAN_RHO_1_7D"][:, scope_index],
        )
        exact_exceed, exact_p = _empirical_p(
            float(observed["PEARSON_R_EXACT_1D"]),
            offset_null["PEARSON_R_EXACT_1D"][:, scope_index],
        )
        full_spearman_exceed, full_spearman_p = _empirical_p(
            float(observed["SPEARMAN_RHO_1_7D"]),
            full_null["SPEARMAN_RHO_1_7D"][:, scope_index],
        )
        full_exact_exceed, full_exact_p = _empirical_p(
            float(observed["PEARSON_R_EXACT_1D"]),
            full_null["PEARSON_R_EXACT_1D"][:, scope_index],
        )
        bootstrap_q025, bootstrap_median, bootstrap_q975 = _quantiles(
            bootstrap_metrics["PEARSON_R_1_7D"][:, scope_index]
        )
        minimum_pairs_pass = int(observed["N_ADJACENT_PAIRS_1_7D"]) >= MIN_ADJACENT_PAIRS
        effect_pass = abs(observed_r) >= MIN_ABS_PEARSON_R
        corrected_p_pass = offset_max_p <= MAX_CORRECTED_P
        loo_pass = int(loo[scope]["LOO_SAME_SIGN"]) >= MIN_LOO_SAME_SIGN
        persistence_rows.append(
            {
                "EXPERIMENT_ID": EXPERIMENT_ID,
                "SCOPE": scope,
                **observed,
                "OFFSET_PERMUTATIONS": N_OFFSET_PERMUTATIONS,
                "OFFSET_PERM_ABS_EXCEED": offset_primary_exceed[scope_index],
                "OFFSET_PERM_P_RAW": raw_offset_primary_p[scope_index],
                "OFFSET_PERM_P_HOLM": offset_holm[scope_index],
                "OFFSET_PERM_MAXT_EXCEED": offset_max_exceed,
                "OFFSET_PERM_P_MAXT": offset_max_p,
                "OFFSET_PERM_SPEARMAN_ABS_EXCEED": spearman_exceed,
                "OFFSET_PERM_SPEARMAN_P_RAW": spearman_p,
                "OFFSET_PERM_EXACT1D_ABS_EXCEED": exact_exceed,
                "OFFSET_PERM_EXACT1D_P_RAW": exact_p,
                "FULL_PIPELINE_CONTROLS": len(full_max),
                "FULL_PIPELINE_ABS_EXCEED": full_primary_exceed[scope_index],
                "FULL_PIPELINE_P_RAW": raw_full_primary_p[scope_index],
                "FULL_PIPELINE_P_HOLM": full_holm[scope_index],
                "FULL_PIPELINE_MAXT_EXCEED": full_max_exceed,
                "FULL_PIPELINE_P_MAXT": full_max_p,
                "FULL_PIPELINE_SPEARMAN_ABS_EXCEED": full_spearman_exceed,
                "FULL_PIPELINE_SPEARMAN_P_RAW": full_spearman_p,
                "FULL_PIPELINE_EXACT1D_ABS_EXCEED": full_exact_exceed,
                "FULL_PIPELINE_EXACT1D_P_RAW": full_exact_p,
                "BOOTSTRAPS": bootstrap_metrics["PEARSON_R_1_7D"].shape[0],
                "BOOTSTRAP_PEARSON_Q025": bootstrap_q025,
                "BOOTSTRAP_PEARSON_MEDIAN": bootstrap_median,
                "BOOTSTRAP_PEARSON_Q975": bootstrap_q975,
                **loo[scope],
                "MINIMUM_PAIRS_PASS": minimum_pairs_pass,
                "MINIMUM_EFFECT_PASS": effect_pass,
                "CORRECTED_P_METHOD": "MAXT_ACROSS_PROGRAMS_AND_POOLED",
                "CORRECTED_P_PASS": corrected_p_pass,
                "LOO_SIGN_PASS": loo_pass,
                "SCOPE_PASS": minimum_pairs_pass and effect_pass and corrected_p_pass and loo_pass,
            }
        )
    persistence_output = pd.DataFrame.from_records(persistence_rows)
    individual_passes = int(
        persistence_output.loc[persistence_output["SCOPE"].isin(programs), "SCOPE_PASS"].sum()
    )
    pooled_pass = bool(
        persistence_output.loc[persistence_output["SCOPE"].eq("POOLED"), "SCOPE_PASS"].iloc[0]
    )
    decision = "pass" if pooled_pass or individual_passes >= 2 else "null"
    persistence_output["E1_DECISION"] = decision
    persistence_output["N_INDIVIDUAL_PROGRAM_PASSES"] = individual_passes
    persistence_output["POOLED_PASS"] = pooled_pass

    offset_change_max = np.nanmax(offset_change_null, axis=1)
    full_change_max = np.nanmax(full_change_null, axis=1)
    change_rows = []
    for program_index, program in enumerate(programs):
        observed = observed_change_points[program]
        observed_score = float(observed["CUSUM_SCORE"])
        offset_exceed, offset_p = _empirical_p(
            observed_score,
            offset_change_null[:, program_index],
            absolute=False,
        )
        offset_max_exceed, offset_max_p = _empirical_p(
            observed_score,
            offset_change_max,
            absolute=False,
        )
        full_exceed, full_p = _empirical_p(
            observed_score,
            full_change_null[:, program_index],
            absolute=False,
        )
        full_max_exceed, full_max_p = _empirical_p(
            observed_score,
            full_change_max,
            absolute=False,
        )
        score_q025, score_median, score_q975 = _quantiles(
            bootstrap_change_scores[:, program_index]
        )
        bootstrap_records = bootstrap_change_records[program]
        delta_q025, delta_median, delta_q975 = _quantiles(
            [float(record["DELTA_POST_MINUS_PRE_KMS"]) for record in bootstrap_records]
        )
        splits = pd.Series(
            [
                f"{record['CHANGE_AFTER_NIGHT']}/{record['CHANGE_NEXT_NIGHT']}"
                for record in bootstrap_records
            ],
            dtype="string",
        ).value_counts()
        modal_split = str(splits.index[0])
        modal_after, modal_next = modal_split.split("/", maxsplit=1)
        change_rows.append(
            {
                "EXPERIMENT_ID": EXPERIMENT_ID,
                "PROGRAM": program,
                **observed,
                "OFFSET_PERMUTATIONS": N_OFFSET_PERMUTATIONS,
                "OFFSET_PERM_EXCEED": offset_exceed,
                "OFFSET_PERM_P_RAW": offset_p,
                "OFFSET_PERM_MAXT_EXCEED": offset_max_exceed,
                "OFFSET_PERM_P_MAXT": offset_max_p,
                "FULL_PIPELINE_CONTROLS": full_change_null.shape[0],
                "FULL_PIPELINE_EXCEED": full_exceed,
                "FULL_PIPELINE_P_RAW": full_p,
                "FULL_PIPELINE_MAXT_EXCEED": full_max_exceed,
                "FULL_PIPELINE_P_MAXT": full_max_p,
                "BOOTSTRAPS": bootstrap_change_scores.shape[0],
                "BOOTSTRAP_SCORE_Q025": score_q025,
                "BOOTSTRAP_SCORE_MEDIAN": score_median,
                "BOOTSTRAP_SCORE_Q975": score_q975,
                "BOOTSTRAP_DELTA_Q025_KMS": delta_q025,
                "BOOTSTRAP_DELTA_MEDIAN_KMS": delta_median,
                "BOOTSTRAP_DELTA_Q975_KMS": delta_q975,
                "BOOTSTRAP_MODAL_CHANGE_AFTER": modal_after,
                "BOOTSTRAP_MODAL_CHANGE_NEXT": modal_next,
                "BOOTSTRAP_MODAL_SPLIT_COUNT": int(splits.iloc[0]),
            }
        )
    change_output = pd.DataFrame.from_records(change_rows)

    offsets_output = observed_aggregate.merge(
        _bootstrap_offset_summary(bootstrap_aggregate),
        on="LABEL",
        how="left",
        validate="one_to_one",
    )
    offsets_output.insert(0, "EXPERIMENT_ID", EXPERIMENT_ID)
    offsets_output["DATE"] = offsets_output["DATE"].dt.strftime("%Y-%m-%d")

    persistence_path = experiment_dir / "temporal_persistence.csv"
    change_path = experiment_dir / "temporal_change_points.csv"
    offsets_path = experiment_dir / "temporal_offsets.csv"
    _write_csv_lf(persistence_output, persistence_path)
    _write_csv_lf(change_output, change_path)
    _write_csv_lf(offsets_output, offsets_path)

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "decision": decision,
        "individual_program_passes": individual_passes,
        "pooled_pass": pooled_pass,
        "observed_rows": len(observed_frame),
        "observed_labels": int(observed_frame["LABEL"].nunique()),
        "largest_component_labels": int(len(observed_aggregate)),
        "component_rows_excluded": {
            "observed": observed_excluded,
            "permutation": permutation_excluded,
            "bootstrap": bootstrap_excluded,
        },
        "full_pipeline_controls": int(permutation_aggregate["PERMUTATION"].nunique()),
        "bootstrap_ensembles": int(bootstrap_aggregate["BOOTSTRAP"].nunique()),
        "offset_permutations": N_OFFSET_PERMUTATIONS,
        "provenance": provenance,
        "outputs": [path.name for path in (persistence_path, change_path, offsets_path)],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
