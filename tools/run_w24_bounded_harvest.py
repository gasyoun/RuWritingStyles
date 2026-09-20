"""W2.4 bounded harvest driver — every `include` journal, ~50 articles each (D20).

Iterates the `include` slugs of knowledge/rcsi/catalogue.json and runs
harvest.harvest_journal(slug, limit=<remaining>, selection="include") in ONE
process, so the rcsi client's 1 req/s throttle paces the whole run. Resumable:
a journal whose corpus sidecars already hold >= CAP pass-verdict texts is
counted as done and skipped, and `limit` is always CAP minus existing passes,
so a restart never overshoots the D20 bound.

Stop conditions (PLAN autonomy contract 2): RcsiRateLimited, or three
consecutive journals failing with a non-rate-limit error. A single failed
journal is recorded and the run continues.

Outputs:
  runs/rcsi-harvest/w24-driver-<stamp>.json       aggregate summary
  knowledge/rcsi/article_review_queue.json        uncertain/exclude article
                                                  metadata for the W2.3-class
                                                  review sheet (no corpus text)
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ruwritingstyles import rcsi  # noqa: E402
from ruwritingstyles.harvest import harvest_journal  # noqa: E402

CAP = 50  # D20: about 50 articles per in-scope journal
QUEUE_PATH = ROOT / "knowledge" / "rcsi" / "article_review_queue.json"


def include_slugs() -> list[str]:
    catalogue = json.loads((ROOT / "knowledge" / "rcsi" / "catalogue.json").read_text(encoding="utf-8"))
    records = catalogue if isinstance(catalogue, list) else catalogue.get("journals", catalogue)
    return [str(r["slug"]) for r in records if r.get("verdict") == "include"]


def existing_pass_count(corpus_dir: Path, slug: str) -> int:
    """Pass-verdict sidecars already in the corpus for this journal."""
    count = 0
    for sidecar_path in corpus_dir.glob("*.json"):
        try:
            data = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("journal_slug") == slug and data.get("extraction", {}).get("verdict") == "pass":
            count += 1
    return count


def main() -> int:
    from ruwritingstyles.harvest import _corpus_dir

    corpus_dir, _quarantine = _corpus_dir()
    slugs = include_slugs()
    print(f"W2.4 bounded harvest: {len(slugs)} include journals, cap {CAP} each", flush=True)

    aggregate: dict[str, Any] = {"started": datetime.now().isoformat(), "journals": []}
    review_queue: list[dict[str, Any]] = []
    consecutive_failures = 0

    for index, slug in enumerate(slugs, 1):
        existing = existing_pass_count(corpus_dir, slug)
        remaining = CAP - existing
        if remaining <= 0:
            print(f"[{index}/{len(slugs)}] {slug}: already at cap ({existing}) — skipped", flush=True)
            aggregate["journals"].append({"slug": slug, "status": "at-cap", "existing": existing})
            consecutive_failures = 0
            continue
        started = time.monotonic()
        try:
            summary = harvest_journal(slug, limit=remaining, selection="include")
        except rcsi.RcsiRateLimited as exc:
            print(f"[{index}/{len(slugs)}] {slug}: RATE LIMITED ({exc}) — stopping run", flush=True)
            aggregate["journals"].append({"slug": slug, "status": "rate-limited", "error": str(exc)})
            break
        except Exception as exc:  # a single bad journal is not a stop condition
            consecutive_failures += 1
            print(f"[{index}/{len(slugs)}] {slug}: FAILED ({exc})", flush=True)
            aggregate["journals"].append({"slug": slug, "status": "failed", "error": str(exc)})
            if consecutive_failures >= 3:
                print("three consecutive journal failures — stopping run", flush=True)
                break
            continue
        consecutive_failures = 0
        elapsed = time.monotonic() - started

        # Extraction-source split from the sidecars this journal wrote/skipped.
        source_split: dict[str, int] = {}
        for entry in summary["written"]:
            sidecar_path = corpus_dir / f"{entry['stem']}.json"
            try:
                sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            source = sidecar.get("extraction", {}).get("source", "unknown")
            source_split[source] = source_split.get(source, 0) + 1
        verdicts = {}
        for skipped in summary["selection_skipped"]:
            verdicts[skipped["verdict"]] = verdicts.get(skipped["verdict"], 0) + 1
            skipped = dict(skipped, journal_slug=slug)
            review_queue.append(skipped)

        row = {
            "slug": slug,
            "status": "ok",
            "written": len(summary["written"]),
            "already_pass": len(summary["skipped"]),
            "quarantined": len(summary["quarantined"]),
            "selection_skipped": verdicts,
            "source_split": source_split,
            "existing_before": existing,
            "elapsed_seconds": round(elapsed, 1),
        }
        aggregate["journals"].append(row)
        print(
            f"[{index}/{len(slugs)}] {slug}: +{row['written']} written, "
            f"{row['already_pass']} already, {row['quarantined']} quarantined, "
            f"skipped {verdicts} in {elapsed:.0f}s", flush=True,
        )

        # Persist progress every journal so a crash loses nothing.
        aggregate["finished_so_far"] = datetime.now().isoformat()
        _write_outputs(aggregate, review_queue)

    aggregate["finished"] = datetime.now().isoformat()
    _write_outputs(aggregate, review_queue)
    print("driver finished", flush=True)
    return 0


def _write_outputs(aggregate: dict[str, Any], review_queue: list[dict[str, Any]]) -> None:
    runs_dir = ROOT / "runs" / "rcsi-harvest"
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = aggregate["started"].replace(":", "").replace("-", "")[:15]
    (runs_dir / f"w24-driver-{stamp}.json").write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    QUEUE_PATH.write_text(
        json.dumps(
            {"generated_on": aggregate.get("finished_so_far") or aggregate["started"], "articles": review_queue},
            ensure_ascii=False, indent=2,
        ) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    sys.exit(main())
