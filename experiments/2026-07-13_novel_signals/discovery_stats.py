"""Reusable calendar-time statistics for the E2 discovery experiment.

The module intentionally performs no repository I/O and does not run an
experiment on import.  Inputs are one-value-per-calendar-date ``pandas.Series``
objects (or mappings) and outputs are small, serializable dictionaries.

Primary E2 statistic
--------------------

``r(lag=0) - median(r(lag))`` for every finite Pearson correlation at the
calendar lags ``-max_lag, ..., -1, +1, ..., +max_lag``.  The default
``max_lag`` is 30 days.  Fisher-z symmetric combinations of ``+d`` and ``-d``
are reported only as secondary diagnostics.

The null randomizes contiguous 14-day blocks of one series and applies a
random circular rotation to the block order.  The bootstrap jointly resamples
14-day moving blocks from both series, retaining their same-date alignment.
Both procedures are deterministic for a fixed seed.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any, Literal

import numpy as np
import pandas as pd


DEFAULT_MAX_LAG_DAYS = 30
DEFAULT_BLOCK_DAYS = 14
DEFAULT_NULL_DRAWS = 999
DEFAULT_SEED = 20260713
_FISHER_CLIP = 1.0 - 1e-12

CorrelationMethod = Literal["pearson", "spearman"]
SeriesInput = pd.Series | Mapping[Any, float]


def _validate_positive_integer(value: int, name: str) -> int:
    value = int(value)
    if value < 1:
        raise ValueError(f"{name} must be at least 1")
    return value


def _as_daily_series(
    values: SeriesInput,
    *,
    duplicate: Literal["raise", "mean", "median"] = "raise",
) -> pd.Series:
    """Return a numeric, sorted Series indexed by normalized UTC-free dates."""
    if isinstance(values, pd.Series):
        series = values.copy()
    elif isinstance(values, Mapping):
        series = pd.Series(dict(values), dtype=float)
    else:
        raise TypeError("time series inputs must be pandas.Series or mappings")

    try:
        index = pd.DatetimeIndex(pd.to_datetime(series.index, utc=True)).tz_convert(None)
    except (TypeError, ValueError) as exc:
        raise ValueError("time-series index must contain parseable calendar dates") from exc
    series.index = index.normalize()
    series = pd.to_numeric(series, errors="coerce").astype(float)

    if series.index.has_duplicates:
        if duplicate == "raise":
            duplicated = series.index[series.index.duplicated()].unique()
            examples = ", ".join(str(value.date()) for value in duplicated[:3])
            raise ValueError(
                "time-series index must be unique by calendar date; "
                f"duplicates include {examples}"
            )
        if duplicate == "mean":
            series = series.groupby(level=0, sort=True).mean()
        elif duplicate == "median":
            series = series.groupby(level=0, sort=True).median()
        else:
            raise ValueError("duplicate must be 'raise', 'mean', or 'median'")
    return series.sort_index()


def _fisher_z(r: float) -> float:
    if not np.isfinite(r):
        return float("nan")
    return float(np.arctanh(np.clip(float(r), -_FISHER_CLIP, _FISHER_CLIP)))


def _correlation_arrays(
    left: np.ndarray,
    right: np.ndarray,
    *,
    min_pairs: int,
    method: CorrelationMethod,
) -> dict[str, float | int]:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    if left.shape != right.shape:
        raise ValueError("correlation arrays must have identical shapes")
    valid = np.isfinite(left) & np.isfinite(right)
    x = left[valid]
    y = right[valid]
    n = int(x.size)
    if n < min_pairs or np.ptp(x) == 0.0 or np.ptp(y) == 0.0:
        return {"r": float("nan"), "fisher_z": float("nan"), "n": n}
    if method == "spearman":
        x = pd.Series(x).rank(method="average").to_numpy(dtype=float)
        y = pd.Series(y).rank(method="average").to_numpy(dtype=float)
    elif method != "pearson":
        raise ValueError("method must be 'pearson' or 'spearman'")
    r = float(np.corrcoef(x, y)[0, 1])
    return {"r": r, "fisher_z": _fisher_z(r), "n": n}


def fisher_z_symmetric(
    correlations: Sequence[float],
    sample_sizes: Sequence[int] | None = None,
) -> dict[str, float | int]:
    """Combine directional correlations symmetrically on the Fisher-z scale.

    When sample sizes are supplied, the conventional ``max(n - 3, 0)`` Fisher
    information weights are used.  Otherwise every finite correlation receives
    equal weight.  This function is a secondary E2 diagnostic; it does not
    define the primary raw-median zero-lag excess.
    """
    correlations_array = np.asarray(list(correlations), dtype=float)
    if sample_sizes is None:
        sizes_array = np.full(correlations_array.shape, np.nan, dtype=float)
        weights = np.ones(correlations_array.shape, dtype=float)
    else:
        sizes_array = np.asarray(list(sample_sizes), dtype=float)
        if sizes_array.shape != correlations_array.shape:
            raise ValueError("sample_sizes must have the same length as correlations")
        weights = np.maximum(sizes_array - 3.0, 0.0)

    valid = (
        np.isfinite(correlations_array)
        & (np.abs(correlations_array) <= 1.0 + 1e-12)
        & np.isfinite(weights)
        & (weights > 0)
    )
    if not np.any(valid):
        return {
            "r": float("nan"),
            "fisher_z": float("nan"),
            "weight": 0.0,
            "n_components": 0,
            "sample_size_sum": 0,
        }

    z = np.arctanh(np.clip(correlations_array[valid], -_FISHER_CLIP, _FISHER_CLIP))
    combined_z = float(np.average(z, weights=weights[valid]))
    finite_sizes = sizes_array[valid & np.isfinite(sizes_array)]
    return {
        "r": float(np.tanh(combined_z)),
        "fisher_z": combined_z,
        "weight": float(weights[valid].sum()),
        "n_components": int(valid.sum()),
        "sample_size_sum": int(finite_sizes.sum()) if finite_sizes.size else 0,
    }


def same_date_intersection_correlation(
    left: SeriesInput,
    right: SeriesInput,
    *,
    min_pairs: int = 4,
    method: CorrelationMethod = "pearson",
    duplicate: Literal["raise", "mean", "median"] = "raise",
) -> dict[str, Any]:
    """Correlate values only on the exact calendar-date intersection."""
    min_pairs = _validate_positive_integer(min_pairs, "min_pairs")
    left_series = _as_daily_series(left, duplicate=duplicate)
    right_series = _as_daily_series(right, duplicate=duplicate)
    joined = pd.concat(
        [left_series.rename("left"), right_series.rename("right")],
        axis=1,
        join="inner",
    )
    result = _correlation_arrays(
        joined["left"].to_numpy(dtype=float),
        joined["right"].to_numpy(dtype=float),
        min_pairs=min_pairs,
        method=method,
    )
    finite = np.isfinite(joined["left"]) & np.isfinite(joined["right"])
    supported_dates = joined.index[finite]
    return {
        **result,
        "method": method,
        "date_min": (
            supported_dates.min().strftime("%Y-%m-%d") if len(supported_dates) else None
        ),
        "date_max": (
            supported_dates.max().strftime("%Y-%m-%d") if len(supported_dates) else None
        ),
    }


def _dense_daily_pair(
    left: pd.Series,
    right: pd.Series,
) -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray]:
    if left.empty and right.empty:
        return pd.DatetimeIndex([]), np.asarray([], dtype=float), np.asarray([], dtype=float)
    starts = [series.index.min() for series in (left, right) if not series.empty]
    ends = [series.index.max() for series in (left, right) if not series.empty]
    calendar = pd.date_range(min(starts), max(ends), freq="D")
    return (
        calendar,
        left.reindex(calendar).to_numpy(dtype=float),
        right.reindex(calendar).to_numpy(dtype=float),
    )


def _lag_correlation_arrays(
    left: np.ndarray,
    right: np.ndarray,
    lag_days: int,
    *,
    min_pairs: int,
    method: CorrelationMethod,
) -> dict[str, float | int]:
    lag_days = int(lag_days)
    if abs(lag_days) >= len(left):
        return {"r": float("nan"), "fisher_z": float("nan"), "n": 0}
    if lag_days > 0:
        # left(t) versus right(t + lag)
        x = left[:-lag_days]
        y = right[lag_days:]
    elif lag_days < 0:
        distance = -lag_days
        x = left[distance:]
        y = right[:-distance]
    else:
        x = left
        y = right
    return _correlation_arrays(x, y, min_pairs=min_pairs, method=method)


def symmetric_lag_correlation(
    left: SeriesInput,
    right: SeriesInput,
    lag_days: int,
    *,
    min_pairs: int = 4,
    method: CorrelationMethod = "pearson",
) -> dict[str, Any]:
    """Combine ``+lag`` and ``-lag`` correlations on the Fisher-z scale."""
    lag_days = _validate_positive_integer(lag_days, "lag_days")
    min_pairs = _validate_positive_integer(min_pairs, "min_pairs")
    left_series = _as_daily_series(left)
    right_series = _as_daily_series(right)
    _, left_values, right_values = _dense_daily_pair(left_series, right_series)
    positive = _lag_correlation_arrays(
        left_values,
        right_values,
        lag_days,
        min_pairs=min_pairs,
        method=method,
    )
    negative = _lag_correlation_arrays(
        left_values,
        right_values,
        -lag_days,
        min_pairs=min_pairs,
        method=method,
    )
    combined = fisher_z_symmetric(
        [float(positive["r"]), float(negative["r"])],
        [int(positive["n"]), int(negative["n"])],
    )
    return {
        "absolute_lag_days": lag_days,
        "positive_r": positive["r"],
        "positive_n": positive["n"],
        "negative_r": negative["r"],
        "negative_n": negative["n"],
        "symmetric_r": combined["r"],
        "symmetric_fisher_z": combined["fisher_z"],
        "symmetric_weight": combined["weight"],
    }


def _zero_lag_excess_arrays(
    left: np.ndarray,
    right: np.ndarray,
    *,
    max_lag_days: int,
    min_pairs: int,
    method: CorrelationMethod,
) -> dict[str, Any]:
    zero = _lag_correlation_arrays(
        left,
        right,
        0,
        min_pairs=min_pairs,
        method=method,
    )
    lag_table: list[dict[str, Any]] = []
    raw_off_lag_correlations: list[float] = []
    symmetric_z_values: list[float] = []

    for lag in range(1, max_lag_days + 1):
        positive = _lag_correlation_arrays(
            left,
            right,
            lag,
            min_pairs=min_pairs,
            method=method,
        )
        negative = _lag_correlation_arrays(
            left,
            right,
            -lag,
            min_pairs=min_pairs,
            method=method,
        )
        for directional in (negative, positive):
            r = float(directional["r"])
            if np.isfinite(r):
                raw_off_lag_correlations.append(r)
        symmetric = fisher_z_symmetric(
            [float(positive["r"]), float(negative["r"])],
            [int(positive["n"]), int(negative["n"])],
        )
        symmetric_z = float(symmetric["fisher_z"])
        if np.isfinite(symmetric_z):
            symmetric_z_values.append(symmetric_z)
        lag_table.append(
            {
                "absolute_lag_days": lag,
                "negative_lag_days": -lag,
                "negative_r": negative["r"],
                "negative_n": negative["n"],
                "positive_lag_days": lag,
                "positive_r": positive["r"],
                "positive_n": positive["n"],
                "symmetric_r": symmetric["r"],
                "symmetric_fisher_z": symmetric["fisher_z"],
                "symmetric_weight": symmetric["weight"],
            }
        )

    off_lag_median_r = (
        float(np.median(raw_off_lag_correlations))
        if raw_off_lag_correlations
        else float("nan")
    )
    zero_r = float(zero["r"])
    primary_excess = (
        zero_r - off_lag_median_r
        if np.isfinite(zero_r) and np.isfinite(off_lag_median_r)
        else float("nan")
    )
    off_lag_median_symmetric_z = (
        float(np.median(symmetric_z_values)) if symmetric_z_values else float("nan")
    )
    zero_z = float(zero["fisher_z"])
    fisher_excess = (
        zero_z - off_lag_median_symmetric_z
        if np.isfinite(zero_z) and np.isfinite(off_lag_median_symmetric_z)
        else float("nan")
    )
    return {
        "method": method,
        "max_lag_days": max_lag_days,
        "zero_lag_r": zero_r,
        "zero_lag_fisher_z": zero_z,
        "zero_lag_n": int(zero["n"]),
        "off_lag_median_r": off_lag_median_r,
        "n_finite_directional_off_lags": len(raw_off_lag_correlations),
        "primary_excess_r": primary_excess,
        "off_lag_median_symmetric_fisher_z": off_lag_median_symmetric_z,
        "secondary_excess_fisher_z": fisher_excess,
        "n_finite_symmetric_lags": len(symmetric_z_values),
        "lag_table": lag_table,
    }


def zero_lag_excess(
    left: SeriesInput,
    right: SeriesInput,
    *,
    max_lag_days: int = DEFAULT_MAX_LAG_DAYS,
    min_pairs: int = 4,
    method: CorrelationMethod = "pearson",
) -> dict[str, Any]:
    """Compute the preregistered raw-median zero-lag excess.

    The primary statistic is exactly ``r(0) - median(r(+/-1..max_lag))`` over
    finite directional correlations.  Calendar-day gaps are represented by a
    dense daily grid; dates absent from either input remain missing rather than
    being treated as observations.
    """
    max_lag_days = _validate_positive_integer(max_lag_days, "max_lag_days")
    min_pairs = _validate_positive_integer(min_pairs, "min_pairs")
    left_series = _as_daily_series(left)
    right_series = _as_daily_series(right)
    _, left_values, right_values = _dense_daily_pair(left_series, right_series)
    return _zero_lag_excess_arrays(
        left_values,
        right_values,
        max_lag_days=max_lag_days,
        min_pairs=min_pairs,
        method=method,
    )


def _pad_to_blocks(
    values: np.ndarray,
    block_days: int,
) -> tuple[np.ndarray, int]:
    n_blocks = int(math.ceil(len(values) / block_days))
    padded_length = n_blocks * block_days
    padded = np.full(padded_length, np.nan, dtype=float)
    padded[: len(values)] = values
    return padded.reshape(n_blocks, block_days), n_blocks


def circular_block_shift_null(
    left: SeriesInput,
    right: SeriesInput,
    *,
    max_lag_days: int = DEFAULT_MAX_LAG_DAYS,
    min_pairs: int = 4,
    method: CorrelationMethod = "pearson",
    block_days: int = DEFAULT_BLOCK_DAYS,
    n_draws: int = DEFAULT_NULL_DRAWS,
    seed: int = DEFAULT_SEED,
    alternative: Literal["greater", "two-sided"] = "greater",
) -> dict[str, Any]:
    """Build a deterministic null from randomized contiguous calendar blocks.

    One member of the pair is divided into contiguous ``block_days`` blocks.
    For each seeded draw, whole blocks are randomly permuted and then circularly
    rotated by a non-zero block offset.  Values within every block remain in
    their original order.  At least 999 draws are always produced, even when
    the number of unique simple circular shifts would be smaller.
    """
    max_lag_days = _validate_positive_integer(max_lag_days, "max_lag_days")
    min_pairs = _validate_positive_integer(min_pairs, "min_pairs")
    block_days = _validate_positive_integer(block_days, "block_days")
    n_draws = max(DEFAULT_NULL_DRAWS, _validate_positive_integer(n_draws, "n_draws"))
    left_series = _as_daily_series(left)
    right_series = _as_daily_series(right)
    calendar, left_values, right_values = _dense_daily_pair(left_series, right_series)
    if len(calendar) < 2 * block_days:
        raise ValueError("calendar span must cover at least two complete block lengths")

    observed = _zero_lag_excess_arrays(
        left_values,
        right_values,
        max_lag_days=max_lag_days,
        min_pairs=min_pairs,
        method=method,
    )
    left_blocks, n_blocks = _pad_to_blocks(left_values, block_days)
    right_blocks, right_n_blocks = _pad_to_blocks(right_values, block_days)
    if n_blocks != right_n_blocks or n_blocks < 2:
        raise ValueError("both series must span at least two common calendar blocks")

    rng = np.random.default_rng(int(seed))
    left_padded = left_blocks.reshape(-1)
    null_table: list[dict[str, Any]] = []
    null_primary: list[float] = []
    observed_primary = float(observed["primary_excess_r"])
    attempts = 0
    invalid_attempts = 0
    max_attempts = max(10_000, 100 * n_draws)

    # Sparse observing calendars can produce a randomized alignment with too
    # few same-date intersections.  Such an alignment has no test statistic
    # and therefore is not counted as a null draw; retry deterministically until
    # the requested number of finite draws is reached.
    while len(null_primary) < n_draws and attempts < max_attempts:
        attempts += 1
        order = rng.permutation(n_blocks)
        rotation = int(rng.integers(1, n_blocks))
        order = np.roll(order, rotation)
        # Avoid the exact identity mapping, including the rare case where a
        # random permutation plus rotation cancels back to identity.
        if np.array_equal(order, np.arange(n_blocks)):
            order = np.roll(order, 1)
        randomized_right = right_blocks[order].reshape(-1)
        statistic = _zero_lag_excess_arrays(
            left_padded,
            randomized_right,
            max_lag_days=max_lag_days,
            min_pairs=min_pairs,
            method=method,
        )
        primary = float(statistic["primary_excess_r"])
        if not np.isfinite(primary):
            invalid_attempts += 1
            continue
        draw = len(null_primary)
        null_primary.append(primary)
        null_table.append(
            {
                "draw": draw,
                "attempt": attempts - 1,
                "seed": int(seed),
                "rotation_blocks": rotation,
                "primary_excess_r": primary,
                "zero_lag_r": statistic["zero_lag_r"],
                "off_lag_median_r": statistic["off_lag_median_r"],
                "secondary_excess_fisher_z": statistic["secondary_excess_fisher_z"],
            }
        )

    if len(null_primary) < n_draws:
        raise RuntimeError(
            "could not obtain the requested number of finite block-null draws; "
            f"got {len(null_primary)} after {attempts} deterministic attempts"
        )

    null_array = np.asarray(null_primary, dtype=float)
    if not np.isfinite(observed_primary) or null_array.size == 0:
        p_value = float("nan")
    elif alternative == "greater":
        p_value = float((1 + np.sum(null_array >= observed_primary)) / (1 + len(null_array)))
    elif alternative == "two-sided":
        p_value = float(
            (1 + np.sum(np.abs(null_array) >= abs(observed_primary)))
            / (1 + len(null_array))
        )
    else:
        raise ValueError("alternative must be 'greater' or 'two-sided'")

    return {
        "observed": observed,
        "primary_statistic": "r0_minus_median_directional_r_lags",
        "block_days": block_days,
        "n_blocks": n_blocks,
        "n_draws": n_draws,
        "n_valid_draws": int(null_array.size),
        "n_attempts": attempts,
        "n_invalid_attempts": invalid_attempts,
        "seed": int(seed),
        "alternative": alternative,
        "p_value": p_value,
        "null_quantiles": (
            {
                "q025": float(np.quantile(null_array, 0.025)),
                "q500": float(np.quantile(null_array, 0.5)),
                "q975": float(np.quantile(null_array, 0.975)),
            }
            if null_array.size
            else {"q025": float("nan"), "q500": float("nan"), "q975": float("nan")}
        ),
        "null_table": null_table,
    }


def _percentile_interval(
    values: np.ndarray,
    confidence: float,
) -> dict[str, float | int]:
    finite = np.asarray(values, dtype=float)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return {"low": float("nan"), "high": float("nan"), "n_valid": 0}
    alpha = (1.0 - confidence) / 2.0
    return {
        "low": float(np.quantile(finite, alpha)),
        "high": float(np.quantile(finite, 1.0 - alpha)),
        "n_valid": int(finite.size),
    }


def block_bootstrap_ci(
    left: SeriesInput,
    right: SeriesInput,
    *,
    max_lag_days: int = DEFAULT_MAX_LAG_DAYS,
    min_pairs: int = 4,
    method: CorrelationMethod = "pearson",
    block_days: int = DEFAULT_BLOCK_DAYS,
    n_resamples: int = 2000,
    confidence: float = 0.95,
    seed: int = DEFAULT_SEED,
    return_distribution: bool = False,
) -> dict[str, Any]:
    """Joint 14-day circular moving-block bootstrap percentile intervals."""
    max_lag_days = _validate_positive_integer(max_lag_days, "max_lag_days")
    min_pairs = _validate_positive_integer(min_pairs, "min_pairs")
    block_days = _validate_positive_integer(block_days, "block_days")
    n_resamples = _validate_positive_integer(n_resamples, "n_resamples")
    if not 0.0 < confidence < 1.0:
        raise ValueError("confidence must lie strictly between 0 and 1")

    left_series = _as_daily_series(left)
    right_series = _as_daily_series(right)
    calendar, left_values, right_values = _dense_daily_pair(left_series, right_series)
    n_days = len(calendar)
    if n_days < block_days:
        raise ValueError("calendar span must be at least one block long")
    observed = _zero_lag_excess_arrays(
        left_values,
        right_values,
        max_lag_days=max_lag_days,
        min_pairs=min_pairs,
        method=method,
    )

    rng = np.random.default_rng(int(seed))
    n_blocks_per_resample = int(math.ceil(n_days / block_days))
    offsets = np.arange(block_days, dtype=np.int64)
    records: list[dict[str, float | int]] = []
    for resample in range(n_resamples):
        starts = rng.integers(0, n_days, size=n_blocks_per_resample)
        indices = ((starts[:, None] + offsets[None, :]) % n_days).reshape(-1)[:n_days]
        statistic = _zero_lag_excess_arrays(
            left_values[indices],
            right_values[indices],
            max_lag_days=max_lag_days,
            min_pairs=min_pairs,
            method=method,
        )
        records.append(
            {
                "resample": resample,
                "zero_lag_r": float(statistic["zero_lag_r"]),
                "off_lag_median_r": float(statistic["off_lag_median_r"]),
                "primary_excess_r": float(statistic["primary_excess_r"]),
                "secondary_excess_fisher_z": float(
                    statistic["secondary_excess_fisher_z"]
                ),
            }
        )

    distribution = pd.DataFrame.from_records(records)
    intervals = {
        column: _percentile_interval(distribution[column].to_numpy(dtype=float), confidence)
        for column in (
            "zero_lag_r",
            "off_lag_median_r",
            "primary_excess_r",
            "secondary_excess_fisher_z",
        )
    }
    result: dict[str, Any] = {
        "observed": observed,
        "primary_statistic": "r0_minus_median_directional_r_lags",
        "block_days": block_days,
        "n_resamples": n_resamples,
        "confidence": confidence,
        "seed": int(seed),
        "intervals": intervals,
    }
    if return_distribution:
        result["distribution"] = distribution.to_dict(orient="records")
    return result


def holm_adjust(p_values: Sequence[float]) -> np.ndarray:
    """Holm step-down family-wise p-value adjustment, preserving NaNs."""
    values = np.asarray(list(p_values), dtype=float)
    adjusted = np.full(values.shape, np.nan, dtype=float)
    finite_indices = np.flatnonzero(np.isfinite(values))
    if finite_indices.size == 0:
        return adjusted
    finite_values = values[finite_indices]
    if np.any((finite_values < 0.0) | (finite_values > 1.0)):
        raise ValueError("finite p-values must lie in [0, 1]")
    order = np.argsort(finite_values, kind="mergesort")
    sorted_values = finite_values[order]
    multipliers = np.arange(len(sorted_values), 0, -1, dtype=float)
    sorted_adjusted = np.maximum.accumulate(sorted_values * multipliers)
    sorted_adjusted = np.clip(sorted_adjusted, 0.0, 1.0)
    restored = np.empty_like(sorted_adjusted)
    restored[order] = sorted_adjusted
    adjusted[finite_indices] = restored
    return adjusted


def holm_adjust_mapping(p_values: Mapping[Any, float]) -> dict[Any, float]:
    """Mapping-preserving convenience wrapper around :func:`holm_adjust`."""
    keys = list(p_values)
    adjusted = holm_adjust([p_values[key] for key in keys])
    return {key: float(value) for key, value in zip(keys, adjusted)}


def _self_test() -> None:
    # Fisher-z symmetry is invariant to component order.
    first = fisher_z_symmetric([0.2, 0.5], [30, 40])
    second = fisher_z_symmetric([0.5, 0.2], [40, 30])
    assert np.isclose(first["r"], second["r"])

    # Exact date intersection ignores unmatched dates.
    dates_a = pd.date_range("2025-01-01", periods=6, freq="D")
    dates_b = pd.date_range("2025-01-03", periods=6, freq="D")
    a = pd.Series(np.arange(6, dtype=float), index=dates_a)
    b = pd.Series(10.0 + 2.0 * np.arange(6, dtype=float), index=dates_b)
    same = same_date_intersection_correlation(a, b, min_pairs=4)
    assert same["n"] == 4
    assert np.isclose(same["r"], 1.0)

    # A shared daily signal has a pronounced same-date excess over off-lags.
    rng = np.random.default_rng(17)
    dates = pd.date_range("2025-02-01", periods=196, freq="D")
    signal = rng.normal(size=len(dates))
    left = pd.Series(signal, index=dates)
    right = pd.Series(signal + rng.normal(scale=0.08, size=len(dates)), index=dates)
    excess = zero_lag_excess(left, right, max_lag_days=30, min_pairs=10)
    assert excess["n_finite_directional_off_lags"] == 60
    assert excess["primary_excess_r"] > 0.7
    assert excess["secondary_excess_fisher_z"] > 0.5

    # The block null always supplies at least 999 reproducible draws.
    null_one = circular_block_shift_null(
        left,
        right,
        max_lag_days=5,
        min_pairs=10,
        n_draws=999,
        seed=23,
    )
    null_two = circular_block_shift_null(
        left,
        right,
        max_lag_days=5,
        min_pairs=10,
        n_draws=999,
        seed=23,
    )
    assert null_one["n_draws"] == 999
    assert null_one["n_valid_draws"] == 999
    assert np.isclose(null_one["p_value"], null_two["p_value"])
    assert np.isclose(
        null_one["null_table"][37]["primary_excess_r"],
        null_two["null_table"][37]["primary_excess_r"],
    )

    # Joint moving-block bootstrap is deterministic for a fixed seed.
    bootstrap_one = block_bootstrap_ci(
        left,
        right,
        max_lag_days=5,
        min_pairs=10,
        n_resamples=64,
        seed=29,
    )
    bootstrap_two = block_bootstrap_ci(
        left,
        right,
        max_lag_days=5,
        min_pairs=10,
        n_resamples=64,
        seed=29,
    )
    ci_one = bootstrap_one["intervals"]["primary_excess_r"]
    ci_two = bootstrap_two["intervals"]["primary_excess_r"]
    assert ci_one == ci_two
    assert ci_one["n_valid"] == 64
    assert ci_one["low"] < ci_one["high"]

    adjusted = holm_adjust([0.01, 0.04, 0.03, np.nan])
    assert np.allclose(adjusted[:3], [0.03, 0.06, 0.06])
    assert np.isnan(adjusted[3])


if __name__ == "__main__":
    _self_test()
    print("discovery_stats self-tests: ok")
