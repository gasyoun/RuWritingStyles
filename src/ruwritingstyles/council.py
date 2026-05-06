"""Offline council bundle creation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class CouncilBundle:
    """Paths created for a council request."""

    council_json: Path
    prompt_md: Path


def create_council_bundle(*, repo_root: Path, run_dir: Path) -> CouncilBundle:
    run_dir = run_dir.resolve()
    segments_path = run_dir / "segments.json"
    reviews_dir = run_dir / "reviews"
    if not segments_path.exists():
        raise FileNotFoundError(f"missing {segments_path}")
    if not reviews_dir.exists():
        raise FileNotFoundError(f"missing {reviews_dir}; run `rws review` first")

    review_paths = sorted(reviews_dir.glob("*.review.json"))
    if not review_paths:
        raise FileNotFoundError(f"no review JSON files found in {reviews_dir}")

    segments_doc = json.loads(segments_path.read_text(encoding="utf-8"))
    run_id = str(segments_doc.get("run_id") or run_dir.name)

    prompt_path = run_dir / "council.prompt.md"
    council_path = run_dir / "council.json"
    review_docs = [_load_review(path) for path in review_paths]

    prompt_path.write_text(
        _render_prompt(
            repo_root=repo_root,
            run_id=run_id,
            run_dir=run_dir,
            segments_json=segments_path.read_text(encoding="utf-8"),
            review_docs=review_docs,
        ),
        encoding="utf-8",
    )

    council_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "prompt_ready",
                "prompt_path": _repo_relative(repo_root, prompt_path),
                "review_files": [_repo_relative(repo_root, path) for path in review_paths],
                "replies": [],
                "decisions": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return CouncilBundle(council_json=council_path, prompt_md=prompt_path)


def _load_review(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    data["_path"] = str(path)
    return data


def _render_prompt(
    *,
    repo_root: Path,
    run_id: str,
    run_dir: Path,
    segments_json: str,
    review_docs: list[dict[str, object]],
) -> str:
    reviews_json = json.dumps(review_docs, ensure_ascii=False, indent=2)

    return f"""# Council Request

You are the RuWritingStyles council coordinator.

Read the style review artifacts, compare findings across styles, and return a structured council result. Do not rewrite the document. Decide which findings are accepted, accepted with modification, rejected, deferred, or informational.

## Run

- Run id: `{run_id}`
- Run directory: `{_repo_relative(repo_root, run_dir)}`

## Required Output

Return a JSON object with this shape:

```json
{{
  "run_id": "{run_id}",
  "status": "completed",
  "replies": [
    {{
      "reply_to": "finding-001",
      "style_id": "zalizniak-shkolnikov-1",
      "position": "agree_with_modification",
      "comment": "Why this style modifies the finding.",
      "proposed_adjustment": "Concrete adjustment."
    }}
  ],
  "decisions": [
    {{
      "finding_id": "finding-001",
      "status": "accepted_with_modification",
      "reason": "Why this decision follows from the council."
    }}
  ]
}}
```

Allowed reply positions: `agree`, `agree_with_modification`, `disagree`, `needs_human_decision`, `out_of_scope`.

Allowed decision statuses: `accepted`, `accepted_with_modification`, `rejected`, `deferred`, `informational`.

Use only finding IDs and `span_id` values present in the review artifacts and `segments.json`.

## Review Artifacts

```json
{reviews_json}
```

## Segments JSON

```json
{segments_json.strip()}
```
"""


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
