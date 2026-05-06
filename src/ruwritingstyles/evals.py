"""Evaluation manifest helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    """One evaluation case from evals/manifest.json."""

    case_id: str
    input_path: Path
    purpose: str
    default_styles: tuple[str, ...]
    expected_risks: tuple[str, ...]


def load_eval_cases(repo_root: Path) -> tuple[EvalCase, ...]:
    manifest_path = repo_root / "evals" / "manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    cases = data.get("cases") if isinstance(data.get("cases"), list) else []
    return tuple(_case(repo_root, item) for item in cases if isinstance(item, dict))


def _case(repo_root: Path, data: dict[str, Any]) -> EvalCase:
    case_id = str(data.get("id") or "")
    if not case_id:
        raise ValueError("eval case missing id")
    input_path = repo_root / str(data.get("input") or "")
    if not input_path.exists():
        raise FileNotFoundError(f"eval case {case_id} references missing input {input_path}")
    return EvalCase(
        case_id=case_id,
        input_path=input_path,
        purpose=str(data.get("purpose") or ""),
        default_styles=tuple(str(item) for item in data.get("default_styles", []) if item),
        expected_risks=tuple(str(item) for item in data.get("expected_risks", []) if item),
    )
