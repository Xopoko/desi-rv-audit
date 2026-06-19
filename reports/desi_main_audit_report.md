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

|   FOLD |   N_LABELS |   N_TRAIN_PAIRS |   N_CONNECTED_COMPONENTS |   LARGEST_COMPONENT_LABEL_FRACTION |   LARGEST_COMPONENT_PAIR_FRACTION |   LSQR_ISTOP |   LSQR_ITERS |   LSQR_ACOND |   LSQR_R1NORM |   LSQR_ARNORM |   N_HOLDOUT_PAIRS |   N_HOLDOUT_SAME_COMPONENT |   N_HOLDOUT_CROSS_COMPONENT |   BEFORE_RAW_WIDTH_KMS |   AFTER_RAW_WIDTH_KMS |   BEFORE_WIDTH_Z |   AFTER_WIDTH_Z |   BEFORE_TAIL_GT_3 |   AFTER_TAIL_GT_3 |   BEFORE_TAIL_GT_5 |   AFTER_TAIL_GT_5 |   BEFORE_MEAN_GAUSSIAN_PAIR_LOSS |   AFTER_MEAN_GAUSSIAN_PAIR_LOSS |   MACRO_WIDTH_BEFORE_Z |   MACRO_WIDTH_AFTER_Z |   MACRO_GAUSSIAN_PAIR_LOSS_BEFORE |   MACRO_GAUSSIAN_PAIR_LOSS_AFTER |   N_PROGRAM_NIGHT_PAIRS |   N_GAIA_GROUP_PAIRS |   GAIA_GROUP_PAIR_FRACTION |
|-------:|-----------:|----------------:|-------------------------:|-----------------------------------:|----------------------------------:|-------------:|-------------:|-------------:|--------------:|--------------:|------------------:|---------------------------:|----------------------------:|-----------------------:|----------------------:|-----------------:|----------------:|-------------------:|------------------:|-------------------:|------------------:|---------------------------------:|--------------------------------:|-----------------------:|----------------------:|----------------------------------:|---------------------------------:|------------------------:|---------------------:|---------------------------:|
|      0 |        516 |       1,337,041 |                        2 |                              0.996 |                             0.998 |            2 |          175 |      769.695 |       778.24  |         0.003 |           346,314 |                    344,899 |                       1,415 |                  3.651 |                 3.17  |            1.02  |           0.888 |              0.052 |             0.041 |              0.022 |             0.02  |                            4.36  |                           4.163 |                  0.977 |                 0.915 |                             4.061 |                            3.983 |               1,736,682 |            1,735,435 |                      0.999 |
|      1 |        518 |       1,335,463 |                        2 |                              0.996 |                             0.998 |            2 |          181 |      804.119 |       777.792 |         0.003 |           348,022 |                    346,861 |                       1,161 |                  3.677 |                 3.17  |            1.023 |           0.888 |              0.052 |             0.041 |              0.022 |             0.02  |                            4.367 |                           4.167 |                  0.98  |                 0.912 |                             4.015 |                            3.936 |               1,736,682 |            1,735,435 |                      0.999 |
|      2 |        515 |       1,336,433 |                        2 |                              0.996 |                             0.998 |            2 |          171 |      741.248 |       778.294 |         0.004 |           346,297 |                    344,922 |                       1,375 |                  3.658 |                 3.163 |            1.019 |           0.886 |              0.051 |             0.04  |              0.022 |             0.019 |                            4.403 |                           4.207 |                  0.969 |                 0.905 |                             4.043 |                            3.964 |               1,736,682 |            1,735,435 |                      0.999 |
|      3 |        516 |       1,333,839 |                        2 |                              0.996 |                             0.998 |            2 |          164 |      695.748 |       778.039 |         0.004 |           349,343 |                    347,988 |                       1,355 |                  3.636 |                 3.144 |            1.015 |           0.882 |              0.051 |             0.04  |              0.022 |             0.02  |                            4.281 |                           4.082 |                  0.968 |                 0.906 |                             3.952 |                            3.872 |               1,736,682 |            1,735,435 |                      0.999 |
|      4 |        517 |       1,336,250 |                        2 |                              0.996 |                             0.998 |            2 |          161 |      673.205 |       778.303 |         0.004 |           346,706 |                    345,476 |                       1,230 |                  3.635 |                 3.136 |            1.017 |           0.882 |              0.051 |             0.04  |              0.022 |             0.019 |                            4.38  |                           4.183 |                  0.968 |                 0.905 |                             4.082 |                            4.005 |               1,736,682 |            1,735,435 |                      0.999 |

Fold-level holdout diagnostics by program pair:

|   FOLD | PROGRAM_PAIR    |   N_HOLDOUT_PAIRS |   RAW_WIDTH_BEFORE_KMS |   RAW_WIDTH_AFTER_KMS |   WIDTH_BEFORE_Z |   WIDTH_AFTER_Z |   TAIL_GT_3_BEFORE |   TAIL_GT_3_AFTER |   TAIL_GT_5_BEFORE |   TAIL_GT_5_AFTER |   GAUSSIAN_PAIR_LOSS_BEFORE |   GAUSSIAN_PAIR_LOSS_AFTER |   TRAIN_PAIR_FLOOR_KMS |
|-------:|:----------------|------------------:|-----------------------:|----------------------:|-----------------:|----------------:|-------------------:|------------------:|-------------------:|------------------:|----------------------------:|---------------------------:|-----------------------:|
|      0 | BACKUP / BACKUP |           198,365 |                  3.666 |                 2.957 |            1.081 |           0.876 |              0.067 |             0.048 |              0.027 |             0.023 |                       4.585 |                      4.264 |                  2.779 |
|      0 | BACKUP / BRIGHT |            44,157 |                  3.72  |                 3.621 |            0.945 |           0.919 |              0.031 |             0.03  |              0.015 |             0.015 |                       3.873 |                      3.853 |                  2.969 |
|      0 | BACKUP / DARK   |             5,512 |                  5.629 |                 5.649 |            0.98  |           0.964 |              0.028 |             0.029 |              0.013 |             0.014 |                       3.767 |                      3.738 |                  3.743 |
|      0 | BRIGHT / BRIGHT |            50,099 |                  2.888 |                 2.785 |            0.891 |           0.852 |              0.03  |             0.029 |              0.017 |             0.017 |                       4.429 |                      4.401 |                  2.046 |
|      0 | BRIGHT / DARK   |            23,634 |                  4.393 |                 4.153 |            0.994 |           0.928 |              0.036 |             0.035 |              0.017 |             0.017 |                       3.943 |                      3.883 |                  2.787 |
|      0 | DARK / DARK     |            23,132 |                  3.535 |                 3.478 |            0.971 |           0.952 |              0.034 |             0.034 |              0.018 |             0.018 |                       3.769 |                      3.757 |                  2.465 |
|      1 | BACKUP / BACKUP |           199,742 |                  3.691 |                 2.953 |            1.089 |           0.874 |              0.067 |             0.048 |              0.027 |             0.022 |                       4.67  |                      4.342 |                  2.778 |
|      1 | BACKUP / BRIGHT |            44,106 |                  3.753 |                 3.628 |            0.957 |           0.921 |              0.031 |             0.03  |              0.015 |             0.015 |                       3.738 |                      3.72  |                  2.967 |
|      1 | BACKUP / DARK   |             5,834 |                  5.717 |                 5.556 |            0.987 |           0.945 |              0.029 |             0.03  |              0.012 |             0.012 |                       3.696 |                      3.664 |                  3.765 |
|      1 | BRIGHT / BRIGHT |            50,110 |                  2.916 |                 2.776 |            0.893 |           0.857 |              0.029 |             0.028 |              0.017 |             0.017 |                       4.268 |                      4.238 |                  2.048 |
|      1 | BRIGHT / DARK   |            23,840 |                  4.421 |                 4.185 |            1.001 |           0.942 |              0.033 |             0.033 |              0.018 |             0.018 |                       4.013 |                      3.96  |                  2.782 |
|      1 | DARK / DARK     |            23,229 |                  3.467 |                 3.399 |            0.957 |           0.937 |              0.033 |             0.033 |              0.017 |             0.017 |                       3.706 |                      3.689 |                  2.48  |
|      2 | BACKUP / BACKUP |           198,295 |                  3.677 |                 2.953 |            1.085 |           0.874 |              0.067 |             0.049 |              0.027 |             0.022 |                       4.607 |                      4.287 |                  2.779 |
|      2 | BACKUP / BRIGHT |            43,822 |                  3.708 |                 3.594 |            0.937 |           0.912 |              0.028 |             0.027 |              0.013 |             0.013 |                       3.875 |                      3.855 |                  2.975 |
|      2 | BACKUP / DARK   |             5,291 |                  5.622 |                 5.462 |            0.952 |           0.922 |              0.023 |             0.022 |              0.009 |             0.009 |                       3.518 |                      3.49  |                  3.848 |
|      2 | BRIGHT / BRIGHT |            50,527 |                  2.914 |                 2.799 |            0.895 |           0.859 |              0.029 |             0.028 |              0.016 |             0.016 |                       4.768 |                      4.733 |                  2.043 |
|      2 | BRIGHT / DARK   |            23,661 |                  4.411 |                 4.198 |            0.992 |           0.933 |              0.032 |             0.031 |              0.016 |             0.016 |                       3.888 |                      3.838 |                  2.786 |
|      2 | DARK / DARK     |            23,326 |                  3.498 |                 3.436 |            0.955 |           0.932 |              0.031 |             0.03  |              0.016 |             0.016 |                       3.6   |                      3.582 |                  2.482 |
|      3 | BACKUP / BACKUP |           200,160 |                  3.641 |                 2.929 |            1.076 |           0.866 |              0.067 |             0.048 |              0.027 |             0.023 |                       4.612 |                      4.29  |                  2.787 |
|      3 | BACKUP / BRIGHT |            44,479 |                  3.723 |                 3.612 |            0.945 |           0.919 |              0.031 |             0.03  |              0.015 |             0.015 |                       3.733 |                      3.705 |                  2.967 |
|      3 | BACKUP / DARK   |             5,455 |                  5.487 |                 5.29  |            0.936 |           0.914 |              0.027 |             0.026 |              0.011 |             0.01  |                       3.826 |                      3.804 |                  3.877 |
|      3 | BRIGHT / BRIGHT |            50,491 |                  2.923 |                 2.797 |            0.897 |           0.857 |              0.028 |             0.028 |              0.016 |             0.016 |                       3.964 |                      3.93  |                  2.044 |
|      3 | BRIGHT / DARK   |            23,752 |                  4.417 |                 4.18  |            0.993 |           0.941 |              0.032 |             0.031 |              0.016 |             0.016 |                       3.888 |                      3.834 |                  2.784 |
|      3 | DARK / DARK     |            23,651 |                  3.482 |                 3.388 |            0.958 |           0.938 |              0.032 |             0.032 |              0.016 |             0.016 |                       3.691 |                      3.668 |                  2.481 |
|      4 | BACKUP / BACKUP |           199,450 |                  3.642 |                 2.924 |            1.077 |           0.866 |              0.065 |             0.047 |              0.026 |             0.022 |                       4.587 |                      4.269 |                  2.787 |
|      4 | BACKUP / BRIGHT |            44,224 |                  3.711 |                 3.593 |            0.945 |           0.915 |              0.028 |             0.028 |              0.014 |             0.014 |                       3.78  |                      3.758 |                  2.976 |
|      4 | BACKUP / DARK   |             5,591 |                  5.464 |                 5.343 |            0.937 |           0.926 |              0.025 |             0.024 |              0.012 |             0.011 |                       3.557 |                      3.533 |                  3.812 |
|      4 | BRIGHT / BRIGHT |            49,889 |                  2.89  |                 2.746 |            0.892 |           0.852 |              0.029 |             0.028 |              0.017 |             0.017 |                       4.497 |                      4.457 |                  2.056 |
|      4 | BRIGHT / DARK   |            23,240 |                  4.336 |                 4.126 |            0.999 |           0.931 |              0.032 |             0.031 |              0.015 |             0.015 |                       3.752 |                      3.703 |                  2.782 |
|      4 | DARK / DARK     |            23,082 |                  3.486 |                 3.43  |            0.956 |           0.937 |              0.036 |             0.036 |              0.02  |             0.019 |                       4.318 |                      4.308 |                  2.471 |

Independent source-half reproducibility for nightly offsets:

|   N_COMMON_LABELS | COMMON_COMPONENT_PAIR   |   GAUGE_SHIFT_B_MINUS_A_KMS |   OFFSET_CORRELATION |   OFFSET_SLOPE_B_ON_A |   MEDIAN_ABS_DIFF_KMS |   ROBUST_WIDTH_DIFF_KMS |
|------------------:|:------------------------|----------------------------:|---------------------:|----------------------:|----------------------:|------------------------:|
|               484 | 1/1                     |                      -0.002 |                 0.98 |                 0.994 |                 0.096 |                   0.174 |

Deterministic shuffled-exposure-night-within-program control:

|   FOLD |   N_LABELS |   N_TRAIN_PAIRS |   N_CONNECTED_COMPONENTS |   LARGEST_COMPONENT_LABEL_FRACTION |   LARGEST_COMPONENT_PAIR_FRACTION |   LSQR_ISTOP |   LSQR_ITERS |   LSQR_ACOND |   LSQR_R1NORM |   LSQR_ARNORM |   N_HOLDOUT_PAIRS |   N_HOLDOUT_SAME_COMPONENT |   N_HOLDOUT_CROSS_COMPONENT |   BEFORE_RAW_WIDTH_KMS |   AFTER_RAW_WIDTH_KMS |   BEFORE_WIDTH_Z |   AFTER_WIDTH_Z |   BEFORE_TAIL_GT_3 |   AFTER_TAIL_GT_3 |   BEFORE_TAIL_GT_5 |   AFTER_TAIL_GT_5 |   BEFORE_MEAN_GAUSSIAN_PAIR_LOSS |   AFTER_MEAN_GAUSSIAN_PAIR_LOSS |   MACRO_WIDTH_BEFORE_Z |   MACRO_WIDTH_AFTER_Z |   MACRO_GAUSSIAN_PAIR_LOSS_BEFORE |   MACRO_GAUSSIAN_PAIR_LOSS_AFTER |   PERMUTATION | CONTROL                                |
|-------:|-----------:|----------------:|-------------------------:|-----------------------------------:|----------------------------------:|-------------:|-------------:|-------------:|--------------:|--------------:|------------------:|---------------------------:|----------------------------:|-----------------------:|----------------------:|-----------------:|----------------:|-------------------:|------------------:|-------------------:|------------------:|---------------------------------:|--------------------------------:|-----------------------:|----------------------:|----------------------------------:|---------------------------------:|--------------:|:---------------------------------------|
|      0 |        522 |       1,318,624 |                        1 |                                  1 |                                 1 |            2 |          119 |      394.572 |       839.112 |         0.003 |           342,263 |                    341,197 |                       1,066 |                  3.668 |                 3.574 |            0.924 |           0.903 |              0.042 |             0.038 |              0.018 |             0.017 |                            4.006 |                           3.948 |                  0.922 |                 0.918 |                             3.902 |                            3.88  |             0 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |
|      1 |        524 |       1,317,153 |                        1 |                                  1 |                                 1 |            2 |          131 |      472.732 |       838.946 |         0.003 |           344,028 |                    343,074 |                         954 |                  3.694 |                 3.588 |            0.928 |           0.906 |              0.041 |             0.037 |              0.017 |             0.017 |                            4.003 |                           3.942 |                  0.928 |                 0.921 |                             3.859 |                            3.838 |             0 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |
|      2 |        523 |       1,318,453 |                        1 |                                  1 |                                 1 |            2 |          116 |      378.775 |       839.322 |         0.003 |           342,364 |                    341,299 |                       1,065 |                  3.675 |                 3.575 |            0.924 |           0.901 |              0.041 |             0.037 |              0.017 |             0.016 |                            4.036 |                           3.979 |                  0.918 |                 0.911 |                             3.88  |                            3.859 |             0 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |
|      3 |        521 |       1,315,433 |                        1 |                                  1 |                                 1 |            2 |          114 |      368.68  |       838.931 |         0.003 |           345,266 |                    344,087 |                       1,179 |                  3.654 |                 3.566 |            0.921 |           0.902 |              0.041 |             0.037 |              0.017 |             0.017 |                            3.935 |                           3.876 |                  0.916 |                 0.915 |                             3.81  |                            3.789 |             0 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |
|      4 |        524 |       1,318,201 |                        1 |                                  1 |                                 1 |            2 |          116 |      379.341 |       839.416 |         0.003 |           342,639 |                    341,695 |                         944 |                  3.652 |                 3.558 |            0.921 |           0.901 |              0.041 |             0.036 |              0.017 |             0.016 |                            4.025 |                           3.967 |                  0.915 |                 0.91  |                             3.927 |                            3.906 |             0 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |
|      0 |        529 |       1,320,961 |                        1 |                                  1 |                                 1 |            2 |          129 |      450.426 |       842.353 |         0.004 |           343,312 |                    342,572 |                         740 |                  3.653 |                 3.541 |            0.931 |           0.903 |              0.043 |             0.04  |              0.018 |             0.018 |                            4.036 |                           3.996 |                  0.924 |                 0.917 |                             3.917 |                            3.903 |             1 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |
|      1 |        529 |       1,319,433 |                        1 |                                  1 |                                 1 |            2 |          131 |      463.385 |       842.606 |         0.004 |           344,890 |                    344,181 |                         709 |                  3.679 |                 3.554 |            0.935 |           0.907 |              0.042 |             0.04  |              0.018 |             0.017 |                            4.027 |                           3.987 |                  0.93  |                 0.921 |                             3.868 |                            3.853 |             1 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |
|      2 |        528 |       1,320,692 |                        1 |                                  1 |                                 1 |            2 |          132 |      472.8   |       843.441 |         0.004 |           343,183 |                    342,297 |                         886 |                  3.66  |                 3.53  |            0.93  |           0.901 |              0.042 |             0.039 |              0.017 |             0.017 |                            4.066 |                           4.026 |                  0.919 |                 0.914 |                             3.886 |                            3.875 |             1 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |
|      3 |        529 |       1,317,938 |                        1 |                                  1 |                                 1 |            2 |          129 |      450.891 |       842.482 |         0.004 |           346,247 |                    345,527 |                         720 |                  3.64  |                 3.527 |            0.927 |           0.9   |              0.042 |             0.04  |              0.018 |             0.018 |                            3.971 |                           3.931 |                  0.918 |                 0.914 |                             3.827 |                            3.815 |             1 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |
|      4 |        530 |       1,320,506 |                        1 |                                  1 |                                 1 |            2 |          138 |      506.926 |       843.097 |         0.004 |           343,555 |                    342,889 |                         666 |                  3.639 |                 3.517 |            0.928 |           0.898 |              0.041 |             0.039 |              0.017 |             0.017 |                            4.058 |                           4.016 |                  0.918 |                 0.913 |                             3.94  |                            3.924 |             1 | SHUFFLED_EXPOSURE_NIGHT_WITHIN_PROGRAM |

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
