"""Sync the Obsidian plugin's bundled data assets from the engine's knowledge/.

The plugin ships byte-for-byte copies of the term dictionary and the journal
profiles so its TypeScript linter uses the *same* data as the Python engine.
`knowledge/` is the single source of truth; this script copies, never edits.
`tools/validate_project.py` fails if the copies drift (run this to fix).

Usage:
    python tools/export_plugin_assets.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE = ROOT / "knowledge"
ASSETS = ROOT / "obsidian-plugin" / "src" / "assets"


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())  # copy verbatim; drift check compares EOL-normalized
    print(f"  {src.relative_to(ROOT).as_posix()} -> {dst.relative_to(ROOT).as_posix()}")


def main() -> int:
    if not ASSETS.parent.parent.exists():
        print("FAIL: obsidian-plugin/ not found")
        return 1
    print("Syncing plugin assets from knowledge/ ...")
    _copy(KNOWLEDGE / "sanskrit-terms.json", ASSETS / "sanskrit-terms.json")
    for preset in sorted((KNOWLEDGE / "journals").glob("*.json")):
        _copy(preset, ASSETS / "journals" / preset.name)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
