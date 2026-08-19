# RCSI harvest — improvised decisions log

_Created: 19-08-2026 · Last updated: 19-08-2026_

Every ruling an execution agent had to improvise while running
[PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md),
one line each, under the plan's ambiguity policy (D17). Append; never rewrite.

| Date | Wave | Ruling | Why |
|---|---|---|---|
| 19-08-2026 | 0 (H3153) | The plan's prescribed harvester `USER_AGENT` (`RuWritingStyles/<version> (research harvester; …)`) is **403'd site-wide** by the RCSI edge; a common browser UA is served 200 on the same URLs, same second. Bake-off samples were fetched with a browser UA. | Measured on both `/{slug}/oai?verb=Identify` and `/{slug}/article/view/{id}`: research UA → 403, browser UA → 200. Not an endpoint problem and not a rate limit. Binds S1.1 — see the benchmark doc's *Fetching* note. |
| 19-08-2026 | 0 (H3153) | The `deeppapernote` extractor is **folded into the `pymupdf-text` candidate**, not benchmarked as a thirteenth row. | Its `scripts/extract_source_text.py` (local-only, ships with the `deeppapernote` skill outside this repo) calls `fitz.open(...)` then `page.get_text("text")` — byte-identical extraction to the plain PyMuPDF candidate. A separate row would have reported the same numbers twice and inflated the matrix. |
| 19-08-2026 | 0 (H3153) | "Six PDF galleys, one per in-scope journal" (S0.3) was read as **the five pinned articles plus Acta Linguistica Petropolitana** — six galleys across five journal slugs, `0869-5873` contributing two. | The plan's pinned-article table (§ *Pinned articles*) names five articles over four slugs; ALP `2306-5737` is the journal named first in the request. Six galleys, every in-scope journal represented. |
| 19-08-2026 | 0 (H3153) | A candidate that cannot return text for one document within a **300 s budget** scores `timeout`, and that counts as a measurement rather than a harness failure. | The harvester has ~300 articles to get through (D20). An engine needing more than five minutes per document is unusable for that workload whatever its accuracy, so the budget is an acceptance criterion, not a convenience. `docling` exceeded it on most samples; the pure-Python readers finished in under 20 s. Override with `--timeout`. |
| 19-08-2026 | 0 (H3153) | `trafilatura` is installed as a bake-off candidate but **not scored**. | It is an HTML extractor with no PDF path. It belongs to S1.5's `extract_html`, not to a PDF bake-off; scoring it would have produced eight meaningless `error` cells. |
| 19-08-2026 | 0 (H3153) | The `ocrmypdf` candidate reads its OCR output back with **PyMuPDF, never `pdftotext`**. | Reading it with poppler scored 0.00 Cyrillic on every Russian sample and made OCR look useless — it was measuring the poppler bug a second time, not tesseract. The fix moved the row from 1/8 to 8/8. General rule: poppler must not appear anywhere in a pipeline over this material, including as the reader at the end of someone else's extractor. |
| 19-08-2026 | 0 (H3153) | The per-document budget applies to **in-process** candidates too, checked between pages, with a post-hoc downgrade for anything that still overruns. | `subprocess.run(timeout=...)` bounds only the venv and CLI candidates. Without the extra check `easyocr` was scored a comfortable `ok` at 504 s while `docling` was cut off at the budget — two different rules inside one matrix. |
| 19-08-2026 | 0 (H3153) | OCR candidates are capped at the **first 6 pages** of each sample. | A full galley through `tesseract rus` costs minutes per sample and the sanity gate judges encoding, not completeness. The cap is a constant in `tools/benchmark_extractors.py` (`OCR_PAGE_CAP`), not a hidden default. |

_Dr. Mārcis Gasūns_
