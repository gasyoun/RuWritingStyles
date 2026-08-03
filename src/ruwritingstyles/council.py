"""Offline council bundle creation."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any
from .io_utils import atomic_write_json, atomic_write_text


@dataclass(frozen=True)
class CouncilBundle:
    """Paths created for a council request."""

    council_json: Path
    prompt_md: Path


from .config import CouncilArchetype, CouncilConfig, Manifest, load_archetypes, load_run_metadata
from .knowledge import search_knowledge_base, extract_keywords_from_reviews

# Philological Conflict Matrix (Step L-03 + L-08 literary expansion)
# (cluster_a, cluster_b) -> resolution_hint
# Keys are stored in one order only; use lookup_conflict_hint() so either
# ordering resolves. L-08 pairs from docs/roadmap_literary_clusters.md §L-08.
CONFLICT_MATRIX = {
    # Pre-L-08 linguistic / mixed pairs
    ("ling_iesh", "ling_nss"): "IESH focus: historical etymology. NSS focus: modern literary norm. Resolution: Use modern spelling by default, but retain etymological variants in citations or expert commentary.",
    ("ling_mss", "ling_kmsh"): "MSS: semantic decomposition. KMSH: cognitive metaphors. Resolution: Use precise formal definitions, but interpret cultural concepts through metaphorical frames.",
    ("lit_structural", "lit_poststructural"): "Structuralist: stable deep structure. Poststructuralist: deconstruction of hierarchies. Resolution: Define a clear structure but add 'epistemic markers' to acknowledge alternative readings.",
    ("lit_textology", "lit_historico_cultural"): "Textology: manuscript evidence. Hist-Cult: epoch spirit. Resolution: Manuscript evidence is absolute for the text itself; historical context is for interpretation.",
    # L-08 required pairs (roadmap_literary_clusters.md §L-08)
    # L1 ↔ L6
    ("lit_opoyaz", "lit_bakhtin"): (
        "OPOYAZ (L1) vs Bakhtin (L6): paradigmatic conflict (antipsychologism / "
        "text-as-mechanism vs dialogism / polyphony). Resolution: escalate — "
        "leave the paradigm choice to the author; do not silently prefer one school. "
        "Cite 'OPOYAZ vs Bakhtin: escalate, author decides'."
    ),
    # L5 ↔ L6
    ("lit_narratology", "lit_bakhtin"): (
        "Narratology (L5) vs Bakhtin (L6): category precision vs openness of concepts. "
        "Resolution: escalate — keep narratological terms exact where the text uses them, "
        "but do not impose rigid definitions on Bakhtinian open terms (хронотоп, голос). "
        "Cite 'Narratology vs Bakhtin: escalate'."
    ),
    # L3 ↔ NSS
    ("lit_textology", "ling_nss"): (
        "Textology (L3) vs NSS: archival accuracy vs normative literary standard. "
        "Resolution: lit_textology_wins — manuscript evidence, shelf-marks, dating hedges, "
        "and attribution caveats override normativist 'correctness' edits. "
        "Cite 'Textology > NSS: lit_textology_wins'."
    ),
    # L9 ↔ NSS
    ("lit_poststructural", "ling_nss"): (
        "Poststructural (L9) vs NSS: deconstruction vs literary norm. "
        "Resolution: lit_poststructural_wins — intentional orthography (différance), "
        "wordplay, and anti-normative rhetoric are method, not error; do not 'correct' them. "
        "Cite 'Poststructural > NSS: lit_poststructural_wins'."
    ),
    # L9 ↔ L5
    ("lit_poststructural", "lit_narratology"): (
        "Poststructural (L9) vs Narratology (L5): play / différance vs closed categories. "
        "Resolution: escalate — do not collapse deconstructive play into narratological "
        "labels, and do not erase category precision where the text is narratological. "
        "Cite 'Poststructural vs Narratology: escalate'."
    ),
}


def lookup_conflict_hint(cluster_a: str | None, cluster_b: str | None) -> str | None:
    """Return the resolution hint for a cluster pair, accepting either key order.

    Returns None when either id is missing or the pair is not in CONFLICT_MATRIX.
    """
    if not cluster_a or not cluster_b:
        return None
    if cluster_a == cluster_b:
        return None
    hint = CONFLICT_MATRIX.get((cluster_a, cluster_b))
    if hint is not None:
        return hint
    return CONFLICT_MATRIX.get((cluster_b, cluster_a))

# Per-domain cluster authority (roadmap_critique.md G-04 + roadmap_literary_clusters.md L-03).
#
# `text_domain` -> {cluster_id: multiplier}. The multiplier scales a passport's base
# weight (or its archetype override, which still supplies the base) and is rendered
# into the council prompt as that agent's authority number.
#
# Three rules keep this composable with the mechanisms already in production:
#
# 1. **A row is authoritative.** When a domain appears here, the row is the ONLY
#    domain-derived multiplier applied — the generic `text_domain in cluster.domains`
#    x1.5 boost does not also fire, and the former hardcoded special cases
#    (etymology->ling_iesh x2.0, semiotics->ling_mts x2.0, literature->lit_* x1.2)
#    are folded in as rows rather than stacked on top. So every (domain, cluster)
#    pair has exactly one documented number instead of a product of three.
# 2. **Absent means neutral (1.0).** A row names only the schools whose authority
#    actually shifts in that domain; every other cluster keeps its base weight.
#    Values < 1.0 suppress a school that is methodologically mute in the domain
#    (the normativist on etymology or textology, say) — suppression is the half of
#    the drafted tables the 3-case shortcut could not express at all.
# 3. **No silent re-tuning.** Where a boost already fired today, the row reproduces
#    today's number, so wiring the table is not a covert re-weighting. The two
#    deliberate exceptions are legislated by the roadmaps themselves:
#    `etymology->ling_iesh` becomes 1.5 (was 1.5 x 2.0 = 3.0 by double-count — note
#    the *ratio* to the suppressed ling_nss is 3x either way, so relative authority
#    is unchanged), and `literary_bakhtin->lit_bakhtin` becomes L-03's 1.8 (was 1.5).
#
# A key ending in `*` matches a cluster-id prefix; the longest matching prefix wins,
# and an exact id always beats a prefix. Domains with no row (`unknown`, and the
# `linguistics`/`lexicography` labels the eval suite uses) stay deliberately neutral
# — G-04's `"default": {c: 1.0 for c in ALL_CLUSTERS}` is this absence, not a row.
DOMAIN_CLUSTER_WEIGHTS: dict[str, dict[str, float]] = {
    # --- G-04, docs/roadmap_critique.md Part IV (short ids resolved to real ones) ---
    "etymology": {"ling_iesh": 1.5, "ling_mss": 1.0, "ling_nss": 0.5},
    "functional_grammar": {"ling_pfg": 1.5, "ling_mss": 1.2, "ling_kmsh": 0.7},
    "discourse_analysis": {"ling_kmsh": 1.5, "ling_dss": 1.2, "ling_mss": 0.8},
    # --- L-03, docs/roadmap_literary_clusters.md Part V ---
    "literary_textology": {"lit_textology": 1.8, "lit_structural": 0.8, "ling_nss": 0.3},
    "literary_bakhtin": {
        "lit_bakhtin": 1.8,
        "lit_opoyaz": 0.4,  # conflicting paradigms (see CONFLICT_MATRIX)
        "lit_narratology": 0.5,
        "ling_nss": 0.2,
    },
    "literary_poststructural": {
        "lit_poststructural": 2.0,
        "lit_narratology": 0.5,
        "ling_nss": 0.1,
    },
    # --- coverage for every remaining domain a cluster file declares ---
    # ling_iesh: ["etymology", "historical_linguistics"]
    "historical_linguistics": {"ling_iesh": 1.5, "ling_tsh": 1.2, "ling_nss": 0.5},
    # ling_mss: ["semantics", "grammar"]
    "semantics": {"ling_mss": 1.5, "ling_kmsh": 1.0, "ling_nss": 0.7},
    "grammar": {"ling_mss": 1.5, "ling_pfg": 1.5},  # norm has a real voice here: no suppression
    # indology: ["sanskrit", "indology", "philology"]
    "sanskrit": {"indology": 1.5, "orient_leningrad": 1.2, "ling_iesh": 1.2, "ling_nss": 0.3},
    "indology": {"indology": 1.5, "orient_leningrad": 1.2, "ling_nss": 0.3},
    "philology": {"indology": 1.5, "orient_leningrad": 1.5, "lit_textology": 1.2, "ling_nss": 0.8},
    # orient_leningrad: ["oriental_studies", "history", "philology"]
    "oriental_studies": {"orient_leningrad": 1.5, "indology": 1.2, "ling_nss": 0.3},
    "history": {"orient_leningrad": 1.5, "lit_historico_cultural": 1.3, "ling_nss": 0.5},
    # --- the pre-table special cases, ratios preserved ---
    "semiotics": {"ling_mts": 2.0, "lit_structural": 1.2},
    "literature": {"lit_*": 1.2},
}

# The closed vocabulary for run.json's `text_domain` (mirrored by the enum in
# schemas/run.schema.json and the `--text-domain` CLI choices). Union of every
# DOMAIN_CLUSTER_WEIGHTS row, the extra G-07 domains from docs/roadmap_critique.md
# (typology/normative/dialectology), and the deliberately-unrowed labels the eval
# suite stamps on cases (linguistics/lexicography). A domain listed here without a
# table row above stays neutral (every multiplier 1.0) by rule 2 of the table.
TEXT_DOMAINS: tuple[str, ...] = tuple(sorted(
    set(DOMAIN_CLUSTER_WEIGHTS)
    | {"typology", "normative", "dialectology", "linguistics", "lexicography", "unknown"}
))


def domain_cluster_multiplier(text_domain: str, cluster_id: str | None) -> float:
    """Authority multiplier for one cluster under one text domain (1.0 = neutral)."""
    row = DOMAIN_CLUSTER_WEIGHTS.get(text_domain)
    if not row or not cluster_id:
        return 1.0
    if cluster_id in row:
        return row[cluster_id]
    best_prefix = ""
    multiplier = 1.0
    for key, value in row.items():
        if not key.endswith("*"):
            continue
        prefix = key[:-1]
        if cluster_id.startswith(prefix) and len(prefix) >= len(best_prefix):
            best_prefix, multiplier = prefix, value
    return multiplier


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

    atomic_write_text(
        prompt_path,
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
    )

    atomic_write_json(
        council_path,
        {
                "run_id": run_id,
                "status": "prompt_ready",
                "prompt_path": _repo_relative(repo_root, prompt_path),
                "review_files": [_repo_relative(repo_root, path) for path in review_paths],
                "replies": [],
                "decisions": [],
                "profile": profile,
        },
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

        domains, _location = cluster_meta.get(ref.cluster_id, ((), ""))

        # 2. Methodological authority per domain (DOMAIN_CLUSTER_WEIGHTS, G-04 + L-03).
        #    A table row is authoritative — it replaces the generic domain-match boost
        #    below rather than stacking on it, so a cluster's authority in a domain is
        #    exactly one documented number (and can be < 1.0, i.e. suppressed).
        if text_domain in DOMAIN_CLUSTER_WEIGHTS:
            weight *= domain_cluster_multiplier(text_domain, ref.cluster_id)
        # 3. Generic domain-match boost — fail-open for a cluster file that declares a
        #    domain the table does not cover yet (a new `domains:` entry keeps working).
        elif text_domain != "unknown" and text_domain in domains:
            weight *= 1.5

        # De-regioned (prompt-fidelity review F5): the former location-string boost
        # (Moscow/Leningrad archetype × cluster `location`) multiplied weight by
        # geography regardless of whether a passport's method actually fits its
        # cluster — so a misfiled passport (e.g. an accentologist parked in the
        # Moscow Semantic cluster) drew the wrong regional authority. Deliberate
        # cluster boosting is still available via explicit archetype weights in
        # styles/archetypes.yml, which key on cluster_id, not city.

        # Rounded because the table's sub-1.0 multipliers otherwise render float
        # noise (1.5 * 0.3 -> 0.44999999999999996) straight into the council prompt.
        adjusted_weights[ref.style_id] = round(weight, 4)
        
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
2. **Resolve Conflicts**: If styles suggest different changes for the same span, use your strategy and the `_style_weight` (higher is more authoritative) to decide. **CRITICAL**: If a conflict is listed in the `Philological Conflict Matrix`, you MUST cite that entry's own resolution rule verbatim in your `reason` field (e.g. 'Textology > NSS: lit_textology_wins'). Never invent a school-wins verdict for a pair the matrix resolves as `escalate` — for those, cite the escalate rule (e.g. 'OPOYAZ vs Bakhtin: escalate, author decides') and leave the paradigm choice to the author.
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
