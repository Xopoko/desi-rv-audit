# DESI RV Audit

[![tests](https://github.com/Xopoko/desi-rv-audit/actions/workflows/tests.yml/badge.svg)](https://github.com/Xopoko/desi-rv-audit/actions/workflows/tests.yml)

Deterministic quality-control pipeline for multi-epoch radial-velocity
measurements in the public DESI DR1 stellar catalogue.

This repository is not an "AI discovers astrophysics" claim. The statistical
core is ordinary, reproducible Python. Koposov et al. explicitly discuss
night-specific radial-velocity systematics in DESI DR1. This audit independently
quantifies the out-of-sample night-associated residual component that remains in
the public MAIN repeat-observation sample after the published approximate
backup-program correction and program-level uncertainty floors.

## Research Question

Are DESI single-epoch radial velocities and their uncertainties calibrated
consistently across program, observing night, source group, and repeat
observation metadata after applying the published DR1 corrections?

## Pipeline

The pipeline:

1. Loads DESI-like epoch tables from CSV, Parquet, or FITS.
2. Joins radial-velocity rows with `FIBERMAP` metadata and Gaia `SOURCE_ID`
   when available.
3. Groups repeat observations by Gaia `SOURCE_ID`, with `TARGETID` fallback for
   rows without Gaia identifiers.
4. Applies explicit stellar-quality cuts: finite velocity/error, minimum S/N,
   successful fit, `RVS_WARN == 0`, `FIBERSTATUS == 0`,
   `RR_SPECTYPE == STAR`, and `VSINI < 30 km/s` when the columns are present.
5. Applies the published backup-program velocity correction table only to
   `SURVEY == MAIN` and `PROGRAM == BACKUP`, and writes correction coverage
   diagnostics.
6. Uses adopted uncertainty floors of `BRIGHT=1.0 km/s`, `BACKUP=2.0 km/s`,
   and `DARK=1.6 km/s`.
7. Builds within-source epoch pairs and reports robust residual widths, tail
   rates, and constant-RV screening outliers.
8. Runs a source-grouped `PROGRAM:NIGHT` residual audit with:
   - five folds assigned by `GROUP_ID`;
   - no source group shared between train and holdout within a fold;
   - source-balanced pair weights;
   - train-only robust clipping;
   - train-estimated post-correction floors;
   - graph connectedness diagnostics;
   - same-component-only holdout scoring;
   - independent source-half offset reproducibility;
   - coarse exposure-level shuffled-night-within-program controls.

The resulting offsets are diagnostics, not official catalogue corrections.

The split is source-disjoint, not night-disjoint. The model estimates offsets
for nights represented by the training stars and evaluates those offsets on
different stars observed on the same nights. It therefore tests transfer across
sources for known nights, not extrapolation to unseen nights.

This is an exploratory analysis developed iteratively on the public MAIN DR1
sample. Source-grouped folds prevent source reuse within each evaluation, but
the overall workflow was not pre-registered and has not yet been confirmed on a
fully untouched data set. Confirmation would require a pre-specified analysis
on an independent survey, data slice, or future release.

## Quick Start

macOS/Linux:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[fits,dev]"

pytest
```

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[fits,dev]"

python -m pytest
```

Synthetic smoke run on any platform after activation:

```bash
desi-rv-audit analyze data/synthetic_epochs.csv --output-dir outputs/demo --report-output reports/demo_report.md --plots
```

## Reproduce the MAIN Audit

Download the public DESI MAIN files and the Zenodo backup correction:

```bash
desi-rv-audit download-main
```

The downloader is implemented in Python and works on macOS, Windows, and Linux.
It resumes partial downloads by default and validates the expected file sizes and
backup-correction MD5. The legacy Unix shell wrapper
`./scripts/download_main_bundle.sh` and the Windows PowerShell wrapper
`.\scripts\download_main_bundle.ps1` are also available after installing the
package.

Run the audit on macOS/Linux:

```bash
desi-rv-audit analyze \
  data/desi_main/rvpix_exp-main-backup.fits \
  data/desi_main/rvpix_exp-main-bright.fits \
  data/desi_main/rvpix_exp-main-dark.fits \
  --output-dir outputs/desi_main_audit \
  --max-pairs-per-source 20 \
  --lite-output \
  --backup-correction data/desi_corrections/backup_correction.fits \
  --report-output reports/desi_main_audit_report.md \
  --strict-desi-main \
  --plots \
  --program-night-audit \
  --program-night-permutations 20 \
  --program-night-workers 4 \
  --timings-output outputs/desi_main_audit/stage_timings.csv
```

Run the audit on Windows PowerShell:

```powershell
desi-rv-audit analyze `
  data/desi_main/rvpix_exp-main-backup.fits `
  data/desi_main/rvpix_exp-main-bright.fits `
  data/desi_main/rvpix_exp-main-dark.fits `
  --output-dir outputs/desi_main_audit `
  --max-pairs-per-source 20 `
  --lite-output `
  --backup-correction data/desi_corrections/backup_correction.fits `
  --report-output reports/desi_main_audit_report.md `
  --strict-desi-main `
  --plots `
  --program-night-audit `
  --program-night-permutations 20 `
  --program-night-workers 4 `
  --timings-output outputs/desi_main_audit/stage_timings.csv
```

Set `--program-night-workers 1` for the most conservative single-threaded
execution, or raise it on high-memory workstations. The timings CSV records
where wall time is spent in each run.

The local run used for the reproducibility bundle processed:

- 5,342,614 source groups;
- 2,171,341 quality-approved epoch pairs;
- 25,953 constant-RV screening outliers;
- 12,141 stricter constant-RV screening outliers with at least three good epochs
  and baseline greater than one day.

These outlier counts come from the baseline constant-RV screening layer before
applying the diagnostic `PROGRAM:NIGHT` model. They are not interpreted as
confirmed variable stars and are not used as evidence for the main program-night
result.

Runtime on the local machine was 1,831.86 seconds with 11.66 GiB maximum
resident set size for the full 20-permutation audit.

## Main Result

Mean over five source-grouped folds:

The primary real-vs-shuffled comparison is raw robust scatter in km/s. Normalized
widths and Gaussian pair losses use train-estimated floors and are intended for
within-experiment before/after scoring, not direct comparison between real and
shuffled baselines.

| Metric | Real before | Real after | Shuffled before | Shuffled after |
|---|---:|---:|---:|---:|
| Raw robust scatter, km/s | 3.651 | 3.157 | 3.654 | 3.496 |
| Normalized central width | 1.019 | 0.885 | 0.936 | 0.899 |
| Macro normalized width by program pair | 0.972 | 0.909 | 0.927 | 0.915 |
| `|z| > 3` | 0.051 | 0.040 | 0.043 | 0.038 |
| `|z| > 5` | 0.022 | 0.020 | 0.018 | 0.017 |
| Mean Gaussian pair loss | 4.358 | 4.160 | 4.052 | 3.981 |

The real model reduces raw robust scatter by 0.495 km/s, or 13.5%. The coarse
exposure-level shuffled-night controls reduce raw scatter by 0.158 km/s on
average, or 4.3%; across 20 permutations the shuffled improvement ranges from
0.096 to 0.234 km/s, and no shuffled permutation reaches the real improvement.
With only 20 permutations, this is a coarse negative control rather than a
strong formal significance claim.

The strongest program-pair improvement is `BACKUP / BACKUP`: raw robust scatter
changes from 3.663 to 2.943 km/s and normalized central width from 1.081 to
0.871.

Independent source halves recover 484 common `PROGRAM:NIGHT` offsets with:

- offset correlation: 0.980;
- slope B on A: 0.994;
- median absolute difference: 0.096 km/s;
- robust width of offset differences: 0.174 km/s.

Pair-cap sensitivity is stable:

| Max pairs/source | Program-night pairs | Raw before | Raw after | Reduction | Backup/backup reduction | Offset r |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1,694,555 | 3.639 | 3.137 | 13.8% | 0.724 km/s | 0.981 |
| 20 | 1,736,682 | 3.651 | 3.157 | 13.5% | 0.720 km/s | 0.980 |
| 50 | 1,752,357 | 3.654 | 3.160 | 13.5% | 0.720 km/s | 0.980 |

## Reproducibility Bundle

The repository intentionally excludes raw DESI FITS files and generated large
screening-outlier tables. The included reproducibility bundle is compact:

- `reports/desi_main_program_night_audit.md`
- `reports/desi_main_audit_report.md`
- `reports/program_night_artifacts/summary.csv`
- `reports/program_night_artifacts/by_program.csv`
- `reports/program_night_artifacts/reproducibility.csv`
- `reports/program_night_artifacts/permutation_summary.csv`
- `reports/program_night_artifacts/pair_cap_sensitivity.csv`
- `reports/program_night_artifacts/correction_summary.csv`
- `reports/program_night_artifacts/diagnostic_offsets_program_night.csv`
- `reports/program_night_artifacts/source_fold_widths.png`
- `reports/program_night_artifacts/run_manifest.json`

## Interpretation Boundaries

Supported claim:

> After applying the published DESI DR1 backup correction and program-level
> uncertainty floors, source-disjoint cross-validation shows a reproducible
> night-associated residual component in the public MAIN repeat-observation
> sample, strongest in `BACKUP / BACKUP`.

Not claimed:

- that the offsets should be applied to the DESI catalogue;
- that the effect has a specific instrumental cause;
- that remaining heavy tails are astrophysical variability;
- that this is an official DESI correction;
- that the result is a standalone astrophysical discovery.

The intended next step is expert review: determine whether the residual
structure is a known calibration residual, a methodological artifact, or a
potentially useful additional diagnostic.

## Sources

- DESI DR1 stellar catalogue documentation: https://data.desi.lbl.gov/doc/releases/dr1/vac/mws/
- DESI MWS DR1 data model: https://desi-mws-dr1-datamodel.readthedocs.io/en/latest/
- DESI DR1 Stellar Catalogue paper: https://arxiv.org/abs/2505.14787
- DESI DR1 backup-program radial-velocity correction: https://zenodo.org/records/15469272
- DESI data license and acknowledgments: https://data.desi.lbl.gov/doc/acknowledgments/
- RVSpecFit: https://github.com/segasai/rvspecfit
