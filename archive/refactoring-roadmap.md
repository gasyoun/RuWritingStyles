_Created: 24-08-2026 · Last updated: 05-09-2026_

# Refactoring Roadmap

This note records the architectural review and the first refactoring pass for
the executable RuWritingStyles pipeline.

## Architectural Review

The repository is not fully monolithic: the CLI, provider adapters, run
artifacts, reports, validation, evaluation, and prompt bundle creation already
live in separate modules. That structure is workable for the current MVP.

The weak boundary was the deterministic text core. `segment.py` previously did
input reading, Unicode cleanup, Markdown scanning, span assignment, and implicit
linguistic assumptions in one small module. That made the pipeline hard to
extend for corpora, legacy encodings, or deterministic style parameters.

The current refactor keeps the public CLI stable while separating the core
responsibilities:

```text
src/ruwritingstyles/
  document.py      # text input, encoding detection, graceful input errors
  linguistics.py   # Russian-aware surface metrics and token/sentence helpers
  segment.py       # Markdown segmentation and stable span IDs
  review.py        # review prompt bundle creation
  council.py       # cross-style decision bundle creation
  revision.py      # synthesis bundle creation
  verification.py  # fidelity verification bundle creation
  providers.py     # provider adapters and retry telemetry
  execution.py     # provider execution boundary
  validation.py    # artifact validation
```

If the project grows beyond the MVP, the next scalable hierarchy should split
package areas more explicitly:

```text
src/ruwritingstyles/
  core/
    document_io.py
    normalization.py
    segmentation.py
    metrics.py
    rules.py
  artifacts/
    runs.py
    schemas.py
    validation.py
  agents/
    review.py
    council.py
    revision.py
    verification.py
  providers/
    base.py
    openai.py
    google.py
    anthropic.py
    mock.py
  reports/
    markdown.py
    html.py
  cli.py
```

That move should wait until more rules and providers exist, because a larger
package tree would add ceremony without much benefit today.

## Refactoring Steps Taken

1. Added `document.py` as the text input boundary.
   It reads Markdown/TXT as bytes, prefers UTF-8, accepts Russian legacy
   encodings such as CP1251 and KOI8-R when plausible, and raises
   `DocumentInputError` for binary or unsupported input.

2. Added `linguistics.py` for cheap, deterministic Russian-aware metrics.
   It counts words, approximate sentences, Cyrillic/Latin script usage,
   mixed-script tokens, historical Cyrillic letters, stress marks, question and
   exclamation marks, and long sentences.

3. Refactored `segment.py`.
   The module now preserves Unicode philological detail, keeps stable span IDs,
   supports configurable long-paragraph splitting, recognizes both backtick and
   tilde Markdown fences, and attaches per-segment metrics to `segments.json`.

4. Preserved the existing CLI and imports.
   Existing commands still call `read_document`, `normalize_document`, and
   `segment_markdown`; the refactor changes internals, not user workflow.

5. Added regression tests.
   Tests cover CP1251 input, binary rejection, preservation of Russian
   philological marks, deterministic metrics, and sentence-boundary splitting.

## Linguistic Assumptions

The deterministic layer is a surface profiler, not a morphology engine. It does
not lemmatize, parse syntax, infer stress placement, or validate etymology.

The normalizer must preserve philologically meaningful characters. It does not
replace the Russian `yo` letter with `e`, does not strip combining stress marks,
and does not discard historical Cyrillic letters used in older or quoted forms.

Sentence splitting is approximate. It treats terminal punctuation as a boundary,
which is useful for chunking long paragraphs but can overcount abbreviations.
Serious philological conclusions must remain in style rules, source-critical
checks, or expert review, not in these metrics.

Mixed Cyrillic/Latin words are flagged because they can signal transliteration,
OCR noise, copied source sigla, or accidental keyboard-layout corruption. The
metric is descriptive, not automatically erroneous.

## Dependency Guidance

The refactor keeps the existing zero-runtime-dependency policy.

Potential future migrations:

- `PyYAML` for manifest/model-policy parsing instead of regex-based YAML subsets.
- `regex` for Unicode script properties and cleaner Cyrillic/Latin token rules.
- `razdel` for Russian sentence and word segmentation.
- `pymorphy3` or a comparable morphology stack for grammatical features when
  rules need lemmas, parts of speech, case, gender, or number.
- `charset-normalizer` if the repository begins ingesting many unknown legacy
  corpora and the standard-library heuristic is no longer enough.

Add these only when evaluation cases prove the need; otherwise the deterministic
core should stay small, inspectable, and predictable.

_Dr. Mārcis Gasūns_
