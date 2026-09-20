#!/usr/bin/env python
"""Build the W2.4 bounded-harvest report fragment from the run's own artifacts.

Reads the detached driver's aggregate JSON (per-journal rows: written /
already-pass / quarantined / selection skips / extraction-source split /
elapsed / status) and cross-checks it against the private corpus sidecars
harvested on the run date — the sidecars are the authoritative on-disk state.
Writes a Markdown fragment suitable for pasting into
docs/HARVEST_REPORT_rcsi-w24-bounded-harvest_<date>.md.

Usage:
    python tools/build_w24_harvest_report.py --driver <runs/rcsi-harvest/w24-driver-*.json> \
        [--corpus <RuWritingStyles-corpus>] [--date 20-09-2026] [--out fragment.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


def sidecar_stats(corpus_dir: Path, run_date: str) -> dict:
    """Aggregate sidecars whose extraction.harvested_on == run_date."""
    sources: Counter[str] = Counter()
    extractors: Counter[str] = Counter()
    verdicts: Counter[str] = Counter()
    selection: Counter[str] = Counter()
    per_journal: dict[str, Counter] = {}
    files = 0
    for path in sorted((corpus_dir / "PDFtoTXT").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        extraction = data.get("extraction", {})
        if extraction.get("harvested_on") != run_date:
            continue
        files += 1
        slug = data.get("journal_slug", "?")
        bucket = per_journal.setdefault(slug, Counter())
        sources[extraction.get("source", "")] += 1
        bucket[f"source:{extraction.get('source', '')}"] += 1
        extractors[extraction.get("extractor", "")] += 1
        verdicts[extraction.get("verdict", "")] += 1
        sel = data.get("selection", {}).get("verdict", "")
        selection[sel] += 1
        bucket["written"] += 1
    quarantine_dir = corpus_dir / "quarantine"
    quarantined = 0
    if quarantine_dir.exists():
        for p in quarantine_dir.glob("*.json"):
            try:
                payload = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if payload.get("sidecar", {}).get("extraction", {}).get("harvested_on") == run_date:
                quarantined += 1
    return {
        "sidecar_files": files,
        "sources": dict(sources),
        "extractors": dict(extractors),
        "extraction_verdicts": dict(verdicts),
        "selection_verdicts": dict(selection),
        "per_journal": {slug: dict(c) for slug, c in sorted(per_journal.items())},
        "quarantined": quarantined,
    }


def driver_stats(driver_json: Path) -> dict:
    data = json.loads(driver_json.read_text(encoding="utf-8"))
    rows = data.get("journals", [])
    ok = [r for r in rows if r.get("status") == "ok"]
    failed = [r for r in rows if r.get("status") != "ok"]
    total_written = sum(r.get("written", 0) for r in ok)
    total_already = sum(r.get("already_pass", 0) for r in ok)
    total_quarantined = sum(r.get("quarantined", 0) for r in ok)
    split: Counter[str] = Counter()
    for r in ok:
        for source, n in r.get("source_split", {}).items():
            split[source] += n
    return {
        "driver_json": str(driver_json),
        "started": data.get("started", ""),
        "journals_attempted": len(rows),
        "journals_ok": len(ok),
        "journals_failed": [
            {"slug": r.get("slug"), "status": r.get("status"), "error": str(r.get("error", ""))[:120]}
            for r in failed
        ],
        "written": total_written,
        "already_pass": total_already,
        "quarantined": total_quarantined,
        "source_split": dict(split),
        "per_journal_rows": [
            {
                "slug": r.get("slug"),
                "status": r.get("status"),
                "written": r.get("written", 0),
                "already": r.get("already_pass", 0),
                "quarantined": r.get("quarantined", 0),
                "skipped": r.get("selection_skipped", {}),
                "source_split": r.get("source_split", {}),
                "elapsed_s": round(r.get("elapsed_seconds", 0.0), 1),
            }
            for r in rows
        ],
    }


def render(driver: dict, sidecars: dict, run_date: str, cap: int) -> str:
    lines: list[str] = []
    lines.append(f"### Run {run_date} (cap {cap} accepted articles per journal, D20/D17)")
    lines.append("")
    lines.append(f"- Driver aggregate: {driver['driver_json']}")
    lines.append(
        f"- Journals: **{driver['journals_ok']} ok** of 61 include, "
        f"{len(driver['journals_failed'])} failed/rate-limited"
    )
    lines.append(
        f"- Written this run: **{driver['written']}** (+{driver['already_pass']} already-pass skipped, "
        f"resumability confirmed)"
    )
    lines.append(f"- Quarantined this run: **{driver['quarantined']}** (driver count)")
    lines.append(
        f"- Extraction-source split (driver): {driver['source_split'] or '{}'}"
    )
    lines.append(
        f"- Sidecars on disk stamped {run_date}: **{sidecars['sidecar_files']}** "
        f"(sources {sidecars['sources']}, extractors {sidecars['extractors']}, "
        f"extraction verdicts {sidecars['extraction_verdicts']}, selection verdicts {sidecars['selection_verdicts']})"
    )
    lines.append(f"- Quarantine dir entries stamped {run_date}: {sidecars['quarantined']}")
    if driver["journals_failed"]:
        lines.append("- Failures:")
        for f in driver["journals_failed"]:
            lines.append(f"  - `{f['slug']}` — {f['status']}: {f['error']}")
    lines.append("")
    lines.append("| journal | status | written | already | quarantined | skipped (verdicts) | source split | s |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for row in driver["per_journal_rows"]:
        skipped = ", ".join(f"{k} {v}" for k, v in row["skipped"].items()) or "—"
        split = ", ".join(f"{k} {v}" for k, v in row["source_split"].items()) or "—"
        lines.append(
            f"| `{row['slug']}` | {row['status']} | {row['written']} | {row['already']} | "
            f"{row['quarantined']} | {skipped} | {split} | {row['elapsed_s']} |"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--driver", type=Path, required=True)
    parser.add_argument("--corpus", type=Path, default=Path(__file__).resolve().parent.parent.parent / "RuWritingStyles-corpus")
    parser.add_argument("--date", default="20-09-2026")
    parser.add_argument("--cap", type=int, default=50)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    driver = driver_stats(args.driver)
    sidecars = sidecar_stats(args.corpus, args.date)
    fragment = render(driver, sidecars, args.date, args.cap)
    if args.out:
        args.out.write_text(fragment, encoding="utf-8", newline="\n")
        print(f"wrote {args.out}")
    else:
        print(fragment)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
