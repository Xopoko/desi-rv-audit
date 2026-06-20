import pytest
from pathlib import Path

from desi_rv_audit.downloads import (
    BACKUP_CORRECTION_MD5,
    bundle_files,
    download_main_bundle,
)


def test_bundle_files_use_cross_platform_default_outputs():
    files = bundle_files()

    assert [item.output_path.as_posix() for item in files] == [
        "data/desi_main/rvpix_exp-main-backup.fits",
        "data/desi_main/rvpix_exp-main-bright.fits",
        "data/desi_main/rvpix_exp-main-dark.fits",
        "data/desi_corrections/backup_correction.fits",
    ]
    assert files[-1].expected_md5 == BACKUP_CORRECTION_MD5


def test_download_main_bundle_delegates_all_files_to_downloader(tmp_path):
    seen = []

    def fake_downloader(item, resume):
        seen.append((item.url, item.output_path, resume, item.expected_size))

    download_main_bundle(
        main_output=tmp_path / "main",
        correction_output=tmp_path / "corrections",
        downloader=fake_downloader,
        resume=False,
    )

    assert len(seen) == 4
    assert all(path.parent.exists() for _, path, _, _ in seen)
    assert seen[0][1] == tmp_path / "main" / "rvpix_exp-main-backup.fits"
    assert seen[-1][1] == tmp_path / "corrections" / "backup_correction.fits"
    assert seen[-1][2] is False


def test_download_main_bundle_accepts_string_paths(tmp_path):
    seen = []

    def fake_downloader(item, resume):
        seen.append(item.output_path)

    download_main_bundle(
        main_output=str(tmp_path / "main"),
        correction_output=str(tmp_path / "corrections"),
        downloader=fake_downloader,
    )

    assert all(isinstance(path, Path) for path in seen)


def test_download_main_cli_is_registered():
    from desi_rv_audit.cli import _parser

    args = _parser().parse_args(
        [
            "download-main",
            "--main-output",
            "main",
            "--correction-output",
            "corrections",
            "--no-resume",
        ]
    )

    assert args.command == "download-main"
    assert args.main_output == "main"
    assert args.correction_output == "corrections"
    assert args.resume is False


def test_download_main_cli_help_mentions_command(capsys):
    from desi_rv_audit.cli import _parser

    with pytest.raises(SystemExit):
        _parser().parse_args(["--help"])

    assert "download-main" in capsys.readouterr().out
