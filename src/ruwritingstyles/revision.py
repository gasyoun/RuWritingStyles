"""Offline revision bundle creation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


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

    prompt_path.write_text(
        _render_prompt(
            repo_root=repo_root,
            run_id=run_id,
            run_dir=run_dir,
            normalized_text=normalized_text,
            council_json=council_path.read_text(encoding="utf-8"),
            resolution_json=resolution_json,
        ),
        encoding="utf-8",
    )

    revision_path.write_text(
        json.dumps(
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
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return RevisionBundle(revision_json=revision_path, prompt_md=prompt_path)


def _render_prompt(
    *,
    repo_root: Path,
    run_id: str,
    run_dir: Path,
    normalized_text: str,
    council_json: str,
    resolution_json: str = "",
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

    return f"""# Revision Request

You are the RuWritingStyles synthesizer.

Use the council decisions to produce a **minimally edited** version of the document.

## Editing discipline (load-bearing — the revision is judged on fidelity to the source)

- Touch ONLY the spans named in accepted (or accepted-with-modification) council decisions.
  Every other span MUST be copied into `revised_document` **verbatim, character for
  character** — do not rephrase, reorder, "polish", expand, or re-translate untouched text.
- Make the **smallest** change that resolves each accepted finding: add a short caveat, a
  citation marker, an IAST gloss, or correct the specific claim. Do **not** rewrite the
  surrounding sentence or paragraph to accommodate a local fix.
- Keep the document's length close to the original. A targeted correction must not materially
  lengthen the text; if your `revised_document` is noticeably longer than the source, you are
  over-editing — pull back to surgical changes.
- Do not add unsupported facts, and do not hide unresolved issues (put them in `unresolved`).

## Run

- Run id: `{run_id}`
- Run directory: `{_repo_relative(repo_root, run_dir)}`

## Required Output

Return a JSON object with this shape:

```json
{{
  "run_id": "{run_id}",
  "status": "completed",
  "revised_document": "Full revised Markdown document.",
  "applied_changes": [
    {{
      "span_id": "p014",
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

Only apply accepted or accepted-with-modification council decisions. Preserve the author's factual claims unless the council explicitly marks them as unsupported. If the council is still `prompt_ready` and has no decisions, return the original document unchanged and explain that no completed council decisions were available.
{resolution_section}
## Council JSON

```json
{council_json.strip()}
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
