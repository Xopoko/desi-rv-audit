---
explanation_id: sources
concepts:
  - desi
  - spectrum
  - doppler-shift
  - radial-velocity
  - epoch
  - repeat-observation
  - source-identity
  - program
  - observing-night
  - petal
  - quality-cut
  - velocity-correction
  - uncertainty-floor
  - residual
  - robust-width
  - source-disjoint
  - permutation-control
  - bootstrap
  - empirical-p-value
  - correlation
  - pass-null
  - exploratory-analysis
  - dark-matter
  - dark-energy
  - bao
claims:
  - SCOPE-STELLAR
  - SCOPE-DARK-ENERGY
  - SCOPE-DARK-MATTER
  - MEASUREMENT-RV
  - INSTRUMENT-PETAL
  - BASELINE-NIGHT
  - BASELINE-REPLICATION
  - E1-TEMPORAL
  - E2-COHERENCE-NULL
  - E3-PETAL
  - BOUNDARY-OUTLIERS
  - BOUNDARY-EXPLORATORY
sources:
  - S-DESI-DR1-STELLAR-PAPER
  - S-DESI-DR1-STELLAR-DOC
  - S-DESI-MWS-OVERVIEW
  - S-DESI-DR1-BAO
  - S-DESI-GLOSSARY
  - S-DESI-FOCAL-PLANE
  - S-RVSPECFIT
  - S-DARK-MATTER-KINEMATICS
  - S-BACKUP-CORRECTION
  - S-DESI-ACKNOWLEDGMENTS
  - S-GAIA-DR3
---

# Sources and Provenance

[Start](README.md) -> [Evidence map](07_evidence_map.md) -> **Sources**

This is the human-readable view of every record in
[`sources.json`](sources.json). The registry was checked on **2026-08-08**.
Machine-readable IDs, URLs, types, stable identifiers, dates, and roles remain
authoritative in that JSON file.

## External context is not repository evidence

This distinction is essential:

- An **external source** can establish what DESI is, what a catalogue contains,
  how radial velocities are produced, what PETAL means, or how BAO and Galactic
  dynamics connect to wider science.
- **Repository evidence** is a committed local CSV, JSON, or report produced by
  this analysis. It supports outcomes such as the 13.55% baseline improvement,
  the E2 null result, or the E3 PETAL-associated gain.
- An external source may define an input to a repository result without proving
  the result. For example, the focal-plane pages define PETAL; the local E3
  artifacts carry the numerical residual result.

Exact local evidence paths and reproduction lanes are listed in the
[evidence map](07_evidence_map.md). A claim with no external source ID is not
source-free when it has named repository evidence.

## Claim-to-source crosswalk

| Claim | External source IDs | What carries the project-specific outcome? |
|---|---|---|
| `SCOPE-STELLAR` | `S-DESI-DR1-STELLAR-PAPER`, `S-DESI-DR1-STELLAR-DOC`, `S-DESI-DR1-BAO` | External scope plus the root README |
| `SCOPE-DARK-ENERGY` | `S-DESI-DR1-BAO`, `S-DESI-DR1-STELLAR-PAPER` | A boundary; no local dark-energy result exists |
| `SCOPE-DARK-MATTER` | `S-DESI-MWS-OVERVIEW`, `S-DARK-MATTER-KINEMATICS` | A boundary; no local dark-matter result exists |
| `MEASUREMENT-RV` | `S-DESI-DR1-STELLAR-DOC`, `S-RVSPECFIT`, `S-DESI-DR1-STELLAR-PAPER` | External measurement context plus the root README |
| `INSTRUMENT-PETAL` | `S-DESI-GLOSSARY`, `S-DESI-FOCAL-PLANE` | Official geometry plus local `petal_validation.csv` |
| `BASELINE-NIGHT` | `S-DESI-DR1-STELLAR-PAPER`, `S-BACKUP-CORRECTION` | Local baseline CSVs and report |
| `BASELINE-REPLICATION` | none | Local reproducibility CSVs |
| `E1-TEMPORAL` | none | Local discovery-bundle CSVs |
| `E2-COHERENCE-NULL` | none | Local discovery-bundle CSVs |
| `E3-PETAL` | `S-DESI-GLOSSARY`, `S-DESI-FOCAL-PLANE` | Local PETAL CSVs; external pages define only the label |
| `BOUNDARY-OUTLIERS` | none | Root README and local audit report |
| `BOUNDARY-EXPLORATORY` | none | Root README, research plan, and discovery report |

## S-DESI-DR1-STELLAR-PAPER

**Title:** [DESI Data Release 1: Stellar Catalogue](https://arxiv.org/abs/2505.14787)

- **Type:** `primary_paper`
- **Stable identifier:** `arXiv:2505.14787`
- **Scope:** the DESI DR1 Milky Way stellar value-added catalogue, not the
  extragalactic BAO analysis.
- **Role here:** catalogue scope, single-epoch radial velocities, precision,
  and documented DR1 systematics.
- **Boundary:** this paper supplies published context. It does not by itself
  establish any numerical result calculated by this repository.

## S-DESI-DR1-STELLAR-DOC

**Title:** [DESI DR1 Stellar Catalogue of Radial Velocities, Abundances, and Atmospheric Parameters](https://data.desi.lbl.gov/doc/releases/dr1/vac/mws/)

- **Type:** `official_documentation`
- **Stable identifier:** `DESI-DR1-MWS-VAC`
- **Scope:** the official release page for the DR1 stellar catalogue.
- **Role here:** catalogue contents, pipeline provenance, and documented
  repeat-observation counts.
- **Boundary:** the product guide explains what was released; it does not prove
  the audit's residual findings.

## S-DESI-MWS-OVERVIEW

**Title:** [Overview of the DESI Milky Way Survey](https://arxiv.org/abs/2208.08514)

- **Type:** `primary_paper`
- **Stable identifier:** `arXiv:2208.08514`
- **Scope:** the goals and design of the DESI Milky Way Survey.
- **Role here:** stellar kinematics, radial-velocity performance, and the route
  from DESI stellar measurements to later Milky Way science.
- **Boundary:** a survey goal is not a dark-matter inference performed by this
  repository.

## S-DESI-DR1-BAO

**Title:** [DESI 2024 VI: Cosmological Constraints from the Measurements of Baryon Acoustic Oscillations](https://arxiv.org/abs/2404.03002)

- **Type:** `primary_paper`
- **Stable identifier:** `arXiv:2404.03002`
- **Scope:** the separate DESI cosmology analysis using extragalactic tracers.
- **Role here:** documents the route from galaxy, quasar, and Lyman-alpha
  forest measurements through BAO to cosmological and dark-energy constraints.
- **Boundary:** its tracer sample and inference are not the repeat-star audit in
  this repository.

## S-DESI-GLOSSARY

**Title:** [DESI Data Glossary](https://data.desi.lbl.gov/doc/glossary/)

- **Type:** `official_documentation`
- **Stable identifier:** `DESI-DATA-GLOSSARY`
- **Scope:** official DESI data terminology.
- **Role here:** definitions of fiber, focal plane, PETAL, program, spectrum,
  and spectrograph.
- **Boundary:** terminology and geometry do not identify the physical cause of
  a statistical association.

## S-DESI-FOCAL-PLANE

**Title:** [DESI Focal Plane System](https://www.desi.lbl.gov/focal-plane-system/)

- **Type:** `official_documentation`
- **Stable identifier:** `DESI-FOCAL-PLANE`
- **Scope:** the physical layout of the DESI focal plane.
- **Role here:** documents 5,000 positioners arranged into ten wedges of 500
  fibers, providing context for the PETAL label.
- **Boundary:** focal-plane geometry alone does not prove that E3 is a hardware
  fault or locate a causal subsystem.

## S-RVSPECFIT

**Title:** [RVSpecFit: Automated Spectroscopic Pipeline](https://rvspecfit.readthedocs.io/en/latest/)

- **Type:** `software_documentation`
- **Stable identifier:** `RVSPECFIT-DOCS`
- **Scope:** the stellar-template fitting software used in the DESI catalogue
  provenance.
- **Role here:** explains how spectra can be fitted with stellar templates to
  obtain radial velocities and stellar parameters.
- **Boundary:** this repository audits released fitted velocities; it does not
  use this source as evidence for its own numerical audit outcomes.

## S-DARK-MATTER-KINEMATICS

**Title:** [The Local Dark Matter Density](https://arxiv.org/abs/1404.1938)

- **Type:** `scholarly_review`
- **Stable identifier:** `doi:10.1088/0954-3899/41/6/063101`
- **Scope:** a review of how local stellar positions and velocities can inform
  Galactic mass and dark-matter inference.
- **Role here:** supports the broad scientific connection between calibrated
  stellar kinematics and possible later dark-matter studies.
- **Boundary:** the connection is contextual. This repository performs no
  dynamical dark-matter fit.

## S-BACKUP-CORRECTION

**Title:** [DESI DR1 radial velocity correction for the backup program of the main survey](https://doi.org/10.5281/zenodo.15469272)

- **Type:** `data_release`
- **Stable identifier:** `doi:10.5281/zenodo.15469272`
- **Scope:** the published DESI DR1 BACKUP-program correction consumed by this
  repository.
- **Role here:** supplies the correction table applied to matched
  `MAIN/BACKUP` rows before the audit.
- **Boundary:** this external correction is not the diagnostic
  `PROGRAM:NIGHT` offset model, and the repository does not propose its offsets
  as a replacement catalogue correction.

## S-DESI-ACKNOWLEDGMENTS

**Title:** [DESI Data License and Acknowledgments](https://data.desi.lbl.gov/doc/acknowledgments/)

- **Type:** `official_documentation`
- **Stable identifier:** `DESI-DATA-LICENSE`
- **Scope:** terms and acknowledgment requirements for DESI data and
  DESI-derived artifacts.
- **Role here:** records the CC BY 4.0 terms and the required DESI
  acknowledgment route.
- **Boundary:** this is a licensing and attribution source, not scientific
  evidence for an audit claim.

## S-GAIA-DR3

**Title:** [Gaia Data Release 3 contents summary](https://www.cosmos.esa.int/web/gaia/dr3)

- **Type:** `official_documentation`
- **Stable identifier:** `GAIA-DR3`
- **Scope:** the Gaia DR3 release and its source identifiers.
- **Role here:** provides context for the Gaia `SOURCE_ID` values used to group
  repeat observations of the same star when available.
- **Boundary:** an identifier supports grouping; it does not establish the
  repository's statistical outcomes.

## Data, license, and acknowledgment note

The root [README](../README.md#reproducibility-bundle) states that the
multi-gigabyte raw DESI FITS files are not committed. The repository keeps
compact derived CSV, JSON, Markdown, and plot artifacts so readers can inspect
the evidence without redistributing the raw catalogue bundle.

DESI-derived data and artifacts remain subject to the upstream terms and
acknowledgment requirements recorded by
[`S-DESI-ACKNOWLEDGMENTS`](#s-desi-acknowledgments). The source registry records
links and provenance; it does not copy the papers, documentation, or catalogue
into this explanation. Anyone downloading or redistributing upstream data
should recheck the official terms at the stable link.

## Maintenance rule

Do not silently replace a source because a URL moves. Update
[`sources.json`](sources.json) first, preserve the stable identifier, record a
new `checked_at` date, and then update this page and every affected claim. For a
changed repository result, update the named local evidence and claim ledger;
adding an external citation is not a substitute.

Back to: [Evidence map](07_evidence_map.md)
