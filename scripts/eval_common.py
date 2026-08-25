"""Shared helpers for the planlegger/koder eval harnesses.

Kept deliberately small: this is glue code (subprocess + JSON), not a
framework. Each eval script still owns its own wrapper prompt, field list
and scoring logic; only the mechanical parts (running copilot, resolving
paths/agent names, majority-vote aggregation, and report printing) live
here so a fix in one place (e.g. the notat-aggregation bug) can't silently
miss the other scripts.
"""
from __future__ import annotations

import json
import shutil
import sqlite3
import subprocess
import sys
import uuid
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

SESSION_STORE_DB = Path.home() / ".copilot" / "session-store.db"
SESSION_STATE_DIR = Path.home() / ".copilot" / "session-state"

# Child tables keyed by session_id that must be cleaned up alongside a
# deleted session row, to avoid orphaned data in session-store.db.
_SESSION_CHILD_TABLES = (
    "turns",
    "checkpoints",
    "session_files",
    "session_refs",
    "search_index",
    "forge_trajectory_events",
    "assistant_usage_events",
)


def delete_eval_session(session_id: str) -> None:
    """Best-effort delete of a single local session (DB rows + on-disk state).

    Never raises: eval results matter more than cleanup succeeding. A locked
    or missing session-store.db (e.g. another copilot process holding a
    write lock) should not fail the eval run.
    """
    try:
        if SESSION_STORE_DB.exists():
            con = sqlite3.connect(SESSION_STORE_DB, timeout=5)
            try:
                with con:
                    for table in _SESSION_CHILD_TABLES:
                        con.execute(f"DELETE FROM {table} WHERE session_id = ?", (session_id,))
                    con.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            finally:
                con.close()
    except sqlite3.Error:
        pass
    session_dir = SESSION_STATE_DIR / session_id
    if session_dir.exists():
        shutil.rmtree(session_dir, ignore_errors=True)


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def select_tests(tests: list[dict[str, Any]], suite: str) -> list[dict[str, Any]]:
    if suite == "all":
        return tests
    return [test for test in tests if str(test.get("suite", "policy")) == suite]


def load_plugin_name(repo_root: Path) -> str:
    plugin_manifest = repo_root / "plugin" / "plugin.json"
    with plugin_manifest.open("r", encoding="utf-8") as file:
        return str(json.load(file)["name"])


def resolve_tests_path(repo_root: Path, tests_arg: str) -> Path:
    """Resolve a --tests path relative to the repo root, not the cwd.

    Users invoke these scripts by absolute path from arbitrary directories,
    so a plain Path(tests_arg).resolve() would look in the wrong place.
    """
    tests_path = Path(tests_arg)
    if tests_path.is_absolute():
        return tests_path
    candidate = (repo_root / tests_path).resolve()
    if candidate.exists():
        return candidate
    return tests_path.resolve()


def resolve_agent(agent_arg: str, plugin_name: str) -> str:
    return agent_arg if ":" in agent_arg else f"{plugin_name}:{agent_arg}"


def require_copilot_bin(copilot_bin: str) -> bool:
    """Print an error and return False if copilot_bin isn't in PATH."""
    if shutil.which(copilot_bin) is None:
        print(f"error: {copilot_bin!r} not found in PATH", file=sys.stderr)
        return False
    return True


def run_copilot(copilot_bin: str, agent: str, prompt: str, keep_session: bool = False) -> str:
    """Run one copilot invocation and, by default, delete the local session it creates.

    Each call spins up a throwaway session purely for the eval prompt/response;
    keeping those around just fills up the session list. Set keep_session=True
    (e.g. via --keep-sessions) to inspect a run afterwards for debugging.
    """
    session_id = str(uuid.uuid4())
    command = [
        copilot_bin,
        "--agent",
        agent,
        "-p",
        prompt,
        "-s",
        "--no-ask-user",
        "--session-id",
        session_id,
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    try:
        if completed.returncode != 0:
            error_text = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
            raise RuntimeError(error_text)
        return completed.stdout.strip()
    finally:
        if not keep_session:
            delete_eval_session(session_id)


def aggregate_actuals(
    actuals: list[dict[str, str] | None],
    repeats: int,
    key_fields: tuple[str, ...],
    passthrough_fields: tuple[str, ...] = (),
) -> tuple[dict[str, str] | None, str, bool]:
    """Majority-vote across repeated runs.

    Only `key_fields` decide the winner. `passthrough_fields` (e.g. a free-text
    `notat`) are carried along from the winning run for display, but never
    used to break ties -- free text differs between runs almost every time,
    so including it in the vote key made identical decisions with different
    wording count as disagreement (silently turning real passes into
    "inconclusive" failures).
    """
    normalized: list[tuple[str, ...]] = []
    passthrough_by_key: dict[tuple[str, ...], dict[str, str]] = {}
    for actual in actuals:
        if actual is None:
            continue
        key = tuple(actual.get(field, "") for field in key_fields)
        normalized.append(key)
        if passthrough_fields:
            passthrough_by_key.setdefault(key, {field: actual.get(field, "") for field in passthrough_fields})

    if not normalized:
        return None, "could not parse output in any run", False

    counts = Counter(normalized)
    winner, winner_count = counts.most_common(1)[0]
    total_valid = len(normalized)
    has_majority = winner_count > (repeats / 2)

    aggregated = dict(zip(key_fields, winner))
    if passthrough_fields:
        aggregated.update(passthrough_by_key[winner])
    return aggregated, f"majority {winner_count}/{total_valid}", has_majority


@dataclass
class EvalResult:
    test_id: int
    status: str
    notes: str
    expected: dict[str, Any]
    actual: dict[str, str] | None


def summarize(results: Iterable[EvalResult]) -> tuple[int, int]:
    results = list(results)
    passed = sum(1 for result in results if result.status == "pass")
    return passed, len(results) - passed


def print_report(results: list[EvalResult], suite: str, repeats: int, as_json: bool) -> None:
    passed, failed = summarize(results)
    if as_json:
        print(
            json.dumps(
                {
                    "suite": suite,
                    "repeats": repeats,
                    "passed": passed,
                    "failed": failed,
                    "results": [
                        {
                            "id": result.test_id,
                            "status": result.status,
                            "notes": result.notes,
                            "expected": result.expected,
                            "actual": result.actual,
                        }
                        for result in results
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for result in results:
            print(f"[{result.status.upper():5}] {result.test_id}: {result.notes}")
        print(f"\nSummary: {passed} passed, {failed} failed")


def parse_brief(text: str, required_fields: tuple[str, ...], include_raw: bool = False) -> dict[str, str] | None:
    """Parse a KODER_BRIEF text block, shared by eval_koder_brief and eval_golden_trace."""
    import re

    normalized = text.replace("\r\n", "\n").strip()
    if not normalized.startswith("KODER_BRIEF"):
        return None

    missing = [field for field in required_fields if field not in normalized]
    sti_match = re.search(r"^Sti:\s*(.+)$", normalized, flags=re.MULTILINE)
    review_match = re.search(r"^Krever planreview:\s*(.+)$", normalized, flags=re.MULTILINE)
    if sti_match is None or review_match is None:
        return None

    result = {
        "sti": sti_match.group(1).strip().lower(),
        "planreview": review_match.group(1).strip().lower(),
        "missing_fields": ",".join(missing),
    }
    if include_raw:
        result["raw"] = normalized
    return result
