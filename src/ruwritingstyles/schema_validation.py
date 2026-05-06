"""Small dependency-free JSON Schema subset validator."""

from __future__ import annotations

import re
from typing import Any


def validate_json_schema(
    data: Any,
    schema: dict[str, Any],
    *,
    schema_store: dict[str, dict[str, Any]] | None = None,
) -> tuple[str, ...]:
    """Validate data against the JSON Schema subset used by this repository."""

    messages: list[str] = []
    _validate(data, schema, "$", schema_store or {}, messages)
    return tuple(messages)


def _validate(
    data: Any,
    schema: dict[str, Any],
    path: str,
    schema_store: dict[str, dict[str, Any]],
    messages: list[str],
) -> None:
    ref = schema.get("$ref")
    if isinstance(ref, str):
        referenced = _resolve_ref(ref, schema_store)
        if referenced is None:
            messages.append(f"{path}: unresolved schema ref {ref}")
            return
        _validate(data, referenced, path, schema_store, messages)
        return

    expected_type = schema.get("type")
    if expected_type is not None and not _matches_type(data, expected_type):
        messages.append(f"{path}: expected {_format_type(expected_type)}, got {_json_type(data)}")
        return

    if "const" in schema and data != schema["const"]:
        messages.append(f"{path}: expected const {schema['const']!r}")

    enum = schema.get("enum")
    if isinstance(enum, list) and data not in enum:
        messages.append(f"{path}: expected one of {enum!r}")

    if isinstance(data, str):
        _validate_string(data, schema, path, messages)

    if isinstance(data, (int, float)) and not isinstance(data, bool):
        _validate_number(data, schema, path, messages)

    if isinstance(data, list):
        items_schema = schema.get("items")
        if isinstance(items_schema, dict):
            for index, item in enumerate(data):
                _validate(item, items_schema, f"{path}[{index}]", schema_store, messages)

    if isinstance(data, dict):
        _validate_object(data, schema, path, schema_store, messages)


def _validate_object(
    data: dict[str, Any],
    schema: dict[str, Any],
    path: str,
    schema_store: dict[str, dict[str, Any]],
    messages: list[str],
) -> None:
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    required = schema.get("required") if isinstance(schema.get("required"), list) else []

    for key in required:
        if key not in data:
            messages.append(f"{path}: missing required property {key}")

    if schema.get("additionalProperties") is False:
        allowed = set(properties)
        for key in data:
            if key not in allowed:
                messages.append(f"{path}.{key}: additional property is not allowed")

    for key, property_schema in properties.items():
        if key in data and isinstance(property_schema, dict):
            _validate(data[key], property_schema, _child_path(path, key), schema_store, messages)


def _validate_string(data: str, schema: dict[str, Any], path: str, messages: list[str]) -> None:
    min_length = schema.get("minLength")
    if isinstance(min_length, int) and len(data) < min_length:
        messages.append(f"{path}: length must be at least {min_length}")

    pattern = schema.get("pattern")
    if isinstance(pattern, str) and re.search(pattern, data) is None:
        messages.append(f"{path}: does not match pattern {pattern!r}")


def _validate_number(data: int | float, schema: dict[str, Any], path: str, messages: list[str]) -> None:
    minimum = schema.get("minimum")
    if isinstance(minimum, (int, float)) and data < minimum:
        messages.append(f"{path}: must be >= {minimum}")

    maximum = schema.get("maximum")
    if isinstance(maximum, (int, float)) and data > maximum:
        messages.append(f"{path}: must be <= {maximum}")


def _resolve_ref(ref: str, schema_store: dict[str, dict[str, Any]]) -> dict[str, Any] | None:
    ref_name = ref.split("/")[-1]
    return schema_store.get(ref_name)


def _matches_type(data: Any, expected_type: Any) -> bool:
    if isinstance(expected_type, list):
        return any(_matches_type(data, item) for item in expected_type)
    if expected_type == "object":
        return isinstance(data, dict)
    if expected_type == "array":
        return isinstance(data, list)
    if expected_type == "string":
        return isinstance(data, str)
    if expected_type == "integer":
        return isinstance(data, int) and not isinstance(data, bool)
    if expected_type == "number":
        return isinstance(data, (int, float)) and not isinstance(data, bool)
    if expected_type == "boolean":
        return isinstance(data, bool)
    if expected_type == "null":
        return data is None
    return True


def _json_type(data: Any) -> str:
    if data is None:
        return "null"
    if isinstance(data, bool):
        return "boolean"
    if isinstance(data, dict):
        return "object"
    if isinstance(data, list):
        return "array"
    if isinstance(data, str):
        return "string"
    if isinstance(data, int):
        return "integer"
    if isinstance(data, float):
        return "number"
    return type(data).__name__


def _format_type(expected_type: Any) -> str:
    if isinstance(expected_type, list):
        return " or ".join(str(item) for item in expected_type)
    return str(expected_type)


def _child_path(path: str, key: str) -> str:
    if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", key):
        return f"{path}.{key}"
    return f"{path}[{key!r}]"
