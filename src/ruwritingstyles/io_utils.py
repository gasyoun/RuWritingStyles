"""Durable filesystem helpers for run and workspace artifacts."""

from __future__ import annotations

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any


def atomic_write_text(path: Path, text: str, *, encoding: str = "utf-8") -> Path:
    """Replace *path* atomically with text written in the same directory."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with NamedTemporaryFile(
            "w",
            encoding=encoding,
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
        return path
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def atomic_write_json(path: Path, value: Any) -> Path:
    return atomic_write_text(
        path,
        json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
    )
