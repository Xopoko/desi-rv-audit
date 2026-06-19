import numpy as np
import pandas as pd

from desi_rv_audit.program_night import _hash_mod, _prepare_pairs, run_program_night_experiment


def test_program_night_reduces_source_grouped_holdout_scatter():
    nights = [f"2021010{idx}" for idx in range(1, 7)]
    offsets = {night: 0.45 * (idx - 2.5) for idx, night in enumerate(nights)}
    rows = []
    for group_id in range(360):
        first = nights[group_id % len(nights)]
        second = nights[(group_id * 2 + 1) % len(nights)]
        if first == second:
            second = nights[(group_id + 1) % len(nights)]
        noise = 0.03 * ((group_id % 5) - 2)
        rows.append(
            {
                "GROUP_ID": group_id,
                "DELTA_VRAD": offsets[first] - offsets[second] + noise,
                "PAIR_ERROR": 0.8,
                "PAIR_ERROR_FORMAL": 0.2,
                "PROGRAM_1": "BACKUP",
                "PROGRAM_2": "BACKUP",
                "NIGHT_1": first,
                "NIGHT_2": second,
                "PROGRAM_PAIR": "BACKUP / BACKUP",
                "DELTA_DAYS": 2.0,
                "EXPOSURE_KEY_1": f"MAIN|BACKUP|{first}",
                "EXPOSURE_KEY_2": f"MAIN|BACKUP|{second}",
            }
        )
    pairs = pd.DataFrame(rows)

    result = run_program_night_experiment(
        pairs,
        n_folds=2,
        min_pairs_per_label=10,
        damp=0.01,
        run_permutation=False,
    )

    assert not result.summary.empty
    assert not result.by_program.empty
    assert not result.offsets.empty
    assert "N_CONNECTED_COMPONENTS" in result.summary.columns
    assert result.summary["AFTER_RAW_WIDTH_KMS"].notna().all()
    assert result.summary["AFTER_RAW_WIDTH_KMS"].mean() < result.summary[
        "BEFORE_RAW_WIDTH_KMS"
    ].mean()


def test_exposure_shuffle_assigns_one_night_per_exposure():
    pairs = pd.DataFrame(
        [
            {
                "GROUP_ID": idx,
                "DELTA_VRAD": 0.1 * idx,
                "PAIR_ERROR": 1.0,
                "PAIR_ERROR_FORMAL": 1.0,
                "PROGRAM_1": "BACKUP",
                "PROGRAM_2": "BACKUP",
                "NIGHT_1": "20210101",
                "NIGHT_2": "20210102",
                "PROGRAM_PAIR": "BACKUP / BACKUP",
                "DELTA_DAYS": 2.0,
                "EXPOSURE_KEY_1": "MAIN|BACKUP|100",
                "EXPOSURE_KEY_2": f"MAIN|BACKUP|20{idx}",
            }
            for idx in range(5)
        ]
    )
    shuffled = _prepare_pairs(pairs, shuffled=True, permutation_index=1)
    assigned = shuffled.loc[shuffled["EXPOSURE_KEY_1"] == "MAIN|BACKUP|100", "LABEL_1"]
    assert assigned.nunique() == 1


def test_source_group_fold_assignment_is_disjoint():
    group_ids = pd.Series([101, 101, 101, 202, 202, 303, 303, 303, 303])
    fold_ids = _hash_mod(group_ids, 5)

    for group_id in group_ids.unique():
        group_folds = np.unique(fold_ids[group_ids == group_id])
        assert len(group_folds) == 1
