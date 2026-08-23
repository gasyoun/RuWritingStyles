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
