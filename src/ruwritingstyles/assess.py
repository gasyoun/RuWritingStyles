"""Impact assessment for protected text qualities (rhyme, meter, tone)."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ImpactBundle:
    """Paths created for an impact assessment request."""

    impact_json: Path
    prompt_md: Path


def create_impact_bundle(*, repo_root: Path, run_dir: Path) -> ImpactBundle:
    run_dir = run_dir.resolve()
    segments_path = run_dir / "segments.json"
    revised_path = run_dir / "revised.md"
    
    if not segments_path.exists():
        raise FileNotFoundError(f"missing {segments_path}")
    if not revised_path.exists():
        # Impact assessment happens after revision
        raise FileNotFoundError(f"missing {revised_path}; run `rws revise` first")

    segments_doc = json.loads(segments_path.read_text(encoding="utf-8"))
    run_id = str(segments_doc.get("run_id") or run_dir.name)
    segments = segments_doc.get("segments", [])

    # Filter for segments with tags
    protected = [s for s in segments if s.get("tags")]
    if not protected:
        prompt_path = run_dir / "impact.prompt.md"
        impact_path = run_dir / "impact.json"
        prompt_path.write_text(
            "# Impact Assessment\n\nNo protected segment tags were found; no provider assessment is required.\n",
            encoding="utf-8",
        )
        impact_path.write_text(
            json.dumps(
                {
                    "run_id": run_id,
                    "status": "completed",
                    "prompt_path": _repo_relative(repo_root, prompt_path),
                    "assessments": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return ImpactBundle(impact_json=impact_path, prompt_md=prompt_path)

    prompt_path = run_dir / "impact.prompt.md"
    impact_path = run_dir / "impact.json"

    prompt_path.write_text(
        _render_prompt(
            run_id=run_id,
            protected_segments=protected,
            revised_text=revised_path.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )

    impact_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "prompt_ready",
                "prompt_path": _repo_relative(repo_root, prompt_path),
                "assessments": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return ImpactBundle(impact_json=impact_path, prompt_md=prompt_path)


def _render_prompt(run_id: str, protected_segments: list[dict], revised_text: str) -> str:
    protected_json = json.dumps(protected_segments, ensure_ascii=False, indent=2)
    
    return f"""# Impact Assessment Request

You are a RuWritingStyles `impact_assessor`.

## Your Mission

Check if the revised document preserved the 'protected qualities' (tags) identified in the original segments.

## Protected Segments (Original)

```json
{protected_json}
```

## Revised Document

```markdown
{revised_text}
```

## Instructions

1. **Locate Segments**: Find the revised version of each protected segment in the provided document.
2. **Evaluate Impact**: For each tag (rhyme, meter, tone, etc.), determine if the quality was preserved, improved, or damaged.
3. **Pass/Fail**: Mark `passed: false` if a protected quality was broken (e.g., a rhyme was lost, a meter was disrupted).

## Required Output

Return a JSON object matching `schemas/impact-output.schema.json`:

```json
{{
  "run_id": "{run_id}",
  "status": "completed",
  "assessments": [
    {{
      "span_id": "p005",
      "tag": "rhyme",
      "impact": "negative",
      "passed": false,
      "comment": "The revision changed 'гора' to 'холм', breaking the rhyme with 'пора'."
    }}
  ]
}}
```
"""


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
