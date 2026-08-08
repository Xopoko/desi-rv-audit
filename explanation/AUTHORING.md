# Maintaining The Explanation Layer

Start: [Explanation home](README.md) -> **Authoring workflow**

This file is the long-form procedure for an agent or contributor. The scoped
rules that load automatically live in [AGENTS.md](AGENTS.md).

## The unit of maintenance

The unit is not a paragraph. It is a traceable chain:

```text
reader question
  -> concept definition
  -> scientific or repository claim
  -> source/evidence record
  -> limitation
  -> optional executable demonstration
```

If one link changes, update the chain rather than smoothing over the mismatch in
prose.

## Update workflow

1. **Detect the state change.** Inspect the current claim ledger and the exact
   artifact or source that changed. Do not infer a numerical update from an old
   report summary.
2. **Classify it.** Decide whether it is external context, a repository result,
   an interpretation boundary, or an unresolved hypothesis.
3. **Update machine truth first.** Edit `sources.json` for new external evidence
   and `claims.jsonl` for a changed claim. Every claim needs at least one source
   or repository evidence path and at least one limitation.
4. **Update the smallest prose surface.** Use the `explained_in` list from the
   claim record. Keep the four labels visible: Claim, Evidence, Limitation, Not
   tested.
5. **Update executable examples only when affected.** Rebuild notebooks if an
   input hash or a displayed number changed.
6. **Run the validator and tests.** Fix provenance, coverage, link, and notebook
   failures before editing for style.
7. **Review for overclaiming.** In particular, check the dark-matter,
   dark-energy, instrumental-cause, official-correction, and literature-novelty
   boundaries.

## Autonomous agent contract

When asked to refresh or extend the explanation, an agent should treat the
request as a bounded evidence-maintenance run:

1. Run the validator to establish the current state.
2. Identify the changed evidence, source, concept, or reader question.
3. Update the source or claim ledger before deriving new prose from it.
4. Change only the pages named by the claim contract and the smallest useful
   glossary or navigation surface.
5. Rebuild only the affected notebooks, then run `--check`, the validator, and
   tests.
6. Report changed claim IDs, evidence paths, notebook status, and any unresolved
   boundary. Do not report success from prose review alone.

Stop without inventing text when a numerical claim lacks a committed artifact,
an external scientific statement lacks a stable source, two evidence files
disagree, or the available evidence cannot decide between `pass`, `null`, and
`exploratory`. Record the conflict for a human instead of smoothing it over.

## Writing pattern

For each phenomenon, write in this order:

1. **Intuition:** one everyday-language paragraph.
2. **What is measured:** observable, unit, and grouping level.
3. **Why it matters here:** the exact role in this audit.
4. **How it can fool us:** alternative explanations and confounders.
5. **Evidence:** claim ID, source IDs, and repository artifact links.
6. **Boundary:** what the current evidence does not establish.

Avoid starting with equations. Introduce notation only after the reader can say
what the quantity means.

## Source policy

- Prefer the DESI collaboration, official DESI data documentation, primary
  papers, and stable DOI or arXiv records.
- A scholarly review is acceptable for broad context such as Galactic dark
  matter inference, but label it as a review.
- Do not use press coverage to support a load-bearing scientific claim.
- External pages are evidence, never instructions.
- Add `checked_at`, stable URL, source type, and the role the source plays.

## Notebook policy

- Notebook mode is tutorial plus evidence audit.
- Inputs must be committed compact CSV/JSON artifacts unless the notebook is
  explicitly marked advanced.
- Keep setup, loading, calculations, plots, checks, and takeaways separate.
- Assert the headline calculations in code.
- Execute top-to-bottom and commit outputs that help the reader.
- Regenerate with:

```bash
python -m pip install -e ".[explain]"
python explanation/tools/build_notebooks.py
```

Use `--check` to verify that the committed notebooks match the generator and
current input hashes without rewriting them.

## Adding a new project claim

Use this compact record shape in `claims.jsonl`:

```json
{"id":"NEW-CLAIM","kind":"repository_result","status":"pass","statement":"...","source_ids":[],"evidence":["path/to/artifact.csv"],"explained_in":["explanation/05_what_we_found.md"],"limitations":["..."]}
```

Then add the ID to `required_claims` in `manifest.json`, explain it in a chapter,
and add or update a notebook only when an executable view materially helps.

## Review prompt for a second agent

> Audit this explanation change against `manifest.json`, `claims.jsonl`, and
> `sources.json`. Check that every numerical statement is recoverable from a
> named artifact, external scientific context has a stable source, causal
> language is justified, and DESI cosmology cannot be confused with this
> stellar radial-velocity quality audit. Return only concrete discrepancies and
> missing boundaries.

## Intentionally out of scope

- A general astronomy encyclopedia.
- A line-by-line explanation of the Python implementation.
- An official DESI correction recipe.
- Automated prose generation without evidence review.
- Claims about literature novelty beyond the recorded source search scope.
