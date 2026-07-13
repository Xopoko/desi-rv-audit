# DESI radial-velocity audit report

## Scope

This report is a **screening and quality-control artifact**, not an astrophysical discovery claim.

## Summary

- Sources summarized: **5,342,614**
- Quality-approved epoch pairs: **2,171,341**
- Sources inconsistent with a constant-RV model under configured thresholds: **25,953**
- Strict constant-RV screening outliers with `n_epochs_good >= 3` and baseline > 1 day: **12,141**
- Median normalized pair residual: **0.057**
- Central 16–84% normalized-residual half-width: **1.021**
- Fraction of pairs with |z| > 5: **0.01951**

For perfectly calibrated independent Gaussian errors and non-variable sources, the central width should be near one. Departures can arise from uncertainty miscalibration, zero-point systematics, real stellar variability, correlations, selection effects, or pipeline failures.

## Source classifications

| classification      |   N_SOURCES |
|:--------------------|------------:|
| insufficient_epochs |   2,624,059 |
| quality_limited     |   1,635,778 |
| stable_like         |   1,056,824 |
| constant_rv_outlier |      25,953 |

## Quality filtering

| SURVEY   | PROGRAM   |   N_EPOCHS_RAW |   N_TARGETIDS_RAW |   N_GROUPS_RAW |   N_EPOCHS_GOOD |   N_TARGETIDS_GOOD |   N_GROUPS_GOOD |   N_GROUPS_2PLUS_GOOD_EPOCHS |   GOOD_EPOCH_FRACTION |
|:---------|:----------|---------------:|------------------:|---------------:|----------------:|-------------------:|----------------:|-----------------------------:|----------------------:|
| MAIN     | BACKUP    |      2,152,133 |         1,218,087 |      1,218,087 |       1,972,869 |          1,165,760 |       1,165,760 |                      556,116 |               0.9167  |
| MAIN     | BRIGHT    |      3,572,976 |         3,059,956 |      3,057,733 |       2,860,521 |          2,443,980 |       2,442,565 |                      377,293 |               0.8006  |
| MAIN     | DARK      |      1,818,406 |         1,297,110 |      1,296,959 |         410,285 |            277,525 |         277,424 |                       87,742 |               0.22563 |

| REASON                  |   N_REJECTED |   FRACTION |
|:------------------------|-------------:|-----------:|
| NONFINITE_RV            |            0 |    0       |
| INVALID_RV_ERROR        |            0 |    0       |
| EXTREME_ABS_RV          |            0 |    0       |
| LOW_SN_R                |    1,471,741 |    0.1951  |
| FIT_NOT_SUCCESSFUL      |    1,701,473 |    0.22555 |
| NON_STELLAR_RR_SPECTYPE |    1,831,465 |    0.24279 |
| RVS_WARNING             |    1,701,473 |    0.22555 |
| FIBER_WARNING           |            0 |    0       |
| MISSING_VSINI           |            0 |    0       |
| HIGH_VSINI              |    1,315,729 |    0.17442 |

Rejection reasons are **not mutually exclusive**; their counts should not be summed.

For the local `MAIN` FITS files, `FIBERSTATUS` is zero for every loaded row, so `FIBER_WARNING=0` is expected rather than evidence that this check is disabled.

## Published Backup Correction

The backup-program velocity correction is applied only to rows where
`SURVEY == MAIN` and `PROGRAM == BACKUP`. TARGETID matches in other programs are
counted for auditability but are not corrected.

| CORRECTION_PATH                              | CORRECTION_MD5                   | CORRECTION_SHA256                                                |   N_CORRECTION_ROWS |   N_CORRECTION_UNIQUE_TARGETIDS |   N_BACKUP_EPOCHS |   N_BACKUP_EPOCHS_MATCHED |   N_BACKUP_EPOCHS_UNMATCHED |   N_NON_BACKUP_TARGETID_MATCHES | CORRECTION_MD5_EXPECTED          |   CORRECTION_MD5_OK |
|:---------------------------------------------|:---------------------------------|:-----------------------------------------------------------------|--------------------:|--------------------------------:|------------------:|--------------------------:|----------------------------:|--------------------------------:|:---------------------------------|--------------------:|
| data/desi_corrections/backup_correction.fits | f48a4b21b541e94d61f4372f4c555f12 | eb4da91267db39f285a277989489f991ea48371336efedd28bd07d2b58e4a400 |           1,218,152 |                       1,218,152 |         2,152,133 |                 2,152,126 |                           7 |                              27 | f48a4b21b541e94d61f4372f4c555f12 |                   1 |

## Calibration diagnostics

Overall normalized pair residuals using calibrated errors:

| GROUP   |   N_PAIRS |   MEDIAN_Z |   ROBUST_WIDTH_Z |   MAD_WIDTH_Z |   Q16_Z |   Q84_Z |   TAIL_GT_3 |   TAIL_GT_5 | Z_COLUMN   |
|:--------|----------:|-----------:|-----------------:|--------------:|--------:|--------:|------------:|------------:|:-----------|
| ALL     | 2,171,341 |      0.057 |            1.021 |         0.965 |  -0.933 |   1.108 |     0.04617 |     0.01951 | PAIR_Z     |

Overall normalized pair residuals using formal catalogue errors:

| GROUP   |   N_PAIRS |   MEDIAN_Z |   ROBUST_WIDTH_Z |   MAD_WIDTH_Z |   Q16_Z |   Q84_Z |   TAIL_GT_3 |   TAIL_GT_5 | Z_COLUMN      |
|:--------|----------:|-----------:|-----------------:|--------------:|--------:|--------:|------------:|------------:|:--------------|
| ALL     | 2,171,341 |      0.133 |            2.142 |         1.854 |  -1.784 |     2.5 |     0.22901 |     0.13966 | PAIR_Z_FORMAL |

By canonical program pair using calibrated errors. Cross-program `PROGRAM_PAIR_Z`
is oriented lexicographically so a zero-point offset does not cancel when epoch
order changes. Same-program pairs have no cross-program orientation; their sign
follows the sorted epoch order and their median should be interpreted as a
within-program residual diagnostic, not a program zero-point estimate.

| PROGRAM_PAIR    |   N_PAIRS |   MEDIAN_Z |   ROBUST_WIDTH_Z |   MAD_WIDTH_Z |   Q16_Z |   Q84_Z |   TAIL_GT_3 |   TAIL_GT_5 | Z_COLUMN       |
|:----------------|----------:|-----------:|-----------------:|--------------:|--------:|--------:|------------:|------------:|:---------------|
| BACKUP / BACKUP | 1,131,158 |      0.124 |            1.045 |         0.954 |  -0.831 |   1.258 |     0.06168 |     0.02419 | PROGRAM_PAIR_Z |
| BACKUP / BRIGHT |   228,008 |      0     |            1.112 |         1.1   |  -1.12  |   1.105 |     0.0391  |     0.01769 | PROGRAM_PAIR_Z |
| BACKUP / DARK   |    28,068 |     -0.127 |            1.133 |         1.126 |  -1.282 |   0.983 |     0.03787 |     0.01543 | PROGRAM_PAIR_Z |
| BRIGHT / BRIGHT |   464,257 |     -0.074 |            0.941 |         0.928 |  -1.027 |   0.856 |     0.02274 |     0.01212 | PROGRAM_PAIR_Z |
| BRIGHT / DARK   |   123,451 |     -0.263 |            1.134 |         1.119 |  -1.406 |   0.862 |     0.04422 |     0.0209  | PROGRAM_PAIR_Z |
| DARK / DARK     |   196,399 |      0.021 |            0.866 |         0.842 |  -0.837 |   0.896 |     0.02282 |     0.01181 | PROGRAM_PAIR_Z |

By canonical program pair using formal catalogue errors:

| PROGRAM_PAIR    |   N_PAIRS |   MEDIAN_Z |   ROBUST_WIDTH_Z |   MAD_WIDTH_Z |   Q16_Z |   Q84_Z |   TAIL_GT_3 |   TAIL_GT_5 | Z_COLUMN              |
|:----------------|----------:|-----------:|-----------------:|--------------:|--------:|--------:|------------:|------------:|:----------------------|
| BACKUP / BACKUP | 1,131,158 |      0.33  |            3.532 |         2.698 |  -2.524 |   4.541 |     0.35735 |     0.23588 | PROGRAM_PAIR_Z_FORMAL |
| BACKUP / BRIGHT |   228,008 |     -0.264 |            1.822 |         1.742 |  -2.161 |   1.484 |     0.15304 |     0.06087 | PROGRAM_PAIR_Z_FORMAL |
| BACKUP / DARK   |    28,068 |     -0.454 |            1.587 |         1.509 |  -2.155 |   1.019 |     0.12149 |     0.04738 | PROGRAM_PAIR_Z_FORMAL |
| BRIGHT / BRIGHT |   464,257 |     -0.101 |            1.277 |         1.255 |  -1.392 |   1.161 |     0.05821 |     0.02168 | PROGRAM_PAIR_Z_FORMAL |
| BRIGHT / DARK   |   123,451 |     -0.33  |            1.493 |         1.432 |  -1.908 |   1.079 |     0.10629 |     0.04292 | PROGRAM_PAIR_Z_FORMAL |
| DARK / DARK     |   196,399 |      0.031 |            1.295 |         1.258 |  -1.243 |   1.347 |     0.07421 |     0.0298  | PROGRAM_PAIR_Z_FORMAL |

By canonical program pair using calibrated errors and only pairs separated by more than one day:

| PROGRAM_PAIR    |   N_PAIRS |   MEDIAN_Z |   ROBUST_WIDTH_Z |   MAD_WIDTH_Z |   Q16_Z |   Q84_Z |   TAIL_GT_3 |   TAIL_GT_5 | Z_COLUMN       |
|:----------------|----------:|-----------:|-----------------:|--------------:|--------:|--------:|------------:|------------:|:---------------|
| BACKUP / BACKUP |   996,012 |      0.173 |            1.068 |         0.981 |  -0.783 |   1.353 |     0.06507 |     0.02601 | PROGRAM_PAIR_Z |
| BACKUP / BRIGHT |   221,306 |      0.004 |            1.116 |         1.104 |  -1.12  |   1.111 |     0.03975 |     0.01805 | PROGRAM_PAIR_Z |
| BACKUP / DARK   |    27,864 |     -0.128 |            1.133 |         1.125 |  -1.284 |   0.983 |     0.03797 |     0.01543 | PROGRAM_PAIR_Z |
| BRIGHT / BRIGHT |   251,926 |     -0.085 |            1.054 |         1.04  |  -1.144 |   0.965 |     0.03689 |     0.01998 | PROGRAM_PAIR_Z |
| BRIGHT / DARK   |   120,350 |     -0.27  |            1.137 |         1.123 |  -1.416 |   0.857 |     0.04498 |     0.02121 | PROGRAM_PAIR_Z |
| DARK / DARK     |   119,224 |      0.055 |            1.006 |         0.994 |  -0.949 |   1.063 |     0.0355  |     0.01849 | PROGRAM_PAIR_Z |

By canonical program pair using formal catalogue errors and only pairs separated by more than one day:

| PROGRAM_PAIR    |   N_PAIRS |   MEDIAN_Z |   ROBUST_WIDTH_Z |   MAD_WIDTH_Z |   Q16_Z |   Q84_Z |   TAIL_GT_3 |   TAIL_GT_5 | Z_COLUMN              |
|:----------------|----------:|-----------:|-----------------:|--------------:|--------:|--------:|------------:|------------:|:----------------------|
| BACKUP / BACKUP |   996,012 |      0.466 |            3.736 |         2.834 |  -2.369 |   5.103 |     0.37123 |     0.24626 | PROGRAM_PAIR_Z_FORMAL |
| BACKUP / BRIGHT |   221,306 |     -0.263 |            1.826 |         1.744 |  -2.161 |   1.491 |     0.15354 |     0.06122 | PROGRAM_PAIR_Z_FORMAL |
| BACKUP / DARK   |    27,864 |     -0.456 |            1.588 |         1.511 |  -2.16  |   1.016 |     0.1217  |     0.04752 | PROGRAM_PAIR_Z_FORMAL |
| BRIGHT / BRIGHT |   251,926 |     -0.114 |            1.448 |         1.406 |  -1.572 |   1.324 |     0.08945 |     0.03597 | PROGRAM_PAIR_Z_FORMAL |
| BRIGHT / DARK   |   120,350 |     -0.338 |            1.501 |         1.437 |  -1.927 |   1.074 |     0.10766 |     0.04371 | PROGRAM_PAIR_Z_FORMAL |
| DARK / DARK     |   119,224 |      0.081 |            1.574 |         1.512 |  -1.463 |   1.685 |     0.11524 |     0.04715 | PROGRAM_PAIR_Z_FORMAL |

By minimum pair `SN_R` quantile:

| SN_R_MIN_BIN      |   N_PAIRS |   MEDIAN_Z |   ROBUST_WIDTH_Z |   MAD_WIDTH_Z |   Q16_Z |   Q84_Z |   TAIL_GT_3 |   TAIL_GT_5 | Z_COLUMN   |
|:------------------|----------:|-----------:|-----------------:|--------------:|--------:|--------:|------------:|------------:|:-----------|
| (4.999, 8.567]    |   361,892 |      0.019 |            0.973 |         0.963 |  -0.953 |   0.992 |     0.0209  |     0.00762 | PAIR_Z     |
| (8.567, 12.954]   |   361,889 |      0.026 |            0.989 |         0.967 |  -0.962 |   1.016 |     0.03061 |     0.01287 | PAIR_Z     |
| (12.954, 19.511]  |   361,891 |      0.016 |            0.979 |         0.952 |  -0.96  |   0.998 |     0.03402 |     0.01507 | PAIR_Z     |
| (19.511, 29.251]  |   361,890 |      0.039 |            1.033 |         0.978 |  -0.975 |   1.091 |     0.05132 |     0.02209 | PAIR_Z     |
| (29.251, 45.433]  |   361,888 |      0.103 |            1.111 |         1.006 |  -0.911 |   1.31  |     0.0675  |     0.02869 | PAIR_Z     |
| (45.433, 202.414] |   361,891 |      0.123 |            1.064 |         0.929 |  -0.803 |   1.325 |     0.07265 |     0.03071 | PAIR_Z     |

Positive-control status: `BACKUP` cross-program pairs are present (256,076); inspect the program-pair table before treating this as a positive-control reproduction.

## Source-Grouped Program-Night Residual Diagnostics

This experiment estimates residual offsets for `PROGRAM:NIGHT` labels after the
published backup correction and program-level uncertainty floors. Folds are
assigned by `GROUP_ID`, so no source group contributes pairs to both train and
holdout within a fold. The fit uses train-only robust clipping, source-balanced
pair weights, train-estimated post-correction floors, and only holdout pairs
whose two labels are in the same train graph component. These offsets are
diagnostics, not official catalogue corrections.

Fold-level holdout diagnostics:

|   FOLD |   N_LABELS |   N_TRAIN_PAIRS |   N_EFFECTIVE_SOURCE_DRAWS |   N_CONNECTED_COMPONENTS |   LARGEST_COMPONENT_LABEL_FRACTION |   LARGEST_COMPONENT_PAIR_FRACTION |   LSQR_ISTOP |   LSQR_ITERS |   LSQR_ACOND |   LSQR_R1NORM |   LSQR_ARNORM |   N_HOLDOUT_PAIRS |   N_HOLDOUT_SAME_COMPONENT |   N_HOLDOUT_CROSS_COMPONENT |   BEFORE_RAW_WIDTH_KMS |   AFTER_RAW_WIDTH_KMS |   BEFORE_WIDTH_Z |   AFTER_WIDTH_Z |   BEFORE_TAIL_GT_3 |   AFTER_TAIL_GT_3 |   BEFORE_TAIL_GT_5 |   AFTER_TAIL_GT_5 |   BEFORE_MEAN_GAUSSIAN_PAIR_LOSS |   AFTER_MEAN_GAUSSIAN_PAIR_LOSS |   MACRO_WIDTH_BEFORE_Z |   MACRO_WIDTH_AFTER_Z |   MACRO_GAUSSIAN_PAIR_LOSS_BEFORE |   MACRO_GAUSSIAN_PAIR_LOSS_AFTER |   N_PROGRAM_NIGHT_PAIRS |   N_GAIA_GROUP_PAIRS |   GAIA_GROUP_PAIR_FRACTION |
|-------:|-----------:|----------------:|---------------------------:|-------------------------:|-----------------------------------:|----------------------------------:|-------------:|-------------:|-------------:|--------------:|--------------:|------------------:|---------------------------:|----------------------------:|-----------------------:|----------------------:|-----------------:|----------------:|-------------------:|------------------:|-------------------:|------------------:|---------------------------------:|--------------------------------:|-----------------------:|----------------------:|----------------------------------:|---------------------------------:|------------------------:|---------------------:|---------------------------:|
|      0 |        516 |       1,334,682 |                    650,960 |                        2 |                              0.996 |                             0.998 |            2 |          174 |      759.885 |       777.235 |         0.004 |           348,461 |                    347,144 |                       1,317 |                  3.661 |                 3.159 |            1.02  |           0.885 |              0.051 |             0.041 |              0.022 |             0.02  |                            4.392 |                           4.192 |                  0.981 |                 0.916 |                             4.098 |                            4.017 |               1,736,682 |            1,735,435 |                      0.999 |
|      1 |        516 |       1,336,775 |                    651,633 |                        2 |                              0.996 |                             0.998 |            2 |          179 |      800.875 |       777.69  |         0.004 |           346,290 |                    344,975 |                       1,315 |                  3.66  |                 3.162 |            1.02  |           0.888 |              0.051 |             0.04  |              0.022 |             0.02  |                            4.4   |                           4.202 |                  0.977 |                 0.913 |                             4.086 |                            4.005 |               1,736,682 |            1,735,435 |                      0.999 |
|      2 |        516 |       1,336,424 |                    652,006 |                        2 |                              0.996 |                             0.998 |            2 |          178 |      793.027 |       778.277 |         0.004 |           346,600 |                    345,281 |                       1,319 |                  3.644 |                 3.156 |            1.018 |           0.886 |              0.051 |             0.04  |              0.022 |             0.019 |                            4.341 |                           4.145 |                  0.969 |                 0.906 |                             3.96  |                            3.883 |               1,736,682 |            1,735,435 |                      0.999 |
|      3 |        519 |       1,335,438 |                    651,901 |                        2 |                              0.996 |                             0.998 |            2 |          176 |      774.882 |       778.387 |         0.003 |           348,218 |                    347,056 |                       1,162 |                  3.659 |                 3.162 |            1.02  |           0.886 |              0.052 |             0.041 |              0.022 |             0.019 |                            4.331 |                           4.133 |                  0.97  |                 0.904 |                             3.977 |                            3.896 |               1,736,682 |            1,735,435 |                      0.999 |
|      4 |        514 |       1,335,579 |                    651,721 |                        2 |                              0.996 |                             0.998 |            2 |          156 |      633.52  |       778.962 |         0.004 |           347,113 |                    345,623 |                       1,490 |                  3.633 |                 3.144 |            1.015 |           0.881 |              0.051 |             0.04  |              0.022 |             0.02  |                            4.327 |                           4.129 |                  0.967 |                 0.901 |                             4.03  |                            3.954 |               1,736,682 |            1,735,435 |                      0.999 |

Fold-level holdout diagnostics by program pair:

|   FOLD | PROGRAM_PAIR    |   N_HOLDOUT_PAIRS |   RAW_WIDTH_BEFORE_KMS |   RAW_WIDTH_AFTER_KMS |   WIDTH_BEFORE_Z |   WIDTH_AFTER_Z |   TAIL_GT_3_BEFORE |   TAIL_GT_3_AFTER |   TAIL_GT_5_BEFORE |   TAIL_GT_5_AFTER |   GAUSSIAN_PAIR_LOSS_BEFORE |   GAUSSIAN_PAIR_LOSS_AFTER |   TRAIN_PAIR_FLOOR_KMS |
|-------:|:----------------|------------------:|-----------------------:|----------------------:|-----------------:|----------------:|-------------------:|------------------:|-------------------:|------------------:|----------------------------:|---------------------------:|-----------------------:|
|      0 | BACKUP / BACKUP |           199,736 |                  3.67  |                 2.935 |            1.081 |           0.867 |              0.066 |             0.048 |              0.026 |             0.022 |                       4.62  |                      4.295 |                  2.783 |
|      0 | BACKUP / BRIGHT |            44,705 |                  3.744 |                 3.625 |            0.951 |           0.922 |              0.029 |             0.028 |              0.014 |             0.014 |                       3.744 |                      3.724 |                  2.966 |
|      0 | BACKUP / DARK   |             5,666 |                  5.693 |                 5.563 |            0.982 |           0.961 |              0.028 |             0.029 |              0.013 |             0.012 |                       3.838 |                      3.81  |                  3.775 |
|      0 | BRIGHT / BRIGHT |            50,464 |                  2.914 |                 2.778 |            0.895 |           0.854 |              0.029 |             0.028 |              0.017 |             0.017 |                       4.58  |                      4.545 |                  2.049 |
|      0 | BRIGHT / DARK   |            23,400 |                  4.434 |                 4.186 |            1.006 |           0.94  |              0.035 |             0.034 |              0.017 |             0.016 |                       3.786 |                      3.725 |                  2.764 |
|      0 | DARK / DARK     |            23,173 |                  3.539 |                 3.48  |            0.97  |           0.953 |              0.038 |             0.038 |              0.02  |             0.02  |                       4.018 |                      4.005 |                  2.464 |
|      1 | BACKUP / BACKUP |           198,164 |                  3.663 |                 2.948 |            1.081 |           0.873 |              0.066 |             0.048 |              0.026 |             0.022 |                       4.634 |                      4.313 |                  2.781 |
|      1 | BACKUP / BRIGHT |            44,006 |                  3.717 |                 3.617 |            0.946 |           0.917 |              0.032 |             0.031 |              0.015 |             0.015 |                       3.833 |                      3.812 |                  2.969 |
|      1 | BACKUP / DARK   |             5,583 |                  5.645 |                 5.546 |            0.98  |           0.94  |              0.028 |             0.027 |              0.011 |             0.012 |                       3.728 |                      3.693 |                  3.796 |
|      1 | BRIGHT / BRIGHT |            50,351 |                  2.924 |                 2.803 |            0.896 |           0.862 |              0.029 |             0.028 |              0.017 |             0.017 |                       4.507 |                      4.474 |                  2.043 |
|      1 | BRIGHT / DARK   |            23,687 |                  4.432 |                 4.207 |            0.999 |           0.944 |              0.032 |             0.032 |              0.017 |             0.016 |                       3.96  |                      3.905 |                  2.773 |
|      1 | DARK / DARK     |            23,184 |                  3.491 |                 3.403 |            0.959 |           0.942 |              0.034 |             0.034 |              0.018 |             0.018 |                       3.853 |                      3.835 |                  2.477 |
|      2 | BACKUP / BACKUP |           198,859 |                  3.67  |                 2.949 |            1.083 |           0.873 |              0.067 |             0.048 |              0.027 |             0.023 |                       4.641 |                      4.321 |                  2.78  |
|      2 | BACKUP / BRIGHT |            43,969 |                  3.734 |                 3.616 |            0.947 |           0.917 |              0.029 |             0.029 |              0.013 |             0.014 |                       3.852 |                      3.83  |                  2.971 |
|      2 | BACKUP / DARK   |             5,722 |                  5.431 |                 5.362 |            0.939 |           0.916 |              0.023 |             0.023 |              0.01  |             0.01  |                       3.564 |                      3.54  |                  3.833 |
|      2 | BRIGHT / BRIGHT |            49,978 |                  2.883 |                 2.761 |            0.887 |           0.852 |              0.028 |             0.027 |              0.015 |             0.015 |                       4.24  |                      4.206 |                  2.054 |
|      2 | BRIGHT / DARK   |            23,634 |                  4.362 |                 4.159 |            0.995 |           0.938 |              0.033 |             0.032 |              0.016 |             0.016 |                       3.886 |                      3.839 |                  2.784 |
|      2 | DARK / DARK     |            23,119 |                  3.486 |                 3.452 |            0.962 |           0.939 |              0.031 |             0.031 |              0.016 |             0.016 |                       3.575 |                      3.559 |                  2.472 |
|      3 | BACKUP / BACKUP |           200,483 |                  3.667 |                 2.944 |            1.086 |           0.872 |              0.067 |             0.048 |              0.027 |             0.022 |                       4.635 |                      4.316 |                  2.782 |
|      3 | BACKUP / BRIGHT |            43,933 |                  3.694 |                 3.579 |            0.94  |           0.909 |              0.029 |             0.028 |              0.014 |             0.014 |                       3.674 |                      3.651 |                  2.977 |
|      3 | BACKUP / DARK   |             5,475 |                  5.515 |                 5.338 |            0.947 |           0.907 |              0.03  |             0.029 |              0.012 |             0.011 |                       3.68  |                      3.649 |                  3.85  |
|      3 | BRIGHT / BRIGHT |            49,829 |                  2.929 |                 2.797 |            0.895 |           0.858 |              0.03  |             0.029 |              0.018 |             0.017 |                       4.253 |                      4.217 |                  2.04  |
|      3 | BRIGHT / DARK   |            23,716 |                  4.455 |                 4.246 |            0.996 |           0.939 |              0.033 |             0.033 |              0.016 |             0.016 |                       3.937 |                      3.881 |                  2.785 |
|      3 | DARK / DARK     |            23,620 |                  3.498 |                 3.431 |            0.959 |           0.938 |              0.031 |             0.031 |              0.016 |             0.016 |                       3.682 |                      3.664 |                  2.475 |
|      4 | BACKUP / BACKUP |           198,770 |                  3.644 |                 2.938 |            1.076 |           0.868 |              0.066 |             0.048 |              0.027 |             0.023 |                       4.532 |                      4.208 |                  2.784 |
|      4 | BACKUP / BRIGHT |            44,193 |                  3.728 |                 3.612 |            0.946 |           0.919 |              0.03  |             0.029 |              0.015 |             0.015 |                       3.898 |                      3.876 |                  2.972 |
|      4 | BACKUP / DARK   |             5,259 |                  5.593 |                 5.474 |            0.956 |           0.924 |              0.024 |             0.023 |              0.011 |             0.01  |                       3.539 |                      3.52  |                  3.816 |
|      4 | BRIGHT / BRIGHT |            50,498 |                  2.882 |                 2.76  |            0.894 |           0.851 |              0.029 |             0.028 |              0.017 |             0.017 |                       4.342 |                      4.312 |                  2.05  |
|      4 | BRIGHT / DARK   |            23,639 |                  4.307 |                 4.052 |            0.98  |           0.917 |              0.033 |             0.031 |              0.016 |             0.017 |                       3.913 |                      3.866 |                  2.82  |
|      4 | DARK / DARK     |            23,264 |                  3.455 |                 3.388 |            0.953 |           0.928 |              0.033 |             0.032 |              0.016 |             0.016 |                       3.958 |                      3.94  |                  2.484 |

Independent source-half reproducibility for nightly offsets:

|   N_COMMON_LABELS | COMMON_COMPONENT_PAIR   |   GAUGE_SHIFT_B_MINUS_A_KMS |   OFFSET_CORRELATION |   OFFSET_SLOPE_B_ON_A |   MEDIAN_ABS_DIFF_KMS |   ROBUST_WIDTH_DIFF_KMS |
|------------------:|:------------------------|----------------------------:|---------------------:|----------------------:|----------------------:|------------------------:|
|               483 | 0/0                     |                      -0.014 |                 0.98 |                 1.002 |                 0.107 |                   0.182 |

Deterministic shuffled-exposure-night-within-program control:

|   FOLD |   N_LABELS |   N_TRAIN_PAIRS |   N_EFFECTIVE_SOURCE_DRAWS |   N_CONNECTED_COMPONENTS |   LARGEST_COMPONENT_LABEL_FRACTION |   LARGEST_COMPONENT_PAIR_FRACTION |   LSQR_ISTOP |   LSQR_ITERS |   LSQR_ACOND |   LSQR_R1NORM |   LSQR_ARNORM |   N_HOLDOUT_PAIRS |   N_HOLDOUT_SAME_COMPONENT |   N_HOLDOUT_CROSS_COMPONENT |   BEFORE_RAW_WIDTH_KMS |   AFTER_RAW_WIDTH_KMS |   BEFORE_WIDTH_Z |   AFTER_WIDTH_Z |   BEFORE_TAIL_GT_3 |   AFTER_TAIL_GT_3 |   BEFORE_TAIL_GT_5 |   AFTER_TAIL_GT_5 |   BEFORE_MEAN_GAUSSIAN_PAIR_LOSS |   AFTER_MEAN_GAUSSIAN_PAIR_LOSS |   MACRO_WIDTH_BEFORE_Z |   MACRO_WIDTH_AFTER_Z |   MACRO_GAUSSIAN_PAIR_LOSS_BEFORE |   MACRO_GAUSSIAN_PAIR_LOSS_AFTER |   PERMUTATION | CONTROL                                  |
|-------:|-----------:|----------------:|---------------------------:|-------------------------:|-----------------------------------:|----------------------------------:|-------------:|-------------:|-------------:|--------------:|--------------:|------------------:|---------------------------:|----------------------------:|-----------------------:|----------------------:|-----------------:|----------------:|-------------------:|------------------:|-------------------:|------------------:|---------------------------------:|--------------------------------:|-----------------------:|----------------------:|----------------------------------:|---------------------------------:|--------------:|:-----------------------------------------|
|      0 |        526 |       1,320,024 |                    643,479 |                        1 |                                  1 |                                 1 |            2 |          136 |      483.837 |       820.052 |         0.003 |           348,461 |                    347,498 |                         963 |                  3.662 |                 3.429 |            0.954 |           0.9   |              0.044 |             0.038 |              0.019 |             0.017 |                            4.142 |                           4.037 |                  0.941 |                 0.921 |                             3.987 |                            3.949 |             0 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |
|      1 |        524 |       1,321,759 |                    644,004 |                        1 |                                  1 |                                 1 |            2 |          127 |      431.809 |       820.548 |         0.003 |           346,290 |                    345,161 |                       1,129 |                  3.659 |                 3.426 |            0.953 |           0.897 |              0.045 |             0.038 |              0.019 |             0.017 |                            4.139 |                           4.034 |                  0.937 |                 0.916 |                             3.96  |                            3.924 |             0 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |
|      2 |        525 |       1,321,734 |                    644,557 |                        1 |                                  1 |                                 1 |            2 |          133 |      463.464 |       820.49  |         0.003 |           346,600 |                    345,535 |                       1,065 |                  3.643 |                 3.424 |            0.952 |           0.898 |              0.044 |             0.038 |              0.018 |             0.017 |                            4.092 |                           3.991 |                  0.93  |                 0.911 |                             3.856 |                            3.821 |             0 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |
|      3 |        525 |       1,319,938 |                    644,236 |                        1 |                                  1 |                                 1 |            2 |          130 |      445.972 |       820.842 |         0.004 |           348,218 |                    347,201 |                       1,017 |                  3.659 |                 3.423 |            0.953 |           0.895 |              0.045 |             0.038 |              0.019 |             0.017 |                            4.08  |                           3.975 |                  0.931 |                 0.911 |                             3.861 |                            3.825 |             0 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |
|      4 |        524 |       1,320,957 |                    644,278 |                        1 |                                  1 |                                 1 |            2 |          127 |      428.915 |       821.529 |         0.003 |           347,113 |                    345,976 |                       1,137 |                  3.635 |                 3.409 |            0.949 |           0.894 |              0.044 |             0.038 |              0.019 |             0.017 |                            4.083 |                           3.979 |                  0.929 |                 0.911 |                             3.913 |                            3.881 |             0 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |
|      0 |        529 |       1,313,647 |                    647,855 |                        1 |                                  1 |                                 1 |            2 |          139 |      541.995 |       817.144 |         0.004 |           348,461 |                    347,604 |                         857 |                  3.66  |                 3.417 |            0.957 |           0.904 |              0.045 |             0.037 |              0.019 |             0.018 |                            4.151 |                           4.035 |                  0.943 |                 0.923 |                             3.98  |                            3.938 |             1 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |
|      1 |        529 |       1,315,537 |                    648,369 |                        1 |                                  1 |                                 1 |            2 |          138 |      534.614 |       817.196 |         0.004 |           346,290 |                    345,431 |                         859 |                  3.66  |                 3.412 |            0.956 |           0.901 |              0.045 |             0.037 |              0.019 |             0.018 |                            4.151 |                           4.035 |                  0.939 |                 0.916 |                             3.963 |                            3.922 |             1 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |
|      2 |        529 |       1,315,246 |                    648,925 |                        1 |                                  1 |                                 1 |            2 |          144 |      568.015 |       817.937 |         0.004 |           346,600 |                    345,791 |                         809 |                  3.644 |                 3.412 |            0.955 |           0.901 |              0.044 |             0.037 |              0.019 |             0.017 |                            4.1   |                           3.987 |                  0.931 |                 0.913 |                             3.859 |                            3.82  |             1 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |
|      3 |        529 |       1,313,772 |                    648,528 |                        1 |                                  1 |                                 1 |            2 |          138 |      523.913 |       817.848 |         0.004 |           348,218 |                    347,437 |                         781 |                  3.659 |                 3.413 |            0.957 |           0.899 |              0.045 |             0.037 |              0.019 |             0.018 |                            4.091 |                           3.974 |                  0.935 |                 0.914 |                             3.87  |                            3.831 |             1 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |
|      4 |        528 |       1,314,556 |                    648,636 |                        1 |                                  1 |                                 1 |            2 |          138 |      530.169 |       818.665 |         0.003 |           347,113 |                    346,271 |                         842 |                  3.634 |                 3.393 |            0.952 |           0.897 |              0.044 |             0.037 |              0.019 |             0.018 |                            4.088 |                           3.971 |                  0.93  |                 0.908 |                             3.908 |                            3.869 |             1 | FULL_PIPELINE_EXPOSURE_NIGHT_PERMUTATION |

## Highest-ranked constant-RV screening outliers

|            group_id | group_kind     |           source_id |            targetid |   n_epochs_good |   weighted_mean_vrad |   p_const |   max_pair_sigma |   time_baseline_days |
|--------------------:|:---------------|--------------------:|--------------------:|----------------:|---------------------:|----------:|-----------------:|---------------------:|
| 3789296645641611136 | GAIA_SOURCE_ID | 3789296645641611136 | 2305843037445561980 |               2 |                 2.49 | 1.29e-311 |            37.74 |                 6.98 |
|  555884461639037824 | GAIA_SOURCE_ID |  555884461639037824 | 2305843013353500779 |               2 |               -31.87 | 4.3e-310  |            37.64 |                 0.99 |
| 3853100274608902400 | GAIA_SOURCE_ID | 3853100274608902400 |   39627937984550133 |               2 |                68.69 | 7.85e-310 |            37.63 |                 7.99 |
| 2909306431363375232 | GAIA_SOURCE_ID | 2909306431363375232 | 2305843030885688726 |               2 |                25.26 | 1.49e-309 |            37.61 |                25.93 |
| 3135369080054535168 | GAIA_SOURCE_ID | 3135369080054535168 | 2305843032571812746 |               2 |               122.33 | 3.02e-308 |            37.53 |                27.92 |
| 1320843803780268160 | GAIA_SOURCE_ID | 1320843803780268160 | 2305843019053535709 |               2 |                19.27 | 5.37e-307 |            37.45 |                54.87 |
| 5739632120705316352 | GAIA_SOURCE_ID | 5739632120705316352 | 2305843051974624918 |               2 |                50.98 | 5.41e-301 |            37.08 |                14.94 |
| 1110080996833292928 | GAIA_SOURCE_ID | 1110080996833292928 |   39633503238750989 |               3 |              -277.57 | 5.51e-310 |            33.62 |                57.92 |
| 4352125858944266624 | GAIA_SOURCE_ID | 4352125858944266624 | 2305843041635673801 |               3 |               -22.62 | 2.66e-303 |            33.46 |                24.91 |
| 3602458593239798528 | GAIA_SOURCE_ID | 3602458593239798528 |   39627745478577178 |               3 |               -58.02 | 2.57e-304 |            33.19 |               108.71 |

## Highest-ranked strict constant-RV screening outliers

|            group_id | group_kind     |           source_id |            targetid |   n_epochs_good |   weighted_mean_vrad |   p_const |   max_pair_sigma |   time_baseline_days |
|--------------------:|:---------------|--------------------:|--------------------:|----------------:|---------------------:|----------:|-----------------:|---------------------:|
| 1110080996833292928 | GAIA_SOURCE_ID | 1110080996833292928 |   39633503238750989 |               3 |              -277.57 | 5.51e-310 |            33.62 |                57.92 |
| 4352125858944266624 | GAIA_SOURCE_ID | 4352125858944266624 | 2305843041635673801 |               3 |               -22.62 | 2.66e-303 |            33.46 |                24.91 |
| 3602458593239798528 | GAIA_SOURCE_ID | 3602458593239798528 |   39627745478577178 |               3 |               -58.02 | 2.57e-304 |            33.19 |               108.71 |
| 2922326641907644288 | GAIA_SOURCE_ID | 2922326641907644288 | 2305843030986332527 |               5 |               130.83 | 2.72e-308 |            30.22 |                84.79 |
| 3586666720047144320 | GAIA_SOURCE_ID | 3586666720047144320 | 2305843035935608655 |               5 |                86.7  | 9.07e-304 |            28.24 |                29.92 |
| 2576270509700797056 | GAIA_SOURCE_ID | 2576270509700797056 | 2305843028406829362 |               4 |               -33.86 | 1.19e-297 |            36.23 |                36.84 |
| 5687165831009399552 | GAIA_SOURCE_ID | 5687165831009399552 | 2305843051584562367 |               4 |                44.25 | 1.96e-297 |            32.92 |                65.82 |
| 3798496671748306432 | GAIA_SOURCE_ID | 3798496671748306432 | 2305843037512667964 |               5 |                62.08 | 2.77e-297 |            29.06 |                76.81 |
| 3197192179338427264 | GAIA_SOURCE_ID | 3197192179338427264 |   39627641002657592 |               3 |                72.16 | 1.01e-296 |            31.76 |               105.77 |
| 3667086443610299904 | GAIA_SOURCE_ID | 3667086443610299904 | 2305843036535398119 |               3 |               -44.46 | 3.27e-296 |            36.27 |                 5.98 |

## Required checks before interpretation

1. Reproduce documented DESI program-level radial-velocity systematics.
2. Inspect warning flags, S/N, posterior skewness/kurtosis, model residuals, and individual spectra.
3. Check whether screening outliers concentrate by night, exposure, fiber, survey, or program.
4. Compare against known variable/binary catalogues and published controls.
5. Have a domain expert review all selection assumptions and any physical interpretation.
