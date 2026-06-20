from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError
from urllib.request import Request, urlopen


DESI_BASE_URL = "https://data.desi.lbl.gov/public/dr1/vac/dr1/mws/iron/v1.0/rv_output/240521"
ZENODO_CORRECTION_URL = "https://zenodo.org/records/15469272/files/backup_correction.fits?download=1"
BACKUP_CORRECTION_MD5 = "f48a4b21b541e94d61f4372f4c555f12"

MAIN_FILE_SIZES = {
    "rvpix_exp-main-backup.fits": 3_400_439_040,
    "rvpix_exp-main-bright.fits": 5_645_370_240,
    "rvpix_exp-main-dark.fits": 2_873_151_360,
}
BACKUP_CORRECTION_SIZE = 19_497_600


@dataclass(frozen=True)
class DownloadItem:
    label: str
    url: str
    output_path: Path
    expected_size: int | None = None
    expected_md5: str | None = None


Downloader = Callable[[DownloadItem, bool], None]


def bundle_files(
    main_output: str | Path = "data/desi_main",
    correction_output: str | Path = "data/desi_corrections",
) -> list[DownloadItem]:
    main_dir = Path(main_output)
    correction_dir = Path(correction_output)
    files = [
        DownloadItem(
            label=name,
            url=f"{DESI_BASE_URL}/{name}",
            output_path=main_dir / name,
            expected_size=size,
        )
        for name, size in MAIN_FILE_SIZES.items()
    ]
    files.append(
        DownloadItem(
            label="backup_correction.fits",
            url=ZENODO_CORRECTION_URL,
            output_path=correction_dir / "backup_correction.fits",
            expected_size=BACKUP_CORRECTION_SIZE,
            expected_md5=BACKUP_CORRECTION_MD5,
        )
    )
    return files


def _file_md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_download(item: DownloadItem) -> None:
    if item.expected_size is not None:
        actual_size = item.output_path.stat().st_size
        if actual_size != item.expected_size:
            raise RuntimeError(
                f"{item.output_path.as_posix()} has size {actual_size}; "
                f"expected {item.expected_size}"
            )
    if item.expected_md5 is not None:
        actual_md5 = _file_md5(item.output_path)
        if actual_md5.lower() != item.expected_md5.lower():
            raise RuntimeError(
                f"{item.output_path.as_posix()} has MD5 {actual_md5}; "
                f"expected {item.expected_md5}"
            )


def download_file(item: DownloadItem, resume: bool = True) -> None:
    item.output_path.parent.mkdir(parents=True, exist_ok=True)
    existing_size = item.output_path.stat().st_size if item.output_path.exists() else 0
    if item.expected_size is not None and existing_size == item.expected_size:
        _validate_download(item)
        print(f"Already downloaded {item.output_path.as_posix()}")
        return

    headers = {}
    mode = "wb"
    if resume and existing_size > 0:
        headers["Range"] = f"bytes={existing_size}-"
        mode = "ab"

    request = Request(item.url, headers=headers)
    try:
        response = urlopen(request)
    except HTTPError as exc:
        if (
            exc.code == 416
            and item.expected_size is not None
            and item.output_path.exists()
            and item.output_path.stat().st_size == item.expected_size
        ):
            _validate_download(item)
            return
        raise

    with response:
        status = getattr(response, "status", response.getcode())
        if mode == "ab" and status != 206:
            mode = "wb"
        print(f"Downloading {item.label} -> {item.output_path.as_posix()}")
        with item.output_path.open(mode) as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)

    _validate_download(item)


def download_main_bundle(
    main_output: str | Path = "data/desi_main",
    correction_output: str | Path = "data/desi_corrections",
    downloader: Downloader = download_file,
    resume: bool = True,
) -> list[DownloadItem]:
    files = bundle_files(main_output=main_output, correction_output=correction_output)
    for item in files:
        item.output_path.parent.mkdir(parents=True, exist_ok=True)
        downloader(item, resume)
    return files
