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


def create_council_bundle(
    *,
    repo_root: Path,
    run_dir: Path,
    manifest: Manifest,
    verification_feedback: dict[str, Any] | None = None,
) -> CouncilBundle:
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
            manifest=manifest,
            verification_feedback=verification_feedback,
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
    review_docs: list[dict[str, Any]],
    manifest: Manifest,
    verification_feedback: dict[str, Any] | None = None,
) -> str:
    weights = {ref.style_id: ref.weight for ref in manifest.passports}
    council_config = manifest.council or CouncilConfig("Coordinator", "Neutral deliberation.")

    # Group findings by span for the prompt
    by_span: dict[str, list[dict[str, Any]]] = {}
    for doc in review_docs:
        style_id = str(doc.get("style_id", "unknown"))
        weight = weights.get(style_id, 1.0)
        findings = doc.get("findings")
        if isinstance(findings, list):
            for finding in findings:
                if isinstance(finding, dict):
                    fid = finding.get("span_id", "global")
                    f_with_meta = dict(finding)
                    f_with_meta["_style_weight"] = weight
                    by_span.setdefault(fid, []).append(f_with_meta)

    grouped_findings_json = json.dumps(by_span, ensure_ascii=False, indent=2)

    feedback_section = ""
    if verification_feedback:
        warnings = verification_feedback.get("warnings", [])
        if warnings:
            feedback_json = json.dumps(warnings, ensure_ascii=False, indent=2)
            feedback_section = f"""
## Verification Feedback (CRITICAL)

The previous revision attempt failed verification with these warnings. You MUST address these issues in your new decisions.

```json
{feedback_json}
```
"""

    return f"""# Council Request

You are the RuWritingStyles council: `{council_config.archetype}`.

## Your Mission

Read the style review findings, compare advice across styles, and return a structured council result. 

**Conflict Resolution Strategy:**
{council_config.conflict_resolution_strategy}
{feedback_section}
## Instructions

1. **Compare Advice**: For each document span, look at findings from all styles.
2. **Resolve Conflicts**: If styles suggest different changes for the same span, use your strategy and the `_style_weight` (higher is more authoritative) to decide.
3. **Synthesis**: You can accept a finding exactly, reject it, or create a "modified" finding that combines advice from multiple styles.
4. **Informational**: Mark findings as informational if they are interesting observations that don't justify a text change.

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
      "comment": "Synthesis of Zalizniak and Tronsky advice.",
      "proposed_adjustment": "Synthesized revision text."
    }}
  ],
  "decisions": [
    {{
      "finding_id": "finding-001",
      "status": "accepted_with_modification",
      "reason": "Why this decision follows from the council strategy."
    }}
  ]
}}
```

Allowed reply positions: `agree`, `agree_with_modification`, `disagree`, `needs_human_decision`, `out_of_scope`.
Allowed decision statuses: `accepted`, `accepted_with_modification`, `rejected`, `deferred`, `informational`.

## Findings Grouped By Span

```json
{grouped_findings_json}
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
