#!/usr/bin/env python3
"""Classify a disk-inventory TSV into the six Sanskritology voices.

`tools/disk_inventory.py` writes the catalogue (source/path/size_bytes/mtime/name/ext/depth);
this tool reads it back and answers the questions the catalogue deliberately does NOT
answer (see that module's docstring): which of the six benchmark voices a path belongs
to, its genre, its language, and which PDFs carry no evidence of a text layer.

The classification is **name-and-path evidence only** — the Drive catalogue has no
metadata beyond a filename, and nothing here downloads a file. Every row is therefore
`matched` / `unmatched`, never `absent`: a voice with zero matched files means "no file
named for him in this catalogue", not "Drive holds none of him".

Usage:

    python tools/classify_corpus_inventory.py \\
        ../RuWritingStyles-corpus/inventory/gdrive_shared.tsv \\
        ../RuWritingStyles-corpus/inventory/gdrive_my.tsv \\
        --out ../RuWritingStyles-corpus/inventory/classify_report.md \\
        --json ../RuWritingStyles-corpus/inventory/classify_report.json

Exit codes: 0 report written · 2 no input rows.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

# --- voices ---------------------------------------------------------------------
# Surname patterns are matched case-insensitively against the whole path. Cyrillic
# `\b` is Unicode-aware in Python 3, so `\bсмирнов\b` does not fire on `Смирнова`.
# `exclude` exists because the estate really does hold a *different* Смирнова
# (folder `Смирнова Т. Allegro`) beside Б. Л. Смирнов's Mahābhārata volumes.
VOICES = {
    "elizarenkova": {
        "label": "Элизаренкова",
        "include": [r"елизаренков", r"elizarenkov"],
        "exclude": [],
    },
    "toporov": {
        "label": "Топоров",
        "include": [r"топоров", r"toporov"],
        "exclude": [],
    },
    "smirnov": {
        "label": "Смирнов Б. Л.",
        "include": [r"\bсмирнов\b", r"\bsmirnov\b"],
        "exclude": [r"\bсмирнова\b", r"\bsmirnova\b"],
    },
    "lidova": {
        "label": "Лидова",
        "include": [r"лидова", r"lidova"],
        "exclude": [],
    },
    "paribok": {
        "label": "Парибок",
        "include": [r"парибок", r"paribok"],
        "exclude": [],
    },
    "leitan": {
        "label": "Лейтан",
        "include": [r"лейтан", r"leitan"],
        "exclude": [],
    },
}

# --- genre ----------------------------------------------------------------------
# Ordered: the first rule that fires wins, so the narrow markers precede broad ones.
GENRE_RULES = [
    # A transcript of a spoken session is not authored prose — it must not be
    # counted as an article just because the author's name is in the filename.
    ("транскрипт-запись", [r"медленное чтение", r"транскрипт", r"вебинар", r"лекция", r"запись", r"созвон"]),
    ("предисловие-рецензия", [r"предислов", r"вступ", r"от редактор", r"реценз", r"review", r"foreword", r"предисл", r"комментар"]),
    ("монография-перевод", [r"собрание сочинений", r"\bпсс\b", r"монограф", r"перевод", r"translation", r"том\b", r"книг\w*", r"book"]),
    ("статья", [r"статья", r"статьи", r"article", r"доклад", r"тезис", r"conference", r"вестник", r"\bвя\b", r"journal"]),
]

OCR_MARKER = re.compile(r"ocr", re.IGNORECASE)
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
LATIN = re.compile(r"[A-Za-z]")
PSS_PATTERN = re.compile(
    r"собрани\w* сочин|полное собрани|\bпсс\b|opera omnia|gesammelte", re.IGNORECASE
)


def load_rows(paths: list[Path]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            for row in reader:
                if not row.get("path"):
                    continue
                row["_tsv"] = path.name
                rows.append(row)
    return rows


def voice_of(path: str) -> tuple[str, str]:
    lowered = path.lower()
    for key, spec in VOICES.items():
        if any(re.search(pat, lowered) for pat in spec["exclude"]):
            # An exclusion only blocks *this* voice's match, never the whole row.
            continue
        if any(re.search(pat, lowered) for pat in spec["include"]):
            return key, "matched"
    return "", "unmatched"


def genre_of(path: str) -> str:
    lowered = path.lower()
    for name, patterns in GENRE_RULES:
        if any(re.search(pat, lowered) for pat in patterns):
            return name
    return "не размечено"


def language_of(name: str) -> str:
    has_cyr, has_lat = bool(CYRILLIC.search(name)), bool(LATIN.search(name))
    if has_cyr and has_lat:
        return "ru+mixed"
    if has_cyr:
        return "ru"
    if has_lat:
        return "en"
    return "unknown"


def gb(size: str) -> float:
    # rclone reports -1 for native Google Docs/Sheets (no byte size); counting
    # that as a negative gigabyte would quietly shrink every total it touches.
    try:
        value = int(size)
    except (TypeError, ValueError):
        return 0.0
    return max(value, 0) / 1e9


def build_report(rows: list[dict[str, str]], exclude: list[re.Pattern] | None = None) -> dict:
    exclude = exclude or []
    per_source: Counter[str] = Counter()
    bytes_per_source: defaultdict[str, int] = defaultdict(int)
    ext_counts: Counter[str] = Counter()
    roots: defaultdict[str, list] = defaultdict(lambda: [0, 0])
    per_voice: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    textlayer_pending: list[dict[str, str]] = []
    pss: list[dict[str, str]] = []
    excluded_files = 0
    excluded_bytes = 0

    for row in rows:
        src = row.get("source", "")
        path = row.get("path", "")
        name = row.get("name", "")
        ext = (row.get("ext") or "").lower()
        try:
            size = max(int(row.get("size_bytes") or 0), 0)
        except ValueError:
            size = 0

        per_source[src] += 1
        bytes_per_source[src] += size
        ext_counts[ext] += 1
        root = path.split("/", 1)[0]
        roots[root][0] += 1
        roots[root][1] += size

        # Backups carry copies of repo handoffs and notes; classifying those
        # matches surnames in filenames that never name a corpus text.
        if any(pattern.search(path) for pattern in exclude):
            excluded_files += 1
            excluded_bytes += size
            continue

        key, _ = voice_of(path)
        if key:
            per_voice[key].append(row)
        if ext == "pdf" and not OCR_MARKER.search(name):
            textlayer_pending.append(row)
        if PSS_PATTERN.search(path) or (key == "toporov" and re.search(r"том|vol|\bт\.?\s*\d", path.lower())):
            pss.append(row)

    voices: dict[str, dict] = {}
    for key, spec in VOICES.items():
        hits = per_voice.get(key, [])
        lang = Counter(language_of(h["name"]) for h in hits)
        genre = Counter(genre_of(h["path"]) for h in hits)
        grouped: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
        for h in hits:
            grouped[h["path"].rsplit("/", 1)[0] if "/" in h["path"] else h["path"]].append(h)
        groups = [
            {
                "folder": folder,
                "files": len(items),
                "gb": round(sum(gb(i.get("size_bytes", "0")) for i in items), 3),
                "sample": f"{items[0]['source']}:{items[0]['path']}",
            }
            for folder, items in sorted(grouped.items(), key=lambda kv: -len(kv[1]))
        ]
        voices[key] = {
            "label": spec["label"],
            "files": len(hits),
            "gb": round(sum(gb(h.get("size_bytes", "0")) for h in hits), 3),
            "language": dict(lang),
            "genre": dict(genre),
            "exts": dict(Counter((h.get("ext") or "").lower() for h in hits)),
            "groups": groups,
            "paths": [f"{h['source']}:{h['path']}" for h in hits],
        }

    return {
        "rows": len(rows),
        "excluded": {"files": excluded_files, "gb": round(excluded_bytes / 1e9, 3)},
        "roots": [
            {"root": root, "files": n, "gb": round(size / 1e9, 3)}
            for root, (n, size) in sorted(roots.items(), key=lambda kv: -kv[1][1])[:40]
        ],
        "sources": {
            src: {"files": n, "gb": round(bytes_per_source[src] / 1e9, 3)}
            for src, n in per_source.items()
        },
        "extensions": dict(ext_counts),
        "voices": voices,
        "textlayer_unconfirmed_pdfs": len(textlayer_pending),
        "textlayer_unconfirmed_sample": [
            f"{h['source']}:{h['path']}" for h in textlayer_pending[:40]
        ],
        "pss_candidates": [f"{h['source']}:{h['path']}" for h in pss[:40]],
    }


def render_markdown(report: dict) -> str:
    out: list[str] = []
    total_files = report["rows"]
    total_gb = round(sum(s["gb"] for s in report["sources"].values()), 3)
    out.append(f"Всего: **{total_files:,} файлов**, **{total_gb} ГБ**.".replace(",", " "))
    out.append("")
    out.append("| Источник | Файлов | ГБ |")
    out.append("|---|---|---|")
    for src, stats in report["sources"].items():
        out.append(f"| `{src}` | {stats['files']:,} | {stats['gb']} |".replace(",", " "))
    out.append("")
    out.append("## Крупнейшие корневые папки")
    out.append("")
    out.append("| Корень | Файлов | ГБ |")
    out.append("|---|---|---|")
    for root in report["roots"]:
        out.append(f"| `{root['root']}` | {root['files']:,} | {root['gb']} |".replace(",", " "))
    out.append("")
    excluded = report["excluded"]
    if excluded["files"]:
        out.append(
            f"Из классификации исключено **{excluded['files']:,} файл(ов), {excluded['gb']} ГБ** "
            "(шаблоны `--exclude`: резервные копии ноутбуков, где фамилии встречаются "
            "в именах чужих файлов)."
        )
        out.append("")
    out.append("## Шесть голосов (совпадение по имени файла/папки)")
    out.append("")
    out.append("| Голос | Файлов | ГБ | Язык | Жанр | Расширения |")
    out.append("|---|---|---|---|---|---|")
    for key, spec in VOICES.items():
        v = report["voices"][key]
        lang = ", ".join(f"{k}:{n}" for k, n in sorted(v["language"].items())) or "—"
        genre = ", ".join(f"{k}:{n}" for k, n in sorted(v["genre"].items())) or "—"
        exts = ", ".join(f"{k or '∅'}:{n}" for k, n in sorted(v["exts"].items())) or "—"
        out.append(f"| {spec['label']} | {v['files']} | {v['gb']} | {lang} | {genre} | {exts} |")
    out.append("")
    out.append("### Совпадения по голосам (папки и пути)")
    for key, spec in VOICES.items():
        v = report["voices"][key]
        out.append("")
        out.append(f"**{spec['label']}** — {v['files']} файл(ов), {v['gb']} ГБ")
        if not v["groups"]:
            out.append("- (совпадений нет)")
        for group in v["groups"]:
            out.append(f"- `{group['folder']}` — {group['files']} файл(ов), {group['gb']} ГБ")
        out.append("")
        out.append("<details><summary>все пути</summary>")
        out.append("")
        for p in v["paths"]:
            out.append(f"- `{p}`")
        out.append("")
        out.append("</details>")
    out.append("")
    out.append("## PDF без подтверждённого текстового слоя")
    out.append("")
    out.append(
        f"{report['textlayer_unconfirmed_pdfs']} шт. — текстовый слой не подтверждён: "
        "в имени нет OCR-маркера и слой не проверялся извлечением."
    )
    for p in report["textlayer_unconfirmed_sample"]:
        out.append(f"- `{p}`")
    out.append("")
    out.append("## Кандидаты ПСС Топорова")
    out.append("")
    if not report["pss_candidates"]:
        out.append("- (совпадений нет)")
    for p in report["pss_candidates"]:
        out.append(f"- `{p}`")
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Classify a disk inventory into the six voices.")
    parser.add_argument("tsv", nargs="+", type=Path, help="inventory TSV(s) from tools/disk_inventory.py")
    parser.add_argument("--out", type=Path, help="Markdown report path")
    parser.add_argument("--json", dest="json_out", type=Path, help="JSON report path")
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="REGEX",
        help="skip paths matching this regex before voice matching (repeatable); "
        "e.g. '^backup-' to keep laptop backups out of the six-voice table",
    )
    args = parser.parse_args(argv)

    rows = load_rows(args.tsv)
    if not rows:
        print("no rows", file=sys.stderr)
        return 2
    exclude = [re.compile(pattern, re.IGNORECASE) for pattern in args.exclude]
    report = build_report(rows, exclude)
    markdown = render_markdown(report)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(markdown, encoding="utf-8")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
