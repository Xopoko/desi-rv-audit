---
explanation_id: glossary
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
  - redshift
  - quasar
  - lyman-alpha-forest
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
  - S-GAIA-DR3
---

# Glossary

[Start](README.md) -> **Glossary**

These definitions describe how words are used in this explanation and this
repository. A definition helps interpret a claim; it is not evidence that the
claim is true. DESI-specific definitions point to the human-readable
[source registry](SOURCES.md).

## Concept index

| Measurement and survey | Audit and evidence | Scientific context |
|---|---|---|
| [DESI](#desi) | [Quality cut](#quality-cut) | [Dark matter](#dark-matter) |
| [Spectrum](#spectrum) | [Velocity correction](#velocity-correction) | [Dark energy](#dark-energy) |
| [Doppler shift](#doppler-shift) | [Uncertainty floor](#uncertainty-floor) | [BAO](#bao) |
| [Redshift](#redshift) | [Residual](#residual) | [Quasar](#quasar) |
| [Lyman-alpha forest](#lyman-alpha-forest) | [Robust width](#robust-width) |  |
| [Radial velocity](#radial-velocity) |  |  |
| [Epoch](#epoch) | [Source-disjoint](#source-disjoint) |  |
| [Repeat observation](#repeat-observation) | [Permutation control](#permutation-control) |  |
| [Source identity](#source-identity) | [Bootstrap](#bootstrap) |  |
| [Program](#program) | [Empirical p-value](#empirical-p-value) |  |
| [Observing night](#observing-night) | [Correlation](#correlation) |  |
| [PETAL](#petal) | [Pass-null](#pass-null) |  |
|  | [Exploratory analysis](#exploratory-analysis) |  |

## DESI

The **Dark Energy Spectroscopic Instrument**: an instrument on the Mayall
telescope, and by extension the collaboration and survey that use it. DESI
records spectra for several scientific programs. Its name does not imply that
every DESI result is a dark-energy result. See
[`S-DESI-GLOSSARY`](SOURCES.md#s-desi-glossary).

## Spectrum

A measurement of how much light was recorded at different wavelengths. A
stellar spectrum contains patterns of absorption lines that can be compared
with a stellar template. See
[`S-DESI-GLOSSARY`](SOURCES.md#s-desi-glossary).

## Doppler shift

A change in the observed wavelengths of a line pattern caused by motion toward
or away from the observer. At ordinary stellar speeds, the fractional
wavelength shift is approximately radial velocity divided by the speed of
light.

## Radial velocity

The component of an object's velocity along the observer's line of sight,
reported here in kilometers per second. It does not include motion across the
sky and is not the full three-dimensional velocity. DESI catalogue values are
fitted from spectra; this repository audits those values rather than refitting
the spectra. See [`S-RVSPECFIT`](SOURCES.md#s-rvspecfit) and
[`S-DESI-DR1-STELLAR-DOC`](SOURCES.md#s-desi-dr1-stellar-doc).

## Redshift

A displacement of spectral features toward longer wavelengths. Cosmological
redshift is used to place distant galaxies and quasars along the line of sight
and build a three-dimensional map of large-scale structure. That cosmology
measurement is a different use of spectra from the fitted stellar radial
velocities audited by this repository.

## Quasar

An extremely luminous active galactic nucleus powered by matter falling toward
a supermassive black hole. DESI uses quasars both as distant clustering tracers
and as bright background sources whose spectra reveal intervening hydrogen.
They are not part of this repository's repeat-star sample.

## Lyman-alpha forest

A sequence of absorption features in a distant quasar's spectrum, produced by
intervening neutral hydrogen at different redshifts. Its three-dimensional
statistical pattern can trace large-scale structure and BAO. This repository
does not analyse Lyman-alpha spectra.

## Epoch

One measurement occasion for a source. An epoch row carries one fitted velocity
and its uncertainty, along with observation metadata such as program, night,
exposure, fiber, and PETAL.

## Repeat observation

Another epoch for the same source. Comparing repeat observations lets the
source's constant velocity cancel in a difference and exposes measurement
noise, real source variability, or observation-linked structure.

## Source identity

The label used to decide which epoch rows belong to the same astrophysical
object. The pipeline groups by Gaia `SOURCE_ID` when available and falls back to
DESI `TARGETID` otherwise. Keeping source identity intact is essential when
splitting data. See [`S-GAIA-DR3`](SOURCES.md#s-gaia-dr3) for the Gaia release
context.

## Program

An observing regime. This audit uses `BRIGHT`, `DARK`, and `BACKUP` in the DESI
`MAIN` survey. These names describe observations, not three kinds of stars. See
[`S-DESI-GLOSSARY`](SOURCES.md#s-desi-glossary).

## Observing night

The calendar observing session associated with an exposure. A
`PROGRAM:NIGHT` label combines an observing regime with a night. The baseline
model estimates relative diagnostic offsets for such labels.

## PETAL

One of ten wedge-shaped sections of the DESI focal plane. Each PETAL carries 500
fiber positioners and is associated with a spectrograph. PETAL is a coarse
instrument-location label, not a stellar property and not a diagnosis of a
fault. See [`S-DESI-GLOSSARY`](SOURCES.md#s-desi-glossary) and
[`S-DESI-FOCAL-PLANE`](SOURCES.md#s-desi-focal-plane).

## Quality cut

A declared rule that keeps rows suitable for the intended comparison or screens
known failure modes. Examples here include finite values, adequate
signal-to-noise, successful fitting, clean warning flags, stellar
classification, and a rotation limit when the relevant columns exist. A cut
reduces known problems; it cannot guarantee that every retained row is perfect.

## Velocity correction

A change applied to the central measured velocity. This repository applies the
published BACKUP correction only to its documented `MAIN/BACKUP` matches. That
external input is different from the repository's diagnostic night offsets.
See [`S-BACKUP-CORRECTION`](SOURCES.md#s-backup-correction).

## Uncertainty floor

An additional minimum uncertainty added in quadrature to a formal fit error. In
plain language, it enlarges the error budget to acknowledge residual scatter;
it does not shift the measured velocity. The adopted floors are program-level
analysis choices, not newly fitted catalogue velocities.

## Residual

What remains after a comparison or model has accounted for its expected part.
For a repeat pair, a basic residual is the measured velocity difference. After
fitting relative observation-linked offsets, a residual is the part of that
difference the offsets did not explain. A normalized residual divides by an
adopted pair uncertainty.

## Robust width

A measure of the central spread that is less controlled by extreme values than
a standard deviation. This project uses half the distance between the 16th and
84th percentiles. A raw robust width has velocity units; a normalized robust
width is measured in adopted uncertainty units.

## Source-disjoint

A split in which the same source group does not appear in both training and
holdout data within a fold. Different stars can still have been observed on the
same night. Therefore source-disjoint evaluation tests transfer to other stars
on represented nights; it is not automatically night-disjoint and does not
forecast an unseen night.

## Permutation control

A negative control made by deliberately breaking the label relationship under
test while preserving declared structural constraints, then rerunning the
relevant analysis. The real statistic is compared with the distribution from
these shuffled controls. A useful permutation must break the proposed signal
without destroying unrelated structure that the real pipeline also sees.

## Bootstrap

A resampling method used to estimate how an answer varies across plausible
resamples of the observed units. Here the meaningful unit is usually a source
group, so all linked rows from one source travel together. Bootstrap intervals
describe sampling stability; they do not remove systematic bias or create
independent new data.

## Empirical p-value

A tail frequency estimated from actual control draws rather than from a chosen
idealized probability formula. With finite controls, this project uses an
add-one form: one plus the number of controls at least as extreme as the real
statistic, divided by one plus the number of controls. Its resolution is limited
by the number of controls.

## Correlation

A number describing how two quantities vary together. Pearson correlation
tracks linear association; Spearman correlation tracks monotonic rank
association. A high correlation can support reproducibility between separate
fits or across disjoint subsets. The strength of that evidence
depends on what those subsets still share; correlation alone neither proves
causation nor identifies a physical mechanism.

## Pass-null

Two literal decision labels used by this project.

- **Pass:** every declared gate for the tested claim was met in this analysis.
- **Null:** the tested claim was not supported under the declared design.

`Pass` is not universal proof or established novelty. `Null` is not proof that
the effect is exactly zero under every possible model.

## Exploratory analysis

Analysis in which hypotheses, design choices, or refinements were developed
with knowledge of the same broad data release being analysed. Frozen gates,
source-disjoint splits, and controls make an exploratory result more auditable,
but strong confirmation still needs a pre-specified untouched release, survey,
data slice, or unseen-night prediction test.

## Dark matter

Matter inferred from its gravitational effects rather than from emitted light.
Stellar positions and velocities can help constrain a Galactic mass model, but
this repository fits no such model and reports no dark-matter measurement. See
[`S-DARK-MATTER-KINEMATICS`](SOURCES.md#s-dark-matter-kinematics) and
[`S-DESI-MWS-OVERVIEW`](SOURCES.md#s-desi-mws-overview).

## Dark energy

The name given to the unknown cause associated with the observed accelerated
cosmic expansion in standard cosmological descriptions. DESI constrains
dark-energy models through extragalactic distance and clustering measurements.
This stellar measurement-consistency audit does not fit a dark-energy model.
See [`S-DESI-DR1-BAO`](SOURCES.md#s-desi-dr1-bao).

## BAO

**Baryon acoustic oscillations:** a preferred scale left in the large-scale
distribution of matter by sound waves in the early Universe. DESI uses this
statistical standard ruler with galaxies, quasars, and Lyman-alpha forest
tracers to measure cosmic distances. The repeat-star sample in this repository
is not the BAO sample. See
[`S-DESI-DR1-BAO`](SOURCES.md#s-desi-dr1-bao).

## Useful short forms and analysis terms

### Correction

Short for [velocity correction](#velocity-correction) in this explanation. It
changes a central value; it is not the same operation as enlarging an error.

### Floor

Short for [uncertainty floor](#uncertainty-floor). It enlarges the adopted
uncertainty; it does not move the velocity.

### Folds, train, and holdout

A **fold** is one repeatable partition of source groups. The **train** part is
used to estimate offsets, clipping rules, and any train-estimated quantities.
The **holdout** part is used only to score whether those trained quantities help
different source groups. Results are summarized across five folds here.

### Permutation

One shuffled realization used in a [permutation control](#permutation-control).
The word can refer to the relabelling operation or to one resulting control
data set.

### Empirical p

Short for [empirical p-value](#empirical-p-value). It reports a finite-control
tail frequency, not the probability that a scientific hypothesis is true.

### Pass, null, and exploratory

`Pass` and `null` are decision outcomes; `exploratory` describes the evidential
setting. An exploratory analysis can pass its declared gates while still
requiring untouched-data confirmation. See [pass-null](#pass-null) and
[exploratory analysis](#exploratory-analysis).

### Graph

A network of nodes and edges. In the baseline model, a node is a
`PROGRAM:NIGHT` label and an edge is a repeat-source pair connecting two such
labels. Separate connected components cannot be compared by a path of pair
differences.

### Gauge

An arbitrary reference level in a relative model. Pair differences can recover
offset differences, but adding the same constant to every offset in one
connected graph component changes no prediction. Centering each component fixes
that arbitrary level; it does not create an absolute physical calibration.

### CUSUM

**Cumulative sum:** a running total of deviations used to screen for a possible
change point in an ordered sequence. Here it is a secondary view of temporal
offset structure. A large CUSUM score can localize a step-like change, but it
does not identify the cause of that change.

Back to: [Understand DESI RV Audit](README.md)
