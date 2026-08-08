import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zlib


def _load_validator_module():
    repo_root = Path(__file__).resolve().parents[1]
    validator = repo_root / "explanation" / "tools" / "validate_explanation.py"
    spec = importlib.util.spec_from_file_location("explanation_validator", validator)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_builder_module():
    repo_root = Path(__file__).resolve().parents[1]
    builder = repo_root / "explanation" / "tools" / "build_notebooks.py"
    spec = importlib.util.spec_from_file_location("explanation_builder", builder)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _png_chunk(chunk_type, payload):
    crc = zlib.crc32(chunk_type + payload) & 0xFFFFFFFF
    return (
        len(payload).to_bytes(4, "big")
        + chunk_type
        + payload
        + crc.to_bytes(4, "big")
    )


def _png_payload(width, height, pixel=b"\x00\x80\xff\xff", note=b""):
    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + bytes((8, 6, 0, 0, 0))
    )
    scanlines = b"".join(b"\x00" + pixel * width for _ in range(height))
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"tEXt", b"Software\x00" + note)
        + _png_chunk(b"IDAT", zlib.compress(scanlines))
        + _png_chunk(b"IEND", b"")
    )
    return base64.b64encode(png).decode("ascii")


def test_explanation_layer_validates_from_any_working_directory(tmp_path):
    repo_root = Path(__file__).resolve().parents[1]
    validator = repo_root / "explanation" / "tools" / "validate_explanation.py"

    completed = subprocess.run(
        [sys.executable, str(validator)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    try:
        summary = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"validator did not emit JSON\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
        ) from exc

    assert completed.returncode == 0, (
        f"validator failed\nstdout:\n{completed.stdout}\nstderr:\n{completed.stderr}"
    )
    assert summary["ok"] is True
    assert summary["errors"] == []


def test_same_document_markdown_fragments_are_checked(tmp_path):
    validator = _load_validator_module()
    errors = []

    checked = validator._validate_markdown_links(
        "# Present heading\n\n[works](#present-heading) [fails](#missing-heading)\n",
        base_dir=tmp_path,
        context="example.md",
        errors=errors,
    )

    assert checked == 2
    assert errors == [
        "example.md: unresolved same-document link fragment: '#missing-heading'"
    ]


def test_notebook_output_comparison_ignores_png_metadata_but_checks_raster():
    builder = _load_builder_module()
    saved = [
        {
            "output_type": "display_data",
            "data": {
                "image/png": _png_payload(8, 4, note=b"saved metadata"),
                "text/plain": "<Figure size 800x440 with 1 Axes>",
            },
            "metadata": {},
        }
    ]
    reexecuted = [
        {
            "output_type": "display_data",
            "data": {
                "image/png": _png_payload(8, 4, note=b"runtime metadata"),
                "text/plain": "<Figure size 800x440 with 1 Axes>",
            },
            "metadata": {},
        }
    ]

    assert builder._comparable_outputs(saved, "saved") == builder._comparable_outputs(
        reexecuted, "reexecuted"
    )

    reexecuted[0]["data"]["image/png"] = _png_payload(
        8, 4, pixel=b"\xff\x80\x00\xff", note=b"runtime metadata"
    )
    assert builder._comparable_outputs(saved, "saved") != builder._comparable_outputs(
        reexecuted, "reexecuted"
    )
