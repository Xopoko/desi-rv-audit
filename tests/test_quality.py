import pandas as pd

from desi_rv_audit.quality import QualityRules, quality_mask


def test_quality_mask_rejects_warning_and_low_sn():
    frame = pd.DataFrame(
        {
            "TARGETID": [1, 2, 3],
            "VRAD": [10.0, 20.0, 30.0],
            "VRAD_ERR": [1.0, 1.0, 1.0],
            "SN_R": [20.0, 3.0, 20.0],
            "RVS_WARN": [0, 0, 1],
            "SUCCESS": [True, True, True],
        }
    )
    assert quality_mask(frame, QualityRules(min_sn_r=5.0)).tolist() == [True, False, False]
