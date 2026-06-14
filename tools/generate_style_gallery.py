"""Generate docs/STYLE_GALLERY.ru.md — a catalogue of every style with a
clickable GitHub link to its `.md` (the shareable Claude Custom Style content).

Regenerable: run after adding/renaming styles. There is no API to mint claude.ai
Custom-Style share URLs, so the shareable artifact is the prompt file itself —
a colleague opens the link, copies the prompt, and pastes it into Claude →
Settings → Custom styles.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ruwritingstyles.config import load_manifest, load_passport_dicts  # noqa: E402

BLOB = "https://github.com/gasyoun/RuWritingStyles/blob/main/"
RAW = "https://raw.githubusercontent.com/gasyoun/RuWritingStyles/main/"
OUT = ROOT / "docs" / "STYLE_GALLERY.ru.md"


def _clean(title: str) -> str:
    # Strip the generic "Пользовательский стиль для Claude: «Стиль X»" boilerplate.
    title = re.sub(r"^Пользовательский стиль для Claude:\s*", "", title)
    title = re.sub(r"^Стиль\s+", "", title)
    return title.strip().strip("«»\"' ").removeprefix("Стиль ").strip() or title


def _h1(md_path: Path) -> str:
    if not md_path.exists():
        return md_path.stem
    for line in md_path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^#\s+(.+?)\s*$", line)
        if m:
            return _clean(m.group(1).strip())
    return md_path.stem


def main() -> int:
    manifest = load_manifest(ROOT)
    cluster_name = {c.id: c.name for c in manifest.clusters}
    name_by_id = {d["id"]: d["name"] for d in load_passport_dicts(ROOT) if d.get("name")}

    individual: dict[str, list[tuple[str, str, str]]] = {}
    schools: list[tuple[str, str, str]] = []
    for ref in manifest.passports:
        rel = ref.source_prompt.relative_to(ROOT).as_posix()
        # Prefer the passport's clean name; fall back to the (cleaned) .md heading.
        title = name_by_id.get(ref.style_id) or _h1(ref.source_prompt)
        row = (ref.style_id, title, rel)
        if "styles/clusters/" in ref.path.relative_to(ROOT).as_posix():
            schools.append(row)
        else:
            individual.setdefault(ref.cluster_id or "—", []).append(row)

    lines = [
        "# Галерея стилей — ссылки для Custom Style",
        "",
        "Каждый стиль — это `.md`-инструкция, которую можно использовать как",
        "**Claude Custom Style**. Откройте ссылку, скопируйте весь файл и вставьте его в",
        "Claude → **Settings → Custom styles → Create custom style**. Либо временно дайте",
        "Claude содержимое файла в начале диалога и попросите писать по этому профилю.",
        "",
        "> Прямой текст для копирования — кнопка **Raw** на странице файла на GitHub",
        f"> (или `{RAW}<путь>`).",
        "",
        f"Всего стилей: **{sum(len(v) for v in individual.values()) + len(schools)}**. "
        "Регенерируется: `python tools/generate_style_gallery.py`.",
        "",
    ]

    def emit(rows: list[tuple[str, str, str]]) -> None:
        for style_id, title, rel in sorted(rows, key=lambda r: r[0]):
            lines.append(f"- [{title}]({BLOB}{rel}) — `{style_id}`")
        lines.append("")

    lines.append("## Отдельные стили (по школам/кластерам)")
    lines.append("")
    for cid in sorted(individual):
        lines.append(f"### {cluster_name.get(cid, cid)}")
        lines.append("")
        emit(individual[cid])

    if schools:
        lines.append("## Школы целиком (кластерные стили)")
        lines.append("")
        lines.append("Сводные паспорта школ — применяют метод школы, а не одного автора.")
        lines.append("")
        emit(schools)

    OUT.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"Wrote {OUT.relative_to(ROOT).as_posix()} "
          f"({sum(len(v) for v in individual.values()) + len(schools)} styles)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
