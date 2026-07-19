"""Offline revision bundle creation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from .io_utils import atomic_write_json, atomic_write_text


@dataclass(frozen=True)
class RevisionBundle:
    """Paths created for a revision request."""

    revision_json: Path
    prompt_md: Path


def create_revision_bundle(*, repo_root: Path, run_dir: Path) -> RevisionBundle:
    run_dir = run_dir.resolve()
    normalized_path = run_dir / "normalized.md"
    council_path = run_dir / "council.json"
    if not normalized_path.exists():
        raise FileNotFoundError(f"missing {normalized_path}")
    if not council_path.exists():
        raise FileNotFoundError(f"missing {council_path}; run `rws council` first")

    council_doc = json.loads(council_path.read_text(encoding="utf-8"))
    run_id = str(council_doc.get("run_id") or run_dir.name)

    prompt_path = run_dir / "revision.prompt.md"
    revision_path = run_dir / "revision.json"
    normalized_text = normalized_path.read_text(encoding="utf-8")

    resolution_path = run_dir / "resolution.json"
    resolution_json = ""
    if resolution_path.exists():
        resolution_json = resolution_path.read_text(encoding="utf-8")

    segments_json = ""
    segments_path = run_dir / "segments.json"
    if segments_path.exists():
        segments_json = _render_span_map(segments_path.read_text(encoding="utf-8"))

    atomic_write_text(
        prompt_path,
        _render_prompt(
            repo_root=repo_root,
            run_id=run_id,
            run_dir=run_dir,
            normalized_text=normalized_text,
            council_json=council_path.read_text(encoding="utf-8"),
            resolution_json=resolution_json,
            segments_json=segments_json,
        ),
    )

    atomic_write_json(
        revision_path,
        {
                "run_id": run_id,
                "status": "prompt_ready",
                "prompt_path": _repo_relative(repo_root, prompt_path),
                "source_document": _repo_relative(repo_root, normalized_path),
                "council_file": _repo_relative(repo_root, council_path),
                "revised_document_path": None,
                "applied_changes": [],
                "unresolved": [],
        },
    )

    return RevisionBundle(revision_json=revision_path, prompt_md=prompt_path)


def _render_span_map(segments_json: str) -> str:
    """Reduce segments.json to a compact {span_id, type, text} span map.

    The synthesizer needs to see the exact current text of each span so its
    `replacement_text` covers the whole span; it does not need metrics or line
    numbers (the engine owns line placement during reconstruction)."""
    try:
        doc = json.loads(segments_json)
    except json.JSONDecodeError:
        return ""
    spans = []
    for segment in doc.get("segments", []) if isinstance(doc, dict) else []:
        if not isinstance(segment, dict):
            continue
        spans.append(
            {
                "span_id": segment.get("span_id"),
                "type": segment.get("type"),
                "text": segment.get("text"),
            }
        )
    if not spans:
        return ""
    return json.dumps(spans, ensure_ascii=False, indent=2)


def _render_prompt(
    *,
    repo_root: Path,
    run_id: str,
    run_dir: Path,
    normalized_text: str,
    council_json: str,
    resolution_json: str = "",
    segments_json: str = "",
) -> str:
    resolution_section = ""
    if resolution_json:
        resolution_section = f"""
## Human Stylistic Resolutions (Overrides)

The following resolutions represent final human decisions that override automated council outcomes. Prioritize these statuses:

```json
{resolution_json.strip()}
```
"""

    segments_section = ""
    if segments_json:
        segments_section = f"""
## Segments (span map)

Each object is one addressable span with its **exact current text**. To change a
span, return the span's `span_id` and the FULL rewritten text of that span as
`replacement_text` (the engine substitutes the whole span). Do NOT return spans
you are not changing.

```json
{segments_json.strip()}
```
"""

    return f"""# Revision Request

You are the RuWritingStyles synthesizer.

Apply the accepted council decisions as **per-span patches**. You do NOT rewrite or
re-emit the whole document — the engine reconstructs `revised.md` by copying every
untouched span byte-for-byte from the source and substituting only the spans you
return in `applied_changes`. Fidelity of untouched text is therefore guaranteed by
the engine; your job is only the surgical replacements.

## Editing discipline (load-bearing)

- Return an `applied_changes` entry ONLY for a span named in an accepted (or
  accepted-with-modification) council decision. Every span you omit is preserved
  exactly — so omit anything you are not deliberately changing.
- For each change, `replacement_text` is the FULL new text of that one span, making
  the **smallest** edit that resolves the accepted finding: add a short caveat, a
  citation marker, an IAST gloss, or correct the specific claim. Do **not** expand,
  re-translate, or "polish" the rest of the span; keep its length close to the
  original.
- **Hard length budget (engine-enforced):** the total character growth of ALL your
  replacements together must stay well under 40% of the document length, and each
  `replacement_text` should stay close to its span's original length. The engine
  REJECTS oversized patches — the span is then left completely unchanged and the
  finding lands in `unresolved` — so an over-long "improvement" achieves nothing.
  A short targeted insertion always beats a rewrite.
- Do not add unsupported facts, and do not hide unresolved issues (put them in
  `unresolved`).

## Run

- Run id: `{run_id}`
- Run directory: `{_repo_relative(repo_root, run_dir)}`

## Required Output

Return a JSON object with this shape:

```json
{{
  "run_id": "{run_id}",
  "status": "completed",
  "applied_changes": [
    {{
      "span_id": "p014",
      "replacement_text": "The full rewritten text of span p014 only.",
      "source_findings": ["finding-001"],
      "change_type": "strengthen_argument",
      "explanation": "What changed and why."
    }}
  ],
  "unresolved": [
    {{
      "span_id": "p022",
      "reason": "Why human review or external evidence is still needed."
    }}
  ]
}}
```

Only apply accepted or accepted-with-modification council decisions. Preserve the
author's factual claims unless the council explicitly marks them as unsupported. If
the council is still `prompt_ready` and has no decisions, return an empty
`applied_changes` list (the engine then reproduces the original document unchanged)
and note in `unresolved` that no completed council decisions were available.
{resolution_section}{segments_section}
## Council JSON

```json
{council_json.strip()}
```

## Normalized Document (reference only — do not re-emit)

```markdown
{normalized_text.strip()}
```
"""


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
