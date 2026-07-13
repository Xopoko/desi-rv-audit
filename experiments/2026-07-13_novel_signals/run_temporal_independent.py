"""Post-preregistered source-half robustness check for E1.

This does not replace the E1 primary test.  It asks whether persistence remains
when every correlation endpoint comes from a disjoint source half and all
offset graphs are fitted within one program only.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

from discovery_stats import _lag_correlation_arrays, fisher_z_symmetric  # noqa: E402
from desi_rv_audit.hashing import stable_seed  # noqa: E402


INPUT = EXPERIMENT_DIR / "within_program_offsets.csv"
OUTPUT = EXPERIMENT_DIR / "temporal_independent_halves.csv"
NULL_OUTPUT = EXPERIMENT_DIR / "temporal_independent_block_null.csv"
MANIFEST_OUTPUT = EXPERIMENT_DIR / "temporal_independent_manifest.json"

PROGRAMS = ("BACKUP", "BRIGHT", "DARK")
MAX_LAG = 7
MIN_PAIRS = 15
BLOCK_DAYS = 14
N_NULL = 9_999
N_BOOTSTRAP = 1_000
SEED = 20260713


def _dense(a: pd.Series, b: pd.Series) -> tuple[np.ndarray, np.ndarray]:
    calendar = pd.date_range(min(a.index.min(), b.index.min()), max(a.index.max(), b.index.max()), freq="D")
    return a.reindex(calendar).to_numpy(dtype=float), b.reindex(calendar).to_numpy(dtype=float)


def _consecutive_supported_nights(series: pd.Series) -> dict[str, float | int]:
    series = series.sort_index(kind="mergesort")
    days = series.index.to_numpy(dtype="datetime64[D]").astype("int64")
    values = series.to_numpy(dtype=float)
    gaps = np.diff(days)
    keep = (gaps >= 1) & (gaps <= MAX_LAG)
    earlier = values[:-1][keep]
    later = values[1:][keep]
    return {
        "n_nights": int(len(series)),
        "n_pairs": int(len(earlier)),
        "pearson_r": float(np.corrcoef(earlier, later)[0, 1]) if len(earlier) >= 3 else np.nan,
    }


def _statistic(a: np.ndarray, b: np.ndarray) -> dict[str, object]:
    correlations: list[float] = []
    sizes: list[int] = []
    lags: list[dict[str, object]] = []
    for lag in range(1, MAX_LAG + 1):
        a_to_b = _lag_correlation_arrays(a, b, lag, min_pairs=MIN_PAIRS, method="pearson")
        b_to_a = _lag_correlation_arrays(b, a, lag, min_pairs=MIN_PAIRS, method="pearson")
        correlations.extend([float(a_to_b["r"]), float(b_to_a["r"])])
        sizes.extend([int(a_to_b["n"]), int(b_to_a["n"])])
        combined_lag = fisher_z_symmetric(
            [float(a_to_b["r"]), float(b_to_a["r"])],
            [int(a_to_b["n"]), int(b_to_a["n"])],
        )
        lags.append(
            {
                "lag_days": lag,
                "r_a_t_b_t_plus_lag": a_to_b["r"],
                "n_a_t_b_t_plus_lag": a_to_b["n"],
                "r_b_t_a_t_plus_lag": b_to_a["r"],
                "n_b_t_a_t_plus_lag": b_to_a["n"],
                "symmetric_r": combined_lag["r"],
            }
        )
    aggregate = fisher_z_symmetric(correlations, sizes)
    return {"aggregate_r_1_7d": aggregate["r"], "aggregate_fisher_z": aggregate["fisher_z"], "lags": lags}


def _block_order(n_days: int, rng: np.random.Generator) -> np.ndarray:
    n_blocks = int(math.ceil(n_days / BLOCK_DAYS))
    order = rng.permutation(n_blocks)
    rotation = int(rng.integers(1, n_blocks))
    order = np.roll(order, rotation)
    if np.array_equal(order, np.arange(n_blocks)):
        order = np.roll(order, 1)
    return order


def run() -> pd.DataFrame:
    offsets = pd.read_csv(INPUT)
    result_records: list[dict[str, object]] = []
    null_records: list[dict[str, object]] = []
    for program in PROGRAMS:
        subset = offsets.loc[offsets["PROGRAM"] == program]
        series: dict[str, pd.Series] = {}
        for half in ("A", "B"):
            rows = subset.loc[subset["HALF"] == half]
            series[half] = pd.Series(
                rows["OFFSET_KMS"].to_numpy(dtype=float),
                index=pd.to_datetime(rows["NIGHT"].astype(str), format="%Y%m%d"),
            ).sort_index()
        a, b = _dense(series["A"], series["B"])
        observed = _statistic(a, b)
        consecutive_a = _consecutive_supported_nights(series["A"])
        consecutive_b = _consecutive_supported_nights(series["B"])

        n_blocks = int(math.ceil(len(a) / BLOCK_DAYS))
        padded_length = n_blocks * BLOCK_DAYS
        a_pad = np.full(padded_length, np.nan)
        b_pad = np.full(padded_length, np.nan)
        a_pad[: len(a)] = a
        b_pad[: len(b)] = b
        b_blocks = b_pad.reshape(n_blocks, BLOCK_DAYS)
        rng = np.random.default_rng(stable_seed(f"E1:independent:null:{program}:{SEED}"))
        null_values: list[float] = []
        for draw in range(N_NULL):
            order = _block_order(padded_length, rng)
            statistic = _statistic(a_pad, b_blocks[order].reshape(-1))
            value = float(statistic["aggregate_r_1_7d"])
            null_values.append(value)
            null_records.append({"PROGRAM": program, "DRAW": draw, "AGGREGATE_R_1_7D": value})
        null_array = np.asarray(null_values, dtype=float)
        empirical_p = float(
            (1 + np.sum(null_array >= float(observed["aggregate_r_1_7d"]))) / (1 + len(null_array))
        )

        rng = np.random.default_rng(stable_seed(f"E1:independent:bootstrap:{program}:{SEED}"))
        n_blocks_sample = int(math.ceil(len(a) / BLOCK_DAYS))
        offsets_in_block = np.arange(BLOCK_DAYS, dtype=np.int64)
        bootstrap: list[float] = []
        for _ in range(N_BOOTSTRAP):
            starts = rng.integers(0, len(a), size=n_blocks_sample)
            indices = (
                (starts[:, None] + offsets_in_block[None, :]) % len(a)
            ).reshape(-1)[: len(a)]
            bootstrap.append(float(_statistic(a[indices], b[indices])["aggregate_r_1_7d"]))
        boot = np.asarray(bootstrap, dtype=float)
        result_records.append(
            {
                "PROGRAM": program,
                "AGGREGATE_R_1_7D": observed["aggregate_r_1_7d"],
                "HALF_A_N_NIGHTS": consecutive_a["n_nights"],
                "HALF_A_N_CONSECUTIVE_PAIRS_1_7D": consecutive_a["n_pairs"],
                "HALF_A_CONSECUTIVE_PEARSON_R_1_7D": consecutive_a["pearson_r"],
                "HALF_B_N_NIGHTS": consecutive_b["n_nights"],
                "HALF_B_N_CONSECUTIVE_PAIRS_1_7D": consecutive_b["n_pairs"],
                "HALF_B_CONSECUTIVE_PEARSON_R_1_7D": consecutive_b["pearson_r"],
                "BLOCK_NULL_P": empirical_p,
                "NULL_Q975": float(np.nanquantile(null_array, 0.975)),
                "BOOTSTRAP_R_LOW_95": float(np.nanquantile(boot, 0.025)),
                "BOOTSTRAP_R_HIGH_95": float(np.nanquantile(boot, 0.975)),
                "N_NULL": N_NULL,
                "N_BOOTSTRAP": N_BOOTSTRAP,
                "LAG_DETAILS_JSON": json.dumps(observed["lags"], sort_keys=True),
            }
        )
    result = pd.DataFrame.from_records(result_records)
    result.to_csv(OUTPUT, index=False, lineterminator="\n")
    pd.DataFrame.from_records(null_records).to_csv(NULL_OUTPUT, index=False, lineterminator="\n")
    MANIFEST_OUTPUT.write_text(
        json.dumps(
            {
                "schema": "desi_rv_audit.temporal_independent_halves.v1",
                "status": "complete",
                "role": "post_preregistered_robustness_check_not_used_for_E1_decision",
                "parameters": {
                    "max_lag_days": MAX_LAG,
                    "block_days": BLOCK_DAYS,
                    "n_null": N_NULL,
                    "n_bootstrap": N_BOOTSTRAP,
                    "seed": SEED,
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(result.to_json(orient="records"), flush=True)
    return result


if __name__ == "__main__":
    run()
