"""Generate golden parity fixtures for the Obsidian plugin's TS linter.

Runs the engine's `translit_lint.lint_text` over a set of inputs and writes, for
each, `<name>.expected.json` next to a co-located `<name>.md`, plus a
`manifest.json`. The plugin's test/parity.test.ts runs the TypeScript port over
the same `.md` and asserts identical findings — so the two implementations can
never silently diverge.

Real engine inputs (examples/input/*) are copied into the fixtures dir so the
plugin test tree is self-contained. Hand-authored edge cases already live there.

Usage:
    python tools/export_lint_fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ruwritingstyles.translit_lint import lint_text, load_sanskrit_terms  # noqa: E402

FIXTURES = ROOT / "obsidian-plugin" / "test" / "fixtures"

# (name, source .md relative to ROOT, profile dict | None)
# Real engine inputs are copied in; hand-authored cases already live in FIXTURES.
CASES: list[tuple[str, str, dict | None]] = [
    # Real linter-targeted eval inputs (default profile).
    ("translit-cyrillic-latin-hybrid", "examples/input/translit-cyrillic-latin-hybrid.md", None),
    ("translit-first-mention", "examples/input/translit-first-mention.md", None),
    ("translit-inconsistent-rendering", "examples/input/translit-inconsistent-rendering.md", None),
    ("translit-mixed-scheme", "examples/input/translit-mixed-scheme.md", None),
    ("sanskrit-pseudo-etymology", "examples/input/sanskrit-pseudo-etymology.md", None),
    ("karaka-not-padezh", "examples/input/karaka-not-padezh.md", None),
    ("samasa-misclassification", "examples/input/samasa-misclassification.md", None),
    ("vedic-classical-anachronism", "examples/input/vedic-classical-anachronism.md", None),
    ("commentary-layer-mix", "examples/input/commentary-layer-mix.md", None),
    # Hand-authored edge cases (already in FIXTURES).
    ("clean", "obsidian-plugin/test/fixtures/clean.md", None),
    ("code-skip", "obsidian-plugin/test/fixtures/code-skip.md", None),
    ("hybrid-word", "obsidian-plugin/test/fixtures/hybrid-word.md", None),
    ("devanagari-orphan", "obsidian-plugin/test/fixtures/devanagari-orphan.md", None),
    # Profile knob: first_mention_rule that does NOT require IAST suppresses the
    # first-mention finding (the only meaningful linter-facing profile field).
    ("first-mention-suppressed", "obsidian-plugin/test/fixtures/first-mention-suppressed.md",
     {"first_mention_rule": "none"}),
]


def main() -> int:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    terms = load_sanskrit_terms(ROOT)
    manifest = []
    for name, rel_src, profile in CASES:
        src = ROOT / rel_src
        if not src.exists():
            print(f"FAIL: missing source {rel_src}")
            return 1
        text = src.read_text(encoding="utf-8")
        # Self-contained tree: copy real inputs in (hand-authored already here).
        dst_md = FIXTURES / f"{name}.md"
        if src.resolve() != dst_md.resolve():
            dst_md.write_text(text, encoding="utf-8")
        result = lint_text(text, terms, profile)
        (FIXTURES / f"{name}.expected.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        manifest.append({"name": name, "profile": profile})
        print(f"  {name}: {len(result['findings'])} finding(s)")
    (FIXTURES / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Wrote {len(manifest)} fixtures to {FIXTURES.relative_to(ROOT).as_posix()}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
