"""DESI multi-epoch radial-velocity audit utilities."""

from importlib.metadata import PackageNotFoundError, version

__all__ = ["__version__"]

try:
    __version__ = version("desi-rv-audit")
except PackageNotFoundError:  # pragma: no cover - local source tree without install metadata
    __version__ = "0.0.0+local"
