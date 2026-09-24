import json, glob, sys
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")
rows = []
for p in glob.glob("../RuWritingStyles-corpus/quarantine/*.json"):
    d = json.load(open(p, encoding="utf-8"))
    sc = d.get("sidecar", {})
    notes = "; ".join(f"{a.get('source')}:{a.get('extractor')}/{str(a.get('note',''))[:40]}" for a in d.get("attempts", []))
    rows.append((sc.get("journal_slug"), sc.get("language", "?"), sc.get("title_ru", "")[:40], notes[:110]))
print("total quarantined:", len(rows))
c = Counter(r[0] for r in rows)
print("by slug:", dict(c))
for r in rows[:12]:
    print(r)
