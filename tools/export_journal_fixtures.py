"""Generate golden journal-compliance fixtures for the Obsidian plugin.

Runs the engine's report.journal_compliance() over a fixed set of (document,
profile) cases and writes input + expected JSON under
obsidian-plugin/test/fixtures/journal/. The plugin's journal.test.ts runs the
TypeScript port over the same inputs and asserts equality, so the port can never
silently drift from the engine.

Usage:
    python tools/export_journal_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ruwritingstyles.report import journal_compliance  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIX = ROOT / "obsidian-plugin" / "test" / "fixtures" / "journal"


def _profile(pid: str) -> dict:
    return json.loads((ROOT / "knowledge" / "journals" / f"{pid}.json").read_text(encoding="utf-8"))


# Each case: a real or synthetic document + a journal profile (by knowledge id
# or inline). The TS test resolves the same profile and compares.
CASES = [
    # The real acceptance case: the gúṇa article vs Вестник СПбГУ.
    {"name": "guna-vestnik", "profile_id": "vestnik-spbu",
     "input_path": ROOT / "examples" / "input" / "lexicography-guna.md"},
    # Russian abstract + keywords present, English absent (the real submission gap).
    {"name": "ru-only", "profile_id": "vestnik-spbu",
     "text": "# Заголовок\n\n**Аннотация.** Текст.\n\n**Ключевые слова:** гуна, словарь.\n\nТекст статьи.\n"},
    # Both languages present — fully compliant on abstract/keywords.
    {"name": "both-present", "profile_id": "vestnik-spbu",
     "text": "# T\n\n**Аннотация.** Текст.\n\n## Abstract\n\nText.\n\n**Ключевые слова:** а.\n\n**Keywords:** b.\n"},
    # Over the length limit (tiny inline profile so the fixture stays small).
    {"name": "over-length",
     "profile": {"id": "tiny", "name": "Tiny", "max_chars": 50,
                 "abstract_required": [], "keywords_required": []},
     "text": "# Заголовок\n\n" + "слово " * 40},
    # Abstract word limit — body of 7 words against a max of 5 (over by 2).
    {"name": "abstract-over-words",
     "profile": {"id": "tiny-abs", "name": "Tiny Abs", "abstract_required": ["ru"],
                 "abstract_max_words": 5, "keywords_required": []},
     "text": "# T\n\n**Аннотация.** один два три четыре пять шесть семь.\n\nТекст.\n"},
]


def _camel(comp: dict) -> dict:
    """Rename to the TS JournalCompliance shape (camelCase keys)."""
    return {
        "name": comp["name"],
        "length": comp["length"],
        "citationFormat": comp["citation_format"],
        "transliterationScheme": comp["transliteration_scheme"],
        "abstract": comp["abstract"],
        "keywords": comp["keywords"],
    }


def main() -> int:
    FIX.mkdir(parents=True, exist_ok=True)
    manifest = []
    for case in CASES:
        if "input_path" in case:
            text = case["input_path"].read_text(encoding="utf-8")
        else:
            text = case["text"]
        profile = case.get("profile") or _profile(case["profile_id"])
        comp = journal_compliance(text, profile)

        # Write input (LF) + expected; the TS port normalizes \r\n, so EOLs are moot.
        (FIX / f"{case['name']}.input.md").write_text(text, encoding="utf-8", newline="\n")
        (FIX / f"{case['name']}.expected.json").write_text(
            json.dumps(_camel(comp), ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
        )
        entry = {"name": case["name"]}
        if "profile_id" in case:
            entry["profile_id"] = case["profile_id"]
        else:
            entry["profile"] = case["profile"]
        manifest.append(entry)
        print(f"  {case['name']}: {comp['length']} abstract={comp['abstract']} keywords={comp['keywords']}")

    (FIX / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Wrote {len(manifest)} journal fixtures to {FIX.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
