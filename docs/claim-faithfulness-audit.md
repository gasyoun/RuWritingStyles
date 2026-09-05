_Created: 24-08-2026 · Last updated: 05-09-2026_

# Claim-Faithfulness Audit Protocol

This protocol is the first RuWritingStyles borrow from Academic Research Skills
as a design donor. It re-implements the idea in RuWritingStyles' own terms and
copies no ARS files.

## Purpose

The existing citation layer answers a bibliographic question: does a citation
string resolve to `knowledge/bibliography.json` or a local collection heading?
The claim-faithfulness audit answers a stronger question: does the cited source
support the sentence-level claim it is attached to?

This is not a provider run by default. It is a review packet format and reviewer
workflow for later human or paid-provider execution.

## Audit Packet

Each audited claim is stored in `claim-faithfulness-audit.json` and validated by
[`schemas/claim-faithfulness-audit.schema.json`](https://github.com/gasyoun/RuWritingStyles/blob/main/schemas/claim-faithfulness-audit.schema.json).

Required fields per claim:

| Field | Meaning |
|---|---|
| `claim_id` | Stable id inside the audit packet, e.g. `claim-001`. |
| `span_id` | Segment id from `segments.json`. |
| `claim_text` | The exact claim under review. |
| `citation_ids` | Citation keys attached to the claim. |
| `locator` | Page, section, URL anchor, or local note where support should be checked. |
| `support_status` | `supported`, `partly_supported`, `unsupported`, `wrong_source`, `anchor_missing`, or `needs_human_review`. |
| `severity` | `info`, `warn`, or `high_warn`. |
| `rationale` | Short explanation grounded in the locator. |
| `reviewer_action` | Concrete next action for the author/reviewer. |

## Severity Rules

Use `high_warn` for claims that would mislead a reader if published:

- the citation does not contain the asserted fact;
- the claim reverses or overstates the source;
- the citation exists but has no usable anchor;
- the cited source is the wrong work, edition, or author;
- the source is present only through a secondary summary while the claim reads as primary evidence.

Use `warn` for narrower problems:

- source supports the broad topic but not the exact wording;
- claim needs a page, verse, sutra, or section locator;
- citation is plausible but the bibliography record is incomplete.

Use `info` when the source supports the claim and the locator is sufficient.

## Workflow

1. Extract candidate claims from `revised.md` or `normalized.md`, grouped by
   `span_id`.
2. Attach local citation keys with the existing citation extractor.
3. For each claim, record the most precise available locator.
4. Fill `support_status`, `severity`, `rationale`, and `reviewer_action`.
5. Merge `high_warn` and `warn` results into the regular verification report only
   after reviewer calibration has been run.

## Non-Goals

- Do not run this over unpublished text on a paid provider without explicit
  approval.
- Do not treat missing local bibliography coverage as fabrication.
- Do not copy ARS markdown or prompts into this Apache-licensed repository.

_Dr. Mārcis Gasūns_
