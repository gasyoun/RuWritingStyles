# CORPUS_GDRIVE_INVENTORY_2026-10-17.meta.md — metadoc

_Created: 17-10-2026 · Last updated: 17-10-2026_

This is a **metadoc** — a document *about* a document. Its subject is
[CORPUS_GDRIVE_INVENTORY_2026-10-17.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/CORPUS_GDRIVE_INVENTORY_2026-10-17.md).

## Subject

- **Document:** the report of the full Google Drive inventory taken for the Sanskritology
  style benchmark (H6927).
- **Purpose:** to answer three questions the grill left open — where the corpus actually
  lives on Drive, which of the six voices have material there, and whether Toporov's
  collected works exist on Drive — with numbers that a later session can re-derive.
- **Audience:** the session that runs wave 1 of the benchmark, and whoever has to rule on
  the ПСС question; secondarily anyone about to crawl Drive again.
- **Format / contract:** a set of tables (totals, corpus zone, six voices, genres, PDF text
  layer) plus explicit limits. Every number is reproducible from two committed `.tsv.gz`
  catalogues by `tools/classify_corpus_inventory.py`; the doc must not gain a number that
  the tool cannot re-derive.

## What surrounds it

- **Data (private, not here):** `RuWritingStyles-corpus/inventory/` —
  `gdrive_shared.tsv.gz` (25 961 rows), `gdrive_my.tsv.gz` (471 468 rows),
  `classify_report.md`/`.json`, plus a README with the resume commands. The catalogue is
  **not** committed to this public repository (ruling 20); only the report is.
- **Tool:** [`tools/classify_corpus_inventory.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/classify_corpus_inventory.py)
  (name-and-path classification, `--exclude` for backups, `distinct_pairs` beside the row
  count) and [`tools/disk_inventory.py`](https://github.com/gasyoun/RuWritingStyles/blob/main/tools/disk_inventory.py)
  (the checkpointed crawl).
- **Decisions:** [GRILL_SANSKRITOLOGY_STYLE_BENCHMARK_2026-10-17.md](https://github.com/gasyoun/RuWritingStyles/blob/main/docs/GRILL_SANSKRITOLOGY_STYLE_BENCHMARK_2026-10-17.md)
  — rulings 3 (six voices), 20 (result in RWS docs, data in the private corpus), 21 (Toporov
  by collected works, Lidova `thin`), 22 (books are never bought).
- **Gotchas:** [FINDINGS.md](https://github.com/gasyoun/RuWritingStyles/blob/main/FINDINGS.md) §7.

## What it deliberately does not claim

- It is **not** a claim that a voice is absent from Drive — only that no file is *named*
  for them (translations are titled by work, not translator).
- It does **not** verify a single text layer; the OCR marker in a filename is the only hint
  recorded, and 803 of 804 zone PDFs have none.
- It does **not** settle the ПСС question: it records that the series is not on Drive and
  names the closest equivalent, leaving the substitution to the author.

_Dr. Mārcis Gasūns_
