# Explanation-Layer Agent Guidance

These rules apply only under `explanation/`.

## Purpose

- Maintain a scientific explanation of this repository.
- Explain scientific meaning, measurement logic, evidence, and boundaries.
- Do not turn these documents into a code-architecture manual.

## Read Order

1. Read `README.md` and `manifest.json`.
2. Read only the chapter relevant to the requested concept or claim.
3. Check `claims.jsonl` and `sources.json` before changing factual prose.
4. Open the named repository evidence file before changing a numerical result.

## Authoring Rules

- Keep repository-facing prose in English.
- Lead with intuition, then measurement, then evidence, then limitations.
- Define a term on first use and link its canonical entry in `GLOSSARY.md`.
- Preserve the distinction between external scientific context and findings of
  this repository.
- Never claim that this audit measures dark matter or dark energy directly.
- Never promote correlation, time persistence, or PETAL association to a
  physical cause without new causal evidence.
- Treat `claims.jsonl` as the claim contract and `sources.json` as the external
  source registry. Generated prose is not the source of truth.
- Use stable primary papers, official DESI documentation, or explicit scholarly
  reviews. Record new sources before citing them.
- Keep notebooks deterministic and based on committed compact artifacts by
  default. Do not make raw multi-gigabyte FITS files a prerequisite for the
  default path.

## Updating The Layer

- When a result changes, update its `claims.jsonl` record, every chapter named
  by `explained_in`, and any affected notebook.
- When a concept or claim is added, add it to `manifest.json` coverage lists.
- When a source changes, preserve its stable identifier and update
  `checked_at` rather than silently replacing provenance.
- Do not rewrite unrelated chapters for a local claim change.
- Follow the detailed workflow in `AUTHORING.md`.

## Verification

From the repository root:

```bash
python explanation/tools/validate_explanation.py
python explanation/tools/build_notebooks.py --check
pytest
```

For notebook regeneration or execution, follow the pinned procedure in
[AUTHORING.md](AUTHORING.md#notebook-policy). A change is not complete if
validation fails, a notebook contains an error output, a claim lacks a
limitation, or a linked evidence path is missing.
