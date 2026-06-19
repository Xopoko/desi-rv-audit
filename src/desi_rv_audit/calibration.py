from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import robust_scale


def summarize_pair_residuals(
    pairs: pd.DataFrame,
    group_by: str | None = None,
    z_column: str = "PAIR_Z",
) -> pd.DataFrame:
    if z_column not in pairs.columns and not pairs.empty:
        raise ValueError(f"Pair table does not contain {z_column}")

    label = group_by or "GROUP"
    empty_columns = [
        label,
        "N_PAIRS",
        "MEDIAN_Z",
        "ROBUST_WIDTH_Z",
        "MAD_WIDTH_Z",
        "Q16_Z",
        "Q84_Z",
        "TAIL_GT_3",
        "TAIL_GT_5",
        "Z_COLUMN",
    ]
    if pairs.empty:
        return pd.DataFrame(columns=empty_columns)

    if group_by is None:
        groups = [("ALL", pairs)]
    else:
        if group_by not in pairs.columns:
            raise ValueError(f"Pair table does not contain {group_by}")
        groups = pairs.groupby(group_by, dropna=False, sort=True, observed=True)

    records = []
    for key, group in groups:
        z = pd.to_numeric(group[z_column], errors="coerce").to_numpy(dtype=float)
        z = z[np.isfinite(z)]
        if z.size == 0:
            continue
        q16, q84 = np.quantile(z, [0.16, 0.84])
        records.append(
            {
                label: key,
                "N_PAIRS": int(z.size),
                "MEDIAN_Z": float(np.median(z)),
                "ROBUST_WIDTH_Z": float((q84 - q16) / 2.0),
                "MAD_WIDTH_Z": robust_scale(z),
                "Q16_Z": float(q16),
                "Q84_Z": float(q84),
                "TAIL_GT_3": float(np.mean(np.abs(z) > 3.0)),
                "TAIL_GT_5": float(np.mean(np.abs(z) > 5.0)),
                "Z_COLUMN": z_column,
            }
        )
    return pd.DataFrame.from_records(records, columns=empty_columns)


def add_quantile_bin(
    pairs: pd.DataFrame,
    column: str,
    bins: int = 8,
    output_column: str | None = None,
) -> pd.DataFrame:
    if column not in pairs.columns:
        raise ValueError(f"Pair table does not contain {column}")
    result = pairs.copy()
    output_column = output_column or f"{column}_BIN"
    numeric = pd.to_numeric(result[column], errors="coerce")
    try:
        result[output_column] = pd.qcut(numeric, q=bins, duplicates="drop")
    except ValueError:
        result[output_column] = pd.Series("all", index=result.index, dtype="object")
    return result
