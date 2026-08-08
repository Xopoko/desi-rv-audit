---
explanation_id: light-to-velocity
concepts:
  - spectrum
  - doppler-shift
  - radial-velocity
  - epoch
  - repeat-observation
  - source-identity
  - program
  - observing-night
  - petal
claims:
  - MEASUREMENT-RV
  - INSTRUMENT-PETAL
sources:
  - S-DESI-DR1-STELLAR-DOC
  - S-RVSPECFIT
  - S-DESI-GLOSSARY
  - S-DESI-FOCAL-PLANE
  - S-GAIA-DR3
---

# From Starlight to One Velocity Number

[Start](README.md) -> [The big picture](01_big_picture.md) -> **Light to velocity** -> [Why audit?](03_why_audit.md)

## 1. A star sends a structured spectrum

A star does not emit equal light at every wavelength. Atoms in its atmosphere
absorb light at characteristic wavelengths, leaving a pattern of spectral
lines. The pattern depends on temperature, surface gravity, chemical
composition, rotation, and motion.

DESI does not take an ordinary color photograph for this measurement. An
optical fiber carries the target's light to a spectrograph, which separates the
light by wavelength. The result is roughly a table of wavelength, measured
flux, uncertainty, and quality masks. The official DESI glossary defines a
spectrum this way
([S-DESI-GLOSSARY](SOURCES.md#s-desi-glossary)).

## 2. Motion shifts the line pattern

If a star moves along our line of sight, its spectral pattern is Doppler
shifted. For speeds much smaller than the speed of light, the intuition is:

```text
fractional wavelength shift ~= radial velocity / speed of light
```

The catalogue pipeline does not estimate velocity from one hand-picked line.
RVSpecFit compares the observed spectrum with interpolated synthetic stellar
templates and finds the velocity and stellar parameters that best fit the data
([S-RVSPECFIT](SOURCES.md#s-rvspecfit)).

The output used by this repository is already a fitted radial velocity in
kilometers per second. This repository audits those catalogue measurements; it
does not refit the raw spectra.

## 3. Radial velocity is not full motion

Radial velocity is only the component toward or away from the observer. A
star's full three-dimensional motion also needs motion across the sky and a
distance. Gaia identifiers help connect measurements belonging to the same
physical source, but a Gaia `SOURCE_ID` is an identity key, not a velocity
measurement.

The audit groups rows by Gaia source when possible and uses DESI `TARGETID` as a
fallback. This matters because a repeat-observation test only makes sense when
the rows really describe the same star.

## 4. One epoch is one measurement occasion

An **epoch** is one observation of a source at a particular time. An exposure
(`EXPID`) can contain thousands of sources. An observing night contains one or
more exposures. These levels are related but not interchangeable:

| Level | Plain meaning | Why it matters here |
|---|---|---|
| Source | The physical star | Must not leak between train and holdout |
| Epoch row | One fitted stellar spectrum | Supplies one velocity and error |
| Exposure (`EXPID`) | One coordinated instrument exposure | E3 shuffles PETAL within this level |
| Night | Calendar observing session | Baseline and E1 fit or compare night labels |
| Program | BRIGHT, DARK, or BACKUP observing regime | Calibration behavior can differ |

When the same source has multiple epochs, the catalogue gives repeated
measurements of the same underlying object under different circumstances.

## 5. Five thousand fibers and ten PETALs

DESI's focal plane has 5,000 science positioners arranged in ten wedge-shaped
PETALs, each carrying 500 fibers toward one spectrograph. The official
instrument pages describe this geometry
([S-DESI-FOCAL-PLANE](SOURCES.md#s-desi-focal-plane)).

```text
focal plane
  -> 10 PETAL wedges
  -> 500 positioner/fiber channels per PETAL
  -> one associated spectrograph per PETAL
```

In the committed DR1 inputs, the experiment verified on every input row that
`FIBER // 500 == PETAL_LOC`. PETAL therefore gives a coarse instrumental
location label.

PETAL is **not** a star property. A pattern that follows PETAL may indicate
focal-plane, fiber, spectrograph, target-assignment, or correlated sky/sample
structure. Geometry narrows the search; it does not prove which mechanism is
responsible.

## 6. What can change one measured velocity?

Several categories can contribute:

- real stellar motion, including orbital motion in a binary or pulsation;
- random spectral noise;
- imperfect template matching;
- wavelength-calibration residuals;
- observing-condition or program differences;
- night-associated zero-point changes;
- focal-plane or PETAL-associated structure;
- incorrect uncertainty estimates or quality flags.

The audit's job is not to assume one cause. It asks which statistical patterns
survive quality cuts, held-out-source tests, and negative controls.

Next: [Why repeat observations make an audit possible](03_why_audit.md)
