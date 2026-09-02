"""One-shot backfill of provenance.validated_by/last_validated across all style
passports — roadmap-sanskrit-dh.md Ф2 "Провенанс в паспортах" (H3780 triage).

Two honest tiers:
  - The four H944 corpus-grounded orientalist passports (Bartold, Turaev,
    Krachkovskij, Golenishchev) get the real content-fidelity claim: quote-
    anchored against a primary text from the private corpus intake.
  - Every other passport gets the mechanical claim that is actually true today:
    validate_project.py's bibliography cross-reference check passes for it.

Run once; not wired into CI. Idempotent (skips a file that already has
validated_by).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PASSPORTS_DIR = ROOT / "styles" / "passports"

H944_CORPUS_GROUNDED = {
    "bartold.yml": "H944 corpus-grounding intake (H3369, OxAlpha opencode/z-ai/glm-5.3-flash) — quote-anchored against the primary text",
    "turaev.yml": "H944 corpus-grounding intake (H3369, OxAlpha opencode/z-ai/glm-5.3-flash) — quote-anchored against the primary text",
    "krachkovskij.yml": "H944 corpus-grounding intake (H3369 addendum, OxAlpha opencode/z-ai/glm-5.3-flash) — quote-anchored against the primary text",
    "golenishchev.yml": "H944 corpus-grounding intake (H3369, OxAlpha opencode/z-ai/glm-5.3-flash) — quote-anchored against the primary text",
}
H944_DATE = "2026-08-29"

MECHANICAL_VALIDATOR = "RuWritingStyles CI — validate_project.py bibliography cross-reference check"
MECHANICAL_DATE = "2026-09-02"


def patch_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if "validated_by:" in text:
        return False

    lines = text.splitlines()
    out: list[str] = []
    in_provenance = False
    inserted = False
    for line in lines:
        out.append(line)
        if line.rstrip() == "provenance:":
            in_provenance = True
            continue
        if in_provenance and line.startswith("  derivation_date:"):
            name = path.name
            if name in H944_CORPUS_GROUNDED:
                validated_by = H944_CORPUS_GROUNDED[name]
                date = H944_DATE
            else:
                validated_by = MECHANICAL_VALIDATOR
                date = MECHANICAL_DATE
            out.append(f'  validated_by: "{validated_by}"')
            out.append(f'  last_validated: "{date}"')
            inserted = True
            in_provenance = False

    if not inserted:
        raise ValueError(f"{path}: no provenance.derivation_date line found to anchor the insert")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return True


def main() -> int:
    changed = 0
    for path in sorted(PASSPORTS_DIR.glob("*.yml")):
        if patch_file(path):
            changed += 1
            print(f"patched {path.relative_to(ROOT)}")
    print(f"{changed} passport(s) patched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
