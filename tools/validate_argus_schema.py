#!/usr/bin/env python3
"""
validate_argus_schema.py — validate .argus.yml against config/argus-config.schema.json

Zero-dependency JSON Schema (draft-07 subset) validator for Argus consumer
configuration. Supported keywords:

    type, properties, required, additionalProperties (boolean),
    enum, items, uniqueItems, minimum, maximum

default / description / title / $id / $schema / $schema are documentation-only
and ignored by validation.

Why a subset validator? The repo keeps a stdlib-only toolchain (no jsonschema
dependency) so config validation runs anywhere Python 3 runs — locally, in CI,
and inside the composite action. The schema itself is standard draft-07, so
consumers can also validate with any full JSON Schema tool (IDE, CI, etc.).

Usage:
  python3 tools/validate_argus_schema.py                        # validate config/argus.example.yml
  python3 tools/validate_argus_schema.py --config path.yml      # one or more configs
  python3 tools/validate_argus_schema.py --check-schema         # schema file is well-formed JSON
  python3 tools/validate_argus_schema.py --schema path.json     # alternate schema file

Exit codes:
  0 — all configs valid (or --check-schema passed)
  1 — one or more configs invalid, or the schema file is malformed
  2 — usage error
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import load_config  # reuse .argus.yml parsing (PyYAML or minimal fallback)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = REPO_ROOT / "config" / "argus-config.schema.json"
DEFAULT_CONFIG = REPO_ROOT / "config" / "argus.example.yml"


# ── Validation engine (draft-07 subset) ──────────────────────────────────────

def _type_of(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _matches_type(value: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        return any(_matches_type(value, t) for t in expected)
    actual = _type_of(value)
    if expected == "number":
        return actual in ("number", "integer")
    if expected == "integer":
        # JSON Schema: 1.0 is a valid integer if it has no fractional part.
        return actual == "integer" or (actual == "number" and float(value).is_integer())
    return actual == expected


def validate(value: Any, schema: dict, path: str, errors: list[str]) -> None:
    """Validate ``value`` against ``schema``; append 'path: message' to errors."""
    # type
    if "type" in schema and not _matches_type(value, schema["type"]):
        errors.append(f"{path}: expected type {schema['type']}, got {_type_of(value)}")

    # enum
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not allowed (allowed: {schema['enum']})")

    # object
    if isinstance(value, dict):
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                validate(value[key], sub, f"{path}.{key}" if path else key, errors)
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}: missing required property {key!r}")
        if schema.get("additionalProperties") is False:
            allowed = set(props)
            unknown = sorted(set(value) - allowed)
            if unknown:
                errors.append(f"{path}: unknown propert{'y' if len(unknown) == 1 else 'ies'} {unknown} (additionalProperties: false)")

    # array
    if isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(value):
                validate(item, items, f"{path}[{i}]", errors)
        if schema.get("uniqueItems") and len(value) != len(set(value)):
            errors.append(f"{path}: duplicate items (uniqueItems: true)")

    # numeric bounds
    if _type_of(value) in ("integer", "number") and isinstance(value, (int, float)):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: {value} > maximum {schema['maximum']}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate .argus.yml against config/argus-config.schema.json (zero-dep subset)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--config", action="append", metavar="PATH",
                        help="Path to a .argus.yml to validate (repeatable). Default: config/argus.example.yml")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA), metavar="PATH",
                        help="Path to the JSON schema (default: config/argus-config.schema.json)")
    parser.add_argument("--check-schema", action="store_true",
                        help="Only verify the schema file is well-formed JSON, then exit")
    args = parser.parse_args()

    schema_path = Path(args.schema)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        print(f"[argus:schema] FAIL: cannot read schema {schema_path}: {exc}", file=sys.stderr)
        return 1

    if args.check_schema:
        print(f"[argus:schema] schema {schema_path} is valid JSON")
        return 0

    config_paths = [Path(p) for p in (args.config or [str(DEFAULT_CONFIG)])]

    all_ok = True
    for config_path in config_paths:
        if not config_path.exists():
            print(f"[argus:schema] FAIL: config not found: {config_path}", file=sys.stderr)
            all_ok = False
            continue

        data = load_config.load_raw_yaml(config_path)
        errors: list[str] = []
        validate(data, schema, "", errors)
        if errors:
            all_ok = False
            print(f"[argus:schema] FAIL: {config_path} does not conform to {schema_path.name}:")
            for err in errors:
                print(f"  ✗ {err}", file=sys.stderr)
        else:
            print(f"[argus:schema] ok: {config_path} conforms to {schema_path.name}")

    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())