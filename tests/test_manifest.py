import json

from desi_rv_audit import __version__
from desi_rv_audit.manifest import add_output_files, build_manifest


def test_manifest_records_release_tag_and_model_hyperparameters(tmp_path, monkeypatch):
    input_path = tmp_path / "input.csv"
    input_path.write_text("TARGETID,VRAD,VRAD_ERR\n1,10,1\n", encoding="utf-8")
    monkeypatch.setenv("DESI_RV_AUDIT_ANALYSIS_SHA", "abc123")
    monkeypatch.setenv("DESI_RV_AUDIT_RELEASE_TAG", "v0.3.0")
    monkeypatch.setattr("desi_rv_audit.manifest._git_dirty", lambda: False)

    manifest = build_manifest(
        [input_path],
        {"CORRECTION_MD5": "deadbeef"},
        {
            "program_night_max_abs_z": 5.0,
            "program_night_clip_sigma": 3.5,
            "program_night_clip_iterations": 3,
            "program_night_damp": 0.2,
            "program_night_min_delta_days": 1.0,
            "program_night_bootstraps": 50,
            "fold_hash_algorithm": "blake2b-64-v1",
        },
    )

    assert manifest["git_commit"] == "abc123"
    assert manifest["git_dirty"] is False
    assert manifest["release_tag"] == "v0.3.0"
    assert manifest["parameters"]["program_night_max_abs_z"] == 5.0
    assert manifest["parameters"]["program_night_clip_sigma"] == 3.5
    assert manifest["parameters"]["program_night_clip_iterations"] == 3
    assert manifest["parameters"]["program_night_damp"] == 0.2
    assert manifest["parameters"]["program_night_min_delta_days"] == 1.0
    assert manifest["parameters"]["program_night_bootstraps"] == 50
    assert manifest["parameters"]["fold_hash_algorithm"] == "blake2b-64-v1"
    json.dumps(manifest)


def test_manifest_records_input_names_with_posix_separators(tmp_path, monkeypatch):
    input_dir = tmp_path / "nested"
    input_dir.mkdir()
    input_path = input_dir / "input.csv"
    input_path.write_text("TARGETID,VRAD,VRAD_ERR\n1,10,1\n", encoding="utf-8")
    monkeypatch.setenv("DESI_RV_AUDIT_ANALYSIS_SHA", "abc123")

    manifest = build_manifest([input_path], {}, {})

    assert manifest["input_files"][0]["name"] == input_path.as_posix()


def test_package_version_comes_from_metadata():
    assert __version__ == "0.3.0"


def test_manifest_records_output_hashes(tmp_path):
    (tmp_path / "result.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "run_manifest.json").write_text("{}", encoding="utf-8")

    result = add_output_files({"git_commit": "abc"}, tmp_path)

    assert result["output_files"] == [
        {
            "name": "result.csv",
            "size": 4,
            "sha256": "daff832f802000e645771a60983c76c963f6ee602a6230e45237bd360e91cc1a",
        }
    ]


def test_manifest_explicit_output_allowlist_excludes_stale_files(tmp_path):
    (tmp_path / "current.csv").write_text("x\n1\n", encoding="utf-8")
    (tmp_path / "stale.csv").write_text("old\n", encoding="utf-8")

    result = add_output_files(
        {"git_commit": "abc"},
        tmp_path,
        file_names=["current.csv"],
    )

    assert [record["name"] for record in result["output_files"]] == ["current.csv"]
