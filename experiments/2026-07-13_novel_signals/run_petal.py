from __future__ import annotations

import argparse
import gc
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


EXPERIMENT_DIR = Path(__file__).resolve().parent
ROOT = EXPERIMENT_DIR.parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from desi_rv_audit.hashing import stable_hash_mod, stable_seed  # noqa: E402
from desi_rv_audit.program_night import _fit_offsets, _robust_width  # noqa: E402


CACHE = EXPERIMENT_DIR / "pair_cache.pkl"
BASE_MODELS_CACHE = EXPERIMENT_DIR / "petal_base_models.pkl"
CV_OUTPUT = EXPERIMENT_DIR / "petal_cv.csv"
OFFSETS_OUTPUT = EXPERIMENT_DIR / "petal_offsets.csv"
PERMUTATIONS_OUTPUT = EXPERIMENT_DIR / "petal_permutations.csv"
REPLICATION_OUTPUT = EXPERIMENT_DIR / "petal_replication.csv"
MANIFEST_OUTPUT = EXPERIMENT_DIR / "petal_manifest.json"
WORKER_GLOB = "petal_permutations_worker_*.csv"

N_FOLDS = 5
BASE_MIN_PAIRS = 200
BASE_DAMP = 0.2
PETAL_MIN_PAIRS = 50
PETAL_DAMP = 1.0
INITIAL_CONTROLS = 19
EXTENDED_CONTROLS = 99
SEED = 20260713


@dataclass
class OffsetModel:
    offsets: pd.Series
    components: pd.Series
    stats: dict[str, object]


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _base_frame(pairs: pd.DataFrame, mask: np.ndarray) -> pd.DataFrame:
    work = pairs.loc[
        mask,
        ["GROUP_ID", "DELTA_VRAD", "PAIR_ERROR", "PAIR_ERROR_FORMAL", "PN_1", "PN_2"],
    ].copy()
    work = work.rename(columns={"PN_1": "LABEL_1", "PN_2": "LABEL_2"})
    return work


def _fit_base(pairs: pd.DataFrame, mask: np.ndarray) -> OffsetModel:
    offsets, components, stats = _fit_offsets(
        _base_frame(pairs, mask),
        min_pairs_per_label=BASE_MIN_PAIRS,
        max_abs_z=5.0,
        clip_sigma=3.5,
        n_clip_iterations=3,
        damp=BASE_DAMP,
    )
    return OffsetModel(offsets=offsets, components=components, stats=stats)


def fit_or_load_outer_base_models(
    pairs: pd.DataFrame,
    fold_ids: np.ndarray,
    force: bool = False,
) -> list[OffsetModel]:
    if BASE_MODELS_CACHE.exists() and not force:
        value = pd.read_pickle(BASE_MODELS_CACHE)
        if isinstance(value, list) and len(value) == N_FOLDS:
            if value and isinstance(value[0], dict):
                return [OffsetModel(**item) for item in value]
            return value
    models: list[OffsetModel] = []
    for fold in range(N_FOLDS):
        started = perf_counter()
        models.append(_fit_base(pairs, fold_ids != fold))
        print(f"BASE_FOLD {fold} {perf_counter() - started:.3f}s", flush=True)
    pd.to_pickle(
        [
            {"offsets": model.offsets, "components": model.components, "stats": model.stats}
            for model in models
        ],
        BASE_MODELS_CACHE,
    )
    return models


def _residual_frame(
    pairs: pd.DataFrame,
    mask: np.ndarray,
    base: OffsetModel,
    petal_1: np.ndarray,
    petal_2: np.ndarray,
) -> pd.DataFrame:
    selected = np.flatnonzero(mask)
    work = pairs.iloc[selected][
        ["GROUP_ID", "DELTA_VRAD", "PAIR_ERROR", "PAIR_ERROR_FORMAL", "PN_1", "PN_2"]
    ].copy()
    base_1 = work["PN_1"].map(base.offsets)
    base_2 = work["PN_2"].map(base.offsets)
    component_1 = work["PN_1"].map(base.components)
    component_2 = work["PN_2"].map(base.components)
    supported = base_1.notna() & base_2.notna() & component_1.eq(component_2)
    work = work.loc[supported].copy()
    selected = selected[supported.to_numpy()]
    work["DELTA_RAW"] = work["DELTA_VRAD"].to_numpy(dtype=float)
    work["DELTA_BASE"] = work["DELTA_RAW"].to_numpy(dtype=float) - (
        base_1.loc[supported].to_numpy(dtype=float) - base_2.loc[supported].to_numpy(dtype=float)
    )
    work["DELTA_VRAD"] = work["DELTA_BASE"]
    work["LABEL_1"] = (
        work["PN_1"].astype(str).to_numpy(dtype=object)
        + ":P"
        + petal_1[selected].astype(str)
    )
    work["LABEL_2"] = (
        work["PN_2"].astype(str).to_numpy(dtype=object)
        + ":P"
        + petal_2[selected].astype(str)
    )
    return work.drop(columns=["PN_1", "PN_2"])


def _center_petal_deviations(offsets: pd.Series) -> pd.Series:
    if offsets.empty:
        return offsets.copy()
    labels = offsets.index.astype(str)
    parent = pd.Series(labels, index=labels, dtype="string").str.rsplit(":P", n=1).str[0]
    values = pd.Series(offsets.to_numpy(dtype=float), index=labels, dtype=float)
    means = values.groupby(parent.to_numpy(dtype=object), sort=False).transform("mean")
    return values - means.to_numpy(dtype=float)


def _fit_nested(train: pd.DataFrame) -> OffsetModel:
    offsets, components, stats = _fit_offsets(
        train,
        min_pairs_per_label=PETAL_MIN_PAIRS,
        max_abs_z=5.0,
        clip_sigma=3.5,
        n_clip_iterations=3,
        damp=PETAL_DAMP,
    )
    return OffsetModel(
        offsets=_center_petal_deviations(offsets),
        components=components,
        stats=stats,
    )


def _evaluate_nested(holdout: pd.DataFrame, nested: OffsetModel) -> dict[str, object]:
    offset_1 = holdout["LABEL_1"].map(nested.offsets)
    offset_2 = holdout["LABEL_2"].map(nested.offsets)
    component_1 = holdout["LABEL_1"].map(nested.components)
    component_2 = holdout["LABEL_2"].map(nested.components)
    supported = offset_1.notna() & offset_2.notna() & component_1.eq(component_2)
    scored = holdout.loc[supported]
    raw = scored["DELTA_RAW"].to_numpy(dtype=float)
    base = scored["DELTA_BASE"].to_numpy(dtype=float)
    nested_residual = base - (
        offset_1.loc[supported].to_numpy(dtype=float) - offset_2.loc[supported].to_numpy(dtype=float)
    )
    raw_width = _robust_width(raw)
    base_width = _robust_width(base)
    nested_width = _robust_width(nested_residual)
    return {
        "N_HOLDOUT_BASE_SUPPORTED": int(len(holdout)),
        "N_HOLDOUT_COMMON_SUPPORT": int(len(scored)),
        "RAW_WIDTH_UNCORRECTED_KMS": raw_width,
        "RAW_WIDTH_PROGRAM_NIGHT_KMS": base_width,
        "RAW_WIDTH_PROGRAM_NIGHT_PETAL_KMS": nested_width,
        "PROGRAM_NIGHT_GAIN_KMS": raw_width - base_width,
        "INCREMENTAL_PETAL_GAIN_KMS": base_width - nested_width,
    }


def _offset_records(scope: str, fold: int | None, model: OffsetModel) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for label, offset in model.offsets.items():
        parent, petal = str(label).rsplit(":P", 1)
        program, night = parent.split(":", 1)
        records.append(
            {
                "SCOPE": scope,
                "FOLD": fold,
                "LABEL": str(label),
                "PROGRAM": program,
                "NIGHT": int(night),
                "PETAL": int(petal),
                "OFFSET_KMS": float(offset),
                "COMPONENT": int(model.components.get(label, -1)),
                "N_LABELS_FIT": model.stats.get("N_LABELS"),
                "N_TRAIN_PAIRS": model.stats.get("N_TRAIN_PAIRS"),
            }
        )
    return records


def run_outer_cv(
    pairs: pd.DataFrame,
    fold_ids: np.ndarray,
    base_models: list[OffsetModel],
    petal_1: np.ndarray,
    petal_2: np.ndarray,
    scope: str,
    capture_offsets: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    fold_records: list[dict[str, object]] = []
    offset_records: list[dict[str, object]] = []
    for fold, base in enumerate(base_models):
        started = perf_counter()
        train = _residual_frame(pairs, fold_ids != fold, base, petal_1, petal_2)
        nested = _fit_nested(train)
        del train
        holdout = _residual_frame(pairs, fold_ids == fold, base, petal_1, petal_2)
        metrics = _evaluate_nested(holdout, nested)
        fold_records.append(
            {
                "SCOPE": scope,
                "FOLD": fold,
                **metrics,
                "N_NESTED_LABELS": nested.stats.get("N_LABELS"),
                "N_NESTED_TRAIN_PAIRS": nested.stats.get("N_TRAIN_PAIRS"),
                "N_NESTED_COMPONENTS": nested.stats.get("N_CONNECTED_COMPONENTS"),
                "ELAPSED_SECONDS": perf_counter() - started,
            }
        )
        if capture_offsets:
            offset_records.extend(_offset_records(scope, fold, nested))
        del holdout, nested
        gc.collect()
        print(
            f"{scope} FOLD {fold} GAIN {metrics['INCREMENTAL_PETAL_GAIN_KMS']:.6f} "
            f"SUPPORT {metrics['N_HOLDOUT_COMMON_SUPPORT']}",
            flush=True,
        )
    return pd.DataFrame.from_records(fold_records), pd.DataFrame.from_records(offset_records)


def _fit_nested_scope(
    pairs: pd.DataFrame,
    mask: np.ndarray,
    petal_1: np.ndarray,
    petal_2: np.ndarray,
    scope: str,
) -> tuple[OffsetModel, list[dict[str, object]]]:
    base = _fit_base(pairs, mask)
    train = _residual_frame(pairs, mask, base, petal_1, petal_2)
    nested = _fit_nested(train)
    del train, base
    return nested, _offset_records(scope, None, nested)


def source_half_replication(
    pairs: pd.DataFrame,
    petal_1: np.ndarray,
    petal_2: np.ndarray,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    half_ids = stable_hash_mod(pairs["GROUP_ID"], 2)
    models: dict[str, OffsetModel] = {}
    records: list[dict[str, object]] = []
    for half, value in (("HALF_A", 0), ("HALF_B", 1)):
        model, model_records = _fit_nested_scope(
            pairs,
            half_ids == value,
            petal_1,
            petal_2,
            half,
        )
        models[half] = model
        records.extend(model_records)
    a = pd.DataFrame(
        {
            "LABEL": models["HALF_A"].offsets.index.astype(str),
            "OFFSET_A_KMS": models["HALF_A"].offsets.to_numpy(dtype=float),
            "COMPONENT_A": models["HALF_A"].offsets.index.map(models["HALF_A"].components),
        }
    )
    b = pd.DataFrame(
        {
            "LABEL": models["HALF_B"].offsets.index.astype(str),
            "OFFSET_B_KMS": models["HALF_B"].offsets.to_numpy(dtype=float),
            "COMPONENT_B": models["HALF_B"].offsets.index.map(models["HALF_B"].components),
        }
    )
    merged = a.merge(b, on="LABEL", how="inner")
    merged["COMPONENT_PAIR"] = merged["COMPONENT_A"].astype(str) + "/" + merged["COMPONENT_B"].astype(str)
    if merged.empty:
        replication = {
            "N_COMMON_LABELS": 0,
            "PEARSON_R": np.nan,
            "SPEARMAN_RHO": np.nan,
            "COMPONENT_PAIR": "",
        }
    else:
        largest = merged["COMPONENT_PAIR"].value_counts().idxmax()
        scored = merged.loc[merged["COMPONENT_PAIR"] == largest]
        x = scored["OFFSET_A_KMS"].to_numpy(dtype=float)
        y = scored["OFFSET_B_KMS"].to_numpy(dtype=float)
        replication = {
            "N_COMMON_LABELS": int(len(scored)),
            "PEARSON_R": float(np.corrcoef(x, y)[0, 1]) if len(scored) >= 2 else np.nan,
            "SPEARMAN_RHO": float(spearmanr(x, y).statistic) if len(scored) >= 2 else np.nan,
            "COMPONENT_PAIR": str(largest),
        }
    return pd.DataFrame([replication]), pd.DataFrame.from_records(records)


def endpoint_codes(pairs: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[np.ndarray]]:
    n_pairs = len(pairs)
    combined_keys = pd.concat([pairs["OBS_KEY_1"], pairs["OBS_KEY_2"]], ignore_index=True)
    codes, uniques = pd.factorize(combined_keys, sort=False)
    del combined_keys
    codes_1 = codes[:n_pairs].astype(np.int32, copy=True)
    codes_2 = codes[n_pairs:].astype(np.int32, copy=True)
    combined_expid = np.concatenate(
        [pairs["EXPID_1"].to_numpy(dtype=np.int64), pairs["EXPID_2"].to_numpy(dtype=np.int64)]
    )
    combined_petal = np.concatenate(
        [pairs["PETAL_1"].to_numpy(dtype=np.int8), pairs["PETAL_2"].to_numpy(dtype=np.int8)]
    )
    _, first = np.unique(codes, return_index=True)
    expid_by_code = combined_expid[first]
    petal_by_code = combined_petal[first]
    if not np.array_equal(combined_expid, expid_by_code[codes]):
        raise ValueError("One OBS_KEY maps to multiple EXPID values")
    if not np.array_equal(combined_petal, petal_by_code[codes]):
        raise ValueError("One OBS_KEY maps to multiple PETAL values")
    del codes, combined_expid, combined_petal, uniques
    order = np.argsort(expid_by_code, kind="stable")
    boundaries = np.flatnonzero(np.r_[True, expid_by_code[order][1:] != expid_by_code[order][:-1], True])
    groups = [order[boundaries[i] : boundaries[i + 1]] for i in range(len(boundaries) - 1)]
    return codes_1, codes_2, expid_by_code, petal_by_code, groups


def shuffled_petals(
    permutation: int,
    codes_1: np.ndarray,
    codes_2: np.ndarray,
    petal_by_code: np.ndarray,
    groups: list[np.ndarray],
) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(stable_seed(f"E3:PETAL:{SEED}:{permutation}"))
    shuffled = petal_by_code.copy()
    for indices in groups:
        if len(indices) > 1:
            shuffled[indices] = rng.permutation(petal_by_code[indices])
    return shuffled[codes_1], shuffled[codes_2]


def _mean_gain(cv: pd.DataFrame) -> float:
    return float(cv["INCREMENTAL_PETAL_GAIN_KMS"].mean())


def _control_record(
    pairs: pd.DataFrame,
    fold_ids: np.ndarray,
    base_models: list[OffsetModel],
    permutation: int,
    codes_1: np.ndarray,
    codes_2: np.ndarray,
    petal_by_code: np.ndarray,
    groups: list[np.ndarray],
) -> dict[str, object]:
    started = perf_counter()
    shuffled_1, shuffled_2 = shuffled_petals(
        permutation,
        codes_1,
        codes_2,
        petal_by_code,
        groups,
    )
    control_cv, _ = run_outer_cv(
        pairs,
        fold_ids,
        base_models,
        shuffled_1,
        shuffled_2,
        scope=f"PERMUTATION_{permutation}",
        capture_offsets=False,
    )
    return {
        "PERMUTATION": permutation,
        "MEAN_INCREMENTAL_GAIN_KMS": _mean_gain(control_cv),
        "MIN_FOLD_GAIN_KMS": float(control_cv["INCREMENTAL_PETAL_GAIN_KMS"].min()),
        "MAX_FOLD_GAIN_KMS": float(control_cv["INCREMENTAL_PETAL_GAIN_KMS"].max()),
        "N_POSITIVE_FOLDS": int((control_cv["INCREMENTAL_PETAL_GAIN_KMS"] > 0).sum()),
        "MEAN_COMMON_SUPPORT": float(control_cv["N_HOLDOUT_COMMON_SUPPORT"].mean()),
        "ELAPSED_SECONDS": perf_counter() - started,
    }


def run_controls_worker(start: int, stop: int) -> Path:
    if start < 0 or stop <= start or stop > EXTENDED_CONTROLS:
        raise ValueError(f"Invalid permutation range [{start}, {stop})")
    pairs = pd.read_pickle(CACHE)
    pairs["PN_1"] = pairs["PROGRAM_1"].astype(str) + ":" + pairs["NIGHT_1"].astype("int64").astype(str)
    pairs["PN_2"] = pairs["PROGRAM_2"].astype(str) + ":" + pairs["NIGHT_2"].astype("int64").astype(str)
    fold_ids = stable_hash_mod(pairs["GROUP_ID"], N_FOLDS)
    base_models = fit_or_load_outer_base_models(pairs, fold_ids, force=False)
    codes_1, codes_2, _, petal_by_code, groups = endpoint_codes(pairs)
    records: list[dict[str, object]] = []
    worker_output = EXPERIMENT_DIR / f"petal_permutations_worker_{start:03d}_{stop:03d}.csv"
    for permutation in range(start, stop):
        record = _control_record(
            pairs,
            fold_ids,
            base_models,
            permutation,
            codes_1,
            codes_2,
            petal_by_code,
            groups,
        )
        records.append(record)
        pd.DataFrame.from_records(records).to_csv(worker_output, index=False, lineterminator="\n")
        print(f"CONTROL {permutation} GAIN {record['MEAN_INCREMENTAL_GAIN_KMS']:.6f}", flush=True)
    return worker_output


def finalize_parallel_controls() -> dict[str, object]:
    real_cv = pd.read_csv(CV_OUTPUT)
    replication = pd.read_csv(REPLICATION_OUTPUT)
    worker_files = sorted(EXPERIMENT_DIR.glob(WORKER_GLOB))
    if not worker_files:
        raise FileNotFoundError("No PETAL permutation worker files found")
    controls = (
        pd.concat([pd.read_csv(path) for path in worker_files], ignore_index=True)
        .sort_values("PERMUTATION")
        .drop_duplicates("PERMUTATION", keep="last")
    )
    real_gain = _mean_gain(real_cv)
    required = EXTENDED_CONTROLS if (
        real_gain >= 0.02
        and set(range(INITIAL_CONTROLS)).issubset(set(controls["PERMUTATION"].astype(int)))
        and real_gain
        > float(
            controls.loc[
                controls["PERMUTATION"].astype(int) < INITIAL_CONTROLS,
                "MEAN_INCREMENTAL_GAIN_KMS",
            ].max()
        )
    ) else INITIAL_CONTROLS
    missing = sorted(set(range(required)) - set(controls["PERMUTATION"].astype(int)))
    if missing:
        raise RuntimeError(f"Missing required PETAL controls: {missing[:10]}")
    controls = controls.loc[controls["PERMUTATION"].astype(int) < required].copy()
    controls.to_csv(PERMUTATIONS_OUTPUT, index=False, lineterminator="\n")
    control_gain = controls["MEAN_INCREMENTAL_GAIN_KMS"].to_numpy(dtype=float)
    p_value = float((1 + np.sum(control_gain >= real_gain)) / (1 + len(control_gain)))
    positive_folds = int((real_cv["INCREMENTAL_PETAL_GAIN_KMS"] > 0).sum())
    replication_r = float(replication.iloc[0]["PEARSON_R"])
    passed = (
        real_gain >= 0.02
        and positive_folds == N_FOLDS
        and p_value <= 0.01
        and replication_r >= 0.50
    )
    suggestive = not passed and real_gain > float(np.nanmax(control_gain))
    manifest = {
        "schema": "desi_rv_audit.program_night_petal.v1",
        "status": "complete",
        "decision": "pass" if passed else ("suggestive" if suggestive else "null"),
        "parameters": {
            "n_folds": N_FOLDS,
            "base_min_pairs_per_label": BASE_MIN_PAIRS,
            "base_damp": BASE_DAMP,
            "petal_min_pairs_per_label": PETAL_MIN_PAIRS,
            "petal_damp": PETAL_DAMP,
            "constraint": "unweighted zero mean across supported PETAL cells within PROGRAM:NIGHT",
            "initial_controls": INITIAL_CONTROLS,
            "extended_controls": EXTENDED_CONTROLS,
            "seed": SEED,
        },
        "real_mean_incremental_gain_kms": real_gain,
        "positive_folds": positive_folds,
        "n_controls": int(len(controls)),
        "control_max_gain_kms": float(np.nanmax(control_gain)),
        "empirical_p": p_value,
        "replication": replication.iloc[0].to_dict(),
        "worker_files": [path.name for path in worker_files],
        "worker_elapsed_seconds_sum": float(controls["ELAPSED_SECONDS"].sum()),
    }
    _write_json(MANIFEST_OUTPUT, manifest)
    return manifest


def run(force_base: bool = False, real_only: bool = False) -> dict[str, object]:
    total_started = perf_counter()
    pairs = pd.read_pickle(CACHE)
    pairs["PN_1"] = pairs["PROGRAM_1"].astype(str) + ":" + pairs["NIGHT_1"].astype("int64").astype(str)
    pairs["PN_2"] = pairs["PROGRAM_2"].astype(str) + ":" + pairs["NIGHT_2"].astype("int64").astype(str)
    fold_ids = stable_hash_mod(pairs["GROUP_ID"], N_FOLDS)
    real_petal_1 = pairs["PETAL_1"].to_numpy(dtype=np.int8)
    real_petal_2 = pairs["PETAL_2"].to_numpy(dtype=np.int8)

    base_models = fit_or_load_outer_base_models(pairs, fold_ids, force=force_base)
    real_cv, cv_offsets = run_outer_cv(
        pairs,
        fold_ids,
        base_models,
        real_petal_1,
        real_petal_2,
        scope="REAL",
        capture_offsets=True,
    )
    real_cv.to_csv(CV_OUTPUT, index=False, lineterminator="\n")
    replication, half_offsets = source_half_replication(pairs, real_petal_1, real_petal_2)
    replication.to_csv(REPLICATION_OUTPUT, index=False, lineterminator="\n")
    full_model, full_offsets = _fit_nested_scope(
        pairs,
        np.ones(len(pairs), dtype=bool),
        real_petal_1,
        real_petal_2,
        "FULL",
    )
    del full_model
    offsets = pd.concat(
        [cv_offsets, half_offsets, pd.DataFrame.from_records(full_offsets)],
        ignore_index=True,
        sort=False,
    )
    offsets.to_csv(OFFSETS_OUTPUT, index=False, lineterminator="\n")

    real_gain = _mean_gain(real_cv)
    if real_only:
        manifest = {
            "schema": "desi_rv_audit.program_night_petal.v1",
            "status": "real_complete_controls_pending",
            "real_mean_incremental_gain_kms": real_gain,
            "positive_folds": int((real_cv["INCREMENTAL_PETAL_GAIN_KMS"] > 0).sum()),
            "replication": replication.iloc[0].to_dict(),
            "elapsed_seconds": perf_counter() - total_started,
        }
        _write_json(MANIFEST_OUTPUT, manifest)
        return manifest

    existing = (
        pd.read_csv(PERMUTATIONS_OUTPUT)
        if PERMUTATIONS_OUTPUT.exists()
        else pd.DataFrame(columns=["PERMUTATION", "MEAN_INCREMENTAL_GAIN_KMS"])
    )
    completed = set(pd.to_numeric(existing.get("PERMUTATION"), errors="coerce").dropna().astype(int))
    codes_1, codes_2, _, petal_by_code, groups = endpoint_codes(pairs)
    target = INITIAL_CONTROLS
    records = existing.to_dict(orient="records")
    permutation = 0
    while permutation < target:
        if permutation not in completed:
            record = _control_record(
                pairs,
                fold_ids,
                base_models,
                permutation,
                codes_1,
                codes_2,
                petal_by_code,
                groups,
            )
            records.append(record)
            pd.DataFrame.from_records(records).sort_values("PERMUTATION").to_csv(
                PERMUTATIONS_OUTPUT,
                index=False,
                lineterminator="\n",
            )
            print(f"CONTROL {permutation} GAIN {record['MEAN_INCREMENTAL_GAIN_KMS']:.6f}", flush=True)
        permutation += 1
        if permutation == INITIAL_CONTROLS:
            first = pd.DataFrame.from_records(records)
            first = first.loc[pd.to_numeric(first["PERMUTATION"], errors="coerce") < INITIAL_CONTROLS]
            if (
                real_gain >= 0.02
                and len(first) == INITIAL_CONTROLS
                and real_gain > float(first["MEAN_INCREMENTAL_GAIN_KMS"].max())
            ):
                target = EXTENDED_CONTROLS

    controls = pd.DataFrame.from_records(records).sort_values("PERMUTATION")
    control_gain = controls["MEAN_INCREMENTAL_GAIN_KMS"].to_numpy(dtype=float)
    p_value = float((1 + np.sum(control_gain >= real_gain)) / (1 + len(control_gain)))
    positive_folds = int((real_cv["INCREMENTAL_PETAL_GAIN_KMS"] > 0).sum())
    replication_r = float(replication.iloc[0]["PEARSON_R"])
    passed = (
        real_gain >= 0.02
        and positive_folds == N_FOLDS
        and p_value <= 0.01
        and replication_r >= 0.50
    )
    suggestive = not passed and real_gain > float(np.nanmax(control_gain))
    manifest = {
        "schema": "desi_rv_audit.program_night_petal.v1",
        "status": "complete",
        "decision": "pass" if passed else ("suggestive" if suggestive else "null"),
        "parameters": {
            "n_folds": N_FOLDS,
            "base_min_pairs_per_label": BASE_MIN_PAIRS,
            "base_damp": BASE_DAMP,
            "petal_min_pairs_per_label": PETAL_MIN_PAIRS,
            "petal_damp": PETAL_DAMP,
            "constraint": "unweighted zero mean across supported PETAL cells within PROGRAM:NIGHT",
            "initial_controls": INITIAL_CONTROLS,
            "extended_controls": EXTENDED_CONTROLS,
            "seed": SEED,
        },
        "real_mean_incremental_gain_kms": real_gain,
        "positive_folds": positive_folds,
        "n_controls": int(len(controls)),
        "control_max_gain_kms": float(np.nanmax(control_gain)),
        "empirical_p": p_value,
        "replication": replication.iloc[0].to_dict(),
        "elapsed_seconds": perf_counter() - total_started,
    }
    _write_json(MANIFEST_OUTPUT, manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-base", action="store_true")
    parser.add_argument("--real-only", action="store_true")
    parser.add_argument("--controls-worker", nargs=2, type=int, metavar=("START", "STOP"))
    parser.add_argument("--finalize-controls", action="store_true")
    args = parser.parse_args()
    if args.controls_worker:
        output = run_controls_worker(*args.controls_worker)
        print(json.dumps({"worker_output": output.name}, sort_keys=True), flush=True)
    elif args.finalize_controls:
        print(json.dumps(finalize_parallel_controls(), sort_keys=True), flush=True)
    else:
        print(json.dumps(run(force_base=args.force_base, real_only=args.real_only), sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
