"""Standalone repository validation for RuWritingStyles.

This script uses only the Python standard library. It implements a robust
YAML parser and reuses the internal JSON Schema subset validator to ensure
all configuration files comply with their schemas.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:
    from ruwritingstyles.schema_validation import lint_schema, validate_json_schema
    from ruwritingstyles.yaml_lite import parse_simple_yaml
except ImportError:
    print("FAIL: could not import from ruwritingstyles (schema_validation / yaml_lite)")
    sys.exit(1)


REQUIRED_FILES = [
    "pyproject.toml",
    "README.md",
    "docs/roadmap.md",
    "docs/agent-protocol.md",
    "docs/cli.md",
    "docs/style-contract.md",
    "docs/provider-roadmaps.md",
    "docs/quickstart.md",
    "docs/refactoring-roadmap.md",
    "evals/manifest.json",
    "model_policy.yml",
    "styles/manifest.yml",
    "schemas/style.schema.json",
    "schemas/manifest.schema.json",
    "schemas/model-policy.schema.json",
    "schemas/eval-manifest.schema.json",
    "schemas/migration-summary.schema.json",
    "src/ruwritingstyles/document.py",
    "src/ruwritingstyles/linguistics.py",
    "src/ruwritingstyles/schema_validation.py",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"OK: {message}")


def load_schema_store() -> dict[str, dict[str, Any]]:
    store = {}
    schema_dir = ROOT / "schemas"
    for path in schema_dir.glob("*.json"):
        with path.open("r", encoding="utf-8") as f:
            store[path.name] = json.load(f)
    return store


def check_required_files() -> None:
    for rel in REQUIRED_FILES:
        if not (ROOT / rel).exists():
            fail(f"missing required file: {rel}")
    ok("required files exist")


def validate_file(rel_path: str, schema_name: str, store: dict[str, dict[str, Any]]) -> Any:
    path = ROOT / rel_path
    if not path.exists():
        fail(f"file not found for validation: {rel_path}")

    content = path.read_text(encoding="utf-8")
    if rel_path.endswith(".yml") or rel_path.endswith(".yaml"):
        data = parse_simple_yaml(content)
    else:
        data = json.loads(content)

    schema = store.get(schema_name)
    if not schema:
        fail(f"schema not found in store: {schema_name}")

    errors = validate_json_schema(data, schema, schema_store=store)
    if errors:
        print(f"Validation errors in {rel_path}:")
        for err in errors:
            print(f"  {err}")
        # print(f"  Parsed data: {json.dumps(data, indent=2, ensure_ascii=False)}")
        fail(f"validation failed for {rel_path} against {schema_name}")

    return data


def _bibliography_ids() -> set:
    data = json.loads((ROOT / "knowledge" / "bibliography.json").read_text(encoding="utf-8"))
    return {entry.get("id") for entry in data if isinstance(entry, dict)}


def _has_cyrillic(text: str) -> bool:
    return any("Ѐ" <= ch <= "ӿ" for ch in text)


def check_cross_references(manifest_data: dict[str, Any]) -> list[str]:
    """Bibliography-id references that must resolve (not enforced by schemas).

    (a) passport `provenance.sources` that look like a bibliography id
        (Latin, contains a 4-digit year) must exist in knowledge/bibliography.json;
        free-form Cyrillic citations are exempt.
    (b) every knowledge/sanskrit-terms.json `source` must be a bibliography id.

    (Eval `required_finding_types` are intentionally NOT constrained to passport
    `checks` — that vocabulary is looser, guided by the prose prompt — so it is
    not checked here.)
    """
    bib_ids = _bibliography_ids()
    errors: list[str] = []

    for ref in manifest_data.get("passports", []):
        path = ROOT / ref["path"]
        data = parse_simple_yaml(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        sources = (data.get("provenance") or {}).get("sources") or []
        for source in sources:
            if isinstance(source, str) and not _has_cyrillic(source) and re.search(r"\b\d{4}\b", source):
                if source not in bib_ids:
                    errors.append(f"passport {ref['id']}: provenance source {source!r} not in knowledge/bibliography.json")

    terms = json.loads((ROOT / "knowledge" / "sanskrit-terms.json").read_text(encoding="utf-8"))
    for term in terms:
        source = term.get("source")
        if source and source not in bib_ids:
            errors.append(f"sanskrit-terms {term.get('ru')!r}: source {source!r} not in knowledge/bibliography.json")

    return errors


def main() -> int:
    print(f"Validating RuWritingStyles repository at {ROOT}")

    check_required_files()
    store = load_schema_store()
    ok("loaded JSON schemas")

    keyword_errors = []
    for name, schema in sorted(store.items()):
        for message in lint_schema(schema):
            keyword_errors.append(f"{name} {message}")
    if keyword_errors:
        for err in keyword_errors:
            print(f"  {err}")
        fail("schemas use unsupported keywords (extend schema_validation.py or remove them)")
    ok("schemas use only supported keywords")

    manifest_data = validate_file("styles/manifest.yml", "manifest.schema.json", store)
    ok("styles/manifest.yml is valid")

    for passport_ref in manifest_data.get("passports", []):
        path = passport_ref.get("path")
        if path:
            validate_file(path, "style.schema.json", store)
            source = passport_ref.get("source_prompt")
            if source and not (ROOT / source).exists():
                fail(f"passport {path} references missing source_prompt {source}")
    ok("all style passports are valid and resolve")

    validate_file("model_policy.yml", "model-policy.schema.json", store)
    ok("model_policy.yml is valid")

    validate_file("evals/manifest.json", "eval-manifest.schema.json", store)
    ok("evals/manifest.json is valid")

    validate_file("knowledge/bibliography.json", "bibliography.schema.json", store)
    ok("knowledge/bibliography.json is valid")

    validate_file("knowledge/sanskrit-terms.json", "sanskrit-terms.schema.json", store)
    ok("knowledge/sanskrit-terms.json is valid")

    cross_ref_errors = check_cross_references(manifest_data)
    if cross_ref_errors:
        for err in cross_ref_errors:
            print(f"  {err}")
        fail("data cross-references do not resolve")
    ok("bibliography cross-references resolve (provenance + sanskrit-terms)")

    journals_dir = ROOT / "knowledge" / "journals"
    if journals_dir.exists():
        for preset in sorted(journals_dir.glob("*.json")):
            validate_file(preset.relative_to(ROOT).as_posix(), "journal-profile.schema.json", store)
        ok("knowledge/journals/*.json are valid")

    example_context = "examples/input/.rws-project/project-context.json"
    if (ROOT / example_context).exists():
        validate_file(example_context, "project-context.schema.json", store)
        ok(f"{example_context} is valid")

    claude_sources = {p.relative_to(ROOT).as_posix() for p in (ROOT / "ClaudeStyles").glob("*.md")}
    passport_sources = {p.get("source_prompt") for p in manifest_data.get("passports", [])}

    if claude_sources != passport_sources:
        missing = sorted(claude_sources - passport_sources)
        extra = sorted(passport_sources - claude_sources)
        if missing:
            print(f"  Missing passports for: {', '.join(missing)}")
        if extra:
            print(f"  Passports reference unknown sources: {', '.join(extra)}")
        fail("ClaudeStyles and manifest passports are out of sync")
    ok("ClaudeStyles and manifest passports are in sync")

    print("\nSUCCESS: Repository validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
