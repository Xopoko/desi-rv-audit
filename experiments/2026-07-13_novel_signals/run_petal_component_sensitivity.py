"""Evaluate E3 after excluding every non-giant nested graph component."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parent
if str(EXPERIMENT_DIR) not in sys.path:
    sys.path.insert(0, str(EXPERIMENT_DIR))

import run_petal as core  # noqa: E402
from desi_rv_audit.hashing import stable_hash_mod  # noqa: E402
from desi_rv_audit.program_night import _robust_width  # noqa: E402


OUTPUT = EXPERIMENT_DIR / "petal_component_sensitivity.csv"


def run() -> pd.DataFrame:
    pairs = pd.read_pickle(core.CACHE)
    pairs["PN_1"] = pairs["PROGRAM_1"].astype(str) + ":" + pairs["NIGHT_1"].astype("int64").astype(str)
    pairs["PN_2"] = pairs["PROGRAM_2"].astype(str) + ":" + pairs["NIGHT_2"].astype("int64").astype(str)
    fold_ids = stable_hash_mod(pairs["GROUP_ID"], core.N_FOLDS)
    base_models = core.fit_or_load_outer_base_models(pairs, fold_ids, force=False)
    offset_rows = pd.read_csv(core.OFFSETS_OUTPUT)
    petal_1 = pairs["PETAL_1"].to_numpy(dtype=np.int8)
    petal_2 = pairs["PETAL_2"].to_numpy(dtype=np.int8)
    records: list[dict[str, object]] = []
    for fold, base in enumerate(base_models):
        rows = offset_rows.loc[offset_rows["SCOPE"].eq("REAL") & offset_rows["FOLD"].eq(fold)]
        offsets = pd.Series(rows["OFFSET_KMS"].to_numpy(dtype=float), index=rows["LABEL"].astype(str))
        components = pd.Series(rows["COMPONENT"].to_numpy(dtype=int), index=rows["LABEL"].astype(str))
        largest = int(components.value_counts().idxmax())
        holdout = core._residual_frame(pairs, fold_ids == fold, base, petal_1, petal_2)
        offset_1 = holdout["LABEL_1"].map(offsets)
        offset_2 = holdout["LABEL_2"].map(offsets)
        component_1 = holdout["LABEL_1"].map(components)
        component_2 = holdout["LABEL_2"].map(components)
        supported = (
            offset_1.notna()
            & offset_2.notna()
            & component_1.eq(largest)
            & component_2.eq(largest)
        )
        scored = holdout.loc[supported]
        base_residual = scored["DELTA_BASE"].to_numpy(dtype=float)
        nested_residual = base_residual - (
            offset_1.loc[supported].to_numpy(dtype=float)
            - offset_2.loc[supported].to_numpy(dtype=float)
        )
        base_width = _robust_width(base_residual)
        nested_width = _robust_width(nested_residual)
        records.append(
            {
                "FOLD": fold,
                "LARGEST_COMPONENT": largest,
                "N_HOLDOUT_GIANT_COMPONENT": int(len(scored)),
                "RAW_WIDTH_PROGRAM_NIGHT_KMS": base_width,
                "RAW_WIDTH_PROGRAM_NIGHT_PETAL_KMS": nested_width,
                "INCREMENTAL_PETAL_GAIN_KMS": base_width - nested_width,
            }
        )
    result = pd.DataFrame.from_records(records)
    result.to_csv(OUTPUT, index=False, lineterminator="\n")
    print(result.to_json(orient="records"), flush=True)
    return result


if __name__ == "__main__":
    run()
