#!/usr/bin/env python3
"""Measure NKRYa keyness for corpus-grounded style passports (H5283).

For each passport: lemmatize its source text (RuWritingStyles-corpus/PDFtoTXT),
take the top-N content lemmas by in-text frequency, fetch their NKRYa ipm
(cached in metadata/nkrya_cache/, throttled to ~6 requests/min), write a JSON
report to metadata/nkrya_keyness/<passport>.json and upsert the generated
«Лексическая подпись (НКРЯ)» section into ClaudeStyles/<passport>-style.md.

  python scripts/nkrya_keyness.py --passports zalizniak-enklitiki          # live fetch of misses
  python scripts/nkrya_keyness.py --all --offline                          # re-render from cache only

Needs the `nkrya` extra (pymorphy3). Offline mode needs no token and no client.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from ruwritingstyles.nkrya_evidence import (  # noqa: E402
    DEFAULT_CACHE_REL, NkryaEvidence, count_content_lemmas, keyness_rows, render_section, upsert_section,
)

BLOB = "https://github.com/gasyoun/RuWritingStyles/blob/main/"
# passport id -> (source text in RuWritingStyles-corpus/PDFtoTXT, human label)
SOURCES = {
    "zalizniak-imennoe": ("zalizniak_russkoe_imennoe_slovoizmenenie_2002_text.txt",
                          "А. А. Зализняк, «Русское именное словоизменение» (2002)"),
    "zalizniak-novgorod": ("zaliznyak_drevnenovgorodsky_dialekt_2004.txt",
                           "А. А. Зализняк, «Древненовгородский диалект» (2004)"),
    "zalizniak-enklitiki": ("2008_Zalizniak_Enklitiki.txt",
                            "А. А. Зализняк, «Древнерусские энклитики» (2008)"),
    "zalizniak-udarenie": ("zaliznyak_drevnerusskoe_udarenie_2019__izd.txt",
                           "А. А. Зализняк, «Древнерусское ударение» (2019)"),
    "bartold": ("1927_Bartold_Kirgizy-istoricheskij-ocherk.txt",
                "В. В. Бартольд, «Киргизы. Исторический очерк» (1927)"),
    "turaev": ("1920_Turaev_Egipetskaya-literatura.txt", "Б. А. Тураев, «Египетская литература» (1920)"),
    "krachkovskij": ("1925_Krachkovskij_Neizvestnoe-sochinenie-avtograf-sirijskogo-emira-Usamy.txt",
                     "И. Ю. Крачковский, «Неизвестное сочинение-автограф сирийского эмира Усамы» (1925)"),
    "golenishchev": ("1880_Golenishchev_Ob-ekzemplyare-Knigi-mertvyh.txt",
                     "В. С. Голенищев, «Об экземпляре Книги мёртвых» (1880; дореформенная орфография "
                     "приведена к современной)"),
}
ZALIZNYAK = [p for p in SOURCES if p.startswith("zalizniak-")]


def anchor_heading(md: str) -> str | None:
    """Insert after the «Лексика» section (Zaliznyak passports), else before «Примеры фраз»."""
    heads = [m.group(0) for m in re.finditer(r"^## .*$", md, flags=re.M)]
    for i, h in enumerate(heads):
        if h.lower().startswith("## лексика") and i + 1 < len(heads):
            return heads[i + 1]
    return next((h for h in heads if h.lower().startswith("## примеры фраз")), None)


def run(passport: str, corpus_dir: Path, evidence: NkryaEvidence, top_n: int, measured: str) -> dict:
    fname, label = SOURCES[passport]
    text = (corpus_dir / fname).read_text(encoding="utf-8", errors="replace")
    counts = count_content_lemmas(text)
    evidence.used_keys.clear()
    rows = keyness_rows(counts, evidence, top_n)
    report_rel = f"metadata/nkrya_keyness/{passport}.json"
    report = {
        "passport": passport, "handoff": "H5283", "measured": measured,
        "source_file": f"RuWritingStyles-corpus/PDFtoTXT/{fname}", "source_label": label,
        "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "lemmatizer": "pymorphy3", "tokens": counts.tokens, "top_n": top_n,
        "keyness": "log2(text ipm / NKRYa ipm); NKRYa ipm floor 0.01 when no portrait",
        "reference": "NKRYa word portrait PORTRAIT_FREQUENCY, main corpus",
        "cache_keys": sorted(set(evidence.used_keys)),
        "rows": rows, "report_rel": report_rel, "report_url": BLOB + report_rel,
    }
    out = REPO / report_rel
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    md_path = REPO / "ClaudeStyles" / f"{passport}-style.md"
    md = md_path.read_text(encoding="utf-8")
    md_path.write_text(upsert_section(md, render_section(report), anchor_heading(md)), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sel = ap.add_mutually_exclusive_group(required=True)
    sel.add_argument("--passports", nargs="+", choices=sorted(SOURCES))
    sel.add_argument("--zaliznyak", action="store_true", help="the four Zaliznyak passports")
    sel.add_argument("--all", action="store_true")
    ap.add_argument("--corpus-dir", type=Path, default=REPO.parent / "RuWritingStyles-corpus" / "PDFtoTXT")
    ap.add_argument("--top-n", type=int, default=30)
    ap.add_argument("--offline", action="store_true", help="cache only; fail on a miss")
    ap.add_argument("--measured", default=dt.date.today().strftime("%d-%m-%Y"))
    a = ap.parse_args(argv)
    passports = ZALIZNYAK if a.zaliznyak else sorted(SOURCES) if a.all else a.passports
    if not a.corpus_dir.is_dir():  # a worktree's sibling is the main checkout's sibling too
        alt = REPO.parent.parent / "RuWritingStyles-corpus" / "PDFtoTXT"
        a.corpus_dir = alt if alt.is_dir() else a.corpus_dir
    evidence = NkryaEvidence(REPO / DEFAULT_CACHE_REL, offline=a.offline, repo_root=REPO)
    for p in passports:
        r = run(p, a.corpus_dir, evidence, a.top_n, a.measured)
        top = ", ".join(f"{x['lemma']} {x['log_ratio']:+.1f}" for x in r["rows"][:5])
        print(f"{p}: {r['tokens']} tokens, {len(r['rows'])} lemmas, {len(r['cache_keys'])} cache entries; top: {top}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
