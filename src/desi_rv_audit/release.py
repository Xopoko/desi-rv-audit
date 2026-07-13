from __future__ import annotations

import gzip
import hashlib
import json
import shutil
from pathlib import Path


COMPACT_OUTPUT_MAP = {
    "program_night_summary.csv": "summary.csv",
    "program_night_by_program.csv": "by_program.csv",
    "program_night_reproducibility.csv": "reproducibility.csv",
    "program_night_permutation_summary.csv": "permutation_summary.csv",
    "correction_summary.csv": "correction_summary.csv",
    "diagnostic_offsets_program_night.csv": "diagnostic_offsets_program_night.csv",
    "program_night_source_fold_widths.png": "source_fold_widths.png",
    "run_manifest.json": "run_manifest.json",
    "stage_timings.csv": "stage_timings.csv",
}

ENSEMBLE_OUTPUT_NAMES = (
    "program_night_permutation_offsets.csv",
    "program_night_permutation_exposure_map.csv",
    "program_night_bootstrap_offsets.csv",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _deterministic_gzip(source: Path, destination: Path) -> None:
    with source.open("rb") as input_handle, destination.open("wb") as output_handle:
        with gzip.GzipFile(
            filename="",
            mode="wb",
            fileobj=output_handle,
            compresslevel=6,
            mtime=0,
        ) as compressed:
            shutil.copyfileobj(input_handle, compressed, length=1024 * 1024)


def package_main_release(
    output_dir: str | Path,
    report_artifact_dir: str | Path,
    release_asset_dir: str | Path,
) -> dict[str, object]:
    output_dir = Path(output_dir)
    report_artifact_dir = Path(report_artifact_dir)
    release_asset_dir = Path(release_asset_dir)
    report_artifact_dir.mkdir(parents=True, exist_ok=True)
    release_asset_dir.mkdir(parents=True, exist_ok=True)

    missing = [
        name
        for name in [*COMPACT_OUTPUT_MAP, *ENSEMBLE_OUTPUT_NAMES]
        if not (output_dir / name).is_file()
    ]
    if missing:
        raise FileNotFoundError(
            "Cannot package an incomplete MAIN run; missing: " + ", ".join(missing)
        )

    compact_records = []
    for source_name, destination_name in COMPACT_OUTPUT_MAP.items():
        source = output_dir / source_name
        destination = report_artifact_dir / destination_name
        shutil.copy2(source, destination)
        compact_records.append(
            {
                "name": destination.name,
                "size": destination.stat().st_size,
                "sha256": _sha256(destination),
            }
        )

    ensemble_records = []
    for name in ENSEMBLE_OUTPUT_NAMES:
        source = output_dir / name
        destination = release_asset_dir / f"{name}.gz"
        _deterministic_gzip(source, destination)
        ensemble_records.append(
            {
                "name": name,
                "size": source.stat().st_size,
                "sha256": _sha256(source),
                "gzip_name": destination.name,
                "gzip_size": destination.stat().st_size,
                "gzip_sha256": _sha256(destination),
            }
        )

    run_manifest = json.loads((output_dir / "run_manifest.json").read_text(encoding="utf-8"))
    result = {
        "analysis_git_commit": run_manifest.get("git_commit", ""),
        "analysis_release_tag": run_manifest.get("release_tag", ""),
        "compact_artifacts": compact_records,
        "ensemble_release_assets": ensemble_records,
    }
    (report_artifact_dir / "ensemble_release_manifest.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result
