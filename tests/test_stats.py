import numpy as np
import pandas as pd

from desi_rv_audit.stats import max_pair_sigma, summarize_source, weighted_mean


def test_weighted_mean():
    assert np.isclose(weighted_mean(np.array([0.0, 2.0]), np.array([1.0, 1.0])), 1.0)


def test_max_pair_sigma():
    value = max_pair_sigma(np.array([0.0, 10.0]), np.array([1.0, 1.0]))
    assert np.isclose(value, 10.0 / np.sqrt(2.0))


def test_variable_source_screening():
    frame = pd.DataFrame(
        {
            "TARGETID": [42, 42, 42],
            "VRAD": [0.0, 20.0, -15.0],
            "VRAD_ERR": [0.5, 0.5, 0.5],
            "MJD": [60000.0, 60010.0, 60020.0],
        }
    )
    summary = summarize_source(frame, frame)
    assert summary.classification == "candidate_variable"
    assert summary.max_pair_sigma > 5
