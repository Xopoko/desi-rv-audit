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

## Official DESI Acknowledgment

This research used data obtained with the Dark Energy Spectroscopic Instrument
(DESI). DESI construction and operations is managed by the Lawrence Berkeley
National Laboratory. This material is based upon work supported by the U.S.
Department of Energy, Office of Science, Office of High-Energy Physics, under
Contract No. DE–AC02–05CH11231, and by the National Energy Research Scientific
Computing Center, a DOE Office of Science User Facility under the same contract.

Additional support for DESI was provided by the U.S. National Science Foundation
(NSF), Division of Astronomical Sciences under Contract No. AST-0950945 to the
NSF’s National Optical-Infrared Astronomy Research Laboratory; the Science and
Technology Facilities Council of the United Kingdom; the Gordon and Betty Moore
Foundation; the Heising-Simons Foundation; the French Alternative Energies and
Atomic Energy Commission (CEA); the National Council of Humanities, Science and
Technology of Mexico (CONAHCYT); the Ministry of Science and Innovation of Spain
(MICINN), and by the DESI Member Institutions:
https://www.desi.lbl.gov/collaborating-institutions.

The DESI collaboration is honored to be permitted to conduct scientific research
on I’oligam Du’ag (Kitt Peak), a mountain with particular significance to the
Tohono O’odham Nation. Any opinions, findings, and conclusions or
recommendations expressed in this material are those of the author(s) and do not
necessarily reflect the views of the U.S. National Science Foundation, the U.S.
Department of Energy, or any of the listed funding agencies.

## Official DESI Disclaimer

The DESI collaboration is responsible for this website, ensuring that its
content is accurate and up to date. However, it takes no responsibility for
errors or omissions. The DESI collaboration accepts no liability for any loss or
damage resulting from the use of material from this website.

## Official DESI Thanks to Colleagues and Supporters

We would like to acknowledge the countless colleagues, friends, and family
members whose support has been invaluable throughout DESI’s development from its
initial planning to this data release. Their contributions, both professional
and personal, have been essential to the success of this project. We especially
remember those who are no longer with us but whose work and dedication continue
to influence and inspire our scientific endeavors.

Their legacy lives on through this data and the discoveries it will enable.
