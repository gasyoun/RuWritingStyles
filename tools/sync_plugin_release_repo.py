"""Materialize the dedicated Obsidian-plugin release repo from this monorepo.

Official community submission and BRAT expect a *dedicated* repo with
`manifest.json` at its **root** and releases tagged with the **bare** version
(`0.1.0`, no `obsidian-v` prefix), one plugin per repo — which a monorepo
subdirectory cannot provide (see obsidian-plugin/RELEASE.md).

This script copies the built plugin + its metadata from `obsidian-plugin/` into
a target directory (a clone of the dedicated repo, e.g. `gasyoun/ruwritingstyles-obsidian`)
laid out at the target's root. The monorepo stays the dev source of truth; the
dedicated repo is a publish mirror synced on release.

Usage:
    # 1. build the plugin so main.js is current
    cd obsidian-plugin && npm ci && npm run build && cd ..
    # 2. sync into a clone of the dedicated repo
    python tools/sync_plugin_release_repo.py ../ruwritingstyles-obsidian
    # 3. in the dedicated repo: commit, tag BARE `x.y.z`, push
    #    (its own release workflow attaches main.js/manifest.json/styles.css)

Pass --check to verify main.js exists and versions are aligned without copying.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "obsidian-plugin"
TEMPLATE = PLUGIN / "release-repo"

# Root-level files the dedicated repo needs, copied verbatim from the built plugin.
ROOT_FILES = ["manifest.json", "versions.json", "styles.css", "main.js"]
# Files copied from the release-repo template (dedicated-repo-specific docs/config).
TEMPLATE_FILES = ["README.md", ".gitignore", "LICENSE"]


def _versions_aligned() -> tuple[bool, str]:
    manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))
    package = json.loads((PLUGIN / "package.json").read_text(encoding="utf-8"))
    versions = json.loads((PLUGIN / "versions.json").read_text(encoding="utf-8"))
    mv, pv = manifest["version"], package["version"]
    ok = mv == pv and mv in versions
    return ok, f"manifest={mv} package={pv} versions_keys={list(versions)}"


def _check() -> int:
    problems = []
    if not (PLUGIN / "main.js").exists():
        problems.append("obsidian-plugin/main.js missing — run `npm run build` first")
    ok, detail = _versions_aligned()
    if not ok:
        problems.append(f"version mismatch: {detail}")
    if problems:
        for p in problems:
            print(f"FAIL: {p}")
        return 1
    print(f"OK: build present, versions aligned ({detail})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("target", nargs="?", help="path to the dedicated repo clone")
    ap.add_argument("--check", action="store_true", help="verify only, do not copy")
    args = ap.parse_args()

    rc = _check()
    if args.check or rc != 0:
        return rc
    if not args.target:
        print("No target given; --check passed. Pass a target dir to sync.")
        return 0

    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    print(f"Syncing plugin -> {target}")

    for name in ROOT_FILES:
        (target / name).write_bytes((PLUGIN / name).read_bytes())
        print(f"  obsidian-plugin/{name} -> {name}")

    # Ship source + tests too, so the dedicated repo can rebuild main.js and run
    # the same parity tests in its own CI/release workflow.
    for sub in ("src", "test", "esbuild.config.mjs", "tsconfig.json", "package.json", "package-lock.json"):
        src = PLUGIN / sub
        dst = target / sub
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("assets_cache"))
        else:
            dst.write_bytes(src.read_bytes())
        print(f"  obsidian-plugin/{sub} -> {sub}")

    for name in TEMPLATE_FILES:
        src = TEMPLATE / name
        if src.exists():
            (target / name).write_bytes(src.read_bytes())
            print(f"  obsidian-plugin/release-repo/{name} -> {name}")

    # Dedicated-repo CI/release workflow (bare-tag release).
    tmpl_gh = TEMPLATE / ".github"
    if tmpl_gh.is_dir():
        dst_gh = target / ".github"
        if dst_gh.exists():
            shutil.rmtree(dst_gh)
        shutil.copytree(tmpl_gh, dst_gh)
        print("  obsidian-plugin/release-repo/.github -> .github")

    print("Done. In the dedicated repo: commit, then `git tag 0.1.0 && git push --tags`.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
