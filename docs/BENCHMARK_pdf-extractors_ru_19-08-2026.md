# BENCHMARK — PDF text extractors on Russian galleys

_Created: 19-08-2026 · Last updated: 19-08-2026_

Scored bake-off settling **D08** (extractor choice) and **D09** (candidate list) of
[PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/PLAN_RuWritingStyles_rcsi-journal-harvest_2026-Q3.md).
Run by **Opus 5** (`claude-opus-5`) under
[H3153](https://github.com/gasyoun/Uprava/blob/main/handoffs/H3153-Opus_RuWritingStyles_rcsi-pdf-extractor-bakeoff_19.08.26.md).

## Verdict

**Winner: `pymupdf-text`** — PyMuPDF's `page.get_text("text")`. It scored 8/8 at a
**0.6 s median** per document: seven candidates reached 8/8, and it was by far the
cheapest of them (next-fastest full-marks candidate `pypdf` at 2.8 s, `pdfminer.six`
at 6.5 s, the OCR engines at ~25 s).

**Fallback chain, pinned in
[src/ruwritingstyles/config.py](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/config.py)
as `PDF_EXTRACTOR_CHAIN`:**

```
pymupdf-text  ->  pdfminer.six  ->  pypdf  ->  ocrmypdf+tesseract rus
```

Try each in turn and keep the first whose `extract.sanity` verdict is `pass`. The
first three are independent pure-Python text-layer readers; the fourth ignores the
text layer entirely and re-images the page, so it is the escalation for a PDF with
no recoverable text layer at all. That last rung is not an assumption — it also
scored 8/8 here, at a 24 s median.

**`pdftotext` is removed from the pipeline.** It scored **1/8** — it extracted *zero*
Cyrillic from every Russian sample, including all six RCSI galleys. Its single pass
was the one English-language article. This is not a tuning problem: poppler returns
plausible-looking output with the Cyrillic runs blanked, which is precisely the
failure `.ai_state.md` recorded and precisely why a length check would not have
caught it.

This was not a close call needing the D17 tie-break, but it lands where the marked
default pointed anyway: PyMuPDF, because embedded font encodings were the recorded
failure mode.

## How to reproduce

Samples live **outside** this repo (D18); only SHA-256 and source URL are recorded
here. `--venv` supplies the throwaway virtualenv holding candidates that are not
project dependencies (D19).

```
python tools/benchmark_extractors.py --report \
    --samples <scratch>/samples \
    --corpus ../RuWritingStyles-corpus/PDFtoTXT \
    --venv <scratch>/bakeoff-venv \
    --latin-samples 2306-5737 \
    --json <scratch>/scores.json
```

`--only <candidates>` plus `--merge <prior.json>` re-runs one candidate and patches
its cells into an existing matrix, so a slow engine can be re-measured without
repeating the whole sweep. Carried-over cells are **re-judged against the current
thresholds** on merge, so a matrix assembled over several passes can never mix two
calibrations — the four ratios are the measurement, the verdict is only an opinion
about them (`extract.verdict_for`).

`--latin-samples` names samples that are not in Russian; see *Not every RCSI article
is Russian* below. `--resume` skips cells already present in `--merge`, and the tool
checkpoints after **every** cell — the heavy engines take minutes per document, so an
interrupted sweep must cost only the cell it was inside, not the whole row.

### The per-document budget

`--timeout` (default 300 s, run here at **120 s**) is an acceptance criterion, not a
convenience. The harvest is ~300 articles (D20); an engine needing more than two
minutes per document costs over ten hours for one pass, whatever its accuracy. A cell
that overruns is scored `over budget` — its ratios are kept, because they are a real
measurement of what the engine returned, but its verdict is `fail`.

The budget is applied **uniformly**. `subprocess.run(timeout=...)` bounds only the
venv and CLI candidates; the in-process OCR engines check it between pages, and any
cell that still overruns is downgraded afterwards. Without that, `easyocr` scored a
comfortable `ok` at 504 s on the first sample while `docling` was being cut off at
the budget — two different rules in one matrix.

## Candidate inventory (S0.1)

Established on this machine, 19-08-2026. `~/.claude/skills` and `~/.claude/commands`
were swept for further extraction paths as S0.1 requires.

| Candidate | Version | Availability | Note |
|---|---|---|---|
| `pdftotext` (poppler) | 4.00 | on PATH | plain and `-layout` benchmarked separately |
| `pymupdf-text` / `pymupdf-blocks` | PyMuPDF 1.27.2.3 | project dependency | `get_text("text")` and block-ordered |
| `pdfminer.six` | 20260107 | project dependency | |
| `pypdf` | 6.11.0 | project dependency | |
| `ocrmypdf` + `tesseract` | 17.8.0 / 5.5.0 | on PATH | `rus`, `san`, `deu`, `eng`, `osd` traineddata present |
| `pytesseract` (render-then-OCR) | 0.3.13 | project dependency | the crop-then-OCR family, without ocrmypdf's wrapper |
| `easyocr` | 1.7.2 | project dependency | second OCR engine — neural recogniser rather than tesseract's line model. Ran, but ~500 s/document on CPU here: over budget on every sample. |
| `pdfplumber` | 0.11.10 | throwaway venv | not a project dependency |
| `docling` | 2.120.3 | throwaway venv | pulls `torch` 2.13.0 |
| `unstructured` | 0.18.32 | throwaway venv | `unstructured[pdf]` |
| `marker` | — | **unavailable** | `marker-pdf` pins Pillow 10.4.0, which has no Python 3.14 Windows wheel and fails to build from source. Recorded and skipped per D19; never retried. |
| `trafilatura` | 2.2.0 | throwaway venv | **not benchmarked** — an HTML extractor, no PDF path. Belongs to S1.5's `extract_html`, not to this bake-off. |

The `deeppapernote` skill's extractor was found by the S0.1 sweep and is **folded into
`pymupdf-text`**, not scored as a separate row: its `scripts/extract_source_text.py`
calls `fitz.open(...)` then `page.get_text("text")`, so a separate row would have
reported the same numbers twice.

## Sample set (S0.3)

Six PDF galleys — the five articles pinned in the plan plus Acta Linguistica
Petropolitana, covering every in-scope journal — and the two corpus PDFs
[.ai_state.md](https://github.com/gasyoun/RuWritingStyles/blob/main/.ai_state.md)
records as `pdftotext` Cyrillic failures. The latter two are mandatory: a comparison
covering only PDFs that already worked would prove nothing.

| Sample | Journal | Lang | Bytes | SHA-256 (first 16) | Source |
|---|---|---|---|---|---|
| `0869-5873` | Вестник Российской академии наук | ru | 150 386 | `d6fa4720dba7a2a0` | [article/download/268311](https://journals.rcsi.science/0869-5873/article/download/268311/247270) |
| `0869-5873b` | Вестник Российской академии наук | ru | 105 030 | `970b51b15c18e85f` | [article/download/268371](https://journals.rcsi.science/0869-5873/article/download/268371/247336) |
| `2313-2299` | RUDN Journal of Language Studies, Semiotics and Semantics | ru | 566 256 | `918a021aa16471a4` | [article/download/323403](https://journals.rcsi.science/2313-2299/article/download/323403/298069) |
| `2782-5329` | Philological Sciences Bulletin | ru | 1 051 315 | `3faf12033cb15aa7` | [article/download/400674](https://journals.rcsi.science/2782-5329/article/download/400674/668487) |
| `0373-658X` | Вопросы языкознания | ru | 1 189 388 | `81b32a49b79c3391` | [article/download/261465](https://journals.rcsi.science/0373-658X/article/download/261465/240234) |
| `2306-5737` | Acta Linguistica Petropolitana 21.1 | **en** | 491 611 | `0a800324ff42d955` | [article/download/416857](https://journals.rcsi.science/2306-5737/article/download/416857/683756) |
| `corpus:Digital_Humanities-2023` | private corpus | ru | 28 144 429 | `50262eda7334ab8c` | not redistributable |
| `corpus:Digital-Humanities_IgorPilshchikov` | private corpus | ru | 5 889 844 | `ec5f819102dbfa3b` | not redistributable |

## Score matrix (S0.5)

Each cell is the `extract.sanity` verdict plus the three ratios that decided it:
`cyr` = Cyrillic share of all letters, `hit` = share of tokens that look like real
words, `w` = token count. OCR candidates are capped at the first 6 pages
(`OCR_PAGE_CAP`).

| Candidate | 0373-658X | 0869-5873 | 0869-5873b | 2306-5737 | 2313-2299 | 2782-5329 | corpus:Digital_Humanities-2023 | corpus:Digital-Humanities_IgorPilshchikov | passes |
|---|---|---|---|---|---|---|---|---|---|
| `pdftotext` | FAIL cyr 0.00 · hit 0.00 · w 1456 | FAIL cyr 0.00 · hit 0.00 · w 366 | FAIL cyr 0.00 · hit 0.00 · w 171 | PASS cyr 0.00 · hit 0.62 · w 7475 | FAIL cyr 0.00 · hit 0.00 · w 2477 | FAIL cyr 0.00 · hit 0.00 · w 359 | FAIL cyr 0.00 · hit 0.00 · w 5737 | FAIL cyr 0.00 · hit 0.00 · w 2884 | **1/8** |
| `pdftotext -layout` | FAIL cyr 0.00 · hit 0.00 · w 1492 | FAIL cyr 0.00 · hit 0.00 · w 368 | FAIL cyr 0.00 · hit 0.00 · w 171 | PASS cyr 0.00 · hit 0.61 · w 7605 | FAIL cyr 0.00 · hit 0.00 · w 2479 | FAIL cyr 0.00 · hit 0.00 · w 363 | FAIL cyr 0.00 · hit 0.00 · w 5747 | FAIL cyr 0.00 · hit 0.00 · w 2941 | **1/8** |
| `pymupdf-text` | PASS cyr 0.87 · hit 0.51 · w 10079 | PASS cyr 0.92 · hit 0.56 · w 4280 | PASS cyr 0.91 · hit 0.56 · w 1607 | PASS cyr 0.06 · hit 0.59 · w 7883 | PASS cyr 0.74 · hit 0.54 · w 7900 | PASS cyr 0.80 · hit 0.55 · w 1691 | PASS cyr 0.92 · hit 0.55 · w 57272 | PASS cyr 0.93 · hit 0.55 · w 43696 | **8/8** |
| `pymupdf-blocks` | PASS cyr 0.87 · hit 0.51 · w 10079 | PASS cyr 0.92 · hit 0.56 · w 4280 | PASS cyr 0.91 · hit 0.56 · w 1607 | PASS cyr 0.06 · hit 0.59 · w 7883 | PASS cyr 0.74 · hit 0.54 · w 7900 | PASS cyr 0.80 · hit 0.55 · w 1691 | PASS cyr 0.92 · hit 0.55 · w 57272 | PASS cyr 0.93 · hit 0.55 · w 43696 | **8/8** |
| `pdfminer.six` | PASS cyr 0.87 · hit 0.51 · w 10081 | PASS cyr 0.92 · hit 0.56 · w 4280 | PASS cyr 0.91 · hit 0.56 · w 1607 | PASS cyr 0.06 · hit 0.59 · w 7882 | PASS cyr 0.74 · hit 0.54 · w 7901 | PASS cyr 0.80 · hit 0.55 · w 1691 | PASS cyr 0.92 · hit 0.55 · w 57363 | PASS cyr 0.90 · hit 0.55 · w 46242 | **8/8** |
| `pypdf` | PASS cyr 0.87 · hit 0.51 · w 10084 | PASS cyr 0.92 · hit 0.56 · w 4280 | PASS cyr 0.91 · hit 0.56 · w 1607 | PASS cyr 0.06 · hit 0.59 · w 7884 | PASS cyr 0.74 · hit 0.54 · w 7907 | PASS cyr 0.80 · hit 0.55 · w 1698 | PASS cyr 0.92 · hit 0.55 · w 57368 | PASS cyr 0.87 · hit 0.43 · w 56483 | **8/8** |
| `pdfplumber` | PASS cyr 0.87 · hit 0.51 · w 10081 | PASS cyr 0.92 · hit 0.56 · w 4280 | PASS cyr 0.91 · hit 0.56 · w 1607 | PASS cyr 0.06 · hit 0.59 · w 7884 | PASS cyr 0.74 · hit 0.54 · w 7901 | PASS cyr 0.80 · hit 0.55 · w 1691 | PASS cyr 0.92 · hit 0.55 · w 57332 | PASS cyr 0.90 · hit 0.55 · w 46242 | **8/8** |
| `ocrmypdf+tesseract rus` | PASS cyr 0.87 · hit 0.51 · w 10085 | PASS cyr 0.93 · hit 0.56 · w 4286 | PASS cyr 0.91 · hit 0.56 · w 1612 | PASS cyr 0.06 · hit 0.59 · w 7862 | PASS cyr 0.74 · hit 0.54 · w 7903 | PASS cyr 0.81 · hit 0.55 · w 1883 | PASS cyr 0.92 · hit 0.55 · w 57315 | PASS cyr 0.93 · hit 0.55 · w 43717 | **8/8** |
| `tesseract rus (render)` | PASS cyr 0.85 · hit 0.50 · w 2254 | PASS cyr 0.99 · hit 0.56 · w 3712 | PASS cyr 0.91 · hit 0.56 · w 1607 | PASS cyr 0.22 · hit 0.57 · w 2061 | PASS cyr 0.72 · hit 0.54 · w 2095 | PASS cyr 0.81 · hit 0.56 · w 1853 | PASS cyr 0.92 · hit 0.50 · w 727 | PASS cyr 0.91 · hit 0.51 · w 317 | **8/8** |
| `easyocr ru` | over budget (>300s) | over budget (>300s) | over budget (>300s) | over budget (>300s) | over budget (>300s) | over budget (>300s) | over budget (>300s) | over budget (>300s) | **0/8** |
| `docling` | over budget (>300s) | PASS cyr 0.92 · hit 0.58 · w 3980 | PASS cyr 0.91 · hit 0.56 · w 1580 | over budget (>300s) | over budget (>300s) | PASS cyr 0.79 · hit 0.55 · w 1629 | over budget (>300s) | unavailable | **3/8** |
| `marker` | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | **0/8** |
| `unstructured` | PASS cyr 0.87 · hit 0.51 · w 10084 | PASS cyr 0.92 · hit 0.56 · w 4246 | PASS cyr 0.91 · hit 0.56 · w 1585 | PASS cyr 0.06 · hit 0.59 · w 7882 | PASS cyr 0.74 · hit 0.54 · w 7901 | PASS cyr 0.80 · hit 0.55 · w 1691 | PASS cyr 0.92 · hit 0.55 · w 57323 | PASS cyr 0.90 · hit 0.55 · w 46242 | **8/8** |

Per-document cost over the same eight samples (`n` = cells that produced text; `unavailable` and `error` cells cost nothing):

| Candidate | scored | total | median | slowest |
|---|---|---|---|---|
| `pdftotext` | 8 | 17.3 s | 0.9 s | 6.5 s |
| `pdftotext -layout` | 8 | 9.4 s | 0.5 s | 3.5 s |
| `pymupdf-text` | 8 | 10.2 s | 0.6 s | 5.6 s |
| `pymupdf-blocks` | 8 | 17.7 s | 0.4 s | 13.8 s |
| `pdfminer.six` | 8 | 92.2 s | 6.5 s | 43.9 s |
| `pypdf` | 8 | 34.7 s | 2.8 s | 18.2 s |
| `pdfplumber` | 8 | 164.5 s | 12.0 s | 68.3 s |
| `marker` | 0 | — | — | — (unavailable) |
| `ocrmypdf+tesseract rus` | 8 | 195.1 s | 24.4 s | 38.5 s |
| `tesseract rus (render)` | 8 | 222.6 s | 25.3 s | 46.3 s |
| `docling` | 3 | 202.0 s | 75.5 s | 80.5 s |
| `unstructured` | 8 | 245.4 s | 26.4 s | 62.9 s |
| `easyocr ru` | 0 | — | — | — (timeout) |

## Threshold calibration

`SANITY_THRESHOLDS`, pinned in
[config.py](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/config.py)
and defined in
[extract.py](https://github.com/gasyoun/RuWritingStyles/blob/main/src/ruwritingstyles/extract.py):

| Threshold | Value | What set it |
|---|---|---|
| `min_cyrillic_ratio` | 0.55 | Real Russian galleys measured 0.74–0.93. The only readings below 0.55 were 0.06 (an English article — a language verdict, not a failure) and 0.00 (total failure). Nothing observed fell between 0.06 and 0.74, so this is a wide gap, not a knife edge. |
| `max_replacement_ratio` | 0.03 | Clean extractions of the two hardest corpus PDFs still carried 0.6–2.0 % replacement/control characters — residual glyph gaps in the embedded fonts. At the initial 0.01 this axis alone failed text that was 93 % Cyrillic with a 0.55 hit rate: a false negative. Raised to 0.03 so it catches only catastrophic decoding. |
| `min_word_hit_rate` | 0.20 | Real text measured 0.43–0.62 under both the Russian and English heuristics; mojibake measured 0.00. Set well below the observed floor so a terse or heavily terminological article is not discarded. |
| `min_words` | 200 | Below a couple of hundred words the article body did not come out, whatever the ratios say — a title page alone can score perfectly. |

Loosening `max_replacement_ratio` does **not** let mojibake through, because garbling
is caught by the other two axes: `pdftotext` on these files scores 0.018 there and is
still rejected at 0.00 Cyrillic with a 0.00 hit rate.

## The two known-garbled PDFs — explicit verdict

**They are recoverable. The `.ai_state.md` claim that no quotable grounding text
exists for either was true of `pdftotext` only, not of the PDFs.**

| PDF | `pdftotext` | `pymupdf-text` | `pdfminer.six` |
|---|---|---|---|
| `Digital_Humanities-2023.pdf` | fail — cyr 0.00, 5 737 tokens of blanked text | **pass** — cyr 0.92, hit 0.55, 57 272 tokens | **pass** — cyr 0.92, hit 0.55, 57 363 tokens |
| `Digital-Humanities_IgorPilshchikov.pdf` | fail — cyr 0.00, 2 884 tokens | **pass** — cyr 0.93, hit 0.55, 43 696 tokens | **pass** — cyr 0.90, hit 0.55, 46 242 tokens |

The font-encoding problem is real, but it is poppler's. PyMuPDF and pdfminer.six read
the same embedded encodings correctly and return clean Russian.

**What this does and does not unblock.** It removes the *extraction* half of the
corpus-gated H1882 row: quotable Russian text for both volumes now exists on demand.
It does **not** by itself unblock the passports, because the other half of that
row still stands — both files are multi-author collective volumes, not a single
scholar's voice, so there is still no single-author passport to build from them. The
`.ai_state.md` row has been corrected to say exactly that.

## Findings that bind wave 1

Three measurements from this pass constrain
[H3154](https://github.com/gasyoun/Uprava/blob/main/handoffs/H3154-Opus_RuWritingStyles_rcsi-journal-harvester-wave1_19.08.26.md);
each is also a row in
[docs/rcsi-harvest-decisions.log.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/rcsi-harvest-decisions.log.md).

### The prescribed harvester User-Agent is blocked

S1.1 specifies
`RuWritingStyles/<version> (research harvester; sanskrit.research.institute@gmail.com)`.
That string is **403'd site-wide** by the RCSI edge. A common browser UA is served
200 on the same URLs in the same second — measured on both
`/{slug}/oai?verb=Identify` and `/{slug}/article/view/{id}`. It is not an endpoint
problem and not a rate limit; the platform-facts table in the plan (which records OAI
`Identify` returning 200) was established with a different client.

Wave 1 must either send a browser-shaped UA or contact the platform for an allowance;
a polite self-identifying UA as specified will fetch nothing at all. The 1 req/s
throttle is unaffected and was honoured throughout this pass.

### Not every RCSI article is Russian

Acta Linguistica Petropolitana 21.1 is entirely in English (Angela Ralli, on verb
borrowing in Modern Greek). Extraction succeeds perfectly and the Russian-expectation
gate still says `fail` at `cyrillic_ratio` 0.06 — which, read naively, says "no
extractor could handle this PDF".

`sanity(text, expect_cyrillic=False)` scores against an English heuristic instead.
Deciding *which* language to expect is article classification, not extraction, so it
is a caller's parameter rather than an auto-detect: it belongs to
`journal_scope.classify_article` (S1.4). **If the harvester applies the gate blind, it
will discard every English article on the platform as garbled.**

### `pdftotext` is not a fallback for this corpus — and it contaminates OCR too

Not merely worse — it returns zero Cyrillic on all seven Russian samples. Any code
path, script, or future skill that reaches for poppler on RCSI material is broken by
construction.

This has a trap in it that cost a wrong row in the first draft of this matrix. The
`ocrmypdf` candidate re-images each page, OCRs it with `tesseract rus`, and writes a
**new** text layer — and the obvious way to read that layer back is `pdftotext`. Doing
so scored 0.00 Cyrillic on every Russian sample and made OCR look useless. It was
measuring poppler a second time, not tesseract: the direct `tesseract rus (render)`
candidate, which never touches poppler, scored 8/8 all along. Reading the OCR output
with PyMuPDF instead moves `ocrmypdf+tesseract rus` from **1/8 to 8/8**.

The rule that falls out: on this material, poppler must not appear anywhere in a
pipeline — not as the extractor, and not as the reader at the end of somebody else's
extractor.

## What this does not establish

- **Reading order was not measured.** `pymupdf-text` and `pymupdf-blocks` produced
  identical sanity metrics on all eight samples, so the gate cannot separate them;
  blocks costs ~75 % more time. Plain `text` is pinned on that basis. If two-column
  galleys later turn out to interleave badly for quote extraction, that is a
  reading-order question this benchmark did not ask.
- **Six galleys is a small sample.** One article per journal establishes that the
  chain works on each platform template, not that it works on every article.
- **The OCR rung works, but was never *needed*.** `ocrmypdf+tesseract rus` scored 8/8,
  so the escalation is known to function; but no sample required it — every Russian
  sample was already rescued by a text-layer reader. It is pinned for a scanned PDF
  with no text layer, a case this sample set does not contain. Note also that OCR
  recovers far fewer tokens under the 6-page cap (~2 000 vs ~10 000), so a `pass`
  there means "the encoding is sound", not "the whole article was captured".
- **`marker` was never measured**, only recorded unavailable (D19).
- **The heavyweight ML engines were judged on cost, not quality.** `docling` (3/8) and
  `easyocr` (0/8) failed on the budget, not on accuracy — where `easyocr` did finish it
  returned good Russian (cyr 0.84, hit 0.50) and `docling` passed three samples
  cleanly. The verdict against them is "too slow for a 300-article harvest on this
  hardware", which is a claim about this machine and this budget, not about the
  engines. `unstructured` scored 8/8 and is excluded only because it is not a project
  dependency and does not beat PyMuPDF (D19).

_Dr. Mārcis Gasūns_
