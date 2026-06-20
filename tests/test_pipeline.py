from pathlib import Path

import pandas as pd

from desi_rv_audit.pipeline import run_audit, save_outputs


def test_synthetic_demo_contains_expected_kinds():
    root = Path(__file__).resolve().parents[1]
    frame = pd.read_csv(root / "data" / "synthetic_epochs.csv")
    outputs = run_audit(frame)
    joined = outputs.source_summary.merge(
        frame[["TARGETID", "TRUE_KIND"]].drop_duplicates(),
        left_on="targetid",
        right_on="TARGETID",
    )
    variable = joined[joined["TRUE_KIND"] == "variable"]
    stable = joined[joined["TRUE_KIND"] == "stable"]
    assert (variable["classification"] == "candidate_variable").mean() >= 0.8
    assert (stable["classification"] == "candidate_variable").mean() <= 0.05
    assert not outputs.pairs.empty
    assert not outputs.epoch_quality_by_program.empty
    assert "N_EPOCHS_GOOD" in outputs.epoch_quality_by_program.columns


def test_lite_output_skips_heavy_pair_and_source_tables(tmp_path):
    root = Path(__file__).resolve().parents[1]
    frame = pd.read_csv(root / "data" / "synthetic_epochs.csv")
    outputs = run_audit(frame)

    save_outputs(outputs, tmp_path, write_heavy_outputs=False)

    assert not (tmp_path / "source_summary.csv").exists()
    assert not (tmp_path / "pairs.csv").exists()
    assert (tmp_path / "candidate_sources.csv").exists()
    assert (tmp_path / "source_classification_counts.csv").exists()
    assert (tmp_path / "calibration_overall.csv").exists()


def test_load_and_run_writes_stage_timings(tmp_path):
    from desi_rv_audit.pipeline import load_and_run

    root = Path(__file__).resolve().parents[1]
    timings_path = tmp_path / "timings.csv"

    load_and_run(
        [root / "data" / "synthetic_epochs.csv"],
        tmp_path / "outputs",
        timings_output_path=timings_path,
    )

    timings = pd.read_csv(timings_path)
    assert {"stage", "elapsed_seconds"}.issubset(timings.columns)
    assert "load_inputs" in set(timings["stage"])
    assert "save_outputs" in set(timings["stage"])
    assert (timings["elapsed_seconds"] >= 0).all()
