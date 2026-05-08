"""Offline council bundle creation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CouncilBundle:
    """Paths created for a council request."""

    council_json: Path
    prompt_md: Path


from .config import CouncilArchetype, CouncilConfig, Manifest, load_archetypes, load_run_metadata
from .knowledge import search_knowledge_base, extract_keywords_from_reviews

# Philological Conflict Matrix (Step L-03)
# (cluster_a, cluster_b) -> resolution_hint
CONFLICT_MATRIX = {
    ("lit_opoyaz", "lit_bakhtin"): "OPOYAZ focus: plot structure, technical device. Bakhtin focus: dialogism, character voice. Resolution: Prioritize polyphony in dialogues, but maintain formal unity in narrative structure.",
    ("ling_iesh", "ling_nss"): "IESH focus: historical etymology. NSS focus: modern literary norm. Resolution: Use modern spelling by default, but retain etymological variants in citations or expert commentary.",
    ("lit_structural", "lit_poststructural"): "Structuralist: stable deep structure. Poststructuralist: deconstruction of hierarchies. Resolution: Define a clear structure but add 'epistemic markers' to acknowledge alternative readings.",
    ("ling_mss", "ling_kmsh"): "MSS: semantic decomposition. KMSH: cognitive metaphors. Resolution: Use precise formal definitions, but interpret cultural concepts through metaphorical frames.",
    ("lit_textology", "lit_historico_cultural"): "Textology: manuscript evidence. Hist-Cult: epoch spirit. Resolution: Manuscript evidence is absolute for the text itself; historical context is for interpretation.",
}

def create_council_bundle(
    *,
    repo_root: Path,
    run_dir: Path,
    manifest: Manifest,
    verification_feedback: dict[str, Any] | None = None,
    archetype_id: str | None = None,
    profile: str = "researcher",
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

    delib_dir = run_dir / "deliberations"
    delib_paths = []
    if delib_dir.exists():
        delib_paths = sorted(delib_dir.glob("*.delib.json"))

    archetypes = load_archetypes(repo_root)
    archetype_map = {a.id: a for a in archetypes}
    
    # Priority: 1. explicit archetype_id, 2. manifest.council.archetype, 3. None
    selected_id = archetype_id or (manifest.council.archetype if manifest.council else None)
    chosen_archetype = archetype_map.get(selected_id) if selected_id else None

    scrutiny_path = run_dir / "scrutiny" / "scrutiny.json"
    scrutiny_doc = None
    if scrutiny_path.exists():
        scrutiny_doc = _load_review(scrutiny_path)

    project_context_path = run_dir.parent / "project-context.json"
    project_context = None
    if project_context_path.exists():
        project_context = json.loads(project_context_path.read_text(encoding="utf-8"))

    # Knowledge Base Integration
    keywords = extract_keywords_from_reviews(run_dir)
    external_research = search_knowledge_base(repo_root, keywords)

    segments_doc = json.loads(segments_path.read_text(encoding="utf-8"))
    run_id = str(segments_doc.get("run_id") or run_dir.name)
    
    run_metadata = load_run_metadata(run_dir)
    text_domain = run_metadata.get("text_domain", "unknown")

    prompt_path = run_dir / "council.prompt.md"
    council_path = run_dir / "council.json"
    review_docs = [_load_review(path) for path in review_paths]
    delib_docs = [_load_review(path) for path in delib_paths]

    prompt_path.write_text(
        _render_prompt(
            repo_root=repo_root,
            run_id=run_id,
            run_dir=run_dir,
            segments_json=segments_path.read_text(encoding="utf-8"),
            review_docs=review_docs,
            delib_docs=delib_docs,
            scrutiny_doc=scrutiny_doc,
            project_context=project_context,
            external_research=external_research,
            manifest=manifest,
            archetype=chosen_archetype,
            text_domain=text_domain,
            verification_feedback=verification_feedback,
            profile=profile,
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
                "profile": profile,
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


def get_cluster_weights(manifest: Manifest, text_domain: str, archetype: CouncilArchetype | None = None) -> dict[str, float]:
    """Calculate style weights based on cluster domain matching and methodological priority."""
    # Map cluster_id to domains and locations
    cluster_meta = {c.id: (c.domains, c.location) for c in manifest.clusters}
    
    adjusted_weights = {}
    for ref in manifest.passports:
        weight = ref.weight
        
        # 1. Archetype overrides (explicit weights from archetypes.yml)
        if archetype and ref.style_id in archetype.weights:
            weight = archetype.weights[ref.style_id]
        elif archetype and ref.cluster_id in archetype.weights:
            weight = archetype.weights[ref.cluster_id]
        
        domains, location = cluster_meta.get(ref.cluster_id, ((), ""))
        
        # 2. Domain Match Boost
        if text_domain != "unknown" and text_domain in domains:
            weight *= 1.5
            
        # 3. Methodological Authority (Regional/School boosts)
        if text_domain == "etymology" and ref.cluster_id == "ling_iesh":
            weight *= 2.0
        elif text_domain == "semiotics" and ref.cluster_id == "ling_mts":
            weight *= 2.0
        elif text_domain == "literature" and ref.cluster_id and ref.cluster_id.startswith("lit_"):
            weight *= 1.2
            
        # 4. Regional Archetype Boosts
        if archetype:
            is_moscow_arch = "Moscow" in archetype.name
            is_leningrad_arch = "Leningrad" in archetype.name or "Petersburg" in archetype.name
            
            if is_moscow_arch and location == "Moscow":
                weight *= 2.0
            elif is_leningrad_arch and location in ("Leningrad", "Petersburg"):
                weight *= 2.0

        adjusted_weights[ref.style_id] = weight
        
    return adjusted_weights


def _render_prompt(
    *,
    repo_root: Path,
    run_id: str,
    run_dir: Path,
    segments_json: str,
    review_docs: list[dict[str, Any]],
    delib_docs: list[dict[str, Any]],
    scrutiny_doc: dict[str, Any] | None,
    project_context: dict[str, Any] | None,
    external_research: str,
    manifest: Manifest,
    archetype: CouncilArchetype | None,
    text_domain: str = "unknown",
    verification_feedback: dict[str, Any] | None = None,
    profile: str = "researcher",
) -> str:
    weights = get_cluster_weights(manifest, text_domain, archetype)
    council_config = manifest.council or CouncilConfig("Coordinator", "Neutral deliberation.")
    from .profiles import get_profile_suffix
    profile_suffix = get_profile_suffix(profile)

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

    # Collect replies from deliberations
    all_replies: list[dict[str, Any]] = []
    for doc in delib_docs:
        replies = doc.get("replies")
        if isinstance(replies, list):
            all_replies.extend(replies)

    # Prepare conflict matrix for JSON (convert tuple keys to strings)
    serializable_matrix = {f"{k[0]} vs {k[1]}": v for k, v in CONFLICT_MATRIX.items()}
    matrix_json = json.dumps(serializable_matrix, ensure_ascii=False, indent=2)

    grouped_findings_json = json.dumps(by_span, ensure_ascii=False, indent=2)
    replies_json = json.dumps(all_replies, ensure_ascii=False, indent=2)

    context_section = ""
    if project_context:
        commitments = project_context.get("stylistic_commitments", [])
        if commitments:
            commitments_json = json.dumps(commitments, ensure_ascii=False, indent=2)
            context_section = f"""
## Project Context (Cross-Document Consistency)

The following stylistic commitments were made in previous documents of this project. You MUST follow these decisions. If the current document is in a different language, use the 'translations' provided or adapt the decision to the current language while maintaining the same stylistic intent.

```json
{commitments_json}
```
"""

    scrutiny_section = ""
    if scrutiny_doc:
        findings = scrutiny_doc.get("findings", [])
        if findings:
            scrutiny_findings_json = json.dumps(findings, ensure_ascii=False, indent=2)
            scrutiny_section = f"""
## Linguistic Scrutiny Findings (Expert Advice)

A Senior Philologist has audited the document. You MUST treat these findings as authoritative for etymology and anachronism resolution.

```json
{scrutiny_findings_json}
```
"""

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

    research_section = ""
    if external_research:
        research_section = f"""
## External Research (Knowledge Base)

The following data was retrieved from the project's philological knowledge base. You SHOULD use these facts to resolve terminological disputes.

{external_research}
"""

    mission_instructions = archetype.instructions if archetype else "Read the style review findings, compare advice across styles, and return a structured council result."
    personality_desc = f"Personality: {archetype.description}" if archetype else ""

    weights_json = json.dumps(weights, ensure_ascii=False, indent=2)

    return f"""# Council Request

You are the RuWritingStyles council: `{archetype.name if archetype else manifest.council.archetype if manifest.council else "The Coordinator"}`.
{personality_desc}

## Your Mission

{mission_instructions}

## User Profile: {profile.capitalize()}
{profile_suffix}

**Council Weights (Style Authority):**
The following weights represent the authority of each style agent. Use these when resolving conflicts.
```json
{weights_json}
```

**Conflict Resolution Strategy:**
{council_config.conflict_resolution_strategy}

**Philological Conflict Matrix (Methodological Resolution):**
When specific schools disagree, follow these established philological resolution patterns:
```json
{matrix_json}
```
{context_section}
{scrutiny_section}
{research_section}
{feedback_section}
## Instructions

1. **Compare Advice**: For each document span, look at findings from all styles.
2. **Resolve Conflicts**: If styles suggest different changes for the same span, use your strategy and the `_style_weight` (higher is more authoritative) to decide. **CRITICAL**: If a conflict is listed in the `Philological Conflict Matrix`, you MUST cite the specific resolution rule (e.g., 'Bakhtin > OPOYAZ') in your `reason` field.
3. **Synthesis**: You can accept a finding exactly, reject it, or create a "modified" finding that combines advice from multiple styles.
4. **Impact Assessment**: Pay close attention to `tags` in `segments.json`. 
   - If a segment has a `rhyme` tag, ensure proposed changes do not break the rhyme.
   - If it has a `meter` tag, preserve the rhythm.
   - If it has a `tone` tag, maintain the specified tone level.
   - REJECT advice that violates these protected qualities unless the advice is specifically fixing an error in that quality.
6. **Bloom's Taxonomy Labeling (Socratic Council)**: For every `reply` and `decision`, assign a `bloom_level` based on the cognitive depth of your reasoning:
   - `Remember`: Citing a rule or source directly.
   - `Understand`: Interpreting the meaning or context of the text.
   - `Apply`: Standard application of a style rule.
   - `Analyze`: Comparing multiple conflicting styles or linguistic patterns.
   - `Evaluate`: Justifying a choice between schools or resolving a methodological conflict.
   - `Create`: Synthesizing a new solution that reconciles different traditions.

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
      "bloom_level": "Analyze",
      "position": "agree_with_modification",
      "comment": "Synthesis of Zalizniak and Tronsky advice.",
      "proposed_adjustment": "Synthesized revision text."
    }}
  ],
  "decisions": [
    {{
      "finding_id": "finding-001",
      "bloom_level": "Evaluate",
      "status": "accepted_with_modification",
      "primary_school": "ling_iesh",
      "influence": {{
        "ling_iesh": 0.7,
        "ling_mss": 0.3
      }},
      "reason": "Why this decision follows from the council strategy."
    }}
  ],
```
  "stylistic_commitments": [
    {{
      "term": "X",
      "decision": "Use 'X' instead of 'Y' consistently.",
      "rationale": "Consistent with Tronsky's preference for historical roots.",
      "translations": {{
        "en": "X_en",
        "be": "X_be"
      }}
    }}
  ]
}}
```

Allowed reply positions: `agree`, `agree_with_modification`, `disagree`, `needs_human_decision`, `out_of_scope`.
Allowed decision statuses: `accepted`, `accepted_with_modification`, `rejected`, `deferred`, `informational`.

## Cross-Style Deliberation (Debate)

Style agents have reviewed each other's findings. Use these replies to understand consensus or disagreement.

```json
{replies_json}
```

## Findings Grouped By Span

{grouped_findings_json}

## Segments JSON

{segments_json.strip()}
"""


def _repo_relative(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path)
