"""Offline verification bundle creation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class VerificationBundle:
    """Paths created for a verification request."""

    verification_json: Path
    prompt_md: Path


from .config import load_run_metadata

def create_verification_bundle(*, repo_root: Path, run_dir: Path) -> VerificationBundle:
    run_dir = run_dir.resolve()
    run_metadata = load_run_metadata(run_dir)
    text_domain = run_metadata.get("text_domain", "unknown")

    original_path = run_dir / "original.md"
    normalized_path = run_dir / "normalized.md"
    revision_path = run_dir / "revision.json"
    if not original_path.exists():
        raise FileNotFoundError(f"missing {original_path}")
    if not normalized_path.exists():
        raise FileNotFoundError(f"missing {normalized_path}")
    if not revision_path.exists():
        raise FileNotFoundError(f"missing {revision_path}; run `rws revise` first")

    revision_doc = json.loads(revision_path.read_text(encoding="utf-8"))
    run_id = str(revision_doc.get("run_id") or run_dir.name)

    prompt_path = run_dir / "verification.prompt.md"
    verification_path = run_dir / "verification.json"

    revised_document_text = _load_revised_document(repo_root, revision_doc)

    prompt_path.write_text(
        _render_prompt(
            repo_root=repo_root,
            run_id=run_id,
            run_dir=run_dir,
            original_text=original_path.read_text(encoding="utf-8"),
            normalized_text=normalized_path.read_text(encoding="utf-8"),
            revision_json=revision_path.read_text(encoding="utf-8"),
            revised_document_text=revised_document_text,
            text_domain=text_domain,
        ),
        encoding="utf-8",
    )

    verification_path.write_text(
        json.dumps(
            {
                "run_id": run_id,
                "status": "prompt_ready",
                "prompt_path": _repo_relative(repo_root, prompt_path),
                "revision_file": _repo_relative(repo_root, revision_path),
                "passed": [],
                "warnings": [],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    return VerificationBundle(verification_json=verification_path, prompt_md=prompt_path)


def _load_revised_document(repo_root: Path, revision_doc: dict[str, object]) -> str:
    raw_path = revision_doc.get("revised_document_path")
    if not isinstance(raw_path, str) or not raw_path:
        return ""
    path = (repo_root / raw_path).resolve()
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _render_prompt(
    *,
    repo_root: Path,
    run_id: str,
    run_dir: Path,
    original_text: str,
    normalized_text: str,
    revision_json: str,
    revised_document_text: str,
    text_domain: str = "unknown",
) -> str:
    revised_block = revised_document_text.strip() or "(No revised document has been produced yet.)"

    project_context_path = run_dir.parent / "project-context.json"
    project_context_section = ""
    if project_context_path.exists():
        project_context = json.loads(project_context_path.read_text(encoding="utf-8"))
        commitments = project_context.get("commitments", [])
        if commitments:
            commitments_json = json.dumps(commitments, ensure_ascii=False, indent=2)
            project_context_section = f"""
## Stylistic Commitments (Binding Rules)

The following rules were established in previous documents of this project. You MUST verify that the revised document strictly follows these decisions. Flag any inconsistencies as CRITICAL warnings.

```json
{commitments_json}
```
"""

    domain_rules = {
        "etymology": "Rule: EPISTEMIC_CAUTION. All etymological claims must use markers of uncertainty (perhaps, likely) if the source text used them.",
        "semiotics": "Rule: TERMINOLOGICAL_RIGOR. Do not allow simplification of semiotic terms (code, signifier, interpretant) into generic words.",
        "dialectology": "Rule: PHONETIC_FIDELITY. Any change to phonetic transcription or dialectal forms must be flagged as a CRITICAL violation.",
        "history": "Rule: HISTORICAL_DISTANCE. Avoid anachronistic modern terminology in descriptions of past epochs.",
        "literature": "Rule: SCHOLARLY_ETIQUETTE. Do not allow the removal of academic 'hedging' (it seems, apparently) unless it is redundant. Preserve the epistemic humility of the author.",
    }.get(text_domain, "Rule: GENERAL_FIDELITY. Preserve all nuanced scholarly phrasing.")

    return f"""# Verification Request

You are the RuWritingStyles verifier.

## Your Mission

Check whether the revised document preserves the source document's facts, argument structure, citations, examples, and unresolved questions. 

**Philological Fidelity (Domain: {text_domain})**:
{domain_rules}

**Style Consistency Mission**:
Verify that all "Stylistic Commitments" provided below are correctly implemented in the revised text.
{project_context_section}
## Run

- Run id: `{run_id}`
- Run directory: `{_repo_relative(repo_root, run_dir)}`

## Required Output

Return a JSON object with this shape:

```json
{{
  "run_id": "{run_id}",
  "status": "needs_human_review",
  "passed": [
    "facts_preserved"
  ],
  "warnings": [
    {{
      "span_id": "p022",
      "message": "What needs review and why."
    }}
  ]
}}
```

Allowed statuses: `passed`, `needs_human_review`, `failed`.

If no revised document has been produced yet, return `needs_human_review` and explain that verification is blocked until synthesis completes.

## Revision JSON

```json
{revision_json.strip()}
```

## Revised Document

```markdown
{revised_block}
```

## Original Document

```markdown
{original_text.strip()}
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
