import json, glob, sys
sys.stdout.reconfigure(encoding="utf-8")
for p in sorted(glob.glob("../RuWritingStyles-corpus/quarantine/*.json")):
    d = json.load(open(p, encoding="utf-8"))
    sc = d.get("sidecar", {})
    print(p.split("\\")[-1] if "\\" in p else p.split("/")[-1],
          "|", sc.get("journal_slug"), "|", sc.get("title_ru", "")[:50])
    for a in d.get("attempts", []):
        print("   ", a.get("source"), a.get("extractor"), str(a.get("note", ""))[:80])
