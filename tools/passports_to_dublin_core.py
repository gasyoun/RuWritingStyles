"""Export style passports to Dublin Core (DCMI) metadata (roadmap Phase 4).

Each passport is a machine-readable model of one philologist's prose method.
This emits the field -> Dublin Core element mapping the roadmap calls for, as a
single archival XML file (`metadata/dublin-core.xml`) with one simple-DC record
per passport, using the unqualified DCMI element set
(http://purl.org/dc/elements/1.1/). Re-runnable; regenerate after editing
passports. Run: `python tools/passports_to_dublin_core.py`.

Mapping (passport field -> DC element):
  id                       -> dc:identifier
  name                     -> dc:title  (+ dc:subject: the modelled scholar)
  role + best_for          -> dc:description
  best_for + checks + cluster -> dc:subject (one element each)
  language                 -> dc:language
  source_prompt + provenance.sources -> dc:source
  cluster / extends        -> dc:relation
  provenance.derivation_date -> dc:date
  provenance.derived_by    -> dc:contributor
  (constant)               -> dc:creator, dc:publisher, dc:type, dc:format, dc:rights
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ruwritingstyles.config import load_passport_dicts  # noqa: E402

DC_NS = "http://purl.org/dc/elements/1.1/"
CREATOR = "RuWritingStyles project (M. Yu. Gasuns)"
PUBLISHER = "RuWritingStyles"
RIGHTS = "Apache-2.0"
DC_TYPE = "Text"
DC_FORMAT = "text/markdown"
OUT = ROOT / "metadata" / "dublin-core.xml"


def _el(tag: str, value: str) -> str:
    return f"    <dc:{tag}>{escape(str(value))}</dc:{tag}>"


def _record(passport: dict) -> str:
    lines: list[str] = [f'  <record id="{escape(str(passport.get("id", "")))}">']

    if passport.get("id"):
        lines.append(_el("identifier", passport["id"]))
    if passport.get("name"):
        lines.append(_el("title", passport["name"]))
        # The modelled scholar is the subject of the style, not its creator.
        lines.append(_el("subject", passport["name"]))

    lines.append(_el("creator", CREATOR))
    lines.append(_el("publisher", PUBLISHER))

    best_for = [b for b in (passport.get("best_for") or []) if isinstance(b, str)]
    role = passport.get("role")
    description_bits = ([role] if role else []) + best_for
    if description_bits:
        lines.append(_el("description", "; ".join(description_bits)))

    for subject in best_for + [c for c in (passport.get("checks") or []) if isinstance(c, str)]:
        lines.append(_el("subject", subject))
    if passport.get("cluster"):
        lines.append(_el("subject", passport["cluster"]))

    lines.append(_el("type", DC_TYPE))
    lines.append(_el("format", DC_FORMAT))
    if passport.get("language"):
        lines.append(_el("language", passport["language"]))

    if passport.get("source_prompt"):
        lines.append(_el("source", passport["source_prompt"]))
    provenance = passport.get("provenance") or {}
    for src in (provenance.get("sources") or []):
        if isinstance(src, str):
            lines.append(_el("source", src))
    if provenance.get("derived_by"):
        lines.append(_el("contributor", provenance["derived_by"]))
    if provenance.get("derivation_date"):
        lines.append(_el("date", provenance["derivation_date"]))

    if passport.get("cluster"):
        lines.append(_el("relation", f"cluster:{passport['cluster']}"))
    if passport.get("extends"):
        lines.append(_el("relation", passport["extends"]))

    lines.append(_el("rights", RIGHTS))
    lines.append("  </record>")
    return "\n".join(lines)


def main() -> int:
    records = [_record(data) for data in load_passport_dicts(ROOT)]

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<records xmlns:dc="{DC_NS}">\n'
        + "\n".join(records)
        + "\n</records>\n"
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(xml, encoding="utf-8")
    print(f"Wrote {len(records)} Dublin Core records -> {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
