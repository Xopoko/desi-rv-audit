from __future__ import annotations

import hashlib
import json
import os
import platform
import shlex
import subprocess
import sys
from importlib import metadata
from pathlib import Path
from typing import Iterable


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str:
    override = os.environ.get("DESI_RV_AUDIT_ANALYSIS_SHA", "").strip()
    if override:
        return override
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


def _git_dirty() -> bool | str:
    try:
        status = subprocess.check_output(
            ["git", "status", "--short"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return bool(status.strip())
    except Exception:
        return ""


def _release_tag() -> str:
    return os.environ.get("DESI_RV_AUDIT_RELEASE_TAG", "").strip()


def _package_versions() -> dict[str, str]:
    packages = {}
    for name in ("numpy", "pandas", "scipy", "astropy", "matplotlib"):
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return packages


def _command_line() -> str:
    argv = list(sys.argv)
    if argv:
        executable = Path(argv[0])
        if executable.name == "cli.py" and executable.parent.name == "desi_rv_audit":
            argv[0] = "desi-rv-audit"
    return " ".join(shlex.quote(str(part)) for part in argv)


def build_manifest(
    input_paths: Iterable[str | Path],
    correction_summary: dict[str, object],
    parameters: dict[str, object],
) -> dict[str, object]:
    files = []
    for path_like in input_paths:
        path = Path(path_like)
        files.append(
            {
                "name": path.as_posix(),
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {
        "git_commit": _git_commit(),
        "git_dirty": _git_dirty(),
        "release_tag": _release_tag(),
        "command": _command_line(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": _package_versions(),
        "input_files": files,
        "correction": {
            "doi": "10.5281/zenodo.15469272",
            **correction_summary,
        },
        "parameters": parameters,
    }


def add_output_files(
    manifest: dict[str, object],
    output_dir: str | Path,
    file_names: Iterable[str] | None = None,
) -> dict[str, object]:
    result = dict(manifest)
    root = Path(output_dir)
    records = []
    paths = (
        [root / name for name in file_names]
        if file_names is not None
        else sorted(root.iterdir())
    )
    for path in sorted(paths):
        if not path.is_file() or path.name == "run_manifest.json":
            continue
        records.append(
            {
                "name": path.name,
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    result["output_files"] = records
    return result


def write_manifest(path: str | Path, manifest: dict[str, object]) -> None:
    Path(path).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
