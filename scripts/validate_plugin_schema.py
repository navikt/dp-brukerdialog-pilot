"""Validate agent/skill frontmatter and plugin manifests without needing the Copilot CLI.

This is a cheap CI-safe check (stdlib only, no live copilot invocation) that
catches the kind of mistake that would otherwise only surface as a confusing
runtime error from `copilot plugin install`: missing required frontmatter
fields, a name that doesn't match its filename/directory, or a manifest
skill/agent count that's drifted out of sync with what's actually on disk.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
PLUGIN_DIR = REPO_ROOT / "plugin"

REQUIRED_AGENT_FIELDS = ("name", "description")
REQUIRED_SKILL_FIELDS = ("name", "description")

_KEY_VALUE_RE = re.compile(r"^([A-Za-z0-9_-]+):\s*(.*)$")
_NESTED_KEY_VALUE_RE = re.compile(r"^\s{2,}([A-Za-z0-9_-]+):\s*(.*)$")


def parse_frontmatter(text: str) -> dict[str, Any] | None:
    """Parse the simple flat (+ one level of nesting) frontmatter used here.

    Deliberately not a full YAML parser (no lists, no multi-level nesting):
    every agent/skill file in this plugin uses flat `key: value` pairs plus
    at most one nested dict (`metadata:`), so a tiny hand-rolled parser keeps
    this check dependency-free instead of requiring PyYAML in CI.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    body = text[3:end].strip("\n")

    result: dict[str, Any] = {}
    current_nested_key: str | None = None
    for line in body.splitlines():
        if not line.strip():
            continue
        nested_match = _NESTED_KEY_VALUE_RE.match(line)
        if nested_match and current_nested_key:
            key, value = nested_match.groups()
            result.setdefault(current_nested_key, {})[key] = value.strip().strip('"')
            continue
        match = _KEY_VALUE_RE.match(line)
        if not match:
            continue
        key, value = match.groups()
        value = value.strip()
        if value == "":
            current_nested_key = key
            result[key] = {}
        else:
            current_nested_key = None
            result[key] = value.strip('"')
    return result


def validate_agent_file(path: Path) -> list[str]:
    errors: list[str] = []
    frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
    if frontmatter is None:
        return [f"{path}: mangler gyldig frontmatter (--- ... ---)"]

    for field in REQUIRED_AGENT_FIELDS:
        if not frontmatter.get(field):
            errors.append(f"{path}: mangler påkrevd felt '{field}'")

    expected_name = path.name.removesuffix(".agent.md")
    actual_name = frontmatter.get("name")
    if actual_name and actual_name != expected_name:
        errors.append(f"{path}: name={actual_name!r} matcher ikke filnavn (forventet {expected_name!r})")

    for bool_field in ("user-invocable", "disable-model-invocation"):
        if bool_field in frontmatter and frontmatter[bool_field] not in ("true", "false"):
            errors.append(f"{path}: '{bool_field}' må være true/false, fikk {frontmatter[bool_field]!r}")

    return errors


def validate_skill_file(path: Path) -> list[str]:
    errors: list[str] = []
    frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
    if frontmatter is None:
        return [f"{path}: mangler gyldig frontmatter (--- ... ---)"]

    for field in REQUIRED_SKILL_FIELDS:
        if not frontmatter.get(field):
            errors.append(f"{path}: mangler påkrevd felt '{field}'")

    expected_name = path.parent.name
    actual_name = frontmatter.get("name")
    if actual_name and actual_name != expected_name:
        errors.append(f"{path}: name={actual_name!r} matcher ikke mappenavn (forventet {expected_name!r})")

    return errors


def validate_manifests(agent_count: int, skill_count: int) -> list[str]:
    errors: list[str] = []

    plugin_json_path = PLUGIN_DIR / "plugin.json"
    try:
        plugin_json = json.loads(plugin_json_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        return [f"{plugin_json_path}: kunne ikke leses som JSON ({exc})"]

    for field in ("name", "version", "agents", "skills"):
        if field not in plugin_json:
            errors.append(f"{plugin_json_path}: mangler felt '{field}'")

    manifest_path = REPO_ROOT / "package-manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        return errors + [f"{manifest_path}: kunne ikke leses som JSON ({exc})"]

    packages = manifest.get("packages", [])
    if not packages:
        errors.append(f"{manifest_path}: 'packages' er tom eller mangler")
        return errors

    package = packages[0]
    if package.get("agents") != agent_count:
        errors.append(
            f"{manifest_path}: packages[0].agents={package.get('agents')!r}, "
            f"men fant {agent_count} agent-filer på disk"
        )
    if package.get("skills") != skill_count:
        errors.append(
            f"{manifest_path}: packages[0].skills={package.get('skills')!r}, "
            f"men fant {skill_count} skill-mapper på disk"
        )

    return errors


def main() -> int:
    agent_files = sorted((PLUGIN_DIR / "agents").glob("*.agent.md"))
    skill_files = sorted((PLUGIN_DIR / "skills").glob("*/SKILL.md"))

    all_errors: list[str] = []
    for path in agent_files:
        all_errors.extend(validate_agent_file(path))
    for path in skill_files:
        all_errors.extend(validate_skill_file(path))
    all_errors.extend(validate_manifests(len(agent_files), len(skill_files)))

    if all_errors:
        for error in all_errors:
            print(f"[FAIL] {error}")
        print(f"\nSummary: {len(all_errors)} feil funnet")
        return 1

    print(f"[PASS] {len(agent_files)} agent-fil(er) og {len(skill_files)} skill-fil(er) validert OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
