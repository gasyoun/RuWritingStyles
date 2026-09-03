# Screening evidence — `ruwritingstyles-rcsi-catalogue_uncertain-628`

_Created: 03-09-2026 · Last updated: 03-09-2026_

Phase 0-bis evidence for the W2.3 review-queue sheet (roadmap
[docs/ROADMAP_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ROADMAP_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md),
item W2.3). Source data: [knowledge/rcsi/catalogue.json](https://github.com/gasyoun/RuWritingStyles/blob/main/knowledge/rcsi/catalogue.json)
(W2.1 live crawl 31-08-2026, 992 journals: include 61 / exclude 302 / uncertain 629).

## Screening ledger

| Class | n | What resolved it |
|---|---|---|
| (a) deterministic | 1 | Вестник РАН (`0869-5873`): the roadmap rules the five named journals "stay pinned by name regardless of verdict" (W2.1 notes, D13) — a human vote on it would re-ask a decided question |
| (b) dataset lookup | 0 | The five hand-verified profiles in [knowledge/journals/](https://github.com/gasyoun/RuWritingStyles/tree/main/knowledge/journals) all classify `include`; none sits in the uncertain tail, so no lookup fired |
| (c) agent adjudication | 0 | Deliberate: D04's ruling is "the uncertain tail stays visible instead of silently dropped" — the review queue IS the deliverable, so the 628 scope judgments route to the human, not to a model pass |
| (d) human required | 628 | Nothing above settles them: the classifier's designed conflicting-witness verdict or the absence of scope evidence on the platform page |

## The three judgment classes (U7 typology, denominator stated)

| filt | n | share of 629 | Meaning |
|---|---|---|---|
| `conflict` | 15 | 2% | Both a positive and a negative term matched (e.g. `morphology` inside paleontology scope prose). Both term sets shown on the card. |
| `noscope` | 325 | 52% | No `#focusAndScope` text captured at crawl time (the Вестник РАН class: the platform page has no such section). Card states the absence explicitly; judged by name + journal page link. |
| `noterms` | 288 | 46% | Scope text exists, contains no term-list word. Verbatim excerpt quoted on the card. |

Denominator chain (stated on every card and in the footer): 992 crawled → 629 uncertain → 628 cards.

## Uncertain articles — empty with reason

The article-level uncertain queue is **empty at sheet time**: the bounded
harvest (W2.4) that would produce article-level `selection` verdicts has not
run; the five pinned articles were hand-named (D13) and are includes. The
subtitle on the sheet states this and promises a separate article-level sheet
after W2.4, so the article tail is visible-by-contract rather than dropped.

## Emitter preflight notes

- **V9 manifest:** joined `knowledge/rcsi/catalogue.json` on `slug` for all
  628 row ids (fields: name, repository, url, excerpt, verdict, term sets);
  omitted the full `#focusAndScope` texts with reason — the crawl stores
  500-char excerpts only, and the full text is one click away through each
  card's title link, so nothing is judged from a truncated witness.
- **V13 identity gate:** patterns are the escaped catalogue slugs
  (word-bounded); every slug mentioned in a question (own or a foreign ISSN
  quoted inside an excerpt) must appear together with its journal name. Each
  card carries an identity line («Журнал … · id …») satisfying the own-slug
  case. Year ranges in English prose («published in 1996-2012») are not
  catalogue slugs and correctly trip nothing.
- **SLP1 allow-list:** the scope excerpts are verbatim English journal prose;
  the heuristic flags ordinary English words there (`information`,
  `conferences`, …). The generator allows exactly the tokens the rendered
  cards themselves carry (computed per render, never hardcoded) — a genuinely
  SLP1 token in a future excerpt still blocks the build.
- **github_inbox:** not wired — no OAuth device-flow `client_id` exists on
  this machine (checked Uprava docs/tools, `~/.secrets`). Each pack exports to
  its own `…_pack-NN_decisions.json` (V8 banner names the drop path
  `RuWritingStyles/review/`), which prevents the 63-export collision; wiring
  the inbox is a residual for a machine that holds the client id.

_Dr. Mārcis Gasūns_
