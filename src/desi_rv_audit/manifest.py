from __future__ import annotations

import hashlib
import json
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
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return ""


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
                "name": str(path),
                "size": path.stat().st_size,
                "sha256": _sha256(path),
            }
        )
    return {
        "git_commit": _git_commit(),
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


def write_manifest(path: str | Path, manifest: dict[str, object]) -> None:
    Path(path).write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
