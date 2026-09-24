import json, glob, sys
sys.stdout.reconfigure(encoding="utf-8")
for p in glob.glob("../RuWritingStyles-corpus/quarantine/*.json"):
    d = json.load(open(p, encoding="utf-8"))
    sc = d.get("sidecar", {})
    if sc.get("journal_slug") != "0373-658X":
        continue
    print("title:", sc.get("title_en") or sc.get("title_ru"))
    print("language:", repr(sc.get("language")), "expect flip?")
    print(json.dumps(d.get("attempts", []), ensure_ascii=False, indent=1)[:2500])
    break
