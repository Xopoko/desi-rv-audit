---
explanation_id: evidence-map
concepts:
  - desi
  - radial-velocity
  - observing-night
  - petal
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
---

# Evidence Map: From Each Claim to Its Support

[Start](README.md) -> [What the project found](05_what_we_found.md) -> **Evidence map**

This page answers one practical question: **where can I check each statement?**
It follows the machine-readable records in [the claim ledger](claims.jsonl).

## First, separate three kinds of statement

- **External context** describes DESI, its catalogue, or its instrument. Its
  main support is a paper or official page in [the source registry](SOURCES.md).
- A **repository result** is an outcome calculated by this project. Its main
  support is a committed CSV or report. An external source can define an input
  or instrument label, but it cannot prove the project's numerical result.
- A **scope boundary** says what was not established. It may be supported by
  external context, repository records, or both.

The status words below are literal ledger values. `pass` means declared gates
were met in this analysis. `null` means the tested claim did not pass. Neither
word means universal scientific proof.

## Status at a glance

| Claim | Ledger kind | Status | Main human page | Reproduction lane |
|---|---|---|---|---|
| `SCOPE-STELLAR` | external context | `established_context` | [Big picture](01_big_picture.md) | Source check |
| `SCOPE-DARK-ENERGY` | scope boundary | `not_directly_tested` | [Dark matter and dark energy](06_dark_matter_and_dark_energy.md) | Scope-and-source check |
| `SCOPE-DARK-MATTER` | scope boundary | `not_directly_tested` | [Dark matter and dark energy](06_dark_matter_and_dark_energy.md) | Scope-and-source check |
| `MEASUREMENT-RV` | external context | `established_context` | [Light to velocity](02_light_to_velocity.md) | Source check |
| `INSTRUMENT-PETAL` | external context | `established_context` | [Light to velocity](02_light_to_velocity.md) | Source plus committed validation |
| `BASELINE-NIGHT` | repository result | `pass` | [Why audit?](03_why_audit.md) and [Findings](05_what_we_found.md) | Committed evidence or full audit |
| `BASELINE-REPLICATION` | repository result | `pass` | [How evidence works](04_how_evidence_works.md) and [Findings](05_what_we_found.md) | Committed evidence or full audit |
| `E1-TEMPORAL` | repository result | `pass` | [Findings](05_what_we_found.md) | Discovery bundle |
| `E2-COHERENCE-NULL` | repository result | `null` | [Findings](05_what_we_found.md) | Discovery bundle |
| `E3-PETAL` | repository result | `pass` | [Findings](05_what_we_found.md) | Discovery bundle |
| `BOUNDARY-OUTLIERS` | scope boundary | `screening_only` | [Why audit?](03_why_audit.md) and [Findings](05_what_we_found.md) | Report review |
| `BOUNDARY-EXPLORATORY` | scope boundary | `exploratory` | [How evidence works](04_how_evidence_works.md) and [Findings](05_what_we_found.md) | Design-record review |

## How to use a reproduction lane

The cheapest lane is listed first for each claim.

1. **Source check:** open the stable external records and confirm that their
   scope supports the context statement. This is not a rerun of the repository.
2. **Committed-evidence check:** inspect the named, small CSV or report already
   in this repository. No raw DESI FITS download is required.
3. **Bundle verification:** from a prepared Python environment at the repository
   root, run:

   ```text
   python experiments/2026-07-13_novel_signals/verify_bundle.py
   ```

   This checks the discovery decisions, controls, provenance, and retained
   artifact hashes. It does not recompute the analysis from raw FITS files.
4. **Full rerun:** use **Reproduce the MAIN Audit** in the root
   [README](../README.md#reproduce-the-main-audit) for the baseline, or run the
   discovery bundle after its inputs are present:

   ```text
   python experiments/2026-07-13_novel_signals/run_all.py --workers 10
   ```

   These are data-bearing, high-cost lanes. They are not necessary for tracing
   the committed results.

## External context and scope boundaries

### SCOPE-STELLAR — `established_context`

**Statement in plain language:** this repository uses the DESI DR1 stellar
radial-velocity catalogue, not the extragalactic BAO catalogue used for DESI
cosmology.

- **Human pages:** [The big picture](01_big_picture.md) and
  [Dark matter and dark energy](06_dark_matter_and_dark_energy.md).
- **External sources:**
  [`S-DESI-DR1-STELLAR-PAPER`](SOURCES.md#s-desi-dr1-stellar-paper),
  [`S-DESI-DR1-STELLAR-DOC`](SOURCES.md#s-desi-dr1-stellar-doc), and
  [`S-DESI-DR1-BAO`](SOURCES.md#s-desi-dr1-bao).
- **Repository evidence:** [`README.md`](../README.md) states the analysed
  catalogue and the independent-audit scope.
- **Reproduction lane:** compare the stellar catalogue's documented contents
  with the BAO paper's tracer sample, then confirm that the root README names
  stellar single-epoch radial velocities as the input.
- **Does not establish:** the instrument name alone does not tell us which DESI
  sample a result used.

### SCOPE-DARK-ENERGY — `not_directly_tested`

**Statement in plain language:** DESI can constrain dark-energy models through
extragalactic BAO measurements, but this repository estimates no cosmological
parameter.

- **Human pages:** [The big picture](01_big_picture.md) and
  [Dark matter and dark energy](06_dark_matter_and_dark_energy.md).
- **External sources:**
  [`S-DESI-DR1-BAO`](SOURCES.md#s-desi-dr1-bao) for the cosmology route and
  [`S-DESI-DR1-STELLAR-PAPER`](SOURCES.md#s-desi-dr1-stellar-paper) for the
  different stellar catalogue used here.
- **Repository evidence:** none is required for a result, because the claim is
  explicitly that dark energy was not measured here.
- **Reproduction lane:** compare the two documented samples and search the
  repository's stated outputs for a cosmological parameter fit. The expected
  result is that there is none.
- **Does not establish:** calibration relevance to wider DESI science is not a
  dark-energy measurement.

### SCOPE-DARK-MATTER — `not_directly_tested`

**Statement in plain language:** stellar motion can be an input to Galactic
mass modelling, but this repository fits no Galactic mass or dark-matter model.

- **Human pages:** [The big picture](01_big_picture.md) and
  [Dark matter and dark energy](06_dark_matter_and_dark_energy.md).
- **External sources:**
  [`S-DESI-MWS-OVERVIEW`](SOURCES.md#s-desi-mws-overview) and the scholarly
  review [`S-DARK-MATTER-KINEMATICS`](SOURCES.md#s-dark-matter-kinematics).
- **Repository evidence:** none is required for a result, because this is a
  declared boundary.
- **Reproduction lane:** confirm that the external literature connects stellar
  kinematics to mass inference, then inspect the repository's outputs for a
  gravitational-potential or density fit. The expected result is that there is
  none.
- **Does not establish:** better input velocities are not themselves a
  dark-matter result.

### MEASUREMENT-RV — `established_context`

**Statement in plain language:** the stellar catalogue contains line-of-sight
radial velocities fitted from spectra, including single-epoch measurements
that can be compared for repeatedly observed stars.

- **Human page:** [From light to radial velocity](02_light_to_velocity.md).
- **External sources:**
  [`S-DESI-DR1-STELLAR-DOC`](SOURCES.md#s-desi-dr1-stellar-doc),
  [`S-RVSPECFIT`](SOURCES.md#s-rvspecfit), and
  [`S-DESI-DR1-STELLAR-PAPER`](SOURCES.md#s-desi-dr1-stellar-paper).
- **Repository evidence:** [`README.md`](../README.md) names the input fields,
  grouping, quality cuts, and repeat-observation pipeline.
- **Reproduction lane:** use the official product guide to identify the
  velocity product and RVSpecFit to identify the fitting route; then compare
  those definitions with the root README's pipeline description.
- **Does not establish:** radial velocity is only the line-of-sight component,
  not a star's full three-dimensional velocity.

### INSTRUMENT-PETAL — `established_context`

**Statement in plain language:** PETAL labels one of ten DESI focal-plane
wedges, each associated with 500 fibers and a spectrograph. It is an instrument
location label, not a property of a star.

- **Human pages:** [From light to radial velocity](02_light_to_velocity.md) and
  [What the project found](05_what_we_found.md).
- **External sources:**
  [`S-DESI-GLOSSARY`](SOURCES.md#s-desi-glossary) and
  [`S-DESI-FOCAL-PLANE`](SOURCES.md#s-desi-focal-plane).
- **Repository evidence:**
  [`experiments/2026-07-13_novel_signals/petal_validation.csv`](../experiments/2026-07-13_novel_signals/petal_validation.csv)
  records zero `FIBER`/`PETAL_LOC` mismatches and zero invalid rows for each of
  the three input files.
- **Reproduction lane:** read the two official geometry definitions, then check
  the validation CSV columns `N_FIBER_PETAL_MISMATCH`,
  `N_INVALID_FIBER_OR_PETAL`, and `PASS`.
- **Does not establish:** a PETAL association does not identify a particular
  faulty component or separate geometry from correlated target assignment.

## Repository results

### BASELINE-NIGHT — `pass`

**Statement in plain language:** after the published BACKUP correction and the
adopted uncertainty floors, a source-disjoint `PROGRAM:NIGHT` model reduces
held-out raw robust scatter by 0.494756 km/s, or 13.55%, and beats all 100
shuffled-night controls.

- **Human pages:** [Why audit?](03_why_audit.md),
  [How evidence works](04_how_evidence_works.md), and
  [What the project found](05_what_we_found.md).
- **External sources:**
  [`S-DESI-DR1-STELLAR-PAPER`](SOURCES.md#s-desi-dr1-stellar-paper) documents
  the catalogue context; [`S-BACKUP-CORRECTION`](SOURCES.md#s-backup-correction)
  is the published correction consumed by the pipeline. Neither source proves
  the repository's 13.55% result.
- **Repository evidence:**
  [`reports/program_night_artifacts/summary.csv`](../reports/program_night_artifacts/summary.csv),
  [`reports/program_night_artifacts/permutation_summary.csv`](../reports/program_night_artifacts/permutation_summary.csv),
  and
  [`reports/desi_main_program_night_audit.md`](../reports/desi_main_program_night_audit.md).
- **Reproduction lane:** in `summary.csv`, compare
  `BEFORE_RAW_WIDTH_KMS` with `AFTER_RAW_WIDTH_KMS` across the five folds. In
  `permutation_summary.csv`, make the same comparison by `PERMUTATION`. The
  report gives the aggregate and documents the full-audit command.
- **Does not establish:** the offsets are diagnostics for represented nights,
  not an official correction, an unseen-night forecast, or a causal diagnosis.

### BASELINE-REPLICATION — `pass`

**Statement in plain language:** two disjoint source halves recover 483
common `PROGRAM:NIGHT` offsets with Pearson correlation 0.98026 and slope
1.00157.

- **Human pages:** [How evidence works](04_how_evidence_works.md) and
  [What the project found](05_what_we_found.md).
- **External sources:** none. This is a repository-only split-half
  reproducibility result.
- **Repository evidence:**
  [`reports/program_night_artifacts/reproducibility.csv`](../reports/program_night_artifacts/reproducibility.csv)
  contains the headline row, and
  [`reports/program_night_artifacts/reproducibility_by_program.csv`](../reports/program_night_artifacts/reproducibility_by_program.csv)
  shows the aggregate, within-program-demeaned, and program-specific checks.
- **Reproduction lane:** inspect `N_COMMON_LABELS`, `OFFSET_CORRELATION`, and
  `OFFSET_SLOPE_B_ON_A` in the first CSV, then use the `SCOPE` rows in the
  second CSV to see whether the aggregate is only a between-program effect.
- **Does not establish:** agreement between source halves reduces a
  shared-source leakage concern, but both halves share the same release, time
  span, nights, and observation-linked systematics. It does not identify the
  physical cause of the offsets.

### E1-TEMPORAL — `pass`

**Statement in plain language:** successive supported BRIGHT and DARK nights
separated by 1 to 7 days show program-conditioned persistence in their
diagnostic offsets. Their Pearson correlations are 0.33759 and 0.61162, and the
full-pipeline maxT empirical p-value is 0.009901.

- **Human pages:** [How evidence works](04_how_evidence_works.md) and
  [What the project found](05_what_we_found.md).
- **External sources:** none. This is a repository result.
- **Repository evidence:**
  [`temporal_persistence.csv`](../experiments/2026-07-13_novel_signals/temporal_persistence.csv),
  [`temporal_independent_halves.csv`](../experiments/2026-07-13_novel_signals/temporal_independent_halves.csv),
  and
  [`temporal_change_points.csv`](../experiments/2026-07-13_novel_signals/temporal_change_points.csv).
- **Reproduction lane:** inspect the BRIGHT and DARK rows and the fields
  `PEARSON_R_1_7D`, `FULL_PIPELINE_P_MAXT`, `LOO_SAME_SIGN`, and
  `E1_DECISION`; then check the disjoint-half and CUSUM files for the
  secondary robustness views. Run the bundle verifier for a machine check, or
  `run_all.py` for a full discovery rerun.
- **Does not establish:** the statistic does not use every possible pair of
  nights in the range. Persistence is compatible with multi-day states, but it
  does not prove instrument drift or name a mechanism.

### E2-COHERENCE-NULL — `null`

**Statement in plain language:** the strict source-disjoint test does not
reproduce one same-night state shared by BRIGHT and DARK. The symmetric
same-night correlation is 0.01003 and the Holm-adjusted p-value is 0.4614.

- **Human pages:** [How evidence works](04_how_evidence_works.md) and
  [What the project found](05_what_we_found.md).
- **External sources:** none. This is a repository result, including its null
  outcome.
- **Repository evidence:**
  [`cross_program_coherence.csv`](../experiments/2026-07-13_novel_signals/cross_program_coherence.csv)
  and
  [`cross_program_block_null.csv`](../experiments/2026-07-13_novel_signals/cross_program_block_null.csv).
- **Reproduction lane:** in the primary `BRIGHT,DARK` row, inspect
  `SYMMETRIC_R0`, `BLOCK_NULL_P_HOLM`, and `PASS`. The block-null file contains
  the control draws. The bundle verifier confirms that the recorded decision
  remains `null`.
- **Does not establish:** this design's null result does not prove that every
  possible common component is exactly zero.

### E3-PETAL — `pass`

**Statement in plain language:** after the `PROGRAM:NIGHT` model, a smaller
PETAL-associated residual still transfers to held-out sources: mean incremental
gain 0.058141 km/s, five of five positive folds, source-half correlation
0.83133, and empirical p=0.01 from 99 controls.

- **Human pages:** [How evidence works](04_how_evidence_works.md) and
  [What the project found](05_what_we_found.md).
- **External sources:**
  [`S-DESI-GLOSSARY`](SOURCES.md#s-desi-glossary) and
  [`S-DESI-FOCAL-PLANE`](SOURCES.md#s-desi-focal-plane) define PETAL geometry;
  they do not prove the residual.
- **Repository evidence:**
  [`petal_cv.csv`](../experiments/2026-07-13_novel_signals/petal_cv.csv),
  [`petal_permutations.csv`](../experiments/2026-07-13_novel_signals/petal_permutations.csv),
  [`petal_replication.csv`](../experiments/2026-07-13_novel_signals/petal_replication.csv),
  and
  [`petal_independent_program_offsets.csv`](../experiments/2026-07-13_novel_signals/petal_independent_program_offsets.csv).
- **Reproduction lane:** use the five `REAL` rows in `petal_cv.csv` to inspect
  `INCREMENTAL_PETAL_GAIN_KMS`; compare their mean with the 99 control gains in
  `petal_permutations.csv`; then read `PEARSON_R` in
  `petal_replication.csv`. The bundle verifier checks the combined gate.
- **Does not establish:** PETAL localization is not proof of a hardware fault,
  and this model does not separate static `PROGRAM:PETAL` structure from every
  possible night-varying structure.

## Repository scope boundaries

### BOUNDARY-OUTLIERS — `screening_only`

**Statement in plain language:** the constant-velocity outlier lists identify
sources for follow-up screening. They are not confirmed binaries or variable
stars, and they do not support the `PROGRAM:NIGHT` result.

- **Human pages:** [Why audit?](03_why_audit.md) and
  [What the project found](05_what_we_found.md).
- **External sources:** none.
- **Repository evidence:** [`README.md`](../README.md) and
  [`reports/desi_main_audit_report.md`](../reports/desi_main_audit_report.md).
- **Reproduction lane:** read the outlier-count section together with its
  interpretation boundary; confirm that the baseline result uses its own
  source-disjoint evidence rather than the candidate labels.
- **Does not establish:** confirmation requires source-specific astrophysical
  review and independent observations.

### BOUNDARY-EXPLORATORY — `exploratory`

**Statement in plain language:** all current audit and discovery results were
developed within DESI DR1. Strong confirmation still needs a pre-specified,
untouched release, survey, data slice, or unseen-night prediction test.

- **Human pages:** [How evidence works](04_how_evidence_works.md) and
  [What the project found](05_what_we_found.md).
- **External sources:** none.
- **Repository evidence:** [`README.md`](../README.md),
  [`research_plan.json`](../experiments/2026-07-13_novel_signals/research_plan.json),
  and [`report.md`](../experiments/2026-07-13_novel_signals/report.md).
- **Reproduction lane:** compare the frozen decision rules and documented
  amendments in `research_plan.json` with the final decisions in `report.md`,
  then read the root README's untouched-data boundary.
- **Does not establish:** source-disjoint folds, frozen gates, and negative
  controls improve credibility, but they do not make reused DR1 data an
  untouched confirmatory sample.

Next: [Run the 45-minute comprehension check](08_reader_test.md)
