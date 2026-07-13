"""Reproduce the complete three-experiment bundle with parallel E3 controls."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parent
ROOT = EXPERIMENT_DIR.parents[1]
PYTHON = Path(sys.executable)


def _run(script: str, *args: object) -> None:
    command = [str(PYTHON), str(EXPERIMENT_DIR / script), *(str(arg) for arg in args)]
    print("RUN", subprocess.list2cmdline(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def _ranges(start: int, stop: int, workers: int) -> list[tuple[int, int]]:
    count = stop - start
    workers = max(1, min(workers, count))
    size = int(math.ceil(count / workers))
    return [(left, min(left + size, stop)) for left in range(start, stop, size)]


def _run_control_ranges(start: int, stop: int, workers: int) -> None:
    ranges = _ranges(start, stop, workers)
    with ThreadPoolExecutor(max_workers=len(ranges)) as executor:
        futures = [
            executor.submit(_run, "run_petal.py", "--controls-worker", left, right)
            for left, right in ranges
        ]
        for future in futures:
            future.result()


def _initial_controls_trigger_extension() -> bool:
    real_gain = float(
        pd.read_csv(EXPERIMENT_DIR / "petal_cv.csv")["INCREMENTAL_PETAL_GAIN_KMS"].mean()
    )
    worker_files = sorted(EXPERIMENT_DIR.glob("petal_permutations_worker_*.csv"))
    controls = (
        pd.concat([pd.read_csv(path) for path in worker_files], ignore_index=True)
        .sort_values("PERMUTATION")
        .drop_duplicates("PERMUTATION", keep="last")
    )
    initial = controls.loc[controls["PERMUTATION"].astype(int) < 19]
    if set(initial["PERMUTATION"].astype(int)) != set(range(19)):
        raise RuntimeError("Initial E3 controls are incomplete")
    return real_gain >= 0.02 and real_gain > float(initial["MEAN_INCREMENTAL_GAIN_KMS"].max())


def run(workers: int, keep_cache: bool) -> None:
    for name in ("experiment_manifest.json", "claims.jsonl", "report.md"):
        path = EXPERIMENT_DIR / name
        if path.exists():
            path.unlink()
    _run("build_pair_cache.py")
    _run("run_temporal.py")
    _run("run_cross_program.py")
    _run("run_petal.py", "--real-only", "--force-base")
    _run("run_temporal_independent.py")
    _run("run_petal_diagnostics.py")
    _run("run_petal_component_sensitivity.py")
    _run("plot_petal_pattern.py")

    for path in EXPERIMENT_DIR.glob("petal_permutations_worker_*.csv"):
        path.unlink()
    for name in ("petal_cv.csv", "petal_replication.csv", "petal_offsets.csv"):
        shutil.copy2(EXPERIMENT_DIR / name, EXPERIMENT_DIR / name.replace(".csv", ".before.csv"))
    _run("run_petal.py", "--controls-worker", 0, 1)
    shutil.copy2(
        EXPERIMENT_DIR / "petal_permutations_worker_000_001.csv",
        EXPERIMENT_DIR / "petal_permutations_worker_000_001.before.csv",
    )
    _run_control_ranges(1, 19, workers)
    if _initial_controls_trigger_extension():
        _run_control_ranges(19, 99, workers)
    _run("run_petal.py", "--real-only")
    _run("run_petal.py", "--controls-worker", 0, 1)
    _run("verify_petal_provenance.py")
    for path in EXPERIMENT_DIR.glob("*.before.csv"):
        path.unlink()
    _run("run_petal.py", "--finalize-controls")

    _run("discovery_stats.py")
    scripts = [str(path) for path in sorted(EXPERIMENT_DIR.glob("*.py"))]
    subprocess.run([str(PYTHON), "-m", "py_compile", *scripts], cwd=ROOT, check=True)
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)

    if not keep_cache:
        for path in (EXPERIMENT_DIR / "pair_cache.pkl", EXPERIMENT_DIR / "petal_base_models.pkl"):
            if path.exists():
                path.unlink()
        manifest_path = EXPERIMENT_DIR / "pair_cache_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["cache"]["retained_after_run"] = False
        manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    for path in EXPERIMENT_DIR.glob("__pycache__"):
        shutil.rmtree(path)
    _run("finalize_experiments.py")
    _run("verify_bundle.py")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=min(10, max(1, (os.cpu_count() or 2) // 2)))
    parser.add_argument("--keep-cache", action="store_true")
    args = parser.parse_args()
    run(workers=args.workers, keep_cache=args.keep_cache)


if __name__ == "__main__":
    main()
