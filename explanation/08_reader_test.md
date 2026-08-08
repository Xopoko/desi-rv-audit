---
explanation_id: reader-test
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

# The 45-Minute Comprehension Check

[Start](README.md) -> [Evidence map](07_evidence_map.md) -> **Comprehension check**

Use this check to verify the distinctions made across the scientific guide. It
requires only the pages under `explanation/`: no terminal, notebook, raw data,
or calculation software.

## Passing rule

There are eight tasks worth one point each.

> **Pass = at least 7 of 8 tasks passed, with zero critical misconceptions.**

A task passes only when all of its listed pass checks are present in the
reader's answer. Wording does not need to match this page. A reader may draw a
diagram, speak, or write short sentences.

A **critical misconception** causes the whole test to fail even at 8/8. The
critical list is:

- saying this repository directly measures dark matter or dark energy;
- treating diagnostic `PROGRAM:NIGHT` offsets as an official catalogue
  correction;
- saying `E2-COHERENCE-NULL` proves that no common component can exist;
- saying `E3-PETAL` proves a hardware fault or identifies its cause;
- treating screening outliers as confirmed binaries or variable stars;
- saying source-disjoint holdout is also night-disjoint or an unseen-night
  forecast.

## Instructions for the reader

Start at [Understand DESI RV Audit](README.md). Use links, the
[glossary](GLOSSARY.md), and the [evidence map](07_evidence_map.md) whenever you
need them. Do not inspect Python or raw data. Keep moving when a task's suggested
time ends.

## Task 1 — Put the project in the right branch (4 minutes)

Read the sixty-second version and [the big picture](01_big_picture.md). Then
complete both sentences:

1. “DESI cosmology uses ______ to reach BAO and dark-energy constraints.”
2. “This repository instead uses ______ to ask ______.”

**Pass checks:** the answer distinguishes distant extragalactic tracers from
the DR1 stellar radial-velocity catalogue, and describes a repeat-measurement or
calibration-consistency question.

**Critical check:** the reader must not say that this audit fits a cosmological
or dark-energy parameter.

## Task 2 — Explain how light becomes one velocity (5 minutes)

Using [From starlight to one velocity number](02_light_to_velocity.md), explain
this chain to an imaginary friend:

```text
stellar spectrum -> shifted line pattern -> fitted radial velocity
```

Also say what radial velocity leaves out.

**Pass checks:** the answer mentions a Doppler shift of spectral features,
motion toward or away from the observer, and that motion across the sky or full
three-dimensional velocity is not supplied by radial velocity alone.

## Task 3 — Explain why repeats form an audit (6 minutes)

Read [Why audit repeat radial velocities?](03_why_audit.md). Describe what is
gained by comparing two epochs of the same source. Then explain the difference
between all three items:

- a quality cut;
- a velocity correction;
- an uncertainty floor.

**Pass checks:** the reader says that the source's constant velocity cancels in
an epoch difference; a cut removes or screens problematic rows; a correction
shifts a central velocity; and a floor enlarges the adopted uncertainty rather
than shifting the velocity.

## Task 4 — Protect the holdout from source reuse (5 minutes)

Read the source-disjoint section of
[How the evidence works](04_how_evidence_works.md). In plain language, define
train data and holdout data here. Answer this trap question:

> If a night appears in both train and holdout, has source-disjoint evaluation
> failed?

**Pass checks:** the reader says that different source identities, not
necessarily different nights, are separated; training estimates an offset and
holdout asks whether it transfers to other stars on represented nights.

**Critical check:** the reader must not describe this as prediction for a new,
unseen night.

## Task 5 — Match each safeguard to its job (5 minutes)

Without calculating anything, match each numbered term to one lettered
question:

1. Permutation control
2. Bootstrap
3. Empirical p-value
4. Source-half correlation

A. How much does an estimate vary when source groups are resampled?
B. Do separately fitted, disjoint source groups recover similar relative offsets?
C. Could a similarly flexible pipeline find an effect after the relevant
   labels are deliberately broken?
D. How often did a control equal or exceed the real statistic, with
   finite-control correction?

Then explain why correlation alone does not identify a cause.

**Pass checks:** at least three of the four matches are correct
(`1-C, 2-A, 3-D, 4-B`), and the answer states that correlation measures
association rather than physical mechanism.

## Task 6 — Read the result labels literally (7 minutes)

From [What the project found](05_what_we_found.md), assign the correct outcome
to each experiment and give one sentence of meaning:

- `BASELINE-NIGHT`;
- `E1-TEMPORAL`;
- `E2-COHERENCE-NULL`;
- `E3-PETAL`.

**Pass checks:** the outcomes are `pass`, `pass`, `null`, and `pass`; the reader
describes baseline night-associated transfer, within-program temporal
persistence, non-reproduction of strict BRIGHT-DARK same-night coherence, and
a smaller PETAL-associated residual beyond `PROGRAM:NIGHT`.

**Critical checks:** `null` must not become “proved zero,” and PETAL association
must not become proof of a hardware fault.

## Task 7 — State the scientific boundaries (6 minutes)

Read [Dark matter and dark energy](06_dark_matter_and_dark_energy.md) and the
boundary cards in [What the project found](05_what_we_found.md). Give one true
sentence for each topic:

- dark energy;
- dark matter;
- constant-velocity outliers;
- exploratory status.

**Pass checks:** the reader says that dark energy is reached through a separate
extragalactic BAO route; stellar kinematics can feed later dark-matter work but
no such model is fit here; outliers are screening candidates; and confirmation
needs untouched or genuinely independent data.

**Critical checks:** no direct dark-matter or dark-energy result, and no
confirmed-binary interpretation of the outlier list.

## Task 8 — Trace one claim without trusting the prose (7 minutes)

Choose one repository result from the [evidence map](07_evidence_map.md). Point
to all four parts:

1. its exact claim ID and status;
2. its human explanation page;
3. its exact committed evidence path;
4. one limitation or “does not establish” statement.

Finally, say whether an external source or a repository artifact carries the
numerical result.

**Pass checks:** all four parts agree with the evidence map, and the reader says
that the repository artifact—not a DESI background paper—supports the project's
numerical outcome.

## Score sheet

| Task | Pass (0 or 1) | Critical misconception? | Brief note |
|---|---:|---|---|
| 1. Project branch |  |  |  |
| 2. Light to velocity |  |  |  |
| 3. Repeat audit |  |  |  |
| 4. Source-disjoint holdout |  |  |  |
| 5. Safeguards |  |  |  |
| 6. Result labels |  |  |  |
| 7. Boundaries |  |  |  |
| 8. Evidence trace |  |  |  |
| **Total** | **/8** | **must be zero** |  |

Back to: [Understand DESI RV Audit](README.md)
