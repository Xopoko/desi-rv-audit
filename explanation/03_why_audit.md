---
explanation_id: why-audit
concepts:
  - quality-cut
  - velocity-correction
  - uncertainty-floor
  - repeat-observation
  - residual
  - robust-width
  - observing-night
claims:
  - BASELINE-NIGHT
  - BOUNDARY-OUTLIERS
sources:
  - S-DESI-DR1-STELLAR-PAPER
  - S-BACKUP-CORRECTION
---

# Why Audit Repeat Radial Velocities?

[Start](README.md) -> [Light to velocity](02_light_to_velocity.md) -> **Why audit?** -> [How evidence works](04_how_evidence_works.md)

## The simplest thought experiment

Suppose a non-variable star is measured twice. If both measurements and their
uncertainties are well calibrated, the difference should usually be small
relative to the combined uncertainty.

For epochs 1 and 2:

```text
velocity difference = measured velocity 1 - measured velocity 2
pair uncertainty = sqrt(error 1^2 + error 2^2)
normalized residual = velocity difference / pair uncertainty
```

The star's constant velocity cancels in the difference. What remains can expose
noise, real variability, or measurement systematics.

This is a statistical screen, not a guarantee that every star is constant. The
large sample lets common observation-linked patterns emerge even though some
individual stars genuinely vary.

## A useful measurement model

One epoch velocity can be imagined as:

```text
measured velocity
  = star's velocity at that time
  + observation-linked zero-point term
  + random measurement error
```

The zero-point term is deliberately generic. It might depend on program, night,
PETAL, or something not tested. The audit estimates diagnostic relative terms;
it does not begin by declaring a physical cause.

## Quality cuts reduce known failure modes

Before pairing epochs, the project requires finite velocities and errors,
minimum signal-to-noise, a successful fit, no radial-velocity or fiber warning,
a stellar classification, and moderate projected rotation when those fields are
available.

Why these cuts help:

- low signal-to-noise makes the line pattern uncertain;
- a failed fit or warning flag says the pipeline detected a problem;
- a non-star should not be interpreted with a stellar template model;
- very broad lines in a fast rotator reduce radial-velocity precision.

Rejection reasons can overlap. Their counts must not be added as if every
rejected row had exactly one problem.

## Correction and uncertainty floor do different jobs

The DESI DR1 stellar paper documents important BACKUP-program wavelength
calibration systematics and provides an approximate published correction. This
repository applies the external correction only to `MAIN/BACKUP` rows matched
by `TARGETID`
([S-BACKUP-CORRECTION](SOURCES.md#s-backup-correction)).

- A **velocity correction** changes the central measured velocity.
- An **uncertainty floor** increases the adopted error budget by adding a
  minimum residual uncertainty in quadrature.

The adopted floors are 1.0 km/s for BRIGHT, 2.0 km/s for BACKUP, and 1.6 km/s
for DARK. A floor does not shift a velocity. It says the formal fit error alone
is too optimistic for the intended comparison.

## How the project summarizes residuals

Several metrics describe different failure modes:

| Metric | Question answered |
|---|---|
| Median residual | Is there a central directional bias? |
| Raw robust width | How broad is the central velocity-difference distribution in km/s? |
| Normalized robust width | Is the central spread consistent with the adopted uncertainty scale? |
| `|z| > 3` or `|z| > 5` | How much probability remains in extreme tails? |
| Gaussian pair loss | How costly are residual size and stated uncertainty together? |

The robust width is based on the 16th and 84th percentiles rather than the most
extreme points. A normalized central width near one is compatible with a
well-scaled Gaussian core, but it does not prove that tails are Gaussian or that
all systematics are gone.

## From pair differences to program-night offsets

Each repeat-source pair connects two `PROGRAM:NIGHT` labels. Think of labels as
nodes in a network and repeat pairs as edges. Many edges allow the model to
estimate relative label offsets that best explain the observed differences.

Only relative offsets are identifiable. Adding the same constant to every node
in one connected component changes no pair difference, so offsets are centered
within each component. They are diagnostic zero points, not absolute physical
calibrations.

## Why cap and balance pairs per source?

A source observed many times can create many more pairs than an ordinary
source. Without balancing, a few highly repeated sources could dominate the
fit. The audit downweights sources with many pairs and checks pair caps of 10,
20, and 50. The headline reduction remains about 13.5% in all three cases.

## Two different uses of the word outlier

The baseline pipeline also screens sources against a constant-velocity model.
It reports 25,953 broad candidates and 12,141 stricter candidates. These lists
answer, "which sources deserve closer inspection?"

They do **not** answer, "which stars are confirmed binaries or variables?" and
they are not used as evidence for the program-night result. Source-specific
astrophysical confirmation would require additional review and observations.

## The audit question after all preparation

After the published correction, uncertainty floors, quality cuts, source
balancing, and train-only clipping:

> Does a program-and-night model improve velocity consistency for different
> held-out stars more than the same flexible procedure improves data whose
> exposure-night association has been deliberately destroyed?

That comparison is the baseline claim `BASELINE-NIGHT`.

Next: [How the evidence tries not to fool itself](04_how_evidence_works.md)
