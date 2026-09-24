# ROADMAP — RuWritingStyles 2026-Q4 (waves H1 · C1 · E1 · P1)

_Created: 23-08-2026 · Last updated: 24-09-2026_

> **Truth-pass 02-09-2026** (H3775) — `roadmap_handoff_truth.py --check` flagged this
> page drained but still living: **12 of 12 referenced handoffs have shipped, zero remain OPEN**.
> Kept at this path per MG ruling 31-08-2026 (do not archive) — the strategy/plan
> layer still holds even though its backlog has fully closed. A future session
> reopening work here should mint a fresh H### rather than un-close these.

> **Truth-pass 24-09-2026** (H5376, verdict pass E015 wave 1) — re-verified against
> live git history and the current `.ai_state.md`/`CITATION.cff`. Waves H1, C1.1,
> C1.2 (4 of 5 passports), C1.3 and the agent-doable half of P1 are all SHIPPED and
> MERGED (evidence in the unminted-prose table below). Kept ARCHIVE-eligible content
> struck; kept alive because five items remain genuinely unminted or author-gated —
> see **What is left** below, each with a GTD row.

Authored via `/roadmap-interview` on 23-08-2026 after an evidence audit (repo state v2.26.0,
[Q3 roadmap](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/roadmap-2026-q3.md)
residue, open PRs, `.ai_state` queue). MG answered two interview rounds; every wave below
traces to a ruling he made. Execution units live as `H###` handoffs in
[Uprava/handoffs](https://github.com/gasyoun/Uprava/blob/main/handoffs/README.md) — this doc
is the map, not the work order.

## Diagnosis (why exactly these four waves)

Q3 ended with the engineering core green: v2.26.0, required CI gate stable, 60-case protected
eval suite, span-patch revision at pass-rate 0.92. What remains is not new capability but
**throughput**: the [RCSI harvest](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ROADMAP_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md)
wave 0 shipped but waves 1–2 sit unexecuted; five scholar passports stay corpus-gated with
batch size = 0; a paid-provider benchmark has been owed since v2.25.0 (H2713); and a thin
layer of publication/housekeeping buttons (DOI, Obsidian release repo, dependabot) keeps
rolling forward every weekly review. Q4 is the quarter that drains these instead of adding
surface.

## Decisions taken (interview of 23-08-2026)

| # | Fork | Ruling |
|---|---|---|
| 1 | Primary Q4 theme | **Balanced waves** — no single backbone; small parallel waves across harvest, corpus intake, publication, housekeeping |
| 2 | Corpus gate on scholar passports | **Active intake wave** — hunt/extract attributable texts now instead of waiting for them to land |
| 3 | Paid-provider benchmark owed since v2.25.0 | **One bounded window budgeted** (N=5 deepseek) after wave-H1 changes land |
| 4 | Residue items (dependabot, Obsidian repo, DOI) | **Polish wave inside Q4**, not left to weekly sweeps |
| 5 | RCSI harvest depth | **Wave 1 fully, wave 2 gated on wave 1's verdict** — catalogue crawl starts only after the pinned-article guarantee holds |
| 6 | Intake order | **Orientalists first** (Kratchkovsky · Bartold · Turaev · Golenishchev · Shileiko), Lotman/Meletinsky second |

## Wave H1 — RCSI harvest wave 1 (the pinned five-article guarantee)

Executor: [H3154 (Opus 5) — RCSI wave 1: journal profile derivation, article harvester, pinned-article guarantee](https://github.com/gasyoun/Uprava/blob/main/handoffs/H3154-Opus_RuWritingStyles_rcsi-journal-harvester-wave1_19.08.26.md)
— QUEUED since 19-08-2026; its only dependency (H3153, the extractor bake-off) closed in
v2.26.0, so it is launchable now. Deliverables: `rws journal-add` / `journal-harvest` /
`corpus-verify`, the extended journal-profile schema, the five pinned articles harvested with
sidecars and bibliography rows, `SOURCES.md` licence rows.

**Unblocks:** wave H2 of the harvest — the catalogue crawl and bounded bulk
(W2.1–W2.5 of the [RCSI roadmap](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/ROADMAP_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md)) — but per ruling 5 that
wave is gated: it starts only after `rws corpus-verify` holds 5/5 and its own review-sheet
verdict says the platform facts survived contact with reality. Mint the wave-2 handoff at
that gate, not before.

## Wave C1 — corpus intake for the scholar-passport programme

Ruling 2 turned three passive corpus-gated rows into an active programme; ruling 6 fixed the
order.

- **C1.1 — Orientalist intake sprint** → [H3369 (Sonnet 5) — Orientalist scholar text intake sprint into private corpus](https://github.com/gasyoun/Uprava/blob/main/handoffs/H3369-Sonnet_RuWritingStyles_orientalist-corpus-intake_23.08.26.md):
  attributable texts of Kratchkovsky, Bartold, Turaev, Golenishchev and Shileiko hunted,
  license-recorded, extracted through the pinned `PDF_EXTRACTOR_CHAIN`, and committed to the
  private [RuWritingStyles-corpus](https://github.com/gasyoun/RuWritingStyles-corpus) with
  provenance sidecars. Negative controls: the two multi-author Digital Humanities volumes
  must be rejected as non-attributable.
- **C1.2 — Passport builds (gated on C1.1).** Once texts land, the five orientalist passports
  become buildable (the H944 gate lifts). Each passport is a separate judgment-tier handoff
  in the H1861 mold (Lotman/Meletinsky precedent) — mint per-scholar when the intake lands;
  do not author passports inside the sprint.
  **Progress 23-08-2026: Bartold ([H3381](https://github.com/gasyoun/Uprava/blob/main/handoffs/README.md)), Turaev ([H3382](https://github.com/gasyoun/Uprava/blob/main/handoffs/H3382-OxAlpha_RuWritingStyles_turaev-passport-build_23.08.26.md)), Krachkovskij ([H3383](https://github.com/gasyoun/Uprava/blob/main/handoffs/H3383-OxAlpha_RuWritingStyles_krachkovskij-passport-build_23.08.26.md)) and Golenishchev ([H3384](https://github.com/gasyoun/Uprava/blob/main/handoffs/H3384-OxAlpha_RuWritingStyles_golenishchev-passport-build_23.08.26.md)) built and corpus-grounded — 4 of 5; only Shileiko stays gated (texts via V. B. Emelyanov).**
- **C1.3 — Lotman/Meletinsky verification (second in line).** «Структура художественного текста»
  / «Культура и взрыв» / «Поэтика мифа» extractions land via the same intake discipline, then
  the existing [H1861](https://github.com/gasyoun/Uprava/blob/main/handoffs/README.md) passports get corpus-grounded anchors.
- Poppe cluster attachment stays parked behind the @DECIDE row in GTD — texts must pass the
  same intake gate first.

## Wave E1 — one bounded paid benchmark window

The v2.25.0 `limits` clause changed review-prompt text, so every paid number since A29 §4.6/§4.7
is incomparable to the published tables ([H2713 debt](https://github.com/gasyoun/RuWritingStyles/blob/main/.ai_state.md)).
Per ruling 3, budget exactly one bounded window after wave H1 merges:
`rws eval-suite --provider deepseek --repeat 5` → `rws eval-promote`, then quote fresh numbers
against a fresh baseline. The mock lane and CI stay untouched throughout. The same window is
where the author's pending benchmark decision belongs: adjudicate
`h1213dict-dict-zone-order-r05` (@DECIDE row in GTD), the last unresolved H1213 item.

## Wave P1 — polish and publication residue

Status 23-08-2026 (H3370 execution): dependabot triaged — #118/#120 closed superseded
(main already runs `checkout@v7` / `setup-python@v7`), #163–#166 on auto-merge per repo
policy (patch/minor; they rebase+land autonomously). `gasyoun/ruwritingstyles-obsidian`
created public behind a publish-safety GO, bare tag `0.1.0` released with artifacts
([release](https://github.com/ruwritingstyles-obsidian/releases/tag/0.1.0)) — bare, not
`obsidian-v`, because the release workflow and the obsidianmd/BRAT contract require it.
`.zenodo.json` version drift fixed (2.16.0 → 2.26.0). LICENSE now ships in the release
payload. Remaining author buttons: obsidianmd PR, BRAT listing, Zenodo link+deposit,
A29 submission — all in GTD.

Executor for the agent-doable half: [H3370 (Sonnet 5) — Q4 polish sweep](https://github.com/gasyoun/Uprava/blob/main/handoffs/H3370-Sonnet_RuWritingStyles_q4-polish-sweep_23.08.26.md):
six open dependabot PRs triaged (#163–#166 web npm; #120 checkout 5→7; #118 setup-python 6→7),
`gasyoun/ruwritingstyles-obsidian` created from the release-repo scaffold at tag
`obsidian-v0.1.0` behind a publish-safety GO, and CITATION.cff / .zenodo.json verified against
HEAD per [docs/zenodo-doi-steps.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/zenodo-doi-steps.md).

The genuinely human buttons are wired to GTD and stay there until ruled/done:

| Action | Where |
|---|---|
| ~~Link repo to Zenodo + confirm deposit → DOI~~ | **SHIPPED** — `10.5281/zenodo.20696614` live in [`CITATION.cff`](https://github.com/gasyoun/RuWritingStyles/blob/main/CITATION.cff) (verified 24-09-2026) |
| Submit A29 methodology paper to Вестник СПбГУ | [GTD @DO H5376-A29](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md) |
| obsidianmd/obsidian-releases PR + BRAT listing | [GTD @DO H5376-obsidian](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md) |
| GitHub Support GC of dangling corpus objects + archive local backup mirror | [GTD @DO H5376-gc](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md) |

## What is left (truth-pass 24-09-2026, H5376)

All engineering waves shipped and merged — evidence: H3154 harvest wave 1
([PR #175](https://github.com/gasyoun/RuWritingStyles/pull/175)), H3369 orientalist
intake (Bartold/Turaev/Golenishchev/Kratchkovsky gates lifted, docs commits
`8514b12`/`6b19da1`), H3381–H3384 four of five passports
([#176](https://github.com/gasyoun/RuWritingStyles/pull/176)
[#177](https://github.com/gasyoun/RuWritingStyles/pull/177)
[#178](https://github.com/gasyoun/RuWritingStyles/pull/178)
[#179](https://github.com/gasyoun/RuWritingStyles/pull/179)), H1861 Lotman/Meletinsky
([#129](https://github.com/gasyoun/RuWritingStyles/pull/129)), H3370 polish sweep
(dependabot triaged, Obsidian release repo live at tag `0.1.0`). Five items remain
genuinely open, none of them an engineering gap an agent can close unattended:

- [ ] **Shileiko passport** — gated on attributable texts via V. B. Emelyanov (external
  human, not MG). [@WAITING H5376-shileiko](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md), no date.
- [ ] **E1 fresh N=5 DeepSeek re-baseline** — `rws eval-suite --provider deepseek --repeat 5`
  → `rws eval-promote`; agent-doable, not human-gated, still unminted since H3154 merged
  23-08-2026 (`.ai_state.md` line 14, also covers H5283's eight-passport prompt change).
- [ ] **h1213dict-dict-zone-order-r05 adjudication** — the sole unresolved H1213 benchmark
  decision, evidence prepared, needs the author's call.
  [@DECIDE H5376-h1213](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md), no date.
- [ ] **A29 methodology paper → Вестник СПбГУ** — submission is author-only.
  [@DO H5376-A29](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md), no date.
- [ ] **obsidianmd/obsidian-releases PR + BRAT listing** — the plugin mirror is live
  (`gasyoun/ruwritingstyles-obsidian` tag `0.1.0`) but community-directory submission is
  author-only per this repo's own classification (`.ai_state.md` line 15 "Author
  publication actions"). [@DO H5376-obsidian](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md), no date.
- [ ] **GitHub Support GC of dangling corpus objects + archive local backup mirror** —
  account-admin action, author-only. [@DO H5376-gc](https://github.com/gasyoun/Uprava/blob/main/GTD_NEXT_ACTIONS.md), no date.

Kept alive at this path (not archived) per the same 31-08-2026 ruling as the 02-09
truth-pass: the strategy/plan layer still holds even though most of its backlog closed.

## Sequencing

H1, C1.1 and P1 are mutually independent — different repos, different skills; run them in any
order or in parallel sessions. E1 waits on H1. C1.2/C1.3 wait on C1.1. The harvest wave 2
waits on H1 plus its own verdict gate.

## Non-goals

Considered in the interview and explicitly declined, recorded so no future session re-proposes
them:

- **No single-backbone quarter.** A pure RCSI-harvest quarter was offered and declined for
  balance (ruling 1).
- **No passive corpus gating.** Waiting for texts to arrive naturally was declined (ruling 2).
- **No ungated catalogue crawl.** Full W1+W2 push regardless of findings was declined (ruling 5).
- **No new capability surface.** Web Studio features and new passport families beyond the
  corpus-gated ones are out of scope this quarter; Q4 drains, it does not add.
- **No eval-scoring changes.** Same fence as the RCSI plan: harvesting cannot move a score,
  so a moved score would be masking something.
- **No public-repo corpus.** The D18 hard fence restates itself for every wave above.

_Dr. Mārcis Gasūns_
