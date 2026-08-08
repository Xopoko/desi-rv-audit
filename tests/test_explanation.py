import importlib.util
import json
from pathlib import Path
import subprocess
import sys


def _load_validator_module():
    repo_root = Path(__file__).resolve().parents[1]
    validator = repo_root / "explanation" / "tools" / "validate_explanation.py"
    spec = importlib.util.spec_from_file_location("explanation_validator", validator)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
