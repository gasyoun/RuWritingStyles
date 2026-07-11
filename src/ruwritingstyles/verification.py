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


def _render_journal_section(profile: Any, revised_text: str) -> str:
    """Render the target-journal requirements block for the verifier prompt."""
    if not isinstance(profile, dict) or not profile.get("name"):
        return ""

    rules: list[str] = []
    max_chars = profile.get("max_chars")
    if isinstance(max_chars, int) and max_chars > 0:
        current = len(revised_text)
        status = "в пределах нормы" if current <= max_chars else "ПРЕВЫШЕН"
        rules.append(
            f"Объем: не более {max_chars} знаков (сейчас ≈ {current}, лимит {status})."
        )
    citation_format = profile.get("citation_format")
    if citation_format:
        rules.append(f"Список литературы: формат {citation_format}.")
    scheme = profile.get("transliteration_scheme")
    if scheme:
        rules.append(f"Транслитерация санскрита: единая схема {scheme}.")
    first_mention = profile.get("first_mention_rule")
    if first_mention and first_mention != "none":
        rules.append(
            "Первое упоминание термина: " + {
                "ru+iast": "русская передача с IAST в скобках.",
                "iast+ru": "IAST с русской передачей в скобках.",
                "ru-only": "только русская передача.",
                "iast-only": "только IAST.",
            }.get(first_mention, first_mention)
        )
    for key, label in (("abstract_required", "Аннотация"), ("keywords_required", "Ключевые слова")):
        langs = profile.get(key)
        if isinstance(langs, list) and langs:
            rules.append(f"{label}: обязательны на языках — {', '.join(langs)}.")

    if not rules:
        return ""
    body = "\n".join(f"- {rule}" for rule in rules)
    return f"""
## Требования журнала «{profile['name']}»

Проверьте соответствие пересмотренного текста требованиям целевого журнала и отметьте нарушения как предупреждения:
{body}
"""


def _render_run_style_commitments(repo_root: Path, run_dir: Path) -> str:
    """THIS run's style commitments for the verifier prompt (F4 second half).

    The verifier historically saw only *project-level* commitments carried over
    from previous documents; the run's own council `stylistic_commitments` and
    the reviewing passports' `limits` (their binding obligations) never reached
    it, so a run could not confirm the revision honored its own style verdict
    (prompt-fidelity review F4, deferred half — activated in H588 N3 with a
    measured before/after eval pass). Set RWS_VERIFY_STYLE_COMMITMENTS=0 to
    restore the pre-H588 prompt."""
    import os as _os
    if _os.environ.get("RWS_VERIFY_STYLE_COMMITMENTS", "1") == "0":
        return ""

    lines: list[str] = []

    council_path = run_dir / "council.json"
    if council_path.exists():
        try:
            council = json.loads(council_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            council = {}
        commitments = council.get("stylistic_commitments")
        if isinstance(commitments, list) and commitments:
            lines.append("Terminological decisions the council committed this run to:")
            for c in commitments:
                if isinstance(c, dict) and c.get("term"):
                    lines.append(f"- `{c['term']}`: {c.get('decision', '')}")

    style_limits: list[str] = []
    reviews_dir = run_dir / "reviews"
    if reviews_dir.exists():
        for review_path in sorted(reviews_dir.glob("*.review.json")):
            try:
                review = json.loads(review_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            style_id = review.get("style_id")
            if not style_id:
                continue
            passport_path = repo_root / "styles" / "passports" / f"{style_id}.yml"
            if not passport_path.exists():
                continue
            try:
                import yaml
                passport = yaml.safe_load(passport_path.read_text(encoding="utf-8")) or {}
            except Exception:
                continue
            limits = passport.get("limits")
            if isinstance(limits, list) and limits:
                for limit in limits:
                    style_limits.append(f"- [{style_id}] {limit}")
    if style_limits:
        lines.append("")
        lines.append("Binding obligations of the styles that reviewed this run "
                     "(the revised text must not violate any of them):")
        lines.extend(style_limits)

    if not lines:
        return ""
    body = "\n".join(lines)
    return f"""
## Run Style Commitments (This Run)

These commitments come from THIS run's council and the reviewing style passports.
Verify the revised document honors each; report a violation as a warning naming
the commitment and the offending span.

{body}
"""


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
    from .context_builder import build_long_artifact_preview, build_unified_context
    from .knowledge import search_knowledge_base

    revised_block = revised_document_text.strip() or "(No revised document has been produced yet.)"

    # --- Knowledge context from philological collections ---
    domain_keywords = [text_domain] if text_domain != "unknown" else []
    knowledge_passages = search_knowledge_base(repo_root, domain_keywords)
    unified_context_block = build_unified_context(
        manifest={},
        knowledge_results=knowledge_passages,
        source_passage_id=None,
    )

    # --- Revision artifact preview (truncated to save context budget) ---
    revision_preview = build_long_artifact_preview(run_dir / "revision.json", max_lines=60)

    from .project import load_project_context

    project_context = load_project_context(run_dir)
    project_context_section = ""
    commitments = (
        project_context.get("stylistic_commitments")
        or project_context.get("commitments")
        or []
    )
    if commitments:
        commitments_json = json.dumps(commitments, ensure_ascii=False, indent=2)
        project_context_section = f"""
## Stylistic Commitments (Binding Rules)

The following rules were established in previous documents of this project. You MUST verify that the revised document strictly follows these decisions. Flag any inconsistencies as CRITICAL warnings.

```json
{commitments_json}
```
"""

    run_style_section = _render_run_style_commitments(repo_root, run_dir)

    journal_section = _render_journal_section(
        project_context.get("journal_profile"), revised_document_text
    )

    bib_section = ""
    bib_path = run_dir.parent / "references.bib"
    if not bib_path.exists():
        bib_path = repo_root / "references.bib"
        
    if bib_path.exists():
        bib_content = bib_path.read_text(encoding="utf-8")
        bib_section = f"""
## Citation Verifier (Bibliography)
The following BibTeX entries represent the dynamic bibliography for this document. You MUST strictly verify:
1. All citations in the text must match these entries (names, dates, bibliographic references).
2. Direct quotes must be accurately represented and cited.
3. Transliteration of names must follow academic standards consistently.
Flag any missing or incorrect citations as CRITICAL warnings.

```bibtex
{bib_content.strip()[:2000]} 
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
{run_style_section}
{journal_section}
{bib_section}
{unified_context_block}
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
