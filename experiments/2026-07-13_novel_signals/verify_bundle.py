from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parent


def _require(condition: object, message: str) -> None:
    if not bool(condition):
        raise RuntimeError(message)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run() -> None:
    plan = json.loads((EXPERIMENT_DIR / "research_plan.json").read_text(encoding="utf-8"))
    manifest = json.loads((EXPERIMENT_DIR / "experiment_manifest.json").read_text(encoding="utf-8"))
    provenance = json.loads(
        (EXPERIMENT_DIR / "petal_provenance_verification.json").read_text(encoding="utf-8")
    )
    claims = [
        json.loads(line)
        for line in (EXPERIMENT_DIR / "claims.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    claim_status = {claim["claim_id"]: claim["status"] for claim in claims}
    experiments = {item["id"]: item for item in plan["experiments"]}
    _require(len(experiments) == 3, "Expected exactly three preregistered experiments")
    _require(manifest["status"] == "complete", "Bundle manifest is not complete")
    _require(provenance["status"] == "pass", "E3 frozen-code provenance failed")
    _require(
        manifest["research_plan_sha256"] == _sha256(EXPERIMENT_DIR / "research_plan.json"),
        "Research-plan hash mismatch",
    )
    for section in ("scripts", "artifacts", "publication_outputs"):
        names = [entry["name"] for entry in manifest[section]]
        _require(len(names) == len(set(names)), f"Duplicate {section} entries")
        for entry in manifest[section]:
            path = EXPERIMENT_DIR / entry["name"]
            _require(path.exists(), f"Missing {section} file: {entry['name']}")
            _require(path.stat().st_size == entry["size"], f"Size mismatch: {entry['name']}")
            _require(_sha256(path) == entry["sha256"], f"Hash mismatch: {entry['name']}")

    temporal = pd.read_csv(EXPERIMENT_DIR / "temporal_persistence.csv")
    _require(
        set(temporal["SCOPE"]) == {"BACKUP", "BRIGHT", "DARK", "POOLED"}
        and temporal["SCOPE"].is_unique,
        "Unexpected or duplicate E1 scopes",
    )
    e1_criteria = experiments["E1_temporal_persistence"]["success_criteria"]
    e1_recomputed = (
        temporal["N_ADJACENT_PAIRS_1_7D"].ge(e1_criteria["minimum_adjacent_pairs"])
        & temporal["PEARSON_R_1_7D"].abs().ge(e1_criteria["minimum_absolute_pearson_r"])
        & temporal["OFFSET_PERM_P_MAXT"].le(e1_criteria["maximum_corrected_permutation_p"])
        & temporal["LOO_SAME_SIGN"].ge(e1_criteria["minimum_leave_one_fold_out_same_sign"])
    )
    _require(
        np.array_equal(e1_recomputed.to_numpy(dtype=bool), temporal["SCOPE_PASS"].to_numpy(dtype=bool)),
        "Stored E1 gate decisions do not match the preregistered thresholds",
    )
    pooled_pass = bool(e1_recomputed.loc[temporal["SCOPE"].eq("POOLED")].iloc[0])
    individual_passes = int(e1_recomputed.loc[temporal["SCOPE"].ne("POOLED")].sum())
    e1_status = "pass" if pooled_pass or individual_passes >= 2 else "null"

    coherence = pd.read_csv(EXPERIMENT_DIR / "cross_program_coherence.csv")
    primary = coherence.loc[coherence["IS_PRIMARY_PAIR"].astype(bool)]
    _require(len(primary) == 1, "Expected one primary E2 row")
    e2 = primary.iloc[0]
    e2_criteria = experiments["E2_cross_program_coherence"]["success_criteria"]
    e2_pass = bool(
        int(e2["MIN_SHARED_NIGHTS"]) >= e2_criteria["minimum_shared_nights"]
        and float(e2["SYMMETRIC_R0"]) >= e2_criteria["minimum_pearson_r"]
        and float(e2["R_P_A_Q_B"]) >= e2_criteria["minimum_each_cross_half_pearson_r"]
        and float(e2["R_P_B_Q_A"]) >= e2_criteria["minimum_each_cross_half_pearson_r"]
        and float(e2["SYMMETRIC_EXCESS_R"]) >= e2_criteria["minimum_zero_lag_excess_r"]
        and float(e2["BOOTSTRAP_R0_LOW_95"])
        > e2_criteria["minimum_block_bootstrap_lower_95_r"]
        and float(e2["BLOCK_NULL_P_HOLM"])
        <= e2_criteria["maximum_corrected_permutation_p"]
    )
    _require(e2_pass == bool(e2["PASS"]), "Stored E2 decision does not match its gates")
    e2_status = "pass" if e2_pass else "null"

    petal_cv = pd.read_csv(EXPERIMENT_DIR / "petal_cv.csv")
    controls = pd.read_csv(EXPERIMENT_DIR / "petal_permutations.csv")
    replication = pd.read_csv(EXPERIMENT_DIR / "petal_replication.csv").iloc[0]
    petal_manifest = json.loads(
        (EXPERIMENT_DIR / "petal_manifest.json").read_text(encoding="utf-8")
    )
    real_gain = float(petal_cv["INCREMENTAL_PETAL_GAIN_KMS"].mean())
    initial = controls.loc[controls["PERMUTATION"].astype(int) < 19]
    _require(
        set(initial["PERMUTATION"].astype(int)) == set(range(19)),
        "E3 initial control stage is incomplete",
    )
    expected_controls = 99 if real_gain >= 0.02 and real_gain > float(
        initial["MEAN_INCREMENTAL_GAIN_KMS"].max()
    ) else 19
    _require(controls["PERMUTATION"].is_unique, "Duplicate E3 permutation indices")
    _require(
        set(controls["PERMUTATION"].astype(int)) == set(range(expected_controls)),
        "E3 control count violates the sequential rule",
    )
    empirical_p = float(
        (1 + int((controls["MEAN_INCREMENTAL_GAIN_KMS"] >= real_gain).sum()))
        / (1 + expected_controls)
    )
    e3_criteria = experiments["E3_program_night_petal_residual"]["success_criteria"]
    positive_folds = int((petal_cv["INCREMENTAL_PETAL_GAIN_KMS"] > 0).sum())
    e3_pass = bool(
        real_gain >= e3_criteria["minimum_incremental_raw_width_reduction_kms"]
        and positive_folds >= e3_criteria["minimum_positive_folds"]
        and empirical_p <= e3_criteria["maximum_corrected_permutation_p"]
        and float(replication["PEARSON_R"])
        >= e3_criteria["minimum_source_half_offset_correlation"]
    )
    e3_status = (
        "pass"
        if e3_pass
        else (
            "suggestive"
            if real_gain > float(controls["MEAN_INCREMENTAL_GAIN_KMS"].max())
            else "null"
        )
    )
    _require(petal_manifest["decision"] == e3_status, "Stored E3 decision does not match its gates")
    _require(int(petal_manifest["n_controls"]) == expected_controls, "E3 manifest control count mismatch")
    _require(np.isclose(float(petal_manifest["empirical_p"]), empirical_p), "E3 p-value mismatch")
    expected_status = {"E1": e1_status, "E2": e2_status, "E3": e3_status}
    _require(claim_status == expected_status, "Published claim statuses do not match recomputed gates")

    cache_manifest = json.loads(
        (EXPERIMENT_DIR / "pair_cache_manifest.json").read_text(encoding="utf-8")
    )
    cache = EXPERIMENT_DIR / "pair_cache.pkl"
    if cache.exists():
        _require(cache.stat().st_size == cache_manifest["cache"]["size"], "Pair-cache size mismatch")
        _require(_sha256(cache) == cache_manifest["cache"]["sha256"], "Pair-cache hash mismatch")
    else:
        _require(
            cache_manifest["cache"].get("retained_after_run") is False,
            "Deleted pair cache is not marked as non-retained",
        )

    text_suffixes = {".py", ".json", ".jsonl", ".csv", ".md"}
    crlf_files = []
    for path in EXPERIMENT_DIR.iterdir():
        if path.is_file() and path.suffix.lower() in text_suffixes and ".before." not in path.name:
            if b"\r\n" in path.read_bytes():
                crlf_files.append(path.name)
    _require(not crlf_files, f"CRLF found in: {crlf_files}")
    print(
        json.dumps(
            {
                "status": "pass",
                "claims": expected_status,
                "real_petal_gain_kms": real_gain,
                "petal_control_max_kms": float(controls["MEAN_INCREMENTAL_GAIN_KMS"].max()),
                "petal_controls": expected_controls,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    run()
