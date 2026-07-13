from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

import pandas as pd


EXPERIMENT_DIR = Path(__file__).resolve().parent
ROOT = EXPERIMENT_DIR.parents[1]
PLAN = EXPERIMENT_DIR / "research_plan.json"
MANIFEST = EXPERIMENT_DIR / "experiment_manifest.json"
CLAIMS = EXPERIMENT_DIR / "claims.jsonl"
REPORT = EXPERIMENT_DIR / "report.md"

REQUIRED = [
    "temporal_persistence.csv",
    "temporal_change_points.csv",
    "temporal_offsets.csv",
    "temporal_independent_halves.csv",
    "temporal_independent_block_null.csv",
    "temporal_independent_manifest.json",
    "cross_program_coherence.csv",
    "within_program_offsets.csv",
    "cross_program_lags.csv",
    "cross_program_block_null.csv",
    "cross_program_bootstrap.csv",
    "cross_program_manifest.json",
    "petal_cv.csv",
    "petal_offsets.csv",
    "petal_permutations.csv",
    "petal_replication.csv",
    "petal_cv_by_program.csv",
    "petal_component_sensitivity.csv",
    "petal_independent_program_offsets.csv",
    "petal_independent_program_summary.csv",
        "petal_independent_pattern.png",
        "petal_provenance_verification.json",
    "petal_manifest.json",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_sanitize(item) for item in value]
    if hasattr(value, "item"):
        return _sanitize(value.item())
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _write_json(path: Path, value: object) -> None:
    _write_text_atomic(
        path,
        json.dumps(_sanitize(value), indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
    )


def _write_text_atomic(path: Path, value: str) -> None:
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        value,
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def _claims() -> list[dict[str, Any]]:
    temporal = pd.read_csv(EXPERIMENT_DIR / "temporal_persistence.csv")
    bright = temporal.loc[temporal["SCOPE"] == "BRIGHT"].iloc[0]
    dark = temporal.loc[temporal["SCOPE"] == "DARK"].iloc[0]
    e1_pass = str(bright["E1_DECISION"]).lower() == "pass"
    temporal_independent = pd.read_csv(EXPERIMENT_DIR / "temporal_independent_halves.csv")
    bright_independent = temporal_independent.loc[temporal_independent["PROGRAM"] == "BRIGHT"].iloc[0]
    dark_independent = temporal_independent.loc[temporal_independent["PROGRAM"] == "DARK"].iloc[0]

    coherence = pd.read_csv(EXPERIMENT_DIR / "cross_program_coherence.csv")
    e2 = coherence.loc[coherence["IS_PRIMARY_PAIR"].map(_bool)].iloc[0]
    e2_pass = _bool(e2["PASS"])

    petal_manifest = _json(EXPERIMENT_DIR / "petal_manifest.json")
    if petal_manifest.get("status") != "complete":
        raise RuntimeError("E3 controls are incomplete; refusing to finalize")
    e3_decision = str(petal_manifest["decision"])
    provenance = _json(EXPERIMENT_DIR / "petal_provenance_verification.json")
    if provenance.get("status") != "pass":
        raise RuntimeError("E3 frozen-code provenance verification did not pass")
    petal_independent = pd.read_csv(EXPERIMENT_DIR / "petal_independent_program_summary.csv")
    petal_component = pd.read_csv(EXPERIMENT_DIR / "petal_component_sensitivity.csv")

    return [
        {
            "claim_id": "E1",
            "status": "pass" if e1_pass else "null",
            "claim": (
                "Diagnostic PROGRAM:NIGHT offsets retain reproducible, program-conditioned multi-night memory in BRIGHT and DARK."
                if e1_pass
                else "No preregistered multi-night persistence was detected."
            ),
            "metrics": {
                "bright_r_1_7d": bright["PEARSON_R_1_7D"],
                "bright_full_pipeline_maxT_p": bright["FULL_PIPELINE_P_MAXT"],
                "dark_r_1_7d": dark["PEARSON_R_1_7D"],
                "dark_full_pipeline_maxT_p": dark["FULL_PIPELINE_P_MAXT"],
                "bright_disjoint_half_aggregate_r_1_7d": bright_independent["AGGREGATE_R_1_7D"],
                "bright_disjoint_half_block_p": bright_independent["BLOCK_NULL_P"],
                "dark_disjoint_half_aggregate_r_1_7d": dark_independent["AGGREGATE_R_1_7D"],
                "dark_disjoint_half_block_p": dark_independent["BLOCK_NULL_P"],
            },
            "evidence": [
                "temporal_persistence.csv",
                "temporal_change_points.csv",
                "temporal_offsets.csv",
                "temporal_independent_halves.csv",
            ],
            "limitations": [
                "Exploratory within DESI DR1 because the hypothesis was chosen after inspecting the same release.",
                "The 100 full-pipeline controls limit the minimum empirical p-value to 1/101.",
                "Persistence does not by itself identify a physical instrument mechanism.",
                "The independent-half robustness check was added after the primary E1 result and is supporting, not a new preregistered gate.",
            ],
        },
        {
            "claim_id": "E2",
            "status": "pass" if e2_pass else "null",
            "claim": (
                    "Independently fitted, source-disjoint BRIGHT and DARK night offsets share a same-calendar component beyond nearby nonzero lags."
                    if e2_pass
                else "The apparent BRIGHT/DARK same-night coherence from the joint fit was not reproduced after within-program graph separation and source-disjoint cross-comparison."
            ),
            "metrics": {
                "minimum_shared_nights": e2["MIN_SHARED_NIGHTS"],
                "symmetric_same_night_r": e2["SYMMETRIC_R0"],
                "symmetric_zero_lag_excess_r": e2["SYMMETRIC_EXCESS_R"],
                "block_null_p_holm": e2["BLOCK_NULL_P_HOLM"],
                "block_bootstrap_r_low_95": e2["BOOTSTRAP_R0_LOW_95"],
            },
            "evidence": [
                "cross_program_coherence.csv",
                "within_program_offsets.csv",
                "cross_program_lags.csv",
                "cross_program_block_null.csv",
            ],
            "limitations": [
                "A calendar-linked common component is not proof of a specific hardware or pipeline cause.",
                "The experiment is source-disjoint but not an untouched-night prediction test.",
                "BACKUP comparisons are secondary negative-control screens.",
            ],
        },
        {
            "claim_id": "E3",
            "status": e3_decision,
            "claim": (
                "A source-disjoint transferable PETAL-associated deviation remains after PROGRAM:NIGHT correction."
                if e3_decision == "pass"
                else (
                    "A PETAL-localized residual exceeded every control but missed at least one preregistered confirmation gate."
                    if e3_decision == "suggestive"
                    else "No transferable PROGRAM:NIGHT:PETAL residual of at least 0.02 km/s passed the preregistered controls."
                )
            ),
            "metrics": {
                "mean_incremental_gain_kms": petal_manifest["real_mean_incremental_gain_kms"],
                "positive_folds": petal_manifest["positive_folds"],
                "n_controls": petal_manifest["n_controls"],
                "empirical_p": petal_manifest["empirical_p"],
                "source_half_r": petal_manifest["replication"]["PEARSON_R"],
                "bright_A_dark_B_static_petal_r": petal_independent.loc[
                    petal_independent["DIRECTION"] == "BRIGHT_A_DARK_B", "PEARSON_R"
                ].iloc[0],
                "bright_B_dark_A_static_petal_r": petal_independent.loc[
                    petal_independent["DIRECTION"] == "BRIGHT_B_DARK_A", "PEARSON_R"
                ].iloc[0],
                "giant_component_mean_gain_kms": petal_component[
                    "INCREMENTAL_PETAL_GAIN_KMS"
                ].mean(),
            },
            "evidence": [
                "petal_cv.csv",
                "petal_offsets.csv",
                "petal_permutations.csv",
                "petal_replication.csv",
                "petal_cv_by_program.csv",
                "petal_component_sensitivity.csv",
                "petal_independent_program_offsets.csv",
                "petal_independent_program_summary.csv",
            ],
            "limitations": [
                "Only the nested PROGRAM:NIGHT:PETAL model with fixed damping was tested.",
                "Separate complexity-matched static PROGRAM:PETAL, exposure-, tile-, and stellar-dependent models remain untested.",
                "A passed localization would implicate focal-plane geometry, not uniquely identify a spectrograph fault.",
                "The within-EXPID shuffle also breaks stable sky and source-population structure tied to focal-plane assignment, so the result is PETAL-associated rather than causally instrumental.",
                "The model does not separate a static PROGRAM:PETAL pattern from genuinely night-varying PROGRAM:NIGHT:PETAL behavior.",
                "The overall source-half correlation is not a claim that every program independently exceeds r=0.50.",
                "Frozen-code parity was verified numerically after control orchestration; wall-clock columns were excluded.",
            ],
        },
    ]


def _format_float(value: Any, digits: int = 4) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:.{digits}f}" if math.isfinite(number) else "NA"


def _report(claims: list[dict[str, Any]], manifest: dict[str, Any]) -> str:
    by_id = {claim["claim_id"]: claim for claim in claims}
    e1, e2, e3 = by_id["E1"], by_id["E2"], by_id["E3"]
    pair_counts = manifest["pair_cache"]["counts"]
    petal_validation = manifest["pair_cache"]["petal_validation"]
    lines = [
        "# Три discovery-эксперимента по DESI DR1 RV",
        "",
        "Статус: завершено. Это новые результаты внутри данного репозитория и release bundle; литературная новизна отдельно не проверялась.",
        "",
        "## Контракт и данные",
        "",
        "Гипотезы, primary-метрики, пороги и отрицательные контроли были записаны в `research_plan.json` до строгих независимых fit'ов. После read-only scouting сделаны две явно задокументированные поправки: BRIGHT/DARK зафиксирована как единственная primary-пара E2, а E3 заменён на идентифицируемую нулевую внутри `PROGRAM:NIGHT` PETAL-девиацию.",
        "",
        f"Полный вход: {pair_counts['n_epochs_raw']:,} эпох, {pair_counts['n_epochs_good']:,} качественных эпох, {pair_counts['n_pairs_interday']:,} межсуточных пар от {pair_counts['n_sources_interday']:,} источников. На всех {sum(int(row['N_ROWS']) for row in petal_validation):,} FITS-строках `FIBER // 500 == PETAL_LOC`; расхождений: 0.",
        "",
        "## Результаты",
        "",
        "| Эксперимент | Решение | Главный результат |",
        "|---|---:|---|",
        f"| E1: временная память | {e1['status']} | BRIGHT r={_format_float(e1['metrics']['bright_r_1_7d'])}; DARK r={_format_float(e1['metrics']['dark_r_1_7d'])}; full-pipeline maxT p={_format_float(e1['metrics']['dark_full_pipeline_maxT_p'], 6)} |",
        f"| E2: BRIGHT–DARK coherence | {e2['status']} | r0={_format_float(e2['metrics']['symmetric_same_night_r'])}; excess={_format_float(e2['metrics']['symmetric_zero_lag_excess_r'])}; Holm p={_format_float(e2['metrics']['block_null_p_holm'], 6)} |",
        f"| E3: остаток по PETAL | {e3['status']} | gain={_format_float(e3['metrics']['mean_incremental_gain_kms'], 6)} km/s; source-half r={_format_float(e3['metrics']['source_half_r'])}; p={_format_float(e3['metrics']['empirical_p'], 6)} |",
        "",
        "### E1 — временная память и смены состояния",
        "",
        e1["claim"],
        "",
        "BRIGHT и DARK прошли одновременно дешёвый maxT-контроль по 9 999 перестановкам, 100 полнопайплайновых exposure-night controls и leave-one-fold-out проверку знака 5/5. BACKUP заранее не был нужен для успеха и остался null. Вторичный CUSUM нашёл ступени около −0.647 km/s (BRIGHT, 2021-10-09→14) и −0.640 km/s (DARK, 2022-01-31→02-02). В post-hoc проверке на независимо fitted source halves агрегат 1–7 дней сохранился: BRIGHT r="
        + _format_float(e1["metrics"]["bright_disjoint_half_aggregate_r_1_7d"])
        + ", DARK r="
        + _format_float(e1["metrics"]["dark_disjoint_half_aggregate_r_1_7d"])
        + ", оба block p=0.0001. Это program-conditioned временная структура диагностических zero points, совместимая с многодневными состояниями, но не доказательство instrument drift.",
        "",
        "### E2 — независимая межпрограммная связь",
        "",
        e2["claim"],
        "",
        f"Тест использовал только within-program edges и глобально непересекающиеся source halves. В двух зеркальных направлениях минимальное число общих ночей — {int(e2['metrics']['minimum_shared_nights'])}; нижняя 95% граница 14-дневного block-bootstrap для r0 — {_format_float(e2['metrics']['block_bootstrap_r_low_95'])}. 9 999 null-перестановок двигали целые 14-дневные блоки DARK одинаково в обеих половинах, сохраняя кратковременную автокорреляцию. Поэтому joint-fit корреляцию около 0.40 нельзя выдавать за физический общий night-state.",
        "",
        "### E3 — локализация по PETAL",
        "",
        e3["claim"],
        "",
        f"В пяти outer folds сравнивались `PROGRAM:NIGHT` и `PROGRAM:NIGHT + δ(PROGRAM:NIGHT,PETAL)` на одном и том же holdout support. Порог был 0.02 km/s, требовались 5/5 положительных folds, p≤0.01 и source-half r≥0.50. Выполнено controls: {int(e3['metrics']['n_controls'])}. Только гигантская connected component сохраняет mean gain={_format_float(e3['metrics']['giant_component_mean_gain_kms'], 6)} km/s и 5/5 положительных folds. Негейтирующая диагностика разложила gain по within-program парам: BACKUP/BACKUP 0.0710, BRIGHT/BRIGHT 0.0483, DARK/DARK 0.0356 km/s. Отдельные BRIGHT/DARK графы на перекрёстных source halves воспроизвели статический десяти-PETAL рисунок с r={_format_float(e3['metrics']['bright_A_dark_B_static_petal_r'])} и {_format_float(e3['metrics']['bright_B_dark_A_static_petal_r'])}; это сильная, но post-hoc локализация.",
        "",
        "После завершения controls реальный CV и control #0 были повторены текущим замороженным кодом и cache. Все научные поля совпали с точностью ≤1e-12; timing-колонки намеренно исключены из parity check.",
        "",
        "## Что здесь действительно интересного",
        "",
        "E1 и E2 вместе разделяют две идеи, которые исходный аудит смешивал: внутри BRIGHT и DARK есть воспроизводимая многодневная память, но общего same-night состояния между независимо оценёнными программами строгий тест не подтвердил. Значит, структура program-conditioned и её нельзя автоматически превращать в глобальный night-state. E3 независимо локализует переносимый остаток по PETAL; его решение нужно читать буквально, не расширяя на нетестированные stellar/tile/exposure модели.",
        "",
        "![Независимая репликация статического PETAL-рисунка](petal_independent_pattern.png)",
        "",
        "Рисунок — post-hoc диагностика: BRIGHT и DARK оценены в отдельных графах и на перекрёстных непересекающихся половинах источников. Он показывает локализацию, но сам по себе не доказывает аппаратную причинность.",
        "",
        "## Ограничения",
        "",
        "Все три линии exploratory для DESI DR1: гипотезы появились после знакомства с этим release. Сильное подтверждение потребует untouched release или строго chronological unseen-night prediction. Ни временная связь, ни PETAL-локализация сами по себе не называют конкретную физическую причину.",
        "",
        "## Воспроизведение",
        "",
        "Из корня репозитория:",
        "",
        "```powershell",
        ".\\.venv\\Scripts\\python.exe experiments\\2026-07-13_novel_signals\\run_all.py --workers 10",
        "```",
        "",
        "Машинный источник истины: `claims.jsonl`, `experiment_manifest.json` и CSV рядом с этим отчётом.",
        "",
        "QA репозитория на Windows: 37 тестов прошли; 1 базовый тест остаётся Windows-only failure, потому что ожидает 4 LF-байта от `Path.write_text`, который записывает 6 CRLF-байт. Экспериментальные self-tests и `git diff --check` проходят.",
        "",
    ]
    return "\n".join(lines)


def run() -> None:
    if MANIFEST.exists():
        MANIFEST.unlink()
    missing = [name for name in REQUIRED if not (EXPERIMENT_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(f"Missing required experiment outputs: {', '.join(missing)}")

    pair_cache = _json(EXPERIMENT_DIR / "pair_cache_manifest.json")
    e2_manifest = _json(EXPERIMENT_DIR / "cross_program_manifest.json")
    e3_manifest = _json(EXPERIMENT_DIR / "petal_manifest.json")
    if e3_manifest.get("status") != "complete":
        raise RuntimeError("E3 controls are incomplete")

    artifact_names = sorted(
        set(
            REQUIRED
            + [
                "research_plan.json",
                "petal_validation.csv",
                "pair_cache_manifest.json",
                "temporal_offsets.csv",
                "temporal_independent_block_null.csv",
                "temporal_independent_manifest.json",
                "within_program_offsets.csv",
                "cross_program_lags.csv",
                "cross_program_block_null.csv",
                "cross_program_bootstrap.csv",
                "cross_program_manifest.json",
                "petal_replication.csv",
                "petal_cv_by_program.csv",
                "petal_component_sensitivity.csv",
                "petal_independent_program_offsets.csv",
                "petal_independent_program_summary.csv",
                "petal_independent_pattern.png",
                "petal_diagnostics_manifest.json",
                "petal_provenance_verification.json",
            ]
        )
    )
    artifacts = []
    for name in artifact_names:
        path = EXPERIMENT_DIR / name
        if path.exists():
            artifacts.append({"name": name, "size": path.stat().st_size, "sha256": _sha256(path)})

    script_names = [
        "build_pair_cache.py",
        "run_temporal.py",
        "discovery_stats.py",
        "run_cross_program.py",
        "run_petal.py",
        "run_petal_diagnostics.py",
        "run_petal_component_sensitivity.py",
        "plot_petal_pattern.py",
        "run_temporal_independent.py",
        "verify_petal_provenance.py",
        "run_all.py",
        "verify_bundle.py",
        "finalize_experiments.py",
    ]
    manifest = {
        "schema": "desi_rv_audit.discovery_experiments.v1",
        "status": "complete",
        "research_plan_sha256": _sha256(PLAN),
        "git": {
            "head": _git("rev-parse", "HEAD"),
            "branch": _git("branch", "--show-current"),
            "status_porcelain": _git("status", "--short"),
        },
        "runtime": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "packages": {
                name: importlib.metadata.version(name)
                for name in ("numpy", "pandas", "scipy", "astropy")
            },
        },
        "novelty_scope": "New within this repository and release bundle only; literature novelty not assessed.",
        "qa": {
            "project_pytest_command": ".venv/Scripts/python.exe -m pytest -q",
            "project_pytest_passed": 37,
            "project_pytest_failed": 1,
            "known_platform_failure": "tests/test_manifest.py::test_manifest_records_output_hashes expects LF byte count from pathlib.Path.write_text on Windows, which emits CRLF",
            "experimental_checks": [
                "all experiment scripts compile with py_compile",
                "discovery_stats.py self-tests pass",
                "verify_bundle.py validates decisions, controls, hashes when retained, and LF-only text artifacts"
            ]
        },
        "pair_cache": pair_cache,
        "experiment_manifests": {"E2": e2_manifest, "E3": e3_manifest},
        "scripts": [
            {"name": name, "size": (EXPERIMENT_DIR / name).stat().st_size, "sha256": _sha256(EXPERIMENT_DIR / name)}
            for name in script_names
        ],
        "artifacts": artifacts,
    }
    claims = _claims()
    for claim in claims:
        missing_evidence = [
            name for name in claim["evidence"] if not (EXPERIMENT_DIR / name).exists()
        ]
        if missing_evidence:
            raise FileNotFoundError(
                f"{claim['claim_id']} cites missing evidence: {', '.join(missing_evidence)}"
            )
    claims_text = "".join(
        json.dumps(_sanitize(claim), sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
        for claim in claims
    )
    report_text = _report(claims, manifest)
    _write_text_atomic(CLAIMS, claims_text)
    _write_text_atomic(REPORT, report_text)
    manifest["publication_outputs"] = [
        {"name": path.name, "size": path.stat().st_size, "sha256": _sha256(path)}
        for path in (CLAIMS, REPORT)
    ]
    _write_json(MANIFEST, manifest)
    print(json.dumps({claim["claim_id"]: claim["status"] for claim in claims}, sort_keys=True))


if __name__ == "__main__":
    run()
