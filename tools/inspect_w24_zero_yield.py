"""Forensic: why did some W2.4 journals enumerate 300 records but yield nothing?

Reads the rcsi disk cache (no network): reconstructs the first ListRecords
URL for a slug, loads the cached page, counts <record> entries and how many
carry header status="deleted".
"""

from __future__ import annotations

import hashlib
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://journals.rcsi.science"
OAI = "{http://www.openarchives.org/OAI/2.0/}"
CACHE = Path(os.environ.get("TEMP", "/tmp")) / "opencode" / "rcsi-cache"


def first_page(slug: str) -> str:
    url = f"{BASE}/{slug}/oai?verb=ListRecords&metadataPrefix=oai_dc"
    key = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
    return (CACHE / f"{key}.txt").read_text(encoding="utf-8", errors="replace")


def main(slugs: list[str]) -> int:
    for slug in slugs:
        try:
            text = first_page(slug)
        except OSError:
            print(f"{slug}: first OAI page NOT in cache")
            continue
        try:
            root = ET.fromstring(
                __import__("re").sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
            )
        except ET.ParseError as exc:
            print(f"{slug}: cached page not XML ({exc})")
            continue
        records = root.findall(f".//{OAI}record")
        deleted = sum(
            1
            for r in records
            if (h := r.find(f"{OAI}header")) is not None and h.get("status") == "deleted"
        )
        token = root.find(f".//{OAI}resumptionToken")
        token_text = (token.text or "").strip() if token is not None else ""
        err = root.find(f"{OAI}error")
        err_text = f" error=[{err.get('code')}] " if err is not None else ""
        print(
            f"{slug}: records={len(records)} deleted={deleted} "
            f"resumptionToken={'yes' if token_text else 'no'}{err_text}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
