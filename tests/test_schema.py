import pandas as pd

from desi_rv_audit.schema import add_group_columns, coerce_types


def test_success_parser_accepts_float_string_one():
    frame = pd.DataFrame({"SUCCESS": ["1.0", "0.0", 1.0, 0.0]})
    result = coerce_types(frame)
    assert result["SUCCESS"].tolist() == [True, False, True, False]


def test_group_columns_preserve_large_gaia_source_id():
    source_id = 9_007_199_254_740_993
    frame = pd.DataFrame({"TARGETID": [123], "SOURCE_ID": [source_id]})
    result = add_group_columns(coerce_types(frame))
    assert int(result.loc[0, "SOURCE_ID"]) == source_id
    assert int(result.loc[0, "GROUP_ID"]) == source_id
