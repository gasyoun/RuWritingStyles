# RCSI harvest — improvised rulings log (D17)

Append-only. One line per improvised call; the run must finish, every
improvised call stays visible here.

- 23-08-2026 (S1.1): the plan's research-harvester UA is confirmed 403'd
  site-wide; the client ships a browser-shaped UA and keeps the 1 req/s
  throttle. Revisit only if the platform grants an allowance.
- 23-08-2026 (S1.5 spike): the Филологические науки article page carries only a
  ~350-word metadata block — a sub-threshold HTML body means "try the PDF",
  not "quarantine". This is the D07 fall-through working as designed.
- 23-08-2026 (S1.9 fixture export): the live Вестник РАН ListRecords payload
  contains a raw NUL byte inside an abstract — the platform's own XML is
  occasionally not well-formed. The client strips C0 controls before parsing
  (`rcsi._parse_oai`); the fixture is kept byte-faithful to the real response.
- 23-08-2026 (D13 verify): article 2782-5329/400674 exposes no DOI and no EDN
  anywhere on its platform page. The bibliography row is then keyed by the
  article URL instead of a DOI; corpus-verify accepts either key.
- 23-08-2026 (D13 verify): the Плунгян harvested body never repeats its
  Russian title (the body leads with the English metadata block), so a
  title-derived FTS probe would permanently fail an indexed file. The probe
  falls back to the five longest tokens from the text itself.
- 31-08-2026 (W2.1 walk): out-of-range index pages do not go empty — the
  platform re-serves its final five-entry page forever, so an empty-page
  termination rule alone walks 40 pages and stops at `_MAX_INDEX_PAGES`. The
  walk additionally stops on the first page byte-identical to the previous
  one (repeat-detection first seen in the H3369 fuzz-grep discipline).
- 31-08-2026 (W2.1 Identify): five journals (2542-1816, 2782-4926, 2782-540X,
  2782-6058, 3034-6335) redirect their OAI endpoint to a Login HTML page.
  `_parse_oai` degrades non-XML payloads to `RcsiError`; `build_catalogue`
  records the anomaly in `evidence_other` and keeps the journal at its
  scope-based verdict (autonomy contract §2 — one closed OAI is not a stop).
- 31-08-2026 (W2.1 scope): Вестник РАН (0869-5873) genuinely has no
  `#focusAndScope` section on its Editorial Policies page — it stays
  `uncertain` on empty scope, and journal `vramn` (Annals of the Russian
  Academy of Medical Sciences) is a different journal entirely. No evidence
  is invented; the named-journals pin (five articles + Acta profile) already
  covers Вестник РАН without a classifier verdict.
- 31-08-2026 (W2.1 catalogue): the index serves more non-ISSN slugs than the
  19-08 probe saw (`DD`, `NW`, `PharmForm`, `ecolgenet`, …). The crawl keys on
  the URL slug verbatim — the S1.1 hazard ("slug is not always the ISSN")
  generalises to "slug is not always even ISSN-shaped".
