"""The single zero-dependency YAML-subset parser for RuWritingStyles.

Both the runtime config loader (`config.py`) and the CI validator
(`tools/validate_project.py`) import from here, so they cannot disagree on how
the human-editable `*.yml` files are read. The repository intentionally has no
runtime YAML dependency; this covers only the small subset the project uses.

Two views over the same subset live together and share `parse_scalar`:

- `parse_simple_yaml(text)` — generic text -> nested dict/list parse.
- `scalar` / `block` / `list_items` — targeted field extraction used by the
  structured config loaders.

Both tolerate a ``:`` inside a quoted scalar (e.g. a passport `name:` whose
value contains a colon) — the case that previously parsed fine at runtime but
was rejected by the CI validator.
"""

from __future__ import annotations

import re
from typing import Any


def parse_scalar(val: str) -> Any:
    val = val.strip()
    if not val:
        return None
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() == "null" or val == "~":
        return None
    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
        return val[1:-1]
    try:
        if "." in val:
            return float(val)
        return int(val)
    except ValueError:
        return val


def _kv_colon(content: str) -> int:
    """Index of the first ``key: value`` separator colon, or -1.

    A separator colon is not inside quotes and is followed by whitespace or the
    end of the line — so a ``:`` inside ``"a: b"`` is not treated as one."""
    quote: str | None = None
    for i, ch in enumerate(content):
        if quote is not None:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == ":" and (i + 1 == len(content) or content[i + 1] in " \t"):
            return i
    return -1


def parse_simple_yaml(text: str) -> Any:
    """Parse the RuWritingStyles YAML subset into nested dicts/lists."""

    # 1. Lexing
    tokens: list[tuple[int, str, Any]] = []
    for line in text.splitlines():
        if "#" in line:
            line = line[: line.find("#")]
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip())
        content = line.lstrip()

        if content.startswith("- "):
            tokens.append((indent, "LIST_ITEM", None))
            content = content[2:].strip()
            indent += 1  # Virtual indent for same-line content
            if not content:
                continue

        colon = _kv_colon(content)
        if colon != -1:
            key = content[:colon]
            val = content[colon + 1:]
            tokens.append((indent, "KEY", key.strip()))
            val = val.strip()
            if val:
                tokens.append((indent + 1, "VALUE", parse_scalar(val)))
        else:
            tokens.append((indent, "VALUE", parse_scalar(content)))

    # 2. Parsing tokens into a tree
    def build_tree(start_idx: int, min_indent: int) -> tuple[Any, int]:
        if start_idx >= len(tokens):
            return None, 0

        _first_indent, first_type, _ = tokens[start_idx]

        if first_type == "LIST_ITEM":
            res_list: list[Any] = []
            i = start_idx
            while i < len(tokens):
                indent, ttype, _val = tokens[i]
                if indent < min_indent:
                    break
                if ttype == "LIST_ITEM":
                    if i + 1 < len(tokens):
                        ni, _nt, _nv = tokens[i + 1]
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

        if first_type == "KEY":
            res_dict: dict[str, Any] = {}
            i = start_idx
            while i < len(tokens):
                indent, ttype, key = tokens[i]
                if indent < min_indent:
                    break
                if ttype == "KEY":
                    if i + 1 < len(tokens):
                        ni, nt, nv = tokens[i + 1]
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

        if first_type == "VALUE":
            return tokens[start_idx][2], 1

        return None, 1

    tree, _ = build_tree(0, -1)
    return tree


def scalar(text: str, key: str, default: str = "") -> str:
    match = re.search(
        rf"^\s*{re.escape(key)}:\s*['\"]?([^'\"\n]+?)['\"]?\s*$", text, re.MULTILINE
    )
    return match.group(1).strip() if match else default


def block(text: str, key: str) -> str:
    match = re.search(
        rf"^{re.escape(key)}:\s*\n(?P<body>(?:^[ \t].*\n?)*)", text, re.MULTILINE
    )
    return match.group("body") if match else ""


def list_items(text_block: str) -> tuple[str, ...]:
    items: list[str] = []
    for line in text_block.splitlines():
        match = re.match(r"^\s*-\s+['\"]?([^'\"\n]+?)['\"]?\s*$", line)
        if match:
            items.append(match.group(1).strip())
    return tuple(items)
