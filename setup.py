"""Setuptools build hook for the allowlisted RuWritingStyles runtime assets."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


ROOT = Path(__file__).resolve().parent
RUNTIME_PATHS = (
    "ClaudeStyles",
    "styles",
    "schemas",
    "knowledge",
    "evals",
    "examples",
    "model_policy.yml",
    "web/dist",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class RuntimeBuildPy(build_py):
    def run(self) -> None:
        super().run()
        destination_root = Path(self.build_lib) / "ruwritingstyles" / "_runtime"
        if destination_root.exists():
            shutil.rmtree(destination_root)
        destination_root.mkdir(parents=True)

        manifest: dict[str, str] = {}
        for relative in RUNTIME_PATHS:
            source = ROOT / relative
            if not source.exists():
                raise FileNotFoundError(f"required runtime asset missing during build: {source}")
            sources = [source] if source.is_file() else sorted(p for p in source.rglob("*") if p.is_file())
            for source_file in sources:
                rel = source_file.relative_to(ROOT)
                destination = destination_root / rel
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, destination)
                source_hash = _sha256(source_file)
                if _sha256(destination) != source_hash:
                    raise OSError(f"runtime asset checksum mismatch: {rel.as_posix()}")
                manifest[rel.as_posix()] = source_hash

        manifest_path = destination_root / "runtime-assets.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        self._runtime_outputs = [
            str(path) for path in destination_root.rglob("*") if path.is_file()
        ]

    def get_outputs(self, include_bytecode: bool = True):
        return super().get_outputs(include_bytecode) + getattr(self, "_runtime_outputs", [])


setup(cmdclass={"build_py": RuntimeBuildPy})
