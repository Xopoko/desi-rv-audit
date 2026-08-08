"""Build, execute, and validate the scientific explanation notebooks.

Run from any directory; notebook kernels always execute with the repository root
as their working directory so every input path remains repository-relative.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath
from textwrap import dedent
from typing import Any, Callable, Sequence

import nbformat
from nbclient import NotebookClient
from nbformat import NotebookNode


GENERATOR_VERSION = "1.0.0"
SCRIPT_PATH = Path(__file__).resolve()
REPO_ROOT = SCRIPT_PATH.parents[2]
MANIFEST_PATH = REPO_ROOT / "explanation" / "manifest.json"
SCRIPT_RELPATH = "explanation/tools/build_notebooks.py"

BASELINE_INPUTS = (
    "reports/program_night_artifacts/summary.csv",
    "reports/program_night_artifacts/permutation_summary.csv",
    "reports/program_night_artifacts/by_program.csv",
    "reports/program_night_artifacts/reproducibility.csv",
    "reports/program_night_artifacts/reproducibility_by_program.csv",
    "reports/program_night_artifacts/pair_cap_sensitivity.csv",
)

DISCOVERY_INPUTS = (
    "experiments/2026-07-13_novel_signals/temporal_persistence.csv",
    "experiments/2026-07-13_novel_signals/cross_program_coherence.csv",
    "experiments/2026-07-13_novel_signals/petal_cv.csv",
    "experiments/2026-07-13_novel_signals/petal_permutations.csv",
    "experiments/2026-07-13_novel_signals/petal_replication.csv",
    "experiments/2026-07-13_novel_signals/petal_independent_program_offsets.csv",
    "experiments/2026-07-13_novel_signals/petal_independent_program_summary.csv",
)

NOTEBOOK_DEFINITIONS: dict[str, dict[str, Any]] = {
    "baseline-evidence": {
        "claims": ["BASELINE-NIGHT", "BASELINE-REPLICATION"],
        "inputs": BASELINE_INPUTS,
    },
    "discovery-evidence": {
        "claims": ["E1-TEMPORAL", "E2-COHERENCE-NULL", "E3-PETAL"],
        "inputs": DISCOVERY_INPUTS,
    },
}

EXPLANATION_METADATA_KEYS = {
    "generator_version",
    "inputs",
    "claims",
    "executed",
}


class NotebookBuildError(RuntimeError):
    """Raised when the manifest cannot safely drive notebook generation."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _generator_stamp() -> str:
    """Tie committed notebooks to both the API version and exact generator."""
    return f"{GENERATOR_VERSION}+sha256.{_sha256(SCRIPT_PATH)[:12]}"


def _repo_relative_path(raw_path: str, label: str) -> str:
    """Return normalized POSIX form only for paths contained by the repository."""
    posix_path = PurePosixPath(raw_path.replace("\\", "/"))
    windows_path = PureWindowsPath(raw_path)
    if posix_path.is_absolute() or windows_path.is_absolute() or windows_path.drive:
        raise NotebookBuildError(f"{label} must be repository-relative: {raw_path!r}")
    candidate = (REPO_ROOT / Path(*posix_path.parts)).resolve()
    try:
        relative = candidate.relative_to(REPO_ROOT)
    except ValueError as exc:
        raise NotebookBuildError(f"{label} escapes the repository: {raw_path!r}") from exc
    return relative.as_posix()


def _input_hashes(inputs: Sequence[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for relative_path in inputs:
        normalized = _repo_relative_path(relative_path, "Notebook input")
        source = REPO_ROOT / Path(normalized)
        if not source.is_file():
            raise NotebookBuildError(f"Missing notebook input: {normalized}")
        hashes[normalized] = _sha256(source)
    return hashes


def _load_manifest_specs() -> list[dict[str, Any]]:
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise NotebookBuildError(f"Cannot read {MANIFEST_PATH}: {exc}") from exc

    notebook_entries = manifest.get("notebooks")
    if not isinstance(notebook_entries, list):
        raise NotebookBuildError("explanation/manifest.json needs a notebooks list")

    entries_by_id: dict[str, dict[str, Any]] = {}
    for entry in notebook_entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            raise NotebookBuildError("Every notebook manifest entry needs a string id")
        entries_by_id[entry["id"]] = entry

    expected_ids = set(NOTEBOOK_DEFINITIONS)
    actual_ids = set(entries_by_id)
    if actual_ids != expected_ids:
        raise NotebookBuildError(
            "Notebook manifest ids differ from the generator contract: "
            f"expected {sorted(expected_ids)}, found {sorted(actual_ids)}"
        )

    specs: list[dict[str, Any]] = []
    for notebook_id, definition in NOTEBOOK_DEFINITIONS.items():
        entry = entries_by_id[notebook_id]
        path = entry.get("path")
        generator = entry.get("generator")
        claims = entry.get("claims")
        if not isinstance(path, str) or not path.endswith(".ipynb"):
            raise NotebookBuildError(f"Notebook {notebook_id} has an invalid path")
        normalized_path = _repo_relative_path(path, f"Notebook {notebook_id} path")
        if generator != SCRIPT_RELPATH:
            raise NotebookBuildError(
                f"Notebook {notebook_id} must name {SCRIPT_RELPATH} as generator"
            )
        if claims != definition["claims"]:
            raise NotebookBuildError(
                f"Notebook {notebook_id} claims must be {definition['claims']!r}"
            )
        specs.append(
            {
                "id": notebook_id,
                "path": normalized_path,
                "claims": list(definition["claims"]),
                "inputs": tuple(definition["inputs"]),
            }
        )
    return specs


def _markdown(cell_id: str, source: str) -> NotebookNode:
    cell = nbformat.v4.new_markdown_cell(dedent(source).strip() + "\n")
    cell["id"] = cell_id
    return cell


def _code(cell_id: str, source: str) -> NotebookNode:
    cell = nbformat.v4.new_code_cell(dedent(source).strip() + "\n")
    cell["id"] = cell_id
    return cell


def _new_notebook(
    *, cells: list[NotebookNode], claims: Sequence[str], inputs: Sequence[str]
) -> NotebookNode:
    return nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python"},
            "explanation": {
                "generator_version": _generator_stamp(),
                "inputs": _input_hashes(inputs),
                "claims": list(claims),
                "executed": False,
            },
        },
    )


def _build_baseline_notebook(claims: Sequence[str]) -> NotebookNode:
    cells = [
        _markdown(
            "baseline-title",
            """
            # Baseline evidence: real observing nights versus shuffled controls

            This executable walkthrough asks whether a program-and-night label
            captures repeatable structure in DESI stellar radial-velocity
            differences. It uses only the compact CSV files committed to this
            repository: no network access and no raw FITS files.

            ## tl;dr

            - Across five held-out folds, the mean raw robust-scatter reduction
              is **0.494756 km/s**, from **3.651302** to **3.156547 km/s**
              (**13.55%**).
            - The mean reductions from **100 shuffled-night controls** range
              from **0.071803** to **0.293896 km/s**. None reaches the real
              result, so the add-one empirical p-value is **1/101 = 0.009901**.
            - Two disjoint source halves recover **483** common
              PROGRAM:NIGHT offsets with Pearson correlation **r = 0.98026**
              (slope **1.00157**).
            - **Source-disjoint means different stars are used for training and
              testing on nights represented in the data.** It does not mean the
              model predicts a completely new observing night.

            These checks support a transferable night-associated diagnostic.
            They do not identify a physical cause and do not define an official
            catalogue correction.
            """,
        ),
        _markdown(
            "baseline-context",
            """
            ## Context & Methods

            A star observed more than once should give compatible radial
            velocities after accounting for uncertainty. Here, *robust scatter*
            is a width summary designed to be less dominated by extreme pairs
            than an ordinary standard deviation. A positive gain means the
            held-out differences became narrower after applying offsets learned
            from other sources.

            A *fold* is one train/test split. The source split prevents the same
            star from teaching and testing the model. The nights, however, are
            represented on both sides; this is transfer to new stars on known
            nights, not forecasting of unseen nights.

            A shuffled control reruns the pipeline after breaking the link
            between exposures and their real nights. The empirical p-value uses
            the conservative add-one rule
            `(controls at least as large as real + 1) / (number of controls + 1)`.

            ### Key Assumptions

            - The committed summaries faithfully represent the recorded audit
              run and use the same units: kilometres per second (km/s).
            - Folds are averaged equally, matching the claim ledger.
            - The permutation comparison is against each control's mean across
              the same five folds.
            """,
        ),
        _markdown(
            "baseline-data",
            """
            ## Data

            `summary.csv` contains the five real held-out folds;
            `permutation_summary.csv` contains 100 shuffled controls times five
            folds. The remaining files provide program-pair context,
            split-half reproducibility, and pair-cap sensitivity. The next cell
            lists every input and row count so the data path is visible.
            """,
        ),
        _code(
            "baseline-load",
            """
            from pathlib import Path
            import math

            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd

            def require(condition, message):
                if not bool(condition):
                    raise RuntimeError(message)

            ROOT = Path.cwd().resolve()
            require((ROOT / "explanation" / "manifest.json").is_file(),
                "Run this notebook with the repository root as the working directory."
            )

            INPUTS = {
                "summary": "reports/program_night_artifacts/summary.csv",
                "permutations": "reports/program_night_artifacts/permutation_summary.csv",
                "by_program": "reports/program_night_artifacts/by_program.csv",
                "reproducibility": "reports/program_night_artifacts/reproducibility.csv",
                "reproducibility_by_program": "reports/program_night_artifacts/reproducibility_by_program.csv",
                "pair_cap_sensitivity": "reports/program_night_artifacts/pair_cap_sensitivity.csv",
            }
            datasets = {
                name: pd.read_csv(ROOT / relative_path)
                for name, relative_path in INPUTS.items()
            }
            pd.DataFrame(
                {
                    "input": list(INPUTS),
                    "rows": [len(datasets[name]) for name in INPUTS],
                    "repository path": list(INPUTS.values()),
                }
            )
            """,
        ),
        _markdown(
            "baseline-results",
            """
            ## Results

            ### 1. Recompute the headline comparison

            The real gain is `BEFORE_RAW_WIDTH_KMS - AFTER_RAW_WIDTH_KMS`
            within each fold. Each shuffled control is reduced to the same
            five-fold mean before it is compared with the real mean. Explicit
            checks below are deliberate claim guards: execution stops if a committed
            input no longer supports the documented numbers.
            """,
        ),
        _code(
            "baseline-headline",
            """
            summary = datasets["summary"].copy()
            permutations = datasets["permutations"].copy()
            reproducibility = datasets["reproducibility"].copy()
            reproducibility_by_program = datasets["reproducibility_by_program"].copy()
            pair_cap_sensitivity = datasets["pair_cap_sensitivity"].copy()

            summary["GAIN_KMS"] = (
                summary["BEFORE_RAW_WIDTH_KMS"] - summary["AFTER_RAW_WIDTH_KMS"]
            )
            real_mean_before = summary["BEFORE_RAW_WIDTH_KMS"].mean()
            real_mean_after = summary["AFTER_RAW_WIDTH_KMS"].mean()
            real_mean_gain = summary["GAIN_KMS"].mean()
            real_gain_percent = 100.0 * real_mean_gain / real_mean_before

            permutations["GAIN_KMS"] = (
                permutations["BEFORE_RAW_WIDTH_KMS"]
                - permutations["AFTER_RAW_WIDTH_KMS"]
            )
            control_mean_gains = permutations.groupby(
                "PERMUTATION", sort=True
            )["GAIN_KMS"].mean()
            control_exceedances = int((control_mean_gains >= real_mean_gain).sum())
            add_one_p = (control_exceedances + 1) / (len(control_mean_gains) + 1)

            replication = reproducibility.iloc[0]
            replication_all = reproducibility_by_program.loc[
                reproducibility_by_program["SCOPE"] == "ALL"
            ].iloc[0]
            default_pair_cap = pair_cap_sensitivity.loc[
                pair_cap_sensitivity["MAX_PAIRS_PER_SOURCE"] == 20
            ].iloc[0]

            require(len(summary) == 5, "Expected five baseline folds")
            require(math.isclose(real_mean_gain, 0.49475552781884735, abs_tol=1e-12), "Baseline mean gain changed")
            require(math.isclose(real_mean_before, 3.6513022349357853, abs_tol=1e-12), "Baseline before-width changed")
            require(math.isclose(real_mean_after, 3.156546707116938, abs_tol=1e-12), "Baseline after-width changed")
            require(len(control_mean_gains) == 100, "Expected 100 baseline controls")
            require(math.isclose(control_mean_gains.min(), 0.07180256357435093, abs_tol=1e-12), "Baseline control minimum changed")
            require(math.isclose(control_mean_gains.max(), 0.2938955956991919, abs_tol=1e-12), "Baseline control maximum changed")
            require(control_exceedances == 0, "A baseline control now reaches the real result")
            require(math.isclose(add_one_p, 1 / 101, abs_tol=1e-15), "Baseline empirical p-value changed")
            require(int(replication["N_COMMON_LABELS"]) == 483, "Common split-half label count changed")
            require(math.isclose(replication["OFFSET_CORRELATION"], 0.9802602841058295, abs_tol=1e-12), "Split-half correlation changed")
            require(math.isclose(replication["OFFSET_SLOPE_B_ON_A"], 1.0015687836666636, abs_tol=1e-12), "Split-half slope changed")
            require(math.isclose(replication_all["OFFSET_CORRELATION"], replication["OFFSET_CORRELATION"], abs_tol=1e-12), "Reproducibility summaries disagree")
            require(math.isclose(default_pair_cap["RAW_WIDTH_DELTA_KMS"], real_mean_gain, abs_tol=1e-12), "Default pair-cap result changed")

            pd.DataFrame(
                {
                    "quantity": [
                        "mean before",
                        "mean after",
                        "mean gain",
                        "relative gain",
                        "shuffled-control range",
                        "controls >= real",
                        "add-one empirical p",
                        "source-half correlation",
                    ],
                    "recomputed value": [
                        f"{real_mean_before:.6f} km/s",
                        f"{real_mean_after:.6f} km/s",
                        f"{real_mean_gain:.6f} km/s",
                        f"{real_gain_percent:.2f}%",
                        f"{control_mean_gains.min():.6f} to {control_mean_gains.max():.6f} km/s",
                        f"{control_exceedances} of {len(control_mean_gains)}",
                        f"{add_one_p:.6f} (1/101)",
                        f"{replication['OFFSET_CORRELATION']:.5f}",
                    ],
                }
            )
            """,
        ),
        _code(
            "baseline-control-plot",
            """
            fig, ax = plt.subplots(figsize=(8, 4.4))
            ax.hist(
                control_mean_gains,
                bins=14,
                color="#8FB9A8",
                edgecolor="white",
                label="100 shuffled-night controls",
            )
            ax.axvline(
                real_mean_gain,
                color="#C44E52",
                linewidth=2.5,
                label=f"real nights: {real_mean_gain:.6f} km/s",
            )
            ax.set(
                title="The real five-fold gain exceeds every shuffled-night control",
                xlabel="Mean robust-scatter reduction (km/s; larger is better)",
                ylabel="Number of controls",
            )
            ax.grid(axis="y", alpha=0.25)
            ax.legend(frameon=False)
            fig.tight_layout()
            plt.show()
            """,
        ),
        _markdown(
            "baseline-control-reading",
            """
            The controls can still show positive gains because a flexible fit
            can absorb some chance structure. The relevant result is therefore
            not “controls equal zero”; it is that the real-night gain lies well
            beyond the complete recorded control range. With a finite control
            set, the add-one rule reports `1/101`, never zero.

            ### 2. Descriptive context and sensitivity

            The left panel below describes which program pairs contribute more
            or less gain; it is not a set of separately preregistered claims.
            The right panel checks that changing the maximum number of epoch
            pairs contributed by one source leaves the aggregate result near
            0.5 km/s.
            """,
        ),
        _code(
            "baseline-context-plot",
            """
            by_program = datasets["by_program"].copy()
            by_program["GAIN_KMS"] = (
                by_program["RAW_WIDTH_BEFORE_KMS"]
                - by_program["RAW_WIDTH_AFTER_KMS"]
            )
            program_pair_gain = (
                by_program.groupby("PROGRAM_PAIR", sort=False)["GAIN_KMS"]
                .mean()
                .sort_values()
            )
            cap_view = pair_cap_sensitivity.sort_values("MAX_PAIRS_PER_SOURCE")

            fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
            axes[0].barh(
                program_pair_gain.index,
                program_pair_gain.values,
                color="#4C78A8",
            )
            axes[0].axvline(0, color="#555555", linewidth=0.8)
            axes[0].set(
                title="Mean gain by program pair (descriptive)",
                xlabel="Robust-scatter reduction (km/s)",
                ylabel="Program pair",
            )
            axes[0].grid(axis="x", alpha=0.2)

            axes[1].plot(
                cap_view["MAX_PAIRS_PER_SOURCE"],
                cap_view["RAW_WIDTH_DELTA_KMS"],
                marker="o",
                color="#F28E2B",
                linewidth=2,
            )
            axes[1].set(
                title="Aggregate gain is stable across pair caps",
                xlabel="Maximum epoch pairs per source",
                ylabel="Robust-scatter reduction (km/s)",
                xticks=cap_view["MAX_PAIRS_PER_SOURCE"].tolist(),
            )
            axes[1].grid(alpha=0.2)
            fig.tight_layout()
            plt.show()
            """,
        ),
        _code(
            "baseline-replication-table",
            """
            replication_view = reproducibility_by_program.loc[
                :,
                [
                    "SCOPE",
                    "N_COMMON_LABELS",
                    "OFFSET_CORRELATION",
                    "OFFSET_SLOPE_B_ON_A",
                    "MEDIAN_ABS_DIFF_KMS",
                ],
            ].copy()
            replication_view["OFFSET_CORRELATION"] = replication_view[
                "OFFSET_CORRELATION"
            ].round(5)
            replication_view["OFFSET_SLOPE_B_ON_A"] = replication_view[
                "OFFSET_SLOPE_B_ON_A"
            ].round(5)
            replication_view["MEDIAN_ABS_DIFF_KMS"] = replication_view[
                "MEDIAN_ABS_DIFF_KMS"
            ].round(5)
            replication_view
            """,
        ),
        _markdown(
            "baseline-takeaways",
            """
            ## Takeaways

            1. **BASELINE-NIGHT is supported:** the real mean gain is larger
               than all 100 shuffled-night controls under the recorded design.
            2. **BASELINE-REPLICATION is supported:** separately estimated
               disjoint-source-half offsets agree closely (`r = 0.98026`, slope
               near 1).
            3. The pair-cap check shows similar aggregate gains across the three
               committed caps, reducing concern that a few heavily repeated
               stars alone set the result.
            4. The boundary matters: these are relative diagnostic offsets for
               represented nights. They are neither a causal diagnosis nor a
               ready-to-apply DESI correction.
            """,
        ),
    ]
    return _new_notebook(cells=cells, claims=claims, inputs=BASELINE_INPUTS)


def _build_discovery_notebook(claims: Sequence[str]) -> NotebookNode:
    cells = [
        _markdown(
            "discovery-title",
            """
            # Discovery evidence: time persistence, cross-program null, and PETAL localization

            This executable walkthrough checks the three follow-up experiment
            lines using only compact committed CSVs. It makes no network calls
            and does not require raw DESI FITS files.

            ## tl;dr

            - **E1-TEMPORAL — pass:** successive supported nights with
              1-to-7-day gaps have Pearson correlations of **0.33759 for
              BRIGHT** and **0.61162 for DARK**.
            - **E2-COHERENCE-NULL — null:** the source-disjoint BRIGHT–DARK
              symmetric same-night correlation is **0.01003**, with
              Holm-adjusted **p = 0.4614**.
            - **E3-PETAL — pass:** the mean incremental gain beyond the
              program-night model is **0.058141 km/s**, all **5/5 folds** are
              positive, split-half reproducibility is **r = 0.83133**, and none of
              99 controls reaches the real gain. The add-one p-value is
              **1/100 = 0.01**.

            Persistence, a null cross-program test, and PETAL localization are
            statistical patterns. None establishes an instrument mechanism or
            hardware fault.
            """,
        ),
        _markdown(
            "discovery-context",
            """
            ## Context & Methods

            E1 asks whether a diagnostic night offset resembles the next
            supported night when their gap is 1–7 days. E2 asks a stricter
            question: after source
            halves and within-program graphs are separated, do BRIGHT and DARK
            share a same-calendar-night state? E3 asks whether PETAL-associated
            structure adds held-out predictive value beyond program and night.

            A Pearson correlation `r` ranges from -1 to 1. Values farther from
            zero indicate a stronger linear pattern, but correlation alone does
            not identify its cause. A *null* outcome means this declared test
            did not support the proposed coherence; it does not prove that every
            possible shared component is exactly zero.

            ### Key Assumptions

            - The summary rows retain the preregistered grouping and correction
              methods from the experiment bundle.
            - For E2, two directional correlations are combined with Fisher-z
              weights `n - 3`, then three pairwise p-values receive Holm's
              multiple-testing adjustment.
            - For E3, folds are averaged equally and the empirical p-value uses
              the same add-one rule as the baseline notebook.
            """,
        ),
        _markdown(
            "discovery-data",
            """
            ## Data

            The temporal and coherence files hold the E1/E2 summary rows. E3
            uses five held-out folds, 99 permutation controls, one split-half
            reproducibility summary, and separate program/half PETAL offsets.
            Every committed input is loaded below and its row count is shown.
            """,
        ),
        _code(
            "discovery-load",
            """
            from pathlib import Path
            import math

            import matplotlib.pyplot as plt
            import numpy as np
            import pandas as pd

            def require(condition, message):
                if not bool(condition):
                    raise RuntimeError(message)

            ROOT = Path.cwd().resolve()
            require((ROOT / "explanation" / "manifest.json").is_file(),
                "Run this notebook with the repository root as the working directory."
            )

            INPUTS = {
                "temporal": "experiments/2026-07-13_novel_signals/temporal_persistence.csv",
                "coherence": "experiments/2026-07-13_novel_signals/cross_program_coherence.csv",
                "petal_cv": "experiments/2026-07-13_novel_signals/petal_cv.csv",
                "petal_permutations": "experiments/2026-07-13_novel_signals/petal_permutations.csv",
                "petal_replication": "experiments/2026-07-13_novel_signals/petal_replication.csv",
                "petal_offsets": "experiments/2026-07-13_novel_signals/petal_independent_program_offsets.csv",
                "petal_program_summary": "experiments/2026-07-13_novel_signals/petal_independent_program_summary.csv",
            }
            datasets = {
                name: pd.read_csv(ROOT / relative_path)
                for name, relative_path in INPUTS.items()
            }
            pd.DataFrame(
                {
                    "input": list(INPUTS),
                    "rows": [len(datasets[name]) for name in INPUTS],
                    "repository path": list(INPUTS.values()),
                }
            )
            """,
        ),
        _markdown(
            "e1-heading",
            """
            ## Results

            ### 1. E1 — temporal persistence within programs

            BRIGHT and DARK meet the recorded E1 scope gates. BACKUP does not,
            which is useful friction against an overbroad “every program has
            memory” interpretation. Explicit checks protect the two claim-ledger
            correlations and the full-pipeline maxT result.
            """,
        ),
        _code(
            "e1-recompute",
            """
            temporal = datasets["temporal"].copy().set_index("SCOPE")
            bright_r = temporal.loc["BRIGHT", "PEARSON_R_1_7D"]
            dark_r = temporal.loc["DARK", "PEARSON_R_1_7D"]
            bright_maxt_p = temporal.loc["BRIGHT", "FULL_PIPELINE_P_MAXT"]
            dark_maxt_p = temporal.loc["DARK", "FULL_PIPELINE_P_MAXT"]

            require(math.isclose(bright_r, 0.33759141739964144, abs_tol=1e-12), "E1 BRIGHT correlation changed")
            require(math.isclose(dark_r, 0.6116203576747858, abs_tol=1e-12), "E1 DARK correlation changed")
            require(math.isclose(bright_maxt_p, 1 / 101, abs_tol=1e-15), "E1 BRIGHT maxT p-value changed")
            require(math.isclose(dark_maxt_p, 1 / 101, abs_tol=1e-15), "E1 DARK maxT p-value changed")
            require(temporal.loc["BRIGHT", "SCOPE_PASS"], "E1 BRIGHT scope gate no longer passes")
            require(temporal.loc["DARK", "SCOPE_PASS"], "E1 DARK scope gate no longer passes")
            require(temporal.loc["BRIGHT", "E1_DECISION"] == "pass", "E1 decision changed")

            pd.DataFrame(
                {
                    "scope": ["BRIGHT", "DARK"],
                    "Pearson r (successive, 1–7-day gaps)": [bright_r, dark_r],
                    "full-pipeline maxT p": [bright_maxt_p, dark_maxt_p],
                    "scope gate": [
                        temporal.loc["BRIGHT", "SCOPE_PASS"],
                        temporal.loc["DARK", "SCOPE_PASS"],
                    ],
                }
            ).round(6)
            """,
        ),
        _code(
            "e1-plot",
            """
            temporal_plot = temporal.loc[
                ["BACKUP", "BRIGHT", "DARK", "POOLED"], "PEARSON_R_1_7D"
            ]
            temporal_pass = temporal.loc[
                ["BACKUP", "BRIGHT", "DARK", "POOLED"], "SCOPE_PASS"
            ].astype(bool)
            colors = ["#59A14F" if passed else "#BAB0AC" for passed in temporal_pass]

            fig, ax = plt.subplots(figsize=(7.5, 4.4))
            bars = ax.bar(temporal_plot.index, temporal_plot.values, color=colors)
            ax.axhline(0, color="#555555", linewidth=0.8)
            ax.set(
                title="Successive-night correlation for 1–7-day gaps",
                xlabel="Scope",
                ylabel="Pearson correlation r",
            )
            ax.margins(y=0.18)
            ax.grid(axis="y", alpha=0.2)
            for bar, value in zip(bars, temporal_plot.values):
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    value + (0.018 if value >= 0 else -0.035),
                    f"{value:.3f}",
                    ha="center",
                    va="bottom" if value >= 0 else "top",
                )
            fig.tight_layout()
            plt.show()
            """,
        ),
        _markdown(
            "e2-heading",
            """
            ### 2. E2 — the stricter BRIGHT–DARK coherence test is null

            Each direction uses different source halves. The symmetric value is
            recomputed by transforming both correlations to Fisher z, weighting
            by `n - 3`, averaging, and transforming back. Holm's procedure then
            adjusts the three recorded pairwise p-values without assuming the
            primary pair was the only comparison inspected.
            """,
        ),
        _code(
            "e2-recompute",
            """
            coherence = datasets["coherence"].copy()
            primary = coherence.loc[
                (coherence["PROGRAM_P"] == "BRIGHT")
                & (coherence["PROGRAM_Q"] == "DARK")
            ].iloc[0]

            r_ab = primary["R_P_A_Q_B"]
            r_ba = primary["R_P_B_Q_A"]
            n_ab = primary["N_P_A_Q_B"]
            n_ba = primary["N_P_B_Q_A"]
            symmetric_z = (
                (n_ab - 3) * np.arctanh(r_ab)
                + (n_ba - 3) * np.arctanh(r_ba)
            ) / ((n_ab - 3) + (n_ba - 3))
            symmetric_r = np.tanh(symmetric_z)

            def holm_adjust(p_values):
                values = np.asarray(p_values, dtype=float)
                order = np.argsort(values)
                ordered = values[order]
                scaled = (len(values) - np.arange(len(values))) * ordered
                monotone = np.maximum.accumulate(scaled)
                adjusted = np.empty_like(monotone)
                adjusted[order] = np.minimum(monotone, 1.0)
                return adjusted

            holm_values = pd.Series(
                holm_adjust(coherence["BLOCK_NULL_P"]), index=coherence.index
            )
            primary_holm_p = holm_values.loc[primary.name]

            require(math.isclose(symmetric_r, primary["SYMMETRIC_R0"], abs_tol=1e-14), "E2 symmetric correlation does not reproduce")
            require(math.isclose(symmetric_r, 0.0100284072882246, abs_tol=1e-14), "E2 symmetric correlation changed")
            require(math.isclose(primary_holm_p, primary["BLOCK_NULL_P_HOLM"], abs_tol=1e-12), "E2 Holm adjustment does not reproduce")
            require(math.isclose(primary_holm_p, 0.4614, abs_tol=1e-12), "E2 Holm-adjusted p-value changed")
            require(not primary["PASS"], "E2 outcome unexpectedly changed from null")

            pd.DataFrame(
                {
                    "quantity": [
                        "BRIGHT A → DARK B r",
                        "BRIGHT B → DARK A r",
                        "recomputed symmetric r",
                        "raw block-null p",
                        "recomputed Holm p",
                        "declared outcome",
                    ],
                    "value": [
                        f"{r_ab:.6f} (n={int(n_ab)})",
                        f"{r_ba:.6f} (n={int(n_ba)})",
                        f"{symmetric_r:.6f}",
                        f"{primary['BLOCK_NULL_P']:.4f}",
                        f"{primary_holm_p:.4f}",
                        "null / not passed",
                    ],
                }
            )
            """,
        ),
        _markdown(
            "e3-heading",
            """
            ### 3. E3 — incremental PETAL-associated structure

            A PETAL is one of DESI's focal-plane sectors. The real statistic is
            the held-out width reduction after adding PETAL-associated offsets
            to the existing program-night model. A positive value is an
            improvement; every recorded control here is below the real mean.
            """,
        ),
        _code(
            "e3-recompute",
            """
            petal_cv = datasets["petal_cv"].copy()
            petal_controls = datasets["petal_permutations"].copy()
            petal_replication = datasets["petal_replication"].iloc[0]

            fold_gains = petal_cv["INCREMENTAL_PETAL_GAIN_KMS"]
            petal_mean_gain = fold_gains.mean()
            positive_folds = int((fold_gains > 0).sum())
            control_gains = petal_controls["MEAN_INCREMENTAL_GAIN_KMS"]
            petal_exceedances = int((control_gains >= petal_mean_gain).sum())
            petal_add_one_p = (petal_exceedances + 1) / (len(control_gains) + 1)
            petal_replication_r = petal_replication["PEARSON_R"]

            require(len(fold_gains) == 5, "Expected five E3 folds")
            require(math.isclose(petal_mean_gain, 0.05814104905797004, abs_tol=1e-12), "E3 mean gain changed")
            require(positive_folds == 5, "E3 no longer improves all five folds")
            require(math.isclose(petal_replication_r, 0.8313286827891185, abs_tol=1e-12), "E3 split-half correlation changed")
            require(len(control_gains) == 99, "Expected 99 E3 controls")
            require(petal_exceedances == 0, "An E3 control now reaches the real result")
            require(math.isclose(petal_add_one_p, 0.01, abs_tol=1e-15), "E3 empirical p-value changed")

            pd.DataFrame(
                {
                    "quantity": [
                        "mean incremental gain",
                        "positive folds",
                        "source-half Pearson r",
                        "controls >= real",
                        "add-one empirical p",
                    ],
                    "recomputed value": [
                        f"{petal_mean_gain:.6f} km/s",
                        f"{positive_folds}/{len(fold_gains)}",
                        f"{petal_replication_r:.5f}",
                        f"{petal_exceedances} of {len(control_gains)}",
                        f"{petal_add_one_p:.2f} (1/100)",
                    ],
                }
            )
            """,
        ),
        _code(
            "e3-control-plot",
            """
            fig, ax = plt.subplots(figsize=(8, 4.4))
            ax.hist(
                control_gains,
                bins=14,
                color="#B6992D",
                edgecolor="white",
                label="99 PETAL-label controls",
            )
            ax.axvline(
                petal_mean_gain,
                color="#E15759",
                linewidth=2.5,
                label=f"real PETAL gain: {petal_mean_gain:.6f} km/s",
            )
            ax.set(
                title="The real PETAL gain exceeds every recorded control",
                xlabel="Mean incremental gain beyond program-night (km/s)",
                ylabel="Number of controls",
            )
            ax.grid(axis="y", alpha=0.2)
            ax.legend(frameon=False)
            fig.tight_layout()
            plt.show()
            """,
        ),
        _markdown(
            "petal-independent-heading",
            """
            ### 4. Disjoint program/half PETAL patterns

            The final two inputs offer a second descriptive view. For each of
            ten PETALs, compare median offsets from BRIGHT half A with DARK half
            B, then reverse the halves. We recompute the correlations reported
            in the compact summary. This is evidence that the spatial pattern
            transfers; it still does not identify a hardware cause.
            """,
        ),
        _code(
            "petal-independent-plot",
            """
            petal_offsets = datasets["petal_offsets"].copy()
            petal_program_summary = datasets["petal_program_summary"].copy().set_index(
                "DIRECTION"
            )
            petal_pattern = petal_offsets.pivot(
                index="PETAL",
                columns=["PROGRAM", "HALF"],
                values="MEDIAN_OFFSET_KMS",
            ).sort_index()

            directions = [
                ("BRIGHT_A_DARK_B", ("BRIGHT", "A"), ("DARK", "B")),
                ("BRIGHT_B_DARK_A", ("BRIGHT", "B"), ("DARK", "A")),
            ]
            recomputed_directional_r = {}
            for direction, x_key, y_key in directions:
                recomputed_r = np.corrcoef(
                    petal_pattern[x_key], petal_pattern[y_key]
                )[0, 1]
                recomputed_directional_r[direction] = recomputed_r
                require(math.isclose(
                    recomputed_r,
                    petal_program_summary.loc[direction, "PEARSON_R"],
                    abs_tol=1e-12,
                ), f"PETAL directional correlation changed for {direction}")
                require(
                    int(petal_program_summary.loc[direction, "N_PETALS"]) == 10,
                    f"Expected ten PETALs for {direction}",
                )

            fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.6))
            for ax, (direction, x_key, y_key) in zip(axes, directions):
                x = petal_pattern[x_key]
                y = petal_pattern[y_key]
                ax.scatter(x, y, s=55, color="#4E79A7")
                for petal, x_value, y_value in zip(petal_pattern.index, x, y):
                    ax.annotate(
                        str(petal),
                        (x_value, y_value),
                        xytext=(4, 3),
                        textcoords="offset points",
                        fontsize=8,
                    )
                ax.axhline(0, color="#888888", linewidth=0.7)
                ax.axvline(0, color="#888888", linewidth=0.7)
                ax.set(
                    title=f"{direction.replace('_', ' ')}\\nr = {recomputed_directional_r[direction]:.3f}",
                    xlabel=f"{x_key[0]} half {x_key[1]} median offset (km/s)",
                    ylabel=f"{y_key[0]} half {y_key[1]} median offset (km/s)",
                )
                ax.grid(alpha=0.18)
            fig.tight_layout()
            plt.show()
            """,
        ),
        _markdown(
            "discovery-takeaways",
            """
            ## Takeaways

            1. **E1 passes:** successive supported BRIGHT and DARK nights with
               1–7-day gaps show positive persistence under the recorded
               corrected controls, while BACKUP does not.
            2. **E2 remains null:** the strict BRIGHT–DARK symmetric correlation
               is near zero and its Holm-adjusted p-value is 0.4614.
            3. **E3 passes:** PETAL-associated structure adds a smaller but
               consistently positive held-out gain, reproduces across disjoint
               source halves, and exceeds all 99 controls.
            4. These results localize and characterize residual structure. They
               do not show that PETAL hardware is faulty, prove instrument
               drift, or supply an official correction recipe.
            """,
        ),
    ]
    return _new_notebook(cells=cells, claims=claims, inputs=DISCOVERY_INPUTS)


NOTEBOOK_BUILDERS: dict[str, Callable[[Sequence[str]], NotebookNode]] = {
    "baseline-evidence": _build_baseline_notebook,
    "discovery-evidence": _build_discovery_notebook,
}


def _execute_notebook(notebook: NotebookNode) -> NotebookNode:
    client = NotebookClient(
        notebook,
        timeout=120,
        kernel_name="python3",
        allow_errors=False,
        record_timing=False,
        resources={"metadata": {"path": str(REPO_ROOT)}},
    )
    executed = client.execute()
    executed.metadata["explanation"]["executed"] = True
    nbformat.validate(executed)
    return executed


def build_notebooks() -> list[Path]:
    rendered: list[tuple[Path, NotebookNode]] = []
    for spec in _load_manifest_specs():
        builder = NOTEBOOK_BUILDERS[spec["id"]]
        notebook = builder(spec["claims"])
        nbformat.validate(notebook)
        executed = _execute_notebook(notebook)
        destination = REPO_ROOT / Path(spec["path"])
        rendered.append((destination, executed))

    written: list[Path] = []
    for destination, notebook in rendered:
        destination.parent.mkdir(parents=True, exist_ok=True)
        nbformat.write(notebook, destination)
        written.append(destination)
    return written


def check_notebooks() -> list[str]:
    errors: list[str] = []
    try:
        specs = _load_manifest_specs()
    except NotebookBuildError as exc:
        return [str(exc)]

    for spec in specs:
        relative_path = spec["path"]
        notebook_path = REPO_ROOT / Path(relative_path)
        if not notebook_path.is_file():
            errors.append(f"{relative_path}: notebook is missing")
            continue

        try:
            notebook = nbformat.read(notebook_path, as_version=4)
            nbformat.validate(notebook)
        except Exception as exc:  # nbformat exposes multiple parse/validation types
            errors.append(f"{relative_path}: cannot parse as a valid notebook: {exc}")
            continue

        try:
            expected_notebook = NOTEBOOK_BUILDERS[spec["id"]](spec["claims"])
        except NotebookBuildError as exc:
            errors.append(f"{relative_path}: cannot rebuild the cell contract: {exc}")
            expected_notebook = None
        if expected_notebook is not None:
            if len(notebook.cells) != len(expected_notebook.cells):
                errors.append(
                    f"{relative_path}: cell count differs from the generator "
                    f"({len(notebook.cells)} != {len(expected_notebook.cells)})"
                )
            for index, (actual_cell, expected_cell) in enumerate(
                zip(notebook.cells, expected_notebook.cells), start=1
            ):
                for field in ("id", "cell_type", "source"):
                    if actual_cell.get(field) != expected_cell.get(field):
                        errors.append(
                            f"{relative_path}: cell {index} field {field!r} "
                            "differs from the generator"
                        )

        explanation = notebook.metadata.get("explanation")
        if not isinstance(explanation, dict):
            errors.append(f"{relative_path}: metadata.explanation must be a mapping")
            continue

        actual_keys = set(explanation)
        if actual_keys != EXPLANATION_METADATA_KEYS:
            errors.append(
                f"{relative_path}: metadata.explanation keys must be exactly "
                f"{sorted(EXPLANATION_METADATA_KEYS)}, found {sorted(actual_keys)}"
            )

        expected_generator = _generator_stamp()
        if explanation.get("generator_version") != expected_generator:
            errors.append(
                f"{relative_path}: generator version is stale "
                f"({explanation.get('generator_version')!r} != {expected_generator!r})"
            )

        try:
            current_hashes = _input_hashes(spec["inputs"])
        except NotebookBuildError as exc:
            errors.append(f"{relative_path}: {exc}")
            current_hashes = None
        if current_hashes is not None and explanation.get("inputs") != current_hashes:
            errors.append(f"{relative_path}: input SHA256 metadata is stale")

        if explanation.get("claims") != spec["claims"]:
            errors.append(
                f"{relative_path}: claim metadata must be {spec['claims']!r}"
            )
        if explanation.get("executed") is not True:
            errors.append(f"{relative_path}: metadata.explanation.executed is not true")

        code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
        if not code_cells:
            errors.append(f"{relative_path}: notebook has no code cells")
        for index, cell in enumerate(code_cells, start=1):
            if cell.get("execution_count") is None:
                errors.append(
                    f"{relative_path}: code cell {index} has not been executed"
                )
            for output in cell.get("outputs", []):
                if output.get("output_type") == "error":
                    errors.append(
                        f"{relative_path}: code cell {index} contains an error output "
                        f"({output.get('ename', 'unknown error')})"
                    )
    return errors


def execute_check_notebooks() -> list[str]:
    """Re-execute generated cells in memory and compare their saved outputs."""
    errors = check_notebooks()
    if errors:
        return errors

    for spec in _load_manifest_specs():
        relative_path = spec["path"]
        committed = nbformat.read(REPO_ROOT / Path(relative_path), as_version=4)
        try:
            expected = _execute_notebook(
                NOTEBOOK_BUILDERS[spec["id"]](spec["claims"])
            )
        except Exception as exc:  # execution errors carry useful notebook context
            errors.append(f"{relative_path}: clean re-execution failed: {exc}")
            continue

        for index, (actual_cell, expected_cell) in enumerate(
            zip(committed.cells, expected.cells), start=1
        ):
            if actual_cell.cell_type != "code":
                continue
            if actual_cell.get("execution_count") != expected_cell.get("execution_count"):
                errors.append(
                    f"{relative_path}: cell {index} execution count differs after re-execution"
                )
            if actual_cell.get("outputs", []) != expected_cell.get("outputs", []):
                errors.append(
                    f"{relative_path}: cell {index} saved outputs differ after re-execution"
                )
    return errors


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or verify the committed explanation notebooks."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate committed notebooks without rewriting them",
    )
    parser.add_argument(
        "--execute-check",
        action="store_true",
        help="re-execute in memory and compare committed outputs without rewriting",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.check and args.execute_check:
            raise NotebookBuildError("Choose either --check or --execute-check")
        if args.execute_check:
            errors = execute_check_notebooks()
            if errors:
                for error in errors:
                    print(error, file=sys.stderr)
                return 1
            print("Notebook execution check passed: committed outputs reproduce exactly.")
            return 0
        if args.check:
            errors = check_notebooks()
            if errors:
                for error in errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 1
            print("Notebook check passed: 2 notebooks are current and fully executed.")
            return 0

        written = build_notebooks()
        for path in written:
            print(f"Wrote {path.relative_to(REPO_ROOT).as_posix()}")
        return 0
    except NotebookBuildError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
