import base64
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import zlib

import pytest


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


def _paeth_predictor(left, above, upper_left):
    estimate = left + above - upper_left
    distances = (
        (abs(estimate - left), left),
        (abs(estimate - above), above),
        (abs(estimate - upper_left), upper_left),
    )
    return min(enumerate(distances), key=lambda item: (item[1][0], item[0]))[1][1]


def _filtered_png_row(row, previous, bytes_per_pixel, filter_type):
    encoded = bytearray(len(row))
    for index, value in enumerate(row):
        left = row[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        above = previous[index]
        upper_left = (
            previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        )
        predictors = {
            0: 0,
            1: left,
            2: above,
            3: (left + above) // 2,
            4: _paeth_predictor(left, above, upper_left),
        }
        encoded[index] = (value - predictors[filter_type]) & 0xFF
    return bytes(encoded)


def _png_payload_from_idat(width, height, idat, note=b""):
    ihdr = (
        width.to_bytes(4, "big")
        + height.to_bytes(4, "big")
        + bytes((8, 6, 0, 0, 0))
    )
    png = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", ihdr)
        + _png_chunk(b"tEXt", b"Software\x00" + note)
        + _png_chunk(b"IDAT", idat)
        + _png_chunk(b"IEND", b"")
    )
    return base64.b64encode(png).decode("ascii")


def _png_payload(
    width,
    height,
    pixel=b"\x00\x80\xff\xff",
    note=b"",
    filter_type=0,
    rows=None,
):
    if rows is None:
        rows = [pixel * width for _ in range(height)]
    assert len(rows) == height
    assert all(len(row) == width * 4 for row in rows)
    previous = bytes(width * 4)
    scanlines = bytearray()
    for row in rows:
        scanlines.append(filter_type)
        scanlines.extend(_filtered_png_row(row, previous, 4, filter_type))
        previous = row
    return _png_payload_from_idat(
        width, height, zlib.compress(bytes(scanlines)), note=note
    )


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
    rows = [
        bytes((row_index * 37 + byte_index * 19) % 256 for byte_index in range(32))
        for row_index in range(4)
    ]
    saved = [
        {
            "output_type": "display_data",
            "data": {
                "image/png": _png_payload(
                    8, 4, note=b"saved metadata", rows=rows
                ),
                "text/plain": "<Figure size 800x440 with 1 Axes>",
            },
            "metadata": {},
        }
    ]
    for filter_type in range(5):
        reexecuted = [
            {
                "output_type": "display_data",
                "data": {
                    "image/png": _png_payload(
                        8,
                        4,
                        note=b"runtime metadata",
                        filter_type=filter_type,
                        rows=rows,
                    ),
                    "text/plain": "<Figure size 800x440 with 1 Axes>",
                },
                "metadata": {},
            }
        ]

        assert builder._comparable_outputs(
            saved, "saved"
        ) == builder._comparable_outputs(reexecuted, "reexecuted")

    changed_rows = list(rows)
    changed_rows[0] = b"\xff" + changed_rows[0][1:]
    reexecuted[0]["data"]["image/png"] = _png_payload(
        8, 4, note=b"runtime metadata", rows=changed_rows
    )
    assert builder._comparable_outputs(saved, "saved") != builder._comparable_outputs(
        reexecuted, "reexecuted"
    )


def test_png_fingerprint_rejects_excessive_geometry_and_decompression():
    builder = _load_builder_module()
    excessive_geometry = _png_payload_from_idat(
        builder._MAX_PNG_DIMENSION,
        2_049,
        zlib.compress(b"\x00"),
    )
    with pytest.raises(builder.NotebookBuildError, match="pixel count"):
        builder._png_fingerprint(excessive_geometry, "geometry")

    decompression_bomb = _png_payload_from_idat(
        1,
        1,
        zlib.compress(b"\x00" * 1_000_000),
    )
    with pytest.raises(builder.NotebookBuildError, match="geometry|oversized"):
        builder._png_fingerprint(decompression_bomb, "decompression")
