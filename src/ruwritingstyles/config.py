"""Configuration loaders for the first RuWritingStyles CLI layer.

The repository currently keeps human-editable YAML files but intentionally has
no runtime dependencies. These loaders parse only the small subset of YAML used
by `styles/manifest.yml` and `model_policy.yml`; a full YAML/JSON Schema layer
is planned in the roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any

from .yaml_lite import (
    scalar as _scalar,
    block as _block,
    list_items as _list_items,
    parse_simple_yaml,
)


@dataclass(frozen=True)
class StylePassportRef:
    """A style passport entry from `styles/manifest.yml`."""

    style_id: str
    path: Path
    source_prompt: Path
    cluster_id: str | None = None
    weight: float = 1.0


@dataclass(frozen=True)
class ClusterConfig:
    """A stylistic cluster (school)."""
    id: str
    path: Path
    name: str
    domains: tuple[str, ...] = ()
    location: str = ""


@dataclass(frozen=True)
class CouncilArchetype:
    """A specific council personality."""
    id: str
    name: str
    description: str
    instructions: str
    weights: dict[str, float]


@dataclass(frozen=True)
class CouncilConfig:
    """Council deliberation strategies."""

    archetype: str
    conflict_resolution_strategy: str


@dataclass(frozen=True)
class Manifest:
    """Machine-readable style index needed by the CLI."""

    path: Path
    mvp_style_ids: tuple[str, ...]
    clusters: tuple[ClusterConfig, ...]
    passports: tuple[StylePassportRef, ...]
    council: CouncilConfig | None = None
    councils: tuple[tuple[str, tuple[str, ...]], ...] = ()

    def council_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.councils)

    def resolve_council(self, name: str) -> tuple[str, ...]:
        """Style ids for a named council, or () if the name is unknown."""
        for council_name, style_ids in self.councils:
            if council_name == name:
                return style_ids
        return ()


@dataclass(frozen=True)
class ModelPolicy:
    """Minimal model policy view used by the CLI report."""

    path: Path
    default_provider: str
    default_model: str
    default_reasoning: str
    default_speed: str
    routes: tuple[ModelRoute, ...] = ()
    budget_modes: tuple["BudgetMode", ...] = ()

    def resolve_model(self, task: str, provider_name: str) -> str:
        """Resolve the best model for a specific task and provider."""
        for route in self.routes:
            if route.provider == provider_name and route.task == task:
                return route.model
        return self.default_model

    def resolve_budget(self, name: str) -> "BudgetMode":
        for mode in self.budget_modes:
            if mode.name == name:
                return mode
        available = ", ".join(mode.name for mode in self.budget_modes)
        raise ValueError(f"unknown budget mode {name!r}; available: {available}")


@dataclass(frozen=True)
class BudgetMode:
    name: str
    providers: tuple[str, ...]
    max_outbound_attempts: int
    max_tokens: int
    max_wall_seconds: int
    explicit_selection_required: bool = False


@dataclass(frozen=True)
class ModelRoute:
    """One provider/task route from model_policy.yml."""

    provider: str
    task: str
    model: str
    mode_name: str
    mode_value: str


@dataclass(frozen=True)
class StylePassportSummary:
    """A compact view of a style passport for CLI listing."""

    style_id: str
    name: str
    role: str
    source_prompt: Path
    passport_path: Path
    is_mvp: bool


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_manifest(repo_root: Path) -> Manifest:
    path = repo_root / "styles" / "manifest.yml"
    text = _read(path)

    mvp_style_ids = _list_items(_block(text, "mvp_style_ids"))

    # Named councils: a nested map of council-name -> [style ids]. Parsed with
    # the generic subset parser (handles the dict-of-lists shape the targeted
    # _block/_list_items helpers do not).
    councils: list[tuple[str, tuple[str, ...]]] = []
    councils_block = _block(text, "councils")
    if councils_block:
        parsed = parse_simple_yaml(councils_block)
        if isinstance(parsed, dict):
            for name, ids in parsed.items():
                if isinstance(ids, list):
                    councils.append((str(name), tuple(str(i) for i in ids if i)))

    clusters_block = _block(text, "clusters")
    clusters: list[ClusterConfig] = []
    current_cluster: dict[str, str] = {}
    for line in clusters_block.splitlines():
        item_match = re.match(r"^\s*-\s+id:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", line)
        field_match = re.match(r"^\s+(path|name|location):\s*['\"]?([^'\"\n]+?)['\"]?\s*$", line)
        if item_match:
            if current_cluster:
                clusters.append(_cluster_config(repo_root, current_cluster))
            current_cluster = {"id": item_match.group(1).strip()}
        elif field_match and current_cluster:
            current_cluster[field_match.group(1)] = field_match.group(2).strip()
    if current_cluster:
        clusters.append(_cluster_config(repo_root, current_cluster))

    passports_block = _block(text, "passports")
    entries: list[StylePassportRef] = []
    current: dict[str, str] = {}

    for line in passports_block.splitlines():
        item_match = re.match(r"^\s*-\s+id:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", line)
        field_match = re.match(r"^\s+(path|source_prompt|cluster|level):\s*['\"]?([^'\"\n]+?)['\"]?\s*$", line)

        if item_match:
            if current:
                entries.append(_passport_ref(repo_root, current))
            current = {"id": item_match.group(1).strip()}
        elif field_match and current:
            current[field_match.group(1)] = field_match.group(2).strip()
        elif current:
            weight_match = re.match(r"^\s+weight:\s*([0-9.]+)\s*$", line)
            if weight_match:
                current["weight"] = weight_match.group(1)

    if current:
        entries.append(_passport_ref(repo_root, current))

    council_block = _block(text, "council")
    council = None
    if council_block:
        council = CouncilConfig(
            archetype=_scalar(council_block, "archetype", "The Coordinator"),
            conflict_resolution_strategy=_scalar(
                council_block, "conflict_resolution_strategy", "Neutral deliberation."
            ),
        )

    return Manifest(
        path=path,
        mvp_style_ids=mvp_style_ids,
        clusters=tuple(clusters),
        passports=tuple(entries),
        council=council,
        councils=tuple(councils),
    )


def _cluster_config(repo_root: Path, data: dict[str, str]) -> ClusterConfig:
    path = repo_root / data["path"]
    text = _read(path)
    domains_match = re.search(r"^domains:\s*\[(.*?)\]", text, re.MULTILINE)
    domains = ()
    if domains_match:
        domains = tuple(d.strip().strip("'\"") for d in domains_match.group(1).split(",") if d.strip())
    
    return ClusterConfig(
        id=data["id"],
        path=path,
        name=data.get("name", data["id"]),
        domains=domains,
        location=data.get("location", ""),
    )


def _passport_ref(repo_root: Path, data: dict[str, str]) -> StylePassportRef:
    missing = {"id", "path", "source_prompt"} - data.keys()
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"incomplete manifest passport entry; missing {missing_str}")
    path = repo_root / data["path"]
    source_prompt = repo_root / data["source_prompt"]
    cluster_id = data.get("cluster")
    if not cluster_id and data.get("level") == "cluster":
        cluster_id = data["id"]
        
    return StylePassportRef(
        style_id=data["id"],
        path=path,
        source_prompt=source_prompt,
        cluster_id=cluster_id,
        weight=float(data.get("weight", "1.0")),
    )


def load_model_policy(repo_root: Path) -> ModelPolicy:
    path = repo_root / "model_policy.yml"
    text = _read(path)
    default_block = _block(text, "default_development_mode")

    parsed = parse_simple_yaml(text)
    raw_modes = parsed.get("budget_modes", {}) if isinstance(parsed, dict) else {}
    budget_modes: list[BudgetMode] = []
    if isinstance(raw_modes, dict):
        for name, value in raw_modes.items():
            if not isinstance(value, dict):
                continue
            providers = value.get("providers", [])
            budget_modes.append(BudgetMode(
                name=str(name),
                providers=tuple(str(item) for item in providers) if isinstance(providers, list) else (),
                max_outbound_attempts=int(value.get("max_outbound_attempts", 0)),
                max_tokens=int(value.get("max_tokens", 0)),
                max_wall_seconds=int(value.get("max_wall_seconds", 0)),
                explicit_selection_required=bool(value.get("explicit_selection_required", False)),
            ))

    return ModelPolicy(
        path=path,
        default_provider=_scalar(text, "default_provider", "openai"),
        default_model=_scalar(default_block, "model", "gpt-5.5"),
        default_reasoning=_scalar(default_block, "reasoning", "xhigh"),
        default_speed=_scalar(default_block, "speed", "standard"),
        routes=load_model_routes(repo_root),
        budget_modes=tuple(budget_modes),
    )


def load_model_routes(repo_root: Path) -> tuple[ModelRoute, ...]:
    path = repo_root / "model_policy.yml"
    routes: list[ModelRoute] = []
    provider = ""
    in_routes = False
    task = ""
    fields: dict[str, str] = {}

    def flush() -> None:
        if provider and task and fields.get("model"):
            mode_name = "reasoning" if fields.get("reasoning") else "thinking"
            routes.append(
                ModelRoute(
                    provider=provider,
                    task=task,
                    model=str(fields["model"]),
                    mode_name=mode_name,
                    mode_value=str(fields.get(mode_name) or ""),
                )
            )

    for line in _read(path).splitlines():
        # Any two-space-indented key can open a provider block; only blocks that
        # actually contain task_routes emit routes. A hardcoded alternation here
        # silently dropped deepseek's routes (fixed 07-07-2026): resolve_model then
        # fell back to default_model (gpt-5.5), which the DeepSeek API rejects.
        provider_match = re.match(r"^\s{2}([a-z][a-z0-9_-]*):\s*$", line)
        task_routes_match = re.match(r"^\s{4}task_routes:\s*$", line)
        task_match = re.match(r"^\s{6}([a-z_]+):\s*$", line)
        field_match = re.match(r"^\s{8}(model|reasoning|thinking):\s*['\"]?([^'\"\n]+?)['\"]?\s*$", line)

        if provider_match:
            flush()
            provider = provider_match.group(1)
            in_routes = False
            task = ""
            fields = {}
            continue
        if task_routes_match and provider:
            flush()
            in_routes = True
            task = ""
            fields = {}
            continue
        if in_routes and task_match:
            flush()
            task = task_match.group(1)
            fields = {}
            continue
        if in_routes and field_match and task:
            fields[field_match.group(1)] = field_match.group(2).strip()

    flush()
    return tuple(routes)


def load_archetypes(repo_root: Path) -> tuple[CouncilArchetype, ...]:
    path = repo_root / "styles" / "archetypes.yml"
    if not path.exists():
        return ()
    text = _read(path)
    
    archetypes: list[CouncilArchetype] = []
    # Simplified parser for the archetypes block
    lines = text.splitlines()
    current: dict[Any, Any] = {}
    
    i = 0
    while i < len(lines):
        line = lines[i]
        id_match = re.match(r"^\s*-\s+id:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", line)
        if id_match:
            if current: archetypes.append(CouncilArchetype(**current))
            current = {"id": id_match.group(1).strip(), "weights": {}}
            i += 1
            while i < len(lines) and not re.match(r"^\s*-\s+id:", lines[i]):
                l = lines[i]
                name_m = re.match(r"^\s+name:\s*(.*)$", l)
                desc_m = re.match(r"^\s+description:\s*(.*)$", l)
                inst_m = re.match(r"^\s+instructions:\s*\|\s*$", l)
                wght_m = re.match(r"^\s+weights:\s*$", l)
                
                if name_m: current["name"] = name_m.group(1).strip().strip("'\"")
                elif desc_m: current["description"] = desc_m.group(1).strip().strip("'\"")
                elif inst_m:
                    i += 1
                    inst_lines = []
                    while i < len(lines) and (lines[i].startswith("      ") or lines[i].strip() == ""):
                        inst_lines.append(lines[i][6:])
                        i += 1
                    current["instructions"] = "\n".join(inst_lines)
                    continue
                elif wght_m:
                    i += 1
                    while i < len(lines) and re.match(r"^\s{6}([a-z0-9_-]+):", lines[i]):
                        wm = re.match(r"^\s{6}([a-z0-9_-]+):\s*([0-9.]+)\s*$", lines[i])
                        if wm: current["weights"][wm.group(1)] = float(wm.group(2))
                        i += 1
                    continue
                i += 1
            continue
        i += 1
                
    if current:
        archetypes.append(CouncilArchetype(**current))
        
    return tuple(archetypes)


def _load_passport_file(path: Path) -> dict[str, Any]:
    data = parse_simple_yaml(_read(path))
    if not isinstance(data, dict):
        raise ValueError(f"malformed style passport {path}: expected a YAML object")
    declared_id = data.get("id")
    if not isinstance(declared_id, str) or not declared_id.strip():
        raise ValueError(f"malformed style passport {path}: missing non-empty 'id'")
    return data


def load_passport_by_id(
    repo_root: Path,
    style_id: str,
    manifest: Manifest | None = None,
) -> dict[str, Any] | None:
    """Resolve a public style ID through the manifest and strictly parse its file.

    Cluster passports deliberately declare IDs such as ``cluster:indology`` but
    are exposed as ``indology`` by the manifest, so the manifest mapping—not the
    file's internal ID—is the canonical runtime lookup.
    """
    manifest_path = repo_root / "styles" / "manifest.yml"
    if manifest is None and not manifest_path.exists():
        return None
    actual_manifest = manifest or load_manifest(repo_root)
    for ref in actual_manifest.passports:
        if ref.style_id == style_id:
            return _load_passport_file(ref.path)
    return None


def load_passport_dicts(repo_root: Path) -> list[dict[str, Any]]:
    """Parsed passport dicts from `styles/passports/*.yml`, sorted by filename.

    The raw-dict view of every passport, for tooling that needs fields beyond the
    user-facing summary (checks, best_for, provenance, ...). One loader so the
    glob+parse is not re-implemented per tool."""
    passports_dir = repo_root / "styles" / "passports"
    return [_load_passport_file(path) for path in sorted(passports_dir.glob("*.yml"))]


def load_passport_summaries(repo_root: Path, manifest: Manifest | None = None) -> tuple[StylePassportSummary, ...]:
    actual_manifest = manifest or load_manifest(repo_root)
    summaries: list[StylePassportSummary] = []
    mvp_ids = set(actual_manifest.mvp_style_ids)

    for ref in actual_manifest.passports:
        text = _read(ref.path)
        summaries.append(
            StylePassportSummary(
                style_id=ref.style_id,
                name=_scalar(text, "name", ref.style_id),
                role=_scalar(text, "role", "unknown"),
                source_prompt=ref.source_prompt,
                passport_path=ref.path,
                is_mvp=ref.style_id in mvp_ids,
            )
        )

    return tuple(summaries)


def load_run_metadata(run_dir: Path) -> dict[str, Any]:
    """Load run metadata from run.json or metadata.json in the run directory."""
    for filename in ("run.json", "metadata.json"):
        path = run_dir / filename
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
    return {"text_domain": "unknown"}


def repo_root_from(start: Path | None = None) -> Path:
    """Resolve an installed workspace or a backwards-compatible checkout."""

    from .workspace import find_workspace

    return find_workspace(start)
