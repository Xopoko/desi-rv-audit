import numpy as np
import pandas as pd

from desi_rv_audit.residuals import run_residual_zero_point_calibration


def test_zero_point_reduces_holdout_width_for_program_offset():
    rows = []
    for idx in range(400):
        sign = 1 if idx % 2 == 0 else -1
        rows.append(
            {
                "GROUP_ID": idx,
                "DELTA_VRAD": sign * 2.0 + 0.01 * ((idx % 5) - 2),
                "PAIR_ERROR": 1.0,
                "PAIR_Z": sign * 2.0 + 0.01 * ((idx % 5) - 2),
                "PROGRAM_1": "A" if sign == 1 else "B",
                "PROGRAM_2": "B" if sign == 1 else "A",
                "PROGRAM_PAIR": "A / B",
                "DELTA_DAYS": 2.0,
            }
        )
    pairs = pd.DataFrame(rows)

    summary, offsets, by_program = run_residual_zero_point_calibration(
        pairs,
        dimensions=("PROGRAM",),
        min_pairs_per_label=10,
        damp=0.01,
    )

    assert "PROGRAM" in offsets
    row = summary.iloc[0]
    assert np.isfinite(row["AFTER_ROBUST_WIDTH_Z"])
    assert row["AFTER_ROBUST_WIDTH_Z"] <= row["BEFORE_ROBUST_WIDTH_Z"]
    assert not by_program.empty
