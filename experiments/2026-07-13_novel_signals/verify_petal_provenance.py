from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT = EXPERIMENT_DIR / "petal_provenance_verification.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compare_csv(before: str, after: str, ignored: set[str]) -> dict[str, object]:
    left = pd.read_csv(EXPERIMENT_DIR / before)
    right = pd.read_csv(EXPERIMENT_DIR / after)
    columns = [column for column in left.columns if column not in ignored]
    same_schema = columns == [column for column in right.columns if column not in ignored]
    same_rows = len(left) == len(right)
    numeric_differences: dict[str, float] = {}
    exact_non_numeric = True
    if same_schema and same_rows:
        for column in columns:
            if pd.api.types.is_numeric_dtype(left[column]) and pd.api.types.is_numeric_dtype(right[column]):
                a = pd.to_numeric(left[column], errors="coerce").to_numpy(dtype=float)
                b = pd.to_numeric(right[column], errors="coerce").to_numpy(dtype=float)
                finite = np.isfinite(a) | np.isfinite(b)
                difference = np.abs(a - b)
                numeric_differences[column] = (
                    float(np.nanmax(difference[finite])) if np.any(finite) else 0.0
                )
                if not np.array_equal(np.isnan(a), np.isnan(b)):
                    numeric_differences[column] = float("inf")
            else:
                exact_non_numeric &= left[column].fillna("<NA>").astype(str).equals(
                    right[column].fillna("<NA>").astype(str)
                )
    maximum_numeric_difference_raw = max(numeric_differences.values(), default=float("inf"))
    passed = (
        same_schema
        and same_rows
        and exact_non_numeric
        and np.isfinite(maximum_numeric_difference_raw)
        and maximum_numeric_difference_raw <= 1e-12
    )
    return {
        "before": before,
        "after": after,
        "ignored_columns": sorted(ignored),
        "same_schema": same_schema,
        "same_rows": same_rows,
        "n_rows": int(len(left)),
        "exact_non_numeric": exact_non_numeric,
        "maximum_numeric_difference": (
            maximum_numeric_difference_raw if np.isfinite(maximum_numeric_difference_raw) else None
        ),
        "pass": passed,
        "before_sha256": _sha256(EXPERIMENT_DIR / before),
        "after_sha256": _sha256(EXPERIMENT_DIR / after),
    }


def run() -> dict[str, object]:
    comparisons = [
        _compare_csv("petal_cv.before.csv", "petal_cv.csv", {"ELAPSED_SECONDS"}),
        _compare_csv("petal_replication.before.csv", "petal_replication.csv", set()),
        _compare_csv("petal_offsets.before.csv", "petal_offsets.csv", set()),
        _compare_csv(
            "petal_permutations_worker_000_001.before.csv",
            "petal_permutations_worker_000_001.csv",
            {"ELAPSED_SECONDS"},
        ),
    ]
    result = {
        "schema": "desi_rv_audit.petal_provenance_verification.v1",
        "status": "pass" if all(item["pass"] for item in comparisons) else "fail",
        "contract": "Frozen-code exact numeric parity, excluding wall-clock timing columns.",
        "hashes": {
            "run_petal.py": _sha256(EXPERIMENT_DIR / "run_petal.py"),
            "research_plan.json": _sha256(EXPERIMENT_DIR / "research_plan.json"),
            "pair_cache.pkl": _sha256(EXPERIMENT_DIR / "pair_cache.pkl"),
            "petal_base_models.pkl": _sha256(EXPERIMENT_DIR / "petal_base_models.pkl"),
        },
        "comparisons": comparisons,
    }
    OUTPUT.write_text(
        json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({"status": result["status"], "comparisons": comparisons}, sort_keys=True))
    if result["status"] != "pass":
        raise SystemExit(1)
    return result


if __name__ == "__main__":
    run()
