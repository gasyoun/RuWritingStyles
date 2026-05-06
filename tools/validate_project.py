"""Lightweight repository validation for RuWritingStyles.

This script intentionally uses only the Python standard library. It is not a
full YAML validator; it checks the project invariants that matter before the
proper CLI and schema validation layer exist.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


REQUIRED_FILES = [
    "pyproject.toml",
    "README.md",
    "docs/roadmap.md",
    "docs/agent-protocol.md",
    "docs/cli.md",
    "docs/style-contract.md",
    "docs/provider-roadmaps.md",
    "model_policy.yml",
    "styles/manifest.yml",
    "schemas/style.schema.json",
    "schemas/finding.schema.json",
    "schemas/council.schema.json",
    "schemas/council-output.schema.json",
    "schemas/model-policy.schema.json",
    "schemas/review.schema.json",
    "schemas/review-output.schema.json",
    "schemas/revision.schema.json",
    "schemas/revision-output.schema.json",
    "schemas/verification.schema.json",
    "schemas/verification-output.schema.json",
    "src/ruwritingstyles/__init__.py",
    "src/ruwritingstyles/cli.py",
    "src/ruwritingstyles/config.py",
    "src/ruwritingstyles/council.py",
    "src/ruwritingstyles/execution.py",
    "src/ruwritingstyles/providers.py",
    "src/ruwritingstyles/review.py",
    "src/ruwritingstyles/revision.py",
    "src/ruwritingstyles/runs.py",
    "src/ruwritingstyles/segment.py",
    "src/ruwritingstyles/validation.py",
    "src/ruwritingstyles/verification.py",
    "tests/test_cli_pipeline.py",
]


def fail(message: str) -> None:
    print(f"FAIL {message}")
    raise SystemExit(1)


def ok(message: str) -> None:
    print(f"OK {message}")


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def check_required_files() -> None:
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        if not path.exists():
            fail(f"missing {relative}")
    ok("required files exist")


def check_json_schemas() -> None:
    for path in sorted((ROOT / "schemas").glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            json.load(handle)
    ok("JSON schemas parse")


def extract_yaml_scalar_paths(text: str, key: str) -> list[str]:
    pattern = re.compile(rf"^\s*{re.escape(key)}:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", re.MULTILINE)
    return [match.group(1).strip() for match in pattern.finditer(text)]


def check_style_paths() -> None:
    manifest = read_text(ROOT / "styles" / "manifest.yml")
    passport_paths = extract_yaml_scalar_paths(manifest, "path")

    for relative in passport_paths:
        if not (ROOT / relative).exists():
            fail(f"manifest references missing passport {relative}")

    source_prompts = extract_yaml_scalar_paths(manifest, "source_prompt")
    for passport in sorted((ROOT / "styles" / "passports").glob("*.yml")):
        source_prompts.extend(extract_yaml_scalar_paths(read_text(passport), "source_prompt"))

    for relative in sorted(set(source_prompts)):
        if not (ROOT / relative).exists():
            fail(f"missing source prompt {relative}")

    claude_sources = {path.relative_to(ROOT).as_posix() for path in (ROOT / "ClaudeStyles").glob("*.md")}
    passport_sources = set()
    for passport in sorted((ROOT / "styles" / "passports").glob("*.yml")):
        passport_sources.update(extract_yaml_scalar_paths(read_text(passport), "source_prompt"))

    if claude_sources != passport_sources:
        missing = sorted(claude_sources - passport_sources)
        extra = sorted(passport_sources - claude_sources)
        if missing:
            fail(f"missing passports for source prompts: {', '.join(missing)}")
        if extra:
            fail(f"passports reference unknown source prompts: {', '.join(extra)}")

    if len(passport_paths) != len(claude_sources):
        fail(f"manifest passport count {len(passport_paths)} does not match ClaudeStyles count {len(claude_sources)}")

    ok("style manifest and passport paths resolve")


def check_model_policy() -> None:
    policy = read_text(ROOT / "model_policy.yml")
    for provider in ["openai", "google", "anthropic"]:
        if not re.search(rf"^\s{{2}}{provider}:\s*$", policy, re.MULTILINE):
            fail(f"model_policy.yml missing provider {provider}")

    for model_id in [
        "gpt-5.5",
        "gpt-5.4-mini",
        "gemini-3.1-pro-preview",
        "gemini-3.1-pro-preview-customtools",
        "claude-sonnet-4-6",
    ]:
        if model_id not in policy:
            fail(f"model_policy.yml missing model {model_id}")

    ok("model policy contains required providers and model ids")


def check_pyproject() -> None:
    pyproject = read_text(ROOT / "pyproject.toml")
    for expected in [
        'name = "ruwritingstyles"',
        'rws = "ruwritingstyles.cli:main"',
        'where = ["src"]',
    ]:
        if expected not in pyproject:
            fail(f"pyproject.toml missing {expected}")
    ok("pyproject exposes rws CLI")


def main() -> int:
    check_required_files()
    check_json_schemas()
    check_style_paths()
    check_model_policy()
    check_pyproject()
    ok("repository validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
