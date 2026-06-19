# Data License and Acknowledgments

The source code in this repository is licensed under the MIT License.

DESI data products used by this audit are not covered by the repository's MIT
code license. DESI data are distributed under the Creative Commons Attribution
4.0 International License, with release-paper citation, change-disclosure, and
acknowledgment requirements documented by DESI:

https://data.desi.lbl.gov/doc/acknowledgments/

The compact CSV and PNG files under `reports/program_night_artifacts/` are
transformed/derived artifacts from public DESI DR1 data and should be treated as
DESI-derived data products under those DESI terms.

This audit uses and transforms:

- DESI DR1 stellar catalogue single-epoch radial-velocity files.
- The DESI DR1 backup-program radial-velocity correction dataset.

Backup correction dataset:

- Title: DESI DR1 radial velocity correction for the backup program of the main survey
- Creator: Sergey Koposov
- DOI: 10.5281/zenodo.15469272
- License: Creative Commons Attribution 4.0 International
- File used: `backup_correction.fits`
- Published MD5: `f48a4b21b541e94d61f4372f4c555f12`

Transformations applied in this repository include quality filtering,
source-grouped repeat-observation pairing, applying the published backup
velocity offset to `MAIN/BACKUP` rows, adding program-level uncertainty floors,
and fitting source-disjoint `PROGRAM:NIGHT` residual diagnostics.

Publications, reports, or derived works using these artifacts should cite the
DESI DR1 release paper, the DESI DR1 Stellar Catalogue paper, and the Zenodo
backup-correction dataset, and should include the official DESI acknowledgment
text from the DESI data-license page above.
