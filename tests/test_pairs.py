import numpy as np
import pandas as pd

from desi_rv_audit.pairs import build_pair_table


def test_program_delta_has_canonical_orientation():
    frame = pd.DataFrame(
        {
            "TARGETID": [1, 1],
            "VRAD": [10.0, 13.0],
            "VRAD_ERR": [1.0, 1.0],
            "PROGRAM": ["BRIGHT", "BACKUP"],
            "MJD": [1.0, 2.0],
        }
    )
    pairs = build_pair_table(frame, pd.Series([True, True]))
    row = pairs.iloc[0]
    assert row["PROGRAM_PAIR"] == "BACKUP / BRIGHT"
    assert np.isclose(row["PROGRAM_DELTA_VRAD"], 3.0)
    assert np.isclose(row["PROGRAM_PAIR_Z"], 3.0 / np.sqrt(2.0))


def test_pair_table_preserves_large_source_ids():
    source_id = 9_007_199_254_740_993
    frame = pd.DataFrame(
        {
            "GROUP_ID": [source_id, source_id],
            "TARGETID": [1, 1],
            "SOURCE_ID": pd.Series([source_id, source_id], dtype="Int64"),
            "VRAD": [10.0, 11.0],
            "VRAD_ERR": [1.0, 1.0],
            "MJD": [1.0, 2.0],
        }
    )
    pairs = build_pair_table(frame, pd.Series([True, True]))
    assert int(pairs.loc[0, "SOURCE_ID_1"]) == source_id
    assert int(pairs.loc[0, "SOURCE_ID_2"]) == source_id
