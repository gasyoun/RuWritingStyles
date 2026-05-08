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
    from ruwritingstyles.schema_validation import validate_json_schema
except ImportError:
    print("FAIL: could not import ruwritingstyles.schema_validation from src")
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
    "src/ruwritingstyles/document.py",
    "src/ruwritingstyles/linguistics.py",
    "src/ruwritingstyles/schema_validation.py",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    sys.exit(1)


def ok(message: str) -> None:
    print(f"OK: {message}")


def parse_simple_yaml(text: str) -> Any:
    """A robust zero-dependency YAML parser for the RuWritingStyles subset."""

    # 1. Lexing
    tokens = []
    for line in text.splitlines():
        if "#" in line: line = line[:line.find("#")]
        if not line.strip(): continue

        indent = len(line) - len(line.lstrip())
        content = line.lstrip()

        if content.startswith("- "):
            tokens.append((indent, "LIST_ITEM", None))
            content = content[2:].strip()
            indent += 1 # Virtual indent for same-line content
            if not content: continue

        if ":" in content:
            key, val = content.split(":", 1)
            tokens.append((indent, "KEY", key.strip()))
            val = val.strip()
            if val:
                tokens.append((indent + 1, "VALUE", _parse_scalar(val)))
        else:
            tokens.append((indent, "VALUE", _parse_scalar(content)))

    # 2. Parsing tokens into tree
    def build_tree(start_idx: int, min_indent: int) -> tuple[Any, int]:
        if start_idx >= len(tokens):
            return None, 0

        first_indent, first_type, _ = tokens[start_idx]

        if first_type == "LIST_ITEM":
            res_list = []
            i = start_idx
            while i < len(tokens):
                indent, type, val = tokens[i]
                if indent < min_indent: break

                if type == "LIST_ITEM":
                    if i + 1 < len(tokens):
                        ni, nt, nv = tokens[i+1]
                        if ni > indent:
                            nested, consumed = build_tree(i + 1, indent)
                            res_list.append(nested)
                            i += 1 + consumed
                        else:
                            res_list.append(None)
                            i += 1
                    else:
                        res_list.append(None)
                        i += 1
                else:
                    break
            return res_list, i - start_idx

        elif first_type == "KEY":
            res_dict = {}
            i = start_idx
            while i < len(tokens):
                indent, type, key = tokens[i]
                if indent < min_indent: break

                if type == "KEY":
                    if i + 1 < len(tokens):
                        ni, nt, nv = tokens[i+1]
                        if nt == "VALUE" and ni > indent:
                            res_dict[key] = nv
                            i += 2
                        elif ni > indent:
                            nested, consumed = build_tree(i + 1, indent + 1)
                            res_dict[key] = nested
                            i += 1 + consumed
                        else:
                            res_dict[key] = None
                            i += 1
                    else:
                        res_dict[key] = None
                        i += 1
                else:
                    break
            return res_dict, i - start_idx

        elif first_type == "VALUE":
            return tokens[start_idx][2], 1

        else:
            return None, 1

    tree, _ = build_tree(0, -1)
    return tree


def _parse_scalar(val: str) -> Any:
    val = val.strip()
    if not val: return None
    if val.lower() == "true": return True
    if val.lower() == "false": return False
    if val.lower() == "null" or val == "~": return None
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    try:
        if "." in val: return float(val)
        return int(val)
    except ValueError:
        return val


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


def main() -> int:
    print(f"Validating RuWritingStyles repository at {ROOT}")

    check_required_files()
    store = load_schema_store()
    ok("loaded JSON schemas")

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
