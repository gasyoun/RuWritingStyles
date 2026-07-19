"""Installed runtime assets and explicit editable workspace management."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from importlib.resources import files
from pathlib import Path
from typing import Any, Iterable

from .io_utils import atomic_write_json


WORKSPACE_MARKER = ".rws-workspace.json"
MANAGED_PATHS = (
    "ClaudeStyles",
    "styles",
    "schemas",
    "knowledge",
    "evals",
    "examples",
    "model_policy.yml",
)


def packaged_runtime_root() -> Path:
    candidate = Path(str(files("ruwritingstyles").joinpath("_runtime")))
    if candidate.exists():
        return candidate.resolve()
    # Editable/source checkout fallback; build products never write here.
    source_root = Path(__file__).resolve().parents[2]
    if all((source_root / item).exists() for item in ("ClaudeStyles", "styles", "model_policy.yml")):
        return source_root
    raise FileNotFoundError("installed RuWritingStyles runtime assets are missing")


def bundled_web_dist() -> Path:
    runtime = packaged_runtime_root()
    candidate = runtime / "web" / "dist"
    if candidate.exists():
        return candidate
    raise FileNotFoundError("bundled Web Studio is missing; rebuild the package after `npm run build`")


def find_workspace(start: Path | None = None) -> Path:
    configured = os.environ.get("RWS_WORKSPACE")
    if configured:
        target = Path(configured).expanduser().resolve()
        if not (target / WORKSPACE_MARKER).exists() and not _legacy_checkout(target):
            raise FileNotFoundError(
                f"RWS_WORKSPACE does not contain {WORKSPACE_MARKER}: {target}; run `rws init {target}`"
            )
        return target

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / WORKSPACE_MARKER).exists():
            return candidate
    for candidate in (current, *current.parents):
        if _legacy_checkout(candidate):
            return candidate
    raise FileNotFoundError(
        "could not find a RuWritingStyles workspace; run `rws init` or set RWS_WORKSPACE"
    )


def init_workspace(target: Path, *, upgrade: bool = False) -> dict[str, Any]:
    target = target.expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    marker_path = target / WORKSPACE_MARKER
    vendor_root = packaged_runtime_root()
    vendor_files = _managed_files(vendor_root)

    if marker_path.exists() and not upgrade:
        raise FileExistsError(f"workspace already initialized: {target}")
    if not marker_path.exists() and upgrade:
        raise FileNotFoundError(f"cannot upgrade uninitialized workspace: {target}")

    old_files: dict[str, str] = {}
    if marker_path.exists():
        try:
            old_marker = json.loads(marker_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"malformed workspace marker {marker_path}: {exc}") from exc
        value = old_marker.get("managed_files", {})
        if not isinstance(value, dict):
            raise ValueError(f"malformed workspace marker {marker_path}: managed_files must be an object")
        old_files = {str(k): str(v) for k, v in value.items()}

    if not marker_path.exists():
        collisions = [rel for rel in vendor_files if (target / rel).exists()]
        if collisions:
            preview = ", ".join(collisions[:5])
            raise FileExistsError(f"managed workspace paths already exist: {preview}")

    installed: list[str] = []
    conflicts: list[str] = []
    for rel, vendor_hash in vendor_files.items():
        source = vendor_root / rel
        destination = target / rel
        previous_hash = old_files.get(rel)
        safe_to_replace = (
            not destination.exists()
            or (previous_hash is not None and _sha256(destination) == previous_hash)
        )
        if safe_to_replace:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            if _sha256(destination) != vendor_hash:
                raise OSError(f"checksum verification failed while installing {rel}")
            installed.append(rel)
        elif upgrade:
            vendor_copy = target / ".rws-new" / rel
            vendor_copy.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, vendor_copy)
            conflicts.append(rel)

    from . import __version__

    marker = {
        "format": 1,
        "vendor_version": __version__,
        "managed_paths": list(MANAGED_PATHS),
        "managed_files": vendor_files,
    }
    atomic_write_json(marker_path, marker)
    return {
        "path": str(target),
        "installed": installed,
        "conflicts": conflicts,
        "marker": str(marker_path),
    }


def runtime_asset_manifest(root: Path | None = None) -> dict[str, str]:
    return _managed_files(root or packaged_runtime_root(), include_web=True)


def _managed_files(root: Path, *, include_web: bool = False) -> dict[str, str]:
    names: Iterable[str] = MANAGED_PATHS + (("web/dist",) if include_web else ())
    result: dict[str, str] = {}
    for name in names:
        path = root / name
        if path.is_file():
            result[path.relative_to(root).as_posix()] = _sha256(path)
        elif path.is_dir():
            for child in sorted(item for item in path.rglob("*") if item.is_file()):
                result[child.relative_to(root).as_posix()] = _sha256(child)
        else:
            raise FileNotFoundError(f"required runtime asset is missing: {path}")
    return result


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _legacy_checkout(path: Path) -> bool:
    return (path / "README.md").exists() and (path / "ClaudeStyles").is_dir()
