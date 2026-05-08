"""Offline review bundle creation for style agents."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .config import Manifest, StylePassportSummary, load_passport_summaries


@dataclass(frozen=True)
class ReviewBundle:
    """Paths created for a single style review request."""

    review_json: Path
    prompt_md: Path


@dataclass(frozen=True)
class DeliberationBundle:
    """Paths created for a style deliberation/critique request."""

    deliberation_json: Path
    prompt_md: Path


def create_review_bundle(
    *,
    repo_root: Path,
    run_dir: Path,
    style_id: str,
    manifest: Manifest,
    profile: str = "researcher",
) -> ReviewBundle:
    run_dir = run_dir.resolve()
    segments_path = run_dir / "segments.json"
    normalized_path = run_dir / "normalized.md"
    if not segments_path.exists():
        raise FileNotFoundError(f"missing {segments_path}")
    if not normalized_path.exists():
        raise FileNotFoundError(f"missing {normalized_path}")

    segments_doc = json.loads(segments_path.read_text(encoding="utf-8"))
    run_id = str(segments_doc.get("run_id") or run_dir.name)
    segments = segments_doc.get("segments", [])
    if not isinstance(segments, list):
        raise ValueError("segments.json must contain a list in `segments`")

    passport = _find_passport(repo_root, manifest, style_id)
    review_dir = run_dir / "reviews"
    review_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = review_dir / f"{style_id}.prompt.md"
    review_path = review_dir / f"{style_id}.review.json"

    prompt_path.write_text(
        _render_prompt(
            repo_root=repo_root,
            run_id=run_id,
            run_dir=run_dir,
            passport=passport,
            segments_json=segments_path.read_text(encoding="utf-8"),
            profile=profile,
        ),
        encoding="utf-8",
    )

    review_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "style_id": style_id,
                "status": "prompt_ready",
                "prompt_path": _repo_relative(repo_root, prompt_path),
                "expected_finding_schema": "schemas/finding.schema.json",
                "segment_count": len(segments),
                "findings": [],
                "profile": profile,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return ReviewBundle(review_json=review_path, prompt_md=prompt_path)


def _find_passport(repo_root: Path, manifest: Manifest, style_id: str) -> StylePassportSummary:
    for summary in load_passport_summaries(repo_root, manifest):
        if summary.style_id == style_id:
            return summary
    available = ", ".join(summary.style_id for summary in load_passport_summaries(repo_root, manifest))
    raise ValueError(f"unknown style id {style_id!r}; available styles: {available}")


def create_deliberation_bundle(
    *,
    repo_root: Path,
    run_dir: Path,
    style_id: str,
    manifest: Manifest,
    profile: str = "researcher",
) -> DeliberationBundle:
    run_dir = run_dir.resolve()
    segments_path = run_dir / "segments.json"
    reviews_dir = run_dir / "reviews"
    if not segments_path.exists():
        raise FileNotFoundError(f"missing {segments_path}")
    if not reviews_dir.exists():
        raise FileNotFoundError(f"missing {reviews_dir}; run `rws review` first")

    review_paths = sorted(reviews_dir.glob("*.review.json"))
    review_docs = []
    for path in review_paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["_path"] = str(path)
        review_docs.append(doc)

    segments_doc = json.loads(segments_path.read_text(encoding="utf-8"))
    run_id = str(segments_doc.get("run_id") or run_dir.name)

    passport = _find_passport(repo_root, manifest, style_id)
    delib_dir = run_dir / "deliberations"
    delib_dir.mkdir(parents=True, exist_ok=True)

    prompt_path = delib_dir / f"{style_id}.delib.prompt.md"
    delib_path = delib_dir / f"{style_id}.delib.json"

    # Filter out own findings from the prompt to avoid self-critique confusion
    other_reviews = [d for d in review_docs if d.get("style_id") != style_id]
    other_reviews_json = json.dumps(other_reviews, ensure_ascii=False, indent=2)

    prompt_path.write_text(
        _render_delib_prompt(
            repo_root=repo_root,
            run_id=run_id,
            run_dir=run_dir,
            passport=passport,
            other_reviews_json=other_reviews_json,
            segments_json=segments_path.read_text(encoding="utf-8"),
            profile=profile,
        ),
        encoding="utf-8",
    )

    delib_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "style_id": style_id,
                "status": "prompt_ready",
                "prompt_path": _repo_relative(repo_root, prompt_path),
                "replies": [],
                "profile": profile,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return DeliberationBundle(deliberation_json=delib_path, prompt_md=prompt_path)


def _render_delib_prompt(
    *,
    repo_root: Path,
    run_id: str,
    run_dir: Path,
    passport: StylePassportSummary,
    other_reviews_json: str,
    segments_json: str,
    profile: str = "researcher",
) -> str:
    passport_text = passport.passport_path.read_text(encoding="utf-8")
    from .profiles import get_profile_suffix
    profile_suffix = get_profile_suffix(profile)

    return f"""# Style Deliberation Request

You are a RuWritingStyles `style_deliberator` representing style `{passport.style_id}`.

## Your Mission

Review the style findings provided by OTHER agents. Compare them against your own style rules. For each finding, decide if you agree, disagree, or want to suggest a modification.

## User Profile: {profile.capitalize()}
{profile_suffix}

## Required Output

Return a JSON object with this shape:

```json
{{
  "style_id": "{passport.style_id}",
  "replies": [
    {{
      "reply_to": "finding-001",
      "style_id": "{passport.style_id}",
      "position": "agree",
      "comment": "Why you agree or disagree based on your style rules.",
      "proposed_adjustment": "Optional specific adjustment if you prefer a different wording."
    }}
  ]
}}
```

Allowed positions: `agree`, `agree_with_modification`, `disagree`, `needs_human_decision`, `out_of_scope`.

## Your Style Passport

```yaml
{passport_text.strip()}
```

## Other Style Reviews

```json
{other_reviews_json}
```

## Segments JSON

```json
{segments_json.strip()}
```
"""


def _render_prompt(
    *,
    repo_root: Path,
    run_id: str,
    run_dir: Path,
    passport: StylePassportSummary,
    segments_json: str,
    profile: str = "researcher",
) -> str:
    passport_text = passport.passport_path.read_text(encoding="utf-8")
    style_text = passport.source_prompt.read_text(encoding="utf-8")
    from .profiles import get_profile_suffix
    profile_suffix = get_profile_suffix(profile)

    return f"""# Style Review Request

You are a RuWritingStyles `style_reviewer`.

Review the document segments for style `{passport.style_id}` and return only JSON findings that match `schemas/finding.schema.json`.

## Run

- Run id: `{run_id}`
- Run directory: `{_repo_relative(repo_root, run_dir)}`
- Style id: `{passport.style_id}`
- Style name: `{passport.name}`
- Role: `{passport.role}`

## User Profile: {profile.capitalize()}
{profile_suffix}

## Required Output

Return a JSON object with this shape:

```json
{{
  "style_id": "{passport.style_id}",
  "summary": "Short review summary.",
  "findings": [
    {{
      "id": "finding-001",
      "style_id": "{passport.style_id}",
      "span_id": "p001",
      "severity": "major",
      "type": "missing_source",
      "finding": "What is wrong, grounded in the segment.",
      "suggestion": "Concrete revision advice.",
      "confidence": 0.8
    }}
  ]
}}
```

Use only `span_id` values from `segments.json`. Do not rewrite the whole document. Do not invent sources. If there are no findings, return an empty `findings` array.

## Style Passport

```yaml
{passport_text.strip()}
```

## Full Style Instruction

```markdown
{style_text.strip()}
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
