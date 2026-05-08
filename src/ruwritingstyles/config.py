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


@dataclass(frozen=True)
class ModelPolicy:
    """Minimal model policy view used by the CLI report."""

    path: Path
    default_provider: str
    default_model: str
    default_reasoning: str
    default_speed: str
    routes: tuple[ModelRoute, ...] = ()

    def resolve_model(self, task: str, provider_name: str) -> str:
        """Resolve the best model for a specific task and provider."""
        for route in self.routes:
            if route.provider == provider_name and route.task == task:
                return route.model
        return self.default_model


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


def _scalar(text: str, key: str, default: str = "") -> str:
    match = re.search(rf"^\s*{re.escape(key)}:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else default


def _block(text: str, key: str) -> str:
    match = re.search(rf"^{re.escape(key)}:\s*\n(?P<body>(?:^[ \t].*\n?)*)", text, re.MULTILINE)
    return match.group("body") if match else ""


def _list_items(block: str) -> tuple[str, ...]:
    items: list[str] = []
    for line in block.splitlines():
        match = re.match(r"^\s*-\s+['\"]?([^'\"\n]+?)['\"]?\s*$", line)
        if match:
            items.append(match.group(1).strip())
    return tuple(items)


def load_manifest(repo_root: Path) -> Manifest:
    path = repo_root / "styles" / "manifest.yml"
    text = _read(path)

    mvp_style_ids = _list_items(_block(text, "mvp_style_ids"))
    
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
        council=council
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

    return ModelPolicy(
        path=path,
        default_provider=_scalar(text, "default_provider", "openai"),
        default_model=_scalar(default_block, "model", "gpt-5.5"),
        default_reasoning=_scalar(default_block, "reasoning", "xhigh"),
        default_speed=_scalar(default_block, "speed", "standard"),
        routes=load_model_routes(repo_root),
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
        provider_match = re.match(r"^\s{2}(openai|google|anthropic|openrouter):\s*$", line)
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
    """Find the repository root by walking upward from `start`."""

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "README.md").exists() and (candidate / "ClaudeStyles").exists():
            return candidate
    raise FileNotFoundError("could not find RuWritingStyles repository root")
