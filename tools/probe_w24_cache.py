"""One-off probe: how many records does a journal's cached OAI first page carry,
and does it have a resumptionToken? Reads cache only — no server requests."""
from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://journals.rcsi.science"
cache = Path(os.environ["TEMP"]) / "opencode" / "rcsi-cache"

for slug in sys.argv[1:]:
    url = f"{BASE}/{slug}/oai?verb=ListRecords&metadataPrefix=oai_dc"
    key = hashlib.sha1(url.encode()).hexdigest()[:16]
    path = cache / f"{key}.txt"
    if not path.exists():
        print(f"{slug}: first page not cached")
        continue
    raw = path.read_text(encoding="utf-8", errors="replace")
    records = len(re.findall(r"<record>", raw))
    # crude resumptionToken extraction
    tokens = re.findall(r"<resumptionToken[^>]*>([^<]+)</resitemapToken>|<resumptionToken[^>]*>([^<]+)</resumptionToken>", raw)
    token = (tokens[0][0] or tokens[0][1]) if tokens else None
    print(f"{slug}: {records} records on first page, resumptionToken={'yes: ' + token[:40] if token else 'no'}")

print("total cache entries:", len(list(cache.glob('*'))))
