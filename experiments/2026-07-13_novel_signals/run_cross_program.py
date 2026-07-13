from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parent
ROOT = EXPERIMENT_DIR.parents[1]
SRC = ROOT / "src"
for path in (SRC, EXPERIMENT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from desi_rv_audit.hashing import stable_hash_mod, stable_seed  # noqa: E402
from desi_rv_audit.program_night import _fit_offsets  # noqa: E402
from discovery_stats import (  # noqa: E402
    _zero_lag_excess_arrays,
    fisher_z_symmetric,
    holm_adjust,
    same_date_intersection_correlation,
    zero_lag_excess,
)


CACHE = EXPERIMENT_DIR / "pair_cache.pkl"
OUTPUT = EXPERIMENT_DIR / "cross_program_coherence.csv"
OFFSETS_OUTPUT = EXPERIMENT_DIR / "within_program_offsets.csv"
LAGS_OUTPUT = EXPERIMENT_DIR / "cross_program_lags.csv"
NULL_OUTPUT = EXPERIMENT_DIR / "cross_program_block_null.csv"
BOOTSTRAP_OUTPUT = EXPERIMENT_DIR / "cross_program_bootstrap.csv"
META_OUTPUT = EXPERIMENT_DIR / "cross_program_manifest.json"

PROGRAMS = ("BACKUP", "BRIGHT", "DARK")
PROGRAM_PAIRS = (("BRIGHT", "DARK"), ("BACKUP", "BRIGHT"), ("BACKUP", "DARK"))
PRIMARY_PAIR = ("BRIGHT", "DARK")
MIN_PAIRS_PER_LABEL = 200
MIN_SHARED_NIGHTS = 20
MAX_LAG_DAYS = 30
BLOCK_DAYS = 14
N_NULL_DRAWS = 9_999
N_BOOTSTRAPS = 1_000
SEED = 20260713


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _series(offsets: pd.DataFrame, program: str, half: str) -> pd.Series:
    subset = offsets.loc[(offsets["PROGRAM"] == program) & (offsets["HALF"] == half)]
    result = pd.Series(
        subset["OFFSET_KMS"].to_numpy(dtype=float),
        index=pd.to_datetime(subset["NIGHT"].astype(str), format="%Y%m%d"),
        dtype=float,
    )
    if result.index.has_duplicates:
        raise ValueError(f"Duplicate nights for {program} half {half}")
    return result.sort_index()


def fit_independent_offsets(pairs: pd.DataFrame) -> pd.DataFrame:
    gaia = pairs.loc[pairs["GROUP_KIND"].astype(str) == "GAIA_SOURCE_ID"].copy()
    half_ids = stable_hash_mod(gaia["GROUP_ID"], 2)
    records: list[dict[str, object]] = []
    for half, half_value in (("A", 0), ("B", 1)):
        for program in PROGRAMS:
            mask = (
                (half_ids == half_value)
                & gaia["PROGRAM_1"].astype(str).eq(program)
                & gaia["PROGRAM_2"].astype(str).eq(program)
            )
            work = gaia.loc[
                mask,
                ["GROUP_ID", "DELTA_VRAD", "PAIR_ERROR", "PAIR_ERROR_FORMAL", "NIGHT_1", "NIGHT_2"],
            ].copy()
            work["LABEL_1"] = program + ":" + work["NIGHT_1"].astype("int64").astype(str)
            work["LABEL_2"] = program + ":" + work["NIGHT_2"].astype("int64").astype(str)
            offsets, components, stats = _fit_offsets(
                work,
                min_pairs_per_label=MIN_PAIRS_PER_LABEL,
                max_abs_z=5.0,
                clip_sigma=3.5,
                n_clip_iterations=3,
                damp=0.2,
            )
            if offsets.empty:
                continue
            largest_component = int(components.value_counts().idxmax())
            keep = components.eq(largest_component)
            selected = offsets.loc[keep].copy()
            selected -= float(selected.median())
            for label, offset in selected.items():
                records.append(
                    {
                        "HALF": half,
                        "PROGRAM": program,
                        "NIGHT": int(str(label).split(":", 1)[1]),
                        "OFFSET_KMS": float(offset),
                        "COMPONENT": largest_component,
                        "N_LABELS_FIT": stats["N_LABELS"],
                        "N_TRAIN_PAIRS": stats["N_TRAIN_PAIRS"],
                        "N_CONNECTED_COMPONENTS": stats["N_CONNECTED_COMPONENTS"],
                    }
                )
    result = pd.DataFrame.from_records(records).sort_values(["PROGRAM", "HALF", "NIGHT"])
    result.to_csv(OFFSETS_OUTPUT, index=False, lineterminator="\n")
    return result


def _common_calendar(series: list[pd.Series]) -> pd.DatetimeIndex:
    starts = [item.index.min() for item in series if not item.empty]
    ends = [item.index.max() for item in series if not item.empty]
    return pd.date_range(min(starts), max(ends), freq="D")


def _combined_statistic(
    p_a: np.ndarray,
    p_b: np.ndarray,
    q_a: np.ndarray,
    q_b: np.ndarray,
) -> dict[str, float | int]:
    first = _zero_lag_excess_arrays(
        p_a,
        q_b,
        max_lag_days=MAX_LAG_DAYS,
        min_pairs=MIN_SHARED_NIGHTS,
        method="pearson",
    )
    second = _zero_lag_excess_arrays(
        p_b,
        q_a,
        max_lag_days=MAX_LAG_DAYS,
        min_pairs=MIN_SHARED_NIGHTS,
        method="pearson",
    )
    combined = fisher_z_symmetric(
        [first["zero_lag_r"], second["zero_lag_r"]],
        [first["zero_lag_n"], second["zero_lag_n"]],
    )
    weights = np.maximum(
        np.asarray([first["zero_lag_n"], second["zero_lag_n"]], dtype=float) - 3.0,
        1.0,
    )
    excesses = np.asarray([first["primary_excess_r"], second["primary_excess_r"]], dtype=float)
    finite = np.isfinite(excesses)
    combined_excess = float(np.average(excesses[finite], weights=weights[finite])) if finite.any() else np.nan
    return {
        "R_P_A_Q_B": float(first["zero_lag_r"]),
        "N_P_A_Q_B": int(first["zero_lag_n"]),
        "EXCESS_P_A_Q_B": float(first["primary_excess_r"]),
        "R_P_B_Q_A": float(second["zero_lag_r"]),
        "N_P_B_Q_A": int(second["zero_lag_n"]),
        "EXCESS_P_B_Q_A": float(second["primary_excess_r"]),
        "SYMMETRIC_R0": float(combined["r"]),
        "SYMMETRIC_FISHER_Z": float(combined["fisher_z"]),
        "SYMMETRIC_EXCESS_R": combined_excess,
        "MIN_SHARED_NIGHTS": int(min(first["zero_lag_n"], second["zero_lag_n"])),
    }


def _block_indices(n_days: int, rng: np.random.Generator) -> tuple[np.ndarray, int]:
    n_blocks = int(math.ceil(n_days / BLOCK_DAYS))
    order = rng.permutation(n_blocks)
    rotation = int(rng.integers(1, n_blocks))
    order = np.roll(order, rotation)
    if np.array_equal(order, np.arange(n_blocks)):
        order = np.roll(order, 1)
    padded = np.arange(n_blocks * BLOCK_DAYS, dtype=np.int64).reshape(n_blocks, BLOCK_DAYS)
    indices = padded[order].reshape(-1)
    return indices, rotation


def _null_and_bootstrap(
    program_p: str,
    program_q: str,
    p_a: pd.Series,
    p_b: pd.Series,
    q_a: pd.Series,
    q_b: pd.Series,
) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
    calendar = _common_calendar([p_a, p_b, q_a, q_b])
    arrays = [item.reindex(calendar).to_numpy(dtype=float) for item in (p_a, p_b, q_a, q_b)]
    p_a_values, p_b_values, q_a_values, q_b_values = arrays
    observed = _combined_statistic(p_a_values, p_b_values, q_a_values, q_b_values)

    n_blocks = int(math.ceil(len(calendar) / BLOCK_DAYS))
    padded_length = n_blocks * BLOCK_DAYS
    padded: list[np.ndarray] = []
    for values in arrays:
        target = np.full(padded_length, np.nan, dtype=float)
        target[: len(values)] = values
        padded.append(target)
    p_a_pad, p_b_pad, q_a_pad, q_b_pad = padded

    rng = np.random.default_rng(stable_seed(f"E2:null:{program_p}:{program_q}:{SEED}"))
    null_records: list[dict[str, object]] = []
    for draw in range(N_NULL_DRAWS):
        indices, rotation = _block_indices(padded_length, rng)
        statistic = _combined_statistic(
            p_a_pad,
            p_b_pad,
            q_a_pad[indices],
            q_b_pad[indices],
        )
        null_records.append(
            {
                "PROGRAM_P": program_p,
                "PROGRAM_Q": program_q,
                "DRAW": draw,
                "ROTATION_BLOCKS": rotation,
                "SYMMETRIC_R0": statistic["SYMMETRIC_R0"],
                "SYMMETRIC_EXCESS_R": statistic["SYMMETRIC_EXCESS_R"],
            }
        )
    null = pd.DataFrame.from_records(null_records)
    valid_null = null["SYMMETRIC_EXCESS_R"].to_numpy(dtype=float)
    valid_null = valid_null[np.isfinite(valid_null)]
    p_value = float(
        (1 + np.sum(valid_null >= float(observed["SYMMETRIC_EXCESS_R"]))) / (1 + len(valid_null))
    )

    rng = np.random.default_rng(stable_seed(f"E2:bootstrap:{program_p}:{program_q}:{SEED}"))
    n_blocks_per_sample = int(math.ceil(len(calendar) / BLOCK_DAYS))
    offsets = np.arange(BLOCK_DAYS, dtype=np.int64)
    bootstrap_records: list[dict[str, object]] = []
    for draw in range(N_BOOTSTRAPS):
        starts = rng.integers(0, len(calendar), size=n_blocks_per_sample)
        indices = ((starts[:, None] + offsets[None, :]) % len(calendar)).reshape(-1)[: len(calendar)]
        statistic = _combined_statistic(
            p_a_values[indices],
            p_b_values[indices],
            q_a_values[indices],
            q_b_values[indices],
        )
        bootstrap_records.append(
            {
                "PROGRAM_P": program_p,
                "PROGRAM_Q": program_q,
                "DRAW": draw,
                "SYMMETRIC_R0": statistic["SYMMETRIC_R0"],
                "SYMMETRIC_EXCESS_R": statistic["SYMMETRIC_EXCESS_R"],
            }
        )
    bootstrap = pd.DataFrame.from_records(bootstrap_records)
    r0 = bootstrap["SYMMETRIC_R0"].to_numpy(dtype=float)
    excess = bootstrap["SYMMETRIC_EXCESS_R"].to_numpy(dtype=float)
    summary = {
        **observed,
        "BLOCK_NULL_P": p_value,
        "N_NULL_VALID": int(len(valid_null)),
        "NULL_EXCESS_Q975": float(np.nanquantile(valid_null, 0.975)),
        "BOOTSTRAP_R0_LOW_95": float(np.nanquantile(r0, 0.025)),
        "BOOTSTRAP_R0_HIGH_95": float(np.nanquantile(r0, 0.975)),
        "BOOTSTRAP_EXCESS_LOW_95": float(np.nanquantile(excess, 0.025)),
        "BOOTSTRAP_EXCESS_HIGH_95": float(np.nanquantile(excess, 0.975)),
    }
    return summary, null, bootstrap


def _lag_rows(program_p: str, program_q: str, p_a: pd.Series, p_b: pd.Series, q_a: pd.Series, q_b: pd.Series) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for direction, left, right in (("P_A_Q_B", p_a, q_b), ("P_B_Q_A", p_b, q_a)):
        result = zero_lag_excess(left, right, max_lag_days=MAX_LAG_DAYS, min_pairs=MIN_SHARED_NIGHTS)
        rows.append(
            {
                "PROGRAM_P": program_p,
                "PROGRAM_Q": program_q,
                "DIRECTION": direction,
                "LAG_DAYS": 0,
                "R": result["zero_lag_r"],
                "N": result["zero_lag_n"],
                "IS_PRIMARY_LAG": True,
            }
        )
        for item in result["lag_table"]:
            rows.extend(
                [
                    {
                        "PROGRAM_P": program_p,
                        "PROGRAM_Q": program_q,
                        "DIRECTION": direction,
                        "LAG_DAYS": item["negative_lag_days"],
                        "R": item["negative_r"],
                        "N": item["negative_n"],
                        "IS_PRIMARY_LAG": False,
                    },
                    {
                        "PROGRAM_P": program_p,
                        "PROGRAM_Q": program_q,
                        "DIRECTION": direction,
                        "LAG_DAYS": item["positive_lag_days"],
                        "R": item["positive_r"],
                        "N": item["positive_n"],
                        "IS_PRIMARY_LAG": False,
                    },
                ]
            )
    return rows


def run() -> pd.DataFrame:
    started = perf_counter()
    pairs = pd.read_pickle(CACHE)
    offsets = fit_independent_offsets(pairs)
    del pairs

    result_records: list[dict[str, object]] = []
    null_tables: list[pd.DataFrame] = []
    bootstrap_tables: list[pd.DataFrame] = []
    lag_records: list[dict[str, object]] = []
    for program_p, program_q in PROGRAM_PAIRS:
        p_a, p_b = _series(offsets, program_p, "A"), _series(offsets, program_p, "B")
        q_a, q_b = _series(offsets, program_q, "A"), _series(offsets, program_q, "B")
        summary, null, bootstrap = _null_and_bootstrap(program_p, program_q, p_a, p_b, q_a, q_b)
        spearman_first = same_date_intersection_correlation(
            p_a,
            q_b,
            min_pairs=MIN_SHARED_NIGHTS,
            method="spearman",
        )
        spearman_second = same_date_intersection_correlation(
            p_b,
            q_a,
            min_pairs=MIN_SHARED_NIGHTS,
            method="spearman",
        )
        spearman_combined = fisher_z_symmetric(
            [spearman_first["r"], spearman_second["r"]],
            [spearman_first["n"], spearman_second["n"]],
        )
        lag_records.extend(_lag_rows(program_p, program_q, p_a, p_b, q_a, q_b))
        is_primary = (program_p, program_q) == PRIMARY_PAIR
        pass_gates = (
            is_primary
            and summary["MIN_SHARED_NIGHTS"] >= 100
            and summary["SYMMETRIC_R0"] >= 0.30
            and summary["R_P_A_Q_B"] >= 0.15
            and summary["R_P_B_Q_A"] >= 0.15
            and summary["SYMMETRIC_EXCESS_R"] >= 0.10
            and summary["BOOTSTRAP_R0_LOW_95"] > 0.10
            and summary["BLOCK_NULL_P"] <= 0.01
        )
        result_records.append(
            {
                "PROGRAM_P": program_p,
                "PROGRAM_Q": program_q,
                "IS_PRIMARY_PAIR": is_primary,
                **summary,
                "SPEARMAN_P_A_Q_B": spearman_first["r"],
                "SPEARMAN_P_B_Q_A": spearman_second["r"],
                "SYMMETRIC_SPEARMAN_R": spearman_combined["r"],
                "PASS_PRE_HOLM": pass_gates,
            }
        )
        null_tables.append(null)
        bootstrap_tables.append(bootstrap)

    result = pd.DataFrame.from_records(result_records)
    result["BLOCK_NULL_P_HOLM"] = holm_adjust(result["BLOCK_NULL_P"])
    result["PASS"] = result["PASS_PRE_HOLM"] & result["BLOCK_NULL_P_HOLM"].le(0.01)
    result.to_csv(OUTPUT, index=False, lineterminator="\n")
    pd.concat(null_tables, ignore_index=True).to_csv(NULL_OUTPUT, index=False, lineterminator="\n")
    pd.concat(bootstrap_tables, ignore_index=True).to_csv(
        BOOTSTRAP_OUTPUT, index=False, lineterminator="\n"
    )
    pd.DataFrame.from_records(lag_records).to_csv(LAGS_OUTPUT, index=False, lineterminator="\n")
    _write_json(
        META_OUTPUT,
        {
            "schema": "desi_rv_audit.cross_program_coherence.v1",
            "primary_pair": list(PRIMARY_PAIR),
            "source_sample": "GAIA_SOURCE_ID only",
            "source_halves": "global stable_hash_mod(GROUP_ID, 2)",
            "pair_graphs": "within-program only",
            "secondary_metrics": ["Spearman same-date correlation in both cross-half directions"],
            "parameters": {
                "min_pairs_per_label_per_half": MIN_PAIRS_PER_LABEL,
                "max_lag_days": MAX_LAG_DAYS,
                "block_days": BLOCK_DAYS,
                "n_null_draws": N_NULL_DRAWS,
                "n_bootstraps": N_BOOTSTRAPS,
                "seed": SEED,
            },
            "elapsed_seconds": perf_counter() - started,
            "decision": "pass" if bool(result.loc[result["IS_PRIMARY_PAIR"], "PASS"].all()) else "null",
        },
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    result = run()
    print(result.to_json(orient="records"), flush=True)


if __name__ == "__main__":
    main()
