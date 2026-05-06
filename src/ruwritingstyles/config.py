"""Configuration loaders for the first RuWritingStyles CLI layer.

The repository currently keeps human-editable YAML files but intentionally has
no runtime dependencies. These loaders parse only the small subset of YAML used
by `styles/manifest.yml` and `model_policy.yml`; a full YAML/JSON Schema layer
is planned in the roadmap.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path


@dataclass(frozen=True)
class StylePassportRef:
    """A style passport entry from `styles/manifest.yml`."""

    style_id: str
    path: Path
    source_prompt: Path


@dataclass(frozen=True)
class Manifest:
    """Machine-readable style index needed by the CLI."""

    path: Path
    mvp_style_ids: tuple[str, ...]
    passports: tuple[StylePassportRef, ...]


@dataclass(frozen=True)
class ModelPolicy:
    """Minimal model policy view used by the CLI report."""

    path: Path
    default_provider: str
    default_model: str
    default_reasoning: str
    default_speed: str


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
    passports_block = _block(text, "passports")
    entries: list[StylePassportRef] = []
    current: dict[str, str] = {}

    for line in passports_block.splitlines():
        item_match = re.match(r"^\s*-\s+id:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", line)
        field_match = re.match(r"^\s+(path|source_prompt):\s*['\"]?([^'\"\n]+?)['\"]?\s*$", line)

        if item_match:
            if current:
                entries.append(_passport_ref(repo_root, current))
            current = {"id": item_match.group(1).strip()}
        elif field_match and current:
            current[field_match.group(1)] = field_match.group(2).strip()

    if current:
        entries.append(_passport_ref(repo_root, current))

    return Manifest(path=path, mvp_style_ids=mvp_style_ids, passports=tuple(entries))


def _passport_ref(repo_root: Path, data: dict[str, str]) -> StylePassportRef:
    missing = {"id", "path", "source_prompt"} - data.keys()
    if missing:
        missing_str = ", ".join(sorted(missing))
        raise ValueError(f"incomplete manifest passport entry; missing {missing_str}")
    return StylePassportRef(
        style_id=data["id"],
        path=repo_root / data["path"],
        source_prompt=repo_root / data["source_prompt"],
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
    )


def repo_root_from(start: Path | None = None) -> Path:
    """Find the repository root by walking upward from `start`."""

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "README.md").exists() and (candidate / "ClaudeStyles").exists():
            return candidate
    raise FileNotFoundError("could not find RuWritingStyles repository root")
