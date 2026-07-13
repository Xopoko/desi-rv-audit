import json
from pathlib import Path

from desi_rv_audit.release import (
    COMPACT_OUTPUT_MAP,
    ENSEMBLE_OUTPUT_NAMES,
    package_main_release,
)


def _write_complete_output_fixture(path: Path) -> None:
    path.mkdir()
    for name in COMPACT_OUTPUT_MAP:
        payload = (
            json.dumps({"git_commit": "abc123", "release_tag": "v0.3.0"})
            if name == "run_manifest.json"
            else f"fixture:{name}\n"
        )
        (path / name).write_text(payload, encoding="utf-8")
    for name in ENSEMBLE_OUTPUT_NAMES:
        (path / name).write_text(f"fixture:{name}\n", encoding="utf-8")


def test_package_main_release_is_complete_and_deterministic(tmp_path):
    output_dir = tmp_path / "outputs"
    _write_complete_output_fixture(output_dir)

    first = package_main_release(output_dir, tmp_path / "reports", tmp_path / "assets")
    second = package_main_release(output_dir, tmp_path / "reports2", tmp_path / "assets2")

    assert first == second
    assert first["analysis_git_commit"] == "abc123"
    assert len(first["compact_artifacts"]) == len(COMPACT_OUTPUT_MAP)
    assert len(first["ensemble_release_assets"]) == len(ENSEMBLE_OUTPUT_NAMES)
    assert (tmp_path / "reports" / "ensemble_release_manifest.json").exists()
