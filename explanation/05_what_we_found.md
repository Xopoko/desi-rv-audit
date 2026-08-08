---
explanation_id: findings
concepts:
  - residual
  - robust-width
  - program
  - observing-night
  - source-disjoint
  - permutation-control
  - bootstrap
  - empirical-p-value
  - correlation
  - petal
  - pass-null
  - exploratory-analysis
claims:
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
  - S-BACKUP-CORRECTION
  - S-DESI-GLOSSARY
  - S-DESI-FOCAL-PLANE
---

# What the Project Found

[Start](README.md) -> [How evidence works](04_how_evidence_works.md) -> **What we found** -> [Dark matter and dark energy](06_dark_matter_and_dark_energy.md)

## The short, careful answer

After the published BACKUP correction and the adopted program uncertainty
floors, repeat-star velocity differences still contain a reproducible pattern
associated with observing program and night. That pattern persists over nearby
nights within BRIGHT and DARK. A stricter test does not support one common
same-night state shared by those two programs. A smaller residual also follows
DESI PETAL location after accounting for program and night.

Those sentences describe statistical structure. They do not identify a
hardware fault, establish an official correction, or turn this audit into a
dark-matter or dark-energy measurement.

## Result summary

| Claim | Status | Headline result |
|---|---|---|
| `BASELINE-NIGHT` | pass | `0.494756 km/s` (`13.55%`) mean holdout reduction; 0 of 100 shuffled controls matched it |
| `BASELINE-REPLICATION` | pass | 483 common offsets; source-half `r=0.98026`, slope `1.00157` |
| `E1-TEMPORAL` | pass | BRIGHT `r=0.33759`, DARK `r=0.61162`; full-pipeline maxT `p=0.009901` |
| `E2-COHERENCE-NULL` | null | symmetric BRIGHT-DARK `r=0.01003`; Holm-adjusted `p=0.4614` |
| `E3-PETAL` | pass | `0.058141 km/s` incremental gain; 5/5 positive folds; source-half `r=0.83133`; empirical `p=0.01` |

These are the exact headline values registered in
[the claim ledger](claims.jsonl).

## Baseline: a transferable program-night residual

**Claim `BASELINE-NIGHT`:** a `PROGRAM:NIGHT` model fitted on some stars reduces
the raw robust scatter of velocity differences for different, held-out stars by
`0.494756 km/s` on average, or `13.55%`. None of 100 shuffled-night controls
reaches the real reduction.

In plain language, stars observed on the same represented program-night labels
share enough residual structure that offsets learned from one set of stars help
another set. This remains after applying the published BACKUP correction
([S-BACKUP-CORRECTION](SOURCES.md#s-backup-correction)) and the audit's adopted
uncertainty floors.

**Evidence:** [five-fold summary](../reports/program_night_artifacts/summary.csv),
[shuffled controls](../reports/program_night_artifacts/permutation_summary.csv),
and the [baseline audit report](../reports/desi_main_program_night_audit.md).

**Disjoint-source split-half reproducibility `BASELINE-REPLICATION`:** the two
halves recover 483 common offsets with `r=0.98026` and slope `1.00157`
([split-half table](../reports/program_night_artifacts/reproducibility.csv)).

**Limitation:** the fitted offsets are relative diagnostics for nights present
in training. They are not an official catalogue correction, an extrapolation to
an unseen night, or a diagnosis of physical cause. Both source halves also
share the same release, time span, nights, and observation-linked systematics.

**Not tested:** whether applying these diagnostic offsets would improve every
downstream science analysis.

## E1: nearby-night persistence within BRIGHT and DARK

**Claim `E1-TEMPORAL`:** successive supported nights separated by 1 to 7 days
have positively correlated diagnostic offsets within BRIGHT (`r=0.33759`) and
DARK (`r=0.61162`). The full-pipeline maxT control gives `p=0.009901`.

This is evidence that the fitted program-conditioned pattern is not purely a
collection of unrelated one-night spikes. The word **persistence** means a
correlation across nearby dates; it does not mean an instrument component has
been shown to possess a particular kind of memory.

**Evidence:** [temporal persistence](../experiments/2026-07-13_novel_signals/temporal_persistence.csv)
and [disjoint source halves](../experiments/2026-07-13_novel_signals/temporal_independent_halves.csv).

**Limitation:** the statistic uses successive supported nights with qualifying
gaps, not every possible pair of nights in the range. Temporal correlation is
compatible with multi-day states, but many mechanisms could generate it.

**Not tested:** a chronological forecast in which all measurements from a future
night are absent during fitting.

## E2: no supported common BRIGHT-DARK night state

**Claim tested by `E2-COHERENCE-NULL`:** BRIGHT and DARK share the same
calendar-night state when their program graphs are fitted separately and
opposite source halves are cross-compared.

**Outcome:** the symmetric same-night correlation is only `r=0.01003`, with
Holm-adjusted `p=0.4614`. The stricter source-disjoint design therefore does not
reproduce the earlier apparent joint-fit coherence.

**Evidence:** [cross-program results](../experiments/2026-07-13_novel_signals/cross_program_coherence.csv)
and [14-day block controls](../experiments/2026-07-13_novel_signals/cross_program_block_null.csv).

**Limitation:** this null result says that the declared design did not support a
shared state. It does not prove that every possible common component is exactly
zero at every timescale.

**Not tested:** arbitrary nonlinear, lagged, exposure-level, or other shared
components outside the declared same-night test.

## E3: a smaller PETAL-associated residual

**Claim `E3-PETAL`:** after the `PROGRAM:NIGHT` model, adding a nested PETAL
deviation reduces held-out raw robust width by another `0.058141 km/s` on
average. All 5 folds improve, disjoint source halves correlate at `r=0.83133`,
and none of 99 within-exposure shuffled controls matches the real gain, giving
add-one empirical `p=0.01`.

PETAL is a coarse instrumental location: DESI has ten focal-plane wedges, each
associated with 500 fibers and a spectrograph. The following post-hoc picture
shows that separately fitted, disjoint BRIGHT and DARK source halves recover a
similar ten-PETAL pattern.

![PETAL residual pattern recovered in disjoint BRIGHT and DARK source halves](../experiments/2026-07-13_novel_signals/petal_independent_pattern.png)

The picture helps localize the association, but the primary evidence is the
source-disjoint comparison and controls:
[fold results](../experiments/2026-07-13_novel_signals/petal_cv.csv),
[PETAL shuffles](../experiments/2026-07-13_novel_signals/petal_permutations.csv),
and [source-half reproducibility](../experiments/2026-07-13_novel_signals/petal_replication.csv).

**Limitation:** association with PETAL does not prove a spectrograph or other
hardware fault. The tested model also does not separate static
`PROGRAM:PETAL` structure from a genuinely night-varying PETAL mechanism.
Shuffling PETAL within exposures breaks focal-plane association, but it can also
break sky or source-population structure tied to focal-plane assignment; the
control therefore does not isolate hardware causality.

**Not tested:** every possible stellar-, tile-, exposure-, fiber-, or
spectrograph-dependent explanation.

## The outlier lists are a separate screening product

The constant-velocity outlier lists identify sources that deserve follow-up.
Under claim `BOUNDARY-OUTLIERS`, they are not confirmed binaries or variable
stars, and they are not evidence for `BASELINE-NIGHT`. Confirmation needs
source-specific astrophysical review and independent observations.

## What the results mean together

The safest combined interpretation is:

1. a program-night-associated residual transfers across different stars on
   represented nights;
2. within BRIGHT and DARK, part of that diagnostic structure persists across
   nearby nights;
3. the evidence does not justify collapsing both programs into one global
   same-night state;
4. a smaller transferable residual is associated with PETAL location;
5. none of these statistical associations identifies a physical cause.

All of these experiments remain exploratory within DESI DR1. The gates and
controls constrain what passed, but strong confirmation requires a
pre-specified untouched release, independent survey or data slice, or an
unseen-night prediction test.

Next: [Why this is not a dark-matter or dark-energy measurement](06_dark_matter_and_dark_energy.md)
