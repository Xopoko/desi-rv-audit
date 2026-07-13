# DESI MAIN Program-Night Audit

## Summary

This is a source-grouped residual diagnostic for public DESI DR1 single-epoch
stellar radial velocities. The audit applies the published backup-program
velocity correction only to `MAIN/BACKUP` rows, applies program-level uncertainty
floors, and then tests whether night-associated residual structure remains in
repeat observations.

Koposov et al. explicitly anticipate night-specific radial-velocity systematics
in DESI DR1. This audit independently quantifies the out-of-sample
night-associated residual component that remains after the published approximate
backup correction.

Supported claim:

> Using source-disjoint cross-validation, the public DESI DR1 MAIN
> repeat-observation sample shows a reproducible night-associated component in
> radial-velocity residuals after the published correction. The effect is
> strongest in `BACKUP / BACKUP`. This analysis does not establish its
> instrumental origin or propose an official correction.

## Reproduction Command

```bash
./scripts/download_main_bundle.sh

/usr/bin/time -l .venv/bin/desi-rv-audit analyze data/desi_main/*.fits \
  --output-dir outputs/desi_main_audit \
  --max-pairs-per-source 20 \
  --lite-output \
  --backup-correction data/desi_corrections/backup_correction.fits \
  --report-output reports/desi_main_audit_report.md \
  --strict-desi-main \
  --plots \
  --program-night-audit \
  --program-night-permutations 100 \
  --program-night-bootstraps 50 \
  --program-night-workers 4
```

Local run:

- Sources summarized: 5,342,614
- Quality-approved epoch pairs: 2,171,341
- Constant-RV screening outliers: 25,953
- Strict constant-RV screening outliers: 12,141
- Runtime: 10,753.05 s (2 h 59 min)
- Maximum resident set size: 10.89 GiB

The 25,953 outliers and 12,141 strict outliers come from the baseline
constant-RV screening layer before applying the diagnostic `PROGRAM:NIGHT`
model. They are not interpreted as confirmed variable stars and are not used as
evidence for the main program-night result.

## Published Backup Correction

The correction table is applied only when `SURVEY == MAIN` and
`PROGRAM == BACKUP`. TARGETID matches in other programs are counted but not
corrected.

| Statistic | Value |
|---|---:|
| Correction rows | 1,218,152 |
| Unique correction TARGETIDs | 1,218,152 |
| Backup epochs | 2,152,133 |
| Backup epochs matched | 2,152,126 |
| Backup epochs unmatched | 7 |
| Non-backup TARGETID matches, not corrected | 27 |
| Correction MD5 | `f48a4b21b541e94d61f4372f4c555f12` |
| MD5 check | pass |

## Fold-Level Results

Mean over five source-grouped folds:

| Metric | Real before | Real after | Shuffled before | Shuffled after |
|---|---:|---:|---:|---:|
| Raw robust scatter, km/s | 3.651 | 3.157 | 3.652 | 3.480 |
| Normalized central width | 1.019 | 0.885 | 0.939 | 0.899 |
| Macro normalized width by program pair | 0.973 | 0.908 | 0.930 | 0.914 |
| `|z| > 3` | 0.051 | 0.040 | 0.043 | 0.038 |
| `|z| > 5` | 0.022 | 0.020 | 0.018 | 0.017 |
| Mean Gaussian pair loss | 4.358 | 4.160 | 4.062 | 3.988 |

The real `PROGRAM:NIGHT` model reduces holdout raw robust scatter by
0.495 km/s, or 13.5%. Exposure-level shuffled-night controls reduce raw scatter
by 0.171 km/s on average, or 4.7%. Across 100 permutations, shuffled improvement
ranges from 0.072 to 0.294 km/s; no shuffled permutation reaches the real
improvement. The corrected empirical exceedance estimate is `1 / 101 = 0.0099`.

![Source-grouped fold widths](program_night_artifacts/source_fold_widths.png)

## Program Pair Means

Mean over five folds:

| Program pair | N holdout total | Raw before | Raw after | Reduction | Width before | Width after |
|---|---:|---:|---:|---:|---:|---:|
| `BACKUP / BACKUP` | 996,012 | 3.663 | 2.943 | 19.7% | 1.081 | 0.871 |
| `BACKUP / BRIGHT` | 220,806 | 3.723 | 3.610 | 3.0% | 0.946 | 0.917 |
| `BACKUP / DARK` | 27,705 | 5.575 | 5.457 | 2.1% | 0.961 | 0.930 |
| `BRIGHT / BRIGHT` | 251,120 | 2.906 | 2.780 | 4.3% | 0.893 | 0.855 |
| `BRIGHT / DARK` | 118,076 | 4.398 | 4.170 | 5.2% | 0.995 | 0.935 |
| `DARK / DARK` | 116,360 | 3.494 | 3.431 | 1.8% | 0.961 | 0.940 |

## Graph and Solver Diagnostics

Mean over folds:

- Connected components: 2
- Largest component label fraction: 0.996
- Largest component pair fraction: 0.998
- Holdout pairs scored in the same train component: 346,016 per fold
- Holdout pairs crossing train components and excluded: 1,321 per fold
- `LSQR_ISTOP`: 2 in all folds
- Mean `LSQR_ACOND`: 752
- Mean `LSQR_R1NORM`: 778
- Mean `LSQR_ARNORM`: 0.0038
- Gaia-grouped program-night pairs: 99.93%

Offsets are centered within connected components and are interpreted only as
diagnostic zero-point terms.

The split is source-disjoint, not night-disjoint. The model estimates offsets
for nights represented by the training stars and evaluates those offsets on
different stars observed on the same nights. It therefore tests transfer across
sources for known nights, not extrapolation to unseen nights.

## Independent-Half Reproducibility

Independent source halves recover 483 common `PROGRAM:NIGHT` labels after
component and gauge alignment:

- Offset correlation: 0.980
- Slope B on A: 1.002
- Median absolute difference: 0.107 km/s
- Robust width of offset differences: 0.182 km/s

This is the main check against shared-source leakage or pair-row noise reuse.

Program-specific and within-program-demeaned checks from the same source-half
procedure:

| Scope | N labels | Pearson r | Spearman rho | Slope | Median abs diff, km/s | Robust diff width, km/s |
|---|---:|---:|---:|---:|---:|---:|
| All, demeaned within program | 483 | 0.977 | 0.941 | 0.995 | 0.119 | 0.184 |
| `BACKUP` | 83 | 0.999 | 0.996 | 0.995 | 0.048 | 0.086 |
| `BRIGHT` | 228 | 0.955 | 0.957 | 0.992 | 0.098 | 0.164 |
| `DARK` | 172 | 0.884 | 0.840 | 1.003 | 0.162 | 0.258 |

The aggregate correlation is therefore not solely induced by persistent
between-program differences. Reproducibility is strongest for `BACKUP`, which
is also where the residual-scatter reduction is largest.

This is an exploratory analysis developed iteratively on the public MAIN DR1
sample. Source-grouped folds prevent source reuse within each evaluation, but
the overall workflow was not pre-registered and has not yet been confirmed on a
fully untouched data set. Confirmation would require a pre-specified analysis on
an independent survey, data slice, or future release.

## Pair-Cap Sensitivity

| Max pairs/source | Program-night pairs | Raw before | Raw after | Reduction | Backup/backup reduction | Offset r |
|---:|---:|---:|---:|---:|---:|---:|
| 10 | 1,694,555 | 3.638 | 3.137 | 13.8% | 0.723 km/s | 0.980 |
| 20 | 1,736,682 | 3.651 | 3.157 | 13.5% | 0.720 km/s | 0.980 |
| 50 | 1,752,357 | 3.654 | 3.160 | 13.5% | 0.719 km/s | 0.980 |

## Boundaries

This audit supports:

- a source-grouped out-of-sample residual diagnostic;
- a reproducible night-associated residual component after published
  correction;
- strongest evidence in `BACKUP / BACKUP`;
- compact artifacts that can be independently inspected.

This audit does not prove:

- that the offsets should be applied to the public catalogue;
- that the effect has a specific instrumental cause;
- that heavy tails are astrophysical variability;
- that this is an official DESI correction.

## Artifacts

- `reports/desi_main_audit_report.md`
- `reports/program_night_artifacts/summary.csv`
- `reports/program_night_artifacts/by_program.csv`
- `reports/program_night_artifacts/diagnostic_offsets_program_night.csv`
- `reports/program_night_artifacts/reproducibility.csv`
- `reports/program_night_artifacts/reproducibility_by_program.csv`
- `reports/program_night_artifacts/reproducibility_run_manifest.json`
- `reports/program_night_artifacts/permutation_summary.csv`
- `reports/program_night_artifacts/pair_cap_sensitivity.csv`
- `reports/program_night_artifacts/pair_cap_sensitivity_manifest.json`
- `reports/program_night_artifacts/correction_summary.csv`
- `reports/program_night_artifacts/source_fold_widths.png`
- `reports/program_night_artifacts/run_manifest.json`
- `reports/program_night_artifacts/ensemble_release_manifest.json`
- `reports/program_night_artifacts/stage_timings.csv`
