# PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.meta.md — metadoc

_Created: 19-08-2026 · Last updated: 19-08-2026_

This is a **metadoc** — a document *about* a document. Its subject is
[PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md).
It records what is around the plan, not what is in it. Kept per the standing "one metadoc per
important document" convention.

## Subject

- **Document:** the PLAN index for adding journals.rcsi.science journals to RuWritingStyles as
  both submission profiles and harvested article corpora.
- **Purpose:** to hold every ruling from the 19-08-2026 `/ask` interview so an execution agent
  can build waves 0 and 1 unattended without asking anything.
- **Audience:** the execution agent that runs the minted handoffs; secondarily any future
  session wondering why the harvester was shaped this way.
- **Format / contract:** a decisions table (D01–D20), an autonomy contract, and links to four
  layer documents. The layer documents are subordinate — a contradiction between a layer doc
  and the PLAN's decisions table is resolved in favour of the table.

## Provenance

- **Created:** 19-08-2026, by `/ask` (Opus 5, `claude-opus-5`), from a five-round interview of
  twenty questions.
- **Platform facts** in the PLAN were established by live probe on 19-08-2026, not inferred:
  OAI endpoints, `citation_*` coverage, galley downloadability, the broken site-wide OAI, and
  the slug-is-not-the-ISSN trap.
- **Prior-art sweep** covered the RWS repo itself, IndologyScholars, the installed skills tree,
  and `hub_grep`. `hub_grep "journal harvest OAI-PMH"` returned no hits; the real prior art was
  found by direct grep, which is the recorded reason not to trust a `hub_grep` miss.

## Known limitations / caveats

- **Wave 2 is sketched, not specified.** Only waves 0 and 1 carry file-level steps. Wave 2's
  catalogue crawl will need its own pass once the platform's pagination is actually walked.
- **The fence is narrower than usual.** Of four candidate fences offered, only the
  public-repo-corpus rule was selected. The plan documents this explicitly rather than quietly
  enforcing the other three.
- **The bake-off verdict does not exist yet.** Every statement about which extractor is best is
  a hypothesis until `docs/BENCHMARK_pdf-extractors_ru_19-08-2026.md` is written.
- **Licence facts are per journal and only one is known.** Acta Linguistica Petropolitana is
  CC BY-NC-ND 4.0; the other five were not probed for licence.

## Intended use / known misuse

- **Intended:** paste the handoff starter line into a fresh session and walk away.
- **Misuse:** treating the decisions table as advisory and re-opening a ruled fork mid-build —
  the whole point of the interview was to make that unnecessary. Also: reading the platform
  facts as permanent; they are a dated probe of a third-party site.

## Maintenance & sunset plan

- Update in place when a ruling changes; bump "Last updated" only.
- Waves tick in the ROADMAP, not here.
- Sunset when wave 2 closes and the harvester is a normal feature documented in
  [docs/cli.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/cli.md) — at that
  point the PLAN becomes a historical record and should be marked so.

## Deprecation status

`active`

## Related documents

- [ROADMAP_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ROADMAP_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md) — waves and non-goals.
- [ARCHITECTURE_RuWritingStyles_rcsi-journal-harvest.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ARCHITECTURE_RuWritingStyles_rcsi-journal-harvest.md) — components, schemas, build-vs-reuse.
- [IMPLEMENTATION_RuWritingStyles_rcsi-journal-harvest.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/IMPLEMENTATION_RuWritingStyles_rcsi-journal-harvest.md) — ordered build steps.
- [VERIFICATION_RuWritingStyles_rcsi-journal-harvest.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/VERIFICATION_RuWritingStyles_rcsi-journal-harvest.md) — acceptance and risks.
- [SOURCES.md](https://github.com/gasyoun/RuWritingStyles/blob/main/SOURCES.md) — the rights document the harvest must register into.
- [.ai_state.md](https://github.com/gasyoun/RuWritingStyles/blob/main/.ai_state.md) — carries the H944 / H1882 corpus gates this plan reopens.

## Revision history

| Date | Event | Who (tier+version) |
|---|---|---|
| 19-08-2026 | Plan and all four layer docs authored from a five-round interview | Opus 5 (`claude-opus-5`) |

_Dr. Mārcis Gasūns_
