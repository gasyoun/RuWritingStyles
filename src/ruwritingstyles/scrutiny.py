"""Deep linguistic scrutiny (philological validation) of document segments."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from .io_utils import atomic_write_json, atomic_write_text


@dataclass(frozen=True)
class ScrutinyBundle:
    """Paths created for a linguistic scrutiny request."""

    scrutiny_json: Path
    prompt_md: Path


def create_scrutiny_bundle(*, repo_root: Path, run_dir: Path) -> ScrutinyBundle:
    run_dir = run_dir.resolve()
    segments_path = run_dir / "segments.json"
    normalized_path = run_dir / "normalized.md"

    if not segments_path.exists():
        raise FileNotFoundError(f"missing {segments_path}")
    if not normalized_path.exists():
        raise FileNotFoundError(f"missing {normalized_path}")

    segments_doc = json.loads(segments_path.read_text(encoding="utf-8"))
    run_id = str(segments_doc.get("run_id") or run_dir.name)

    scrutiny_dir = run_dir / "scrutiny"
    scrutiny_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = scrutiny_dir / "scrutiny.prompt.md"
    scrutiny_path = scrutiny_dir / "scrutiny.json"

    atomic_write_text(
        prompt_path,
        _render_prompt(
            run_id=run_id,
            segments_json=segments_path.read_text(encoding="utf-8"),
            normalized_text=normalized_path.read_text(encoding="utf-8"),
        ),
    )

    atomic_write_json(
        scrutiny_path,
        {
                "run_id": run_id,
                "status": "prompt_ready",
                "prompt_path": _repo_relative(repo_root, prompt_path),
                "findings": [],
        },
    )

    return ScrutinyBundle(scrutiny_json=scrutiny_path, prompt_md=prompt_path)


def _render_prompt(run_id: str, segments_json: str, normalized_text: str) -> str:
    return f"""# Linguistic Scrutiny Request

You are a RuWritingStyles `linguistic_scrutinizer` (Senior Philologist).

## Your Mission

Perform a deep philological audit of the document. Identify etymological errors, lexical anachronisms, and syntactic inconsistencies that standard style checkers might miss.

## Focus Areas

1. **Etymological Validity**: Are historical forms and roots used correctly? Check for pseudo-archaisms or "folk etymology."
2. **Lexical Anachronisms**: Identify words or meanings that did not exist in the target period (if a specific period is implied by the style).
3. **Syntactic Fidelity**: Is the sentence structure consistent with the intended historical or academic register?
4. **Morphological Accuracy**: Check for incorrect historical endings or declensions.

## Required Output

Return a JSON object matching `schemas/scrutiny-output.schema.json`:

```json
{{
  "run_id": "{run_id}",
  "status": "completed",
  "findings": [
    {{
      "span_id": "p002",
      "category": "etymology",
      "severity": "critical",
      "finding": "The use of 'X' as a root for 'Y' is a folk etymology; historical linguistics shows 'Z' is the actual root.",
      "suggestion": "Correct the explanation to reference 'Z'.",
      "confidence": 0.95
    }}
  ]
}}
```

## Segments JSON

```json
{segments_json.strip()}
```

## Normalized Document

```markdown
{normalized_text.strip()}
```
"""


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
