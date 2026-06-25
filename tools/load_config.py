#!/usr/bin/env python3
"""
load_config.py — Argus Consumer Configuration Loader

Reads the consumer repository's .argus.yml (if present), merges it with
built-in defaults, validates the result, and outputs a resolved configuration
as JSON to stdout. Designed to be called from the composite action shell step.

Usage:
  python3 tools/load_config.py [--config PATH] [--output-env]

  --config PATH      Path to .argus.yml (default: .argus.yml in cwd)
  --output-env       Write resolved config as GITHUB_ENV key=value pairs
                     instead of JSON (used inside GitHub Actions)
  --validate-only    Parse and validate; exit 1 on errors, no output

Exit codes:
  0 — success
  1 — validation error in .argus.yml
  2 — usage error
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# ── yaml import (stdlib fallback) ─────────────────────────────────────────────
try:
    import yaml  # PyYAML
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

# ── Default configuration ─────────────────────────────────────────────────────

DEFAULTS: dict[str, Any] = {
    "version": "0.3",
    "skills": ["design-review"],
    "overrides": {
        "token-prefix": "--ds-",
        "severity": {},
    },
    "ignore": {
        "paths": [
            "node_modules/**",
            "dist/**",
            ".git/**",
        ],
        "rules": [],
    },
    "fail-on": ["P0", "P1"],
    "output": {
        "group-by-severity": True,
        "show-token-names": True,
        "max-findings": 50,
    },
}

VALID_SKILLS = {"design-review", "security-review", "api-contract", "performance", "infrastructure"}
VALID_SEVERITIES = {"P0", "P1", "P2", "P3"}
SUPPORTED_VERSIONS = {"0.2", "0.3"}

# ── Loader ───────────────────────────────────────────────────────────────────

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into a copy of base."""
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_raw_yaml(config_path: Path) -> dict:
    """Read and parse .argus.yml. Returns empty dict if file not found."""
    if not config_path.exists():
        return {}
    content = config_path.read_text(encoding="utf-8")
    if not content.strip():
        return {}

    if _YAML_AVAILABLE:
        data = yaml.safe_load(content)
        return data if isinstance(data, dict) else {}

    # Minimal fallback parser for simple key: value and list structures
    # Supports the most common .argus.yml patterns without PyYAML dependency.
    return _minimal_yaml_parse(content)


def _minimal_yaml_parse(content: str) -> dict:
    """
    Minimal YAML parser for .argus.yml when PyYAML is unavailable.
    Handles: top-level keys, string values, simple lists, one-level nesting.
    Does NOT handle multi-line strings, anchors, or complex nesting.
    """
    result: dict = {}
    current_key: str | None = None
    current_list: list | None = None
    indent_stack: list[tuple[int, str, dict]] = []  # (indent, key, parent_dict)
    current_dict = result

    for raw in content.splitlines():
        if raw.strip().startswith("#") or not raw.strip():
            continue

        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()

        # List item
        if line.startswith("- "):
            value = line[2:].strip().strip('"').strip("'")
            if current_list is None:
                current_list = []
                if current_key:
                    current_dict[current_key] = current_list
            current_list.append(value)
            continue
        else:
            current_list = None

        # Key: value
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Handle indented nesting (one level)
            if indent > 0 and indent_stack:
                parent_indent, parent_key, parent_dict = indent_stack[-1]
                if indent > parent_indent:
                    current_dict = parent_dict.setdefault(parent_key, {})
                else:
                    indent_stack.pop()
                    current_dict = result

            if value:
                current_dict[key] = value
                current_key = None
            else:
                # Nested block
                current_key = key
                indent_stack.append((indent, key, current_dict))
                current_list = None

    return result


def validate_config(config: dict) -> list[str]:
    """Return a list of validation error messages. Empty list means valid."""
    errors: list[str] = []

    version = str(config.get("version", ""))
    if version and version not in SUPPORTED_VERSIONS:
        errors.append(f"Unsupported config version '{version}'. Supported: {sorted(SUPPORTED_VERSIONS)}")

    skills = config.get("skills", [])
    if not isinstance(skills, list):
        errors.append("'skills' must be a list")
    else:
        unknown = [s for s in skills if s not in VALID_SKILLS]
        if unknown:
            errors.append(f"Unknown skill(s): {unknown}. Valid: {sorted(VALID_SKILLS)}")

    fail_on = config.get("fail-on", [])
    if not isinstance(fail_on, list):
        errors.append("'fail-on' must be a list of severity levels")
    else:
        invalid = [s for s in fail_on if s not in VALID_SEVERITIES]
        if invalid:
            errors.append(f"Invalid severity in 'fail-on': {invalid}. Valid: {sorted(VALID_SEVERITIES)}")

    overrides = config.get("overrides", {})
    if isinstance(overrides, dict):
        severity_overrides = overrides.get("severity", {})
        if isinstance(severity_overrides, dict):
            for rule, sev in severity_overrides.items():
                if sev not in VALID_SEVERITIES:
                    errors.append(f"Invalid severity override for rule '{rule}': '{sev}'")

    output_cfg = config.get("output", {})
    if isinstance(output_cfg, dict):
        max_findings = output_cfg.get("max-findings")
        if max_findings is not None:
            try:
                val = int(max_findings)
                if val < 1 or val > 500:
                    errors.append("'output.max-findings' must be between 1 and 500")
            except (TypeError, ValueError):
                errors.append("'output.max-findings' must be an integer")

    return errors


def resolve_config(config_path: Path) -> dict:
    """Load, merge with defaults, and return the resolved configuration."""
    raw = load_raw_yaml(config_path)
    merged = _deep_merge(DEFAULTS, raw)
    return merged


def emit_github_env(config: dict) -> None:
    """
    Write key=value pairs to GITHUB_ENV so subsequent steps can read them
    as environment variables.

    Variables emitted:
      ARGUS_SKILLS           — comma-separated skill list
      ARGUS_FAIL_ON          — comma-separated severity list
      ARGUS_TOKEN_PREFIX     — design token prefix
      ARGUS_IGNORE_PATHS     — newline-separated ignore glob list
      ARGUS_IGNORE_RULES     — comma-separated ignored rule IDs
      ARGUS_MAX_FINDINGS     — integer max findings
      ARGUS_SHOW_TOKENS      — "true" or "false"
    """
    env_file = os.environ.get("GITHUB_ENV")
    lines: list[str] = [
        f"ARGUS_SKILLS={','.join(config.get('skills', []))}",
        f"ARGUS_FAIL_ON={','.join(config.get('fail-on', []))}",
        f"ARGUS_TOKEN_PREFIX={config.get('overrides', {}).get('token-prefix', '--ds-')}",
        f"ARGUS_IGNORE_RULES={','.join(config.get('ignore', {}).get('rules', []))}",
        f"ARGUS_MAX_FINDINGS={config.get('output', {}).get('max-findings', 50)}",
        f"ARGUS_SHOW_TOKENS={str(config.get('output', {}).get('show-token-names', True)).lower()}",
    ]

    # Multi-line value for ignore paths (GitHub Actions supports EOF syntax)
    ignore_paths = config.get("ignore", {}).get("paths", [])
    lines.append("ARGUS_IGNORE_PATHS<<EOF")
    lines.extend(ignore_paths)
    lines.append("EOF")

    output = "\n".join(lines) + "\n"

    if env_file:
        with open(env_file, "a", encoding="utf-8") as f:
            f.write(output)
    else:
        # Fallback: print to stdout (useful for local testing)
        print(output)


# ── CLI entry point ───────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Argus Consumer Configuration Loader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--config", default=".argus.yml", metavar="PATH",
        help="Path to .argus.yml (default: .argus.yml in current directory)",
    )
    parser.add_argument(
        "--output-env", action="store_true",
        help="Emit GITHUB_ENV variables instead of JSON",
    )
    parser.add_argument(
        "--validate-only", action="store_true",
        help="Validate the config file and exit; no output produced",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    config = resolve_config(config_path)

    errors = validate_config(config)
    if errors:
        print("[argus:load-config] Configuration errors:", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        return 1

    if args.validate_only:
        source = f"{config_path}" if config_path.exists() else "defaults only"
        print(f"[argus:load-config] Config valid ({source})", file=sys.stderr)
        return 0

    if args.output_env:
        emit_github_env(config)
    else:
        print(json.dumps(config, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
