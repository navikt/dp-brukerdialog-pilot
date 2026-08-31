"""Validate agent/skill frontmatter and plugin manifests without needing the Copilot CLI.

This is a cheap CI-safe check (stdlib only, no live copilot invocation) that
catches the kind of mistake that would otherwise only surface as a confusing
runtime error from `copilot plugin install`: missing required frontmatter
fields, a name that doesn't match its filename/directory, or the
`.github/plugin/marketplace.json` entry drifting out of sync (wrong source
path, or name/version mismatch) with `plugin/plugin.json`.
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

# Aggregate byte budget for every agent/skill `name` + `description` field.
# These are always loaded for the model's skill/agent picker regardless of
# whether a given skill is ever actually used in a session, so letting this
# grow unbounded silently taxes every session's context. 8KB gives headroom
# to roughly triple the current plugin size (11 skills + 5 agents, ~2.4KB
# today) before this becomes a hard CI failure that forces a conscious
# decision (trim descriptions, or consciously raise the budget).
MAX_DISCOVERY_TEXT_BYTES = 8 * 1024

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

    if agent_count == 0:
        errors.append(f"{PLUGIN_DIR}: fant ingen agent-filer under agents/")

    marketplace_path = REPO_ROOT / ".github" / "plugin" / "marketplace.json"
    try:
        marketplace = json.loads(marketplace_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        return errors + [f"{marketplace_path}: kunne ikke leses som JSON ({exc})"]

    for field in ("name", "owner", "plugins"):
        if field not in marketplace:
            errors.append(f"{marketplace_path}: mangler felt '{field}'")

    plugins = marketplace.get("plugins", [])
    if not plugins:
        errors.append(f"{marketplace_path}: 'plugins' er tom eller mangler")
        return errors

    for entry in plugins:
        source = entry.get("source")
        if not source:
            errors.append(f"{marketplace_path}: plugin-oppføring mangler 'source'")
            continue
        source_dir = (REPO_ROOT / source).resolve()
        if not source_dir.is_dir():
            errors.append(f"{marketplace_path}: source={source!r} finnes ikke som mappe")
            continue
        source_plugin_json = source_dir / "plugin.json"
        if not source_plugin_json.exists():
            errors.append(f"{marketplace_path}: {source} mangler plugin.json")
            continue
        source_plugin = json.loads(source_plugin_json.read_text(encoding="utf-8"))
        if entry.get("name") != source_plugin.get("name"):
            errors.append(
                f"{marketplace_path}: plugin name={entry.get('name')!r} matcher ikke "
                f"{source_plugin_json}.name={source_plugin.get('name')!r}"
            )
        if entry.get("version") != source_plugin.get("version"):
            errors.append(
                f"{marketplace_path}: plugin version={entry.get('version')!r} matcher ikke "
                f"{source_plugin_json}.version={source_plugin.get('version')!r} (versjonsdrift)"
            )

    return errors


DISCOVERY_TOP_OFFENDERS = 3


def validate_discovery_budget(agent_files: list[Path], skill_files: list[Path]) -> list[str]:
    """Fail if the total name+description text across all frontmatter grows
    past MAX_DISCOVERY_TEXT_BYTES. See the constant's comment for rationale.
    """
    discovery_bytes = 0
    per_file_bytes: list[tuple[int, Path]] = []
    for path in (*agent_files, *skill_files):
        frontmatter = parse_frontmatter(path.read_text(encoding="utf-8"))
        if frontmatter is None:
            continue
        name = frontmatter.get("name")
        description = frontmatter.get("description")
        file_bytes = 0
        if isinstance(name, str):
            file_bytes += len(name.encode("utf-8"))
        if isinstance(description, str):
            file_bytes += len(description.encode("utf-8"))
        discovery_bytes += file_bytes
        per_file_bytes.append((file_bytes, path))

    if discovery_bytes > MAX_DISCOVERY_TEXT_BYTES:
        per_file_bytes.sort(key=lambda pair: pair[0], reverse=True)
        top_offenders = ", ".join(
            f"{path.relative_to(PLUGIN_DIR)} ({size} bytes)"
            for size, path in per_file_bytes[:DISCOVERY_TOP_OFFENDERS]
        )
        return [
            f"samlet discovery-tekst (name+description på tvers av agenter/skills) er "
            f"{discovery_bytes} bytes, budsjettet er {MAX_DISCOVERY_TEXT_BYTES} bytes — "
            "trim beskrivelser eller bevisst hev budsjettet i validate_plugin_schema.py. "
            f"Største bidragsytere: {top_offenders}"
        ]
    return []


def main() -> int:
    agent_files = sorted((PLUGIN_DIR / "agents").glob("*.agent.md"))
    skill_files = sorted((PLUGIN_DIR / "skills").glob("*/SKILL.md"))

    all_errors: list[str] = []
    for path in agent_files:
        all_errors.extend(validate_agent_file(path))
    for path in skill_files:
        all_errors.extend(validate_skill_file(path))
    all_errors.extend(validate_manifests(len(agent_files), len(skill_files)))
    all_errors.extend(validate_discovery_budget(agent_files, skill_files))

    if all_errors:
        for error in all_errors:
            print(f"[FAIL] {error}")
        print(f"\nSummary: {len(all_errors)} feil funnet")
        return 1

    print(f"[PASS] {len(agent_files)} agent-fil(er) og {len(skill_files)} skill-fil(er) validert OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
