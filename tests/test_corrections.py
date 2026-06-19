import pandas as pd
import pytest

from desi_rv_audit.corrections import apply_velocity_calibration, load_backup_correction


def test_backup_correction_only_applies_to_main_backup(tmp_path):
    correction_path = tmp_path / "correction.csv"
    pd.DataFrame({"TARGETID": [1], "VRAD_OFFSET": [5.0]}).to_csv(correction_path, index=False)
    frame = pd.DataFrame(
        {
            "TARGETID": [1, 1, 2],
            "SURVEY": ["MAIN", "MAIN", "MAIN"],
            "PROGRAM": ["BACKUP", "BRIGHT", "BACKUP"],
            "VRAD": [100.0, 100.0, 100.0],
            "VRAD_ERR": [1.0, 1.0, 1.0],
        }
    )

    calibrated = apply_velocity_calibration(frame, correction_path)

    assert calibrated["VRAD_ADOPTED"].tolist() == [95.0, 100.0, 100.0]
    summary = calibrated.attrs["backup_correction_summary"]
    assert summary["N_BACKUP_EPOCHS"] == 2
    assert summary["N_BACKUP_EPOCHS_MATCHED"] == 1
    assert summary["N_BACKUP_EPOCHS_UNMATCHED"] == 1
    assert summary["N_NON_BACKUP_TARGETID_MATCHES"] == 1


def test_backup_correction_rejects_conflicting_targetids(tmp_path):
    correction_path = tmp_path / "correction.csv"
    pd.DataFrame({"TARGETID": [1, 1], "VRAD_OFFSET": [5.0, 6.0]}).to_csv(
        correction_path,
        index=False,
    )

    with pytest.raises(ValueError, match="conflicting offsets"):
        load_backup_correction(correction_path)


def test_backup_correction_md5_mismatch_fails(tmp_path):
    correction_path = tmp_path / "correction.csv"
    pd.DataFrame({"TARGETID": [1], "VRAD_OFFSET": [5.0]}).to_csv(correction_path, index=False)
    frame = pd.DataFrame(
        {
            "TARGETID": [1],
            "SURVEY": ["MAIN"],
            "PROGRAM": ["BACKUP"],
            "VRAD": [100.0],
            "VRAD_ERR": [1.0],
        }
    )

    with pytest.raises(ValueError, match="MD5 mismatch"):
        apply_velocity_calibration(
            frame,
            correction_path,
            expected_backup_correction_md5="00000000000000000000000000000000",
        )
