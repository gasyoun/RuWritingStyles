#!/usr/bin/env python3
"""Verify and compare runtime-asset manifests in wheels and sdists."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
import zipfile
from pathlib import Path


sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

RUNTIME_PREFIXES = (
    "ClaudeStyles/", "styles/", "schemas/", "knowledge/", "evals/",
    "examples/", "web/dist/",
)
RUNTIME_FILES = {"model_policy.yml"}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def wheel_manifest(path: Path) -> dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        manifest_name = next(
            (name for name in archive.namelist() if name.endswith("/_runtime/runtime-assets.json")),
            None,
        )
        if not manifest_name:
            raise ValueError(f"{path}: missing runtime-assets.json")
        prefix = manifest_name.removesuffix("runtime-assets.json")
        manifest = json.loads(archive.read(manifest_name))
        for rel, expected in manifest.items():
            actual = _sha(archive.read(prefix + rel))
            if actual != expected:
                raise ValueError(f"{path}: checksum mismatch for {rel}")
        return manifest


def sdist_manifest(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    with tarfile.open(path, "r:gz") as archive:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            parts = member.name.split("/", 1)
            if len(parts) != 2:
                continue
            rel = parts[1]
            if rel in RUNTIME_FILES or rel.startswith(RUNTIME_PREFIXES):
                handle = archive.extractfile(member)
                if handle is None:
                    raise ValueError(f"{path}: could not read {rel}")
                result[rel] = _sha(handle.read())
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    manifests = []
    for archive in args.archives:
        manifest = wheel_manifest(archive) if archive.suffix == ".whl" else sdist_manifest(archive)
        if not manifest:
            raise ValueError(f"{archive}: empty runtime asset manifest")
        manifests.append((archive, manifest))
        print(f"{archive}: {len(manifest)} runtime assets verified")
    reference_path, reference = manifests[0]
    for path, manifest in manifests[1:]:
        if manifest != reference:
            missing = sorted(set(reference) - set(manifest))
            extra = sorted(set(manifest) - set(reference))
            changed = sorted(k for k in set(reference) & set(manifest) if reference[k] != manifest[k])
            raise ValueError(
                f"runtime manifests differ: {reference_path} vs {path}; "
                f"missing={missing[:5]} extra={extra[:5]} changed={changed[:5]}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
