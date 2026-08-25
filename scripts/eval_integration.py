"""Real end-to-end integration test for the plugin.

Unlike eval_planlegger.py / eval_koder_brief.py / eval_golden_trace.py, this
script does NOT simulate a contract test with "ikke bruk verktøy". It spins up
a real scratch git repo, runs `planlegger` against it with tools enabled, and
checks that the resulting file changes on disk actually match what was asked
for. This is the only harness that exercises real tool use (file edits, git),
so it catches things the simulated contract tests structurally cannot.

Each test case describes:
- fixture: files to seed in a throwaway git repo
- prompt: the real task given to planlegger
- expect_contains: substrings that must appear in named files afterwards
- expect_no_commit: if true, assert no new commit was made (since the prompt
  doesn't ask for one, and agent policy says no auto-commit unless asked)
- expect_no_file_changes: if true, assert the working tree is completely
  unchanged (used for stopp-punkt tests, where planlegger should refuse to
  delegate/edit anything without explicit confirmation it can't get since
  the harness runs with --no-ask-user)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from eval_common import (
    delete_eval_session,
    load_json,
    load_plugin_name,
    require_copilot_bin,
    resolve_agent,
    resolve_tests_path,
    select_tests,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return completed.stdout.strip()


def setup_scratch_repo(fixture: dict[str, str]) -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="dp-brukerdialog-pilot-eval-"))
    run_git(["init", "-q"], scratch)
    run_git(["config", "user.email", "eval@example.com"], scratch)
    run_git(["config", "user.name", "Eval Harness"], scratch)
    for rel_path, content in fixture.items():
        target = scratch / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    run_git(["add", "-A"], scratch)
    run_git(["commit", "-q", "-m", "init"], scratch)
    return scratch


def run_real_task(copilot_bin: str, agent: str, prompt: str, scratch: Path, timeout: int, keep_session: bool) -> tuple[bool, str]:
    session_id = str(uuid.uuid4())
    command = [
        copilot_bin,
        "--agent",
        agent,
        "-p",
        prompt,
        "-s",
        "--no-ask-user",
        "--allow-all-tools",
        "-C",
        str(scratch),
        "--session-id",
        session_id,
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        ok = completed.returncode == 0
        output = completed.stdout.strip() or completed.stderr.strip()
        return ok, output
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    finally:
        if not keep_session:
            delete_eval_session(session_id)


def check_test(test: dict[str, Any], scratch: Path) -> list[str]:
    """Return a list of failure reasons (empty means the test passed)."""
    failures: list[str] = []

    for rel_path, needles in test.get("expect_contains", {}).items():
        target = scratch / rel_path
        if not target.exists():
            failures.append(f"{rel_path} finnes ikke")
            continue
        content = target.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in content:
                failures.append(f"{rel_path} mangler forventet innhold: {needle!r}")

    if test.get("expect_no_commit", True):
        commit_count = run_git(["rev-list", "--count", "HEAD"], scratch)
        if commit_count != "1":
            failures.append(f"forventet ingen ny commit (fortsatt 1 commit), fant {commit_count}")

    if test.get("expect_no_file_changes"):
        status = run_git(["status", "--porcelain"], scratch)
        if status:
            failures.append(f"forventet ingen filendringer (stopp-punkt skal blokkere), fant:\n{status}")

    return failures


def main() -> int:
    plugin_name = load_plugin_name(REPO_ROOT)

    parser = argparse.ArgumentParser(description="Run real end-to-end integration test against a scratch repo")
    parser.add_argument("--tests", default="eval/integration-tests.json", help="Path to test matrix JSON")
    parser.add_argument("--agent", default=f"{plugin_name}:planlegger", help="Agent name to run")
    parser.add_argument("--copilot-bin", default="copilot", help="Copilot CLI binary")
    parser.add_argument("--suite", choices=("all", "smoke", "policy"), default="all", help="Test suite selector")
    parser.add_argument("--run", action="store_true", help="Run the tests (required; this harness has no dry-run mode)")
    parser.add_argument("--timeout", type=int, default=300, help="Timeout per test in seconds")
    parser.add_argument(
        "--keep-sessions",
        action="store_true",
        help="Don't delete the local copilot session created by each run (default: delete)",
    )
    parser.add_argument(
        "--keep-scratch",
        action="store_true",
        help="Don't delete the scratch git repo after each run (default: delete); useful for debugging",
    )
    args = parser.parse_args()

    if not args.run:
        print("Denne harnessen kjører ekte verktøykall mot en scratch-repo. Bruk --run for å bekrefte.", file=sys.stderr)
        return 1

    if not require_copilot_bin(args.copilot_bin):
        return 1

    tests_path = resolve_tests_path(REPO_ROOT, args.tests)
    tests = select_tests(load_json(tests_path), args.suite)
    if not tests:
        print(f"Ingen tester funnet for suite={args.suite!r} i {tests_path}", file=sys.stderr)
        return 1

    agent = resolve_agent(args.agent, plugin_name)
    passed = 0
    failed = 0

    for test in tests:
        test_id = int(test["id"])
        prompt = str(test["prompt"])
        fixture = dict(test.get("fixture", {}))

        scratch = setup_scratch_repo(fixture)
        try:
            ok, output = run_real_task(args.copilot_bin, agent, prompt, scratch, args.timeout, args.keep_sessions)
            if not ok:
                print(f"[FAIL ] {test_id}: copilot-kjøring feilet: {output[:300]}")
                failed += 1
                continue

            failures = check_test(test, scratch)
            if failures:
                print(f"[FAIL ] {test_id}: {'; '.join(failures)}")
                failed += 1
            else:
                print(f"[PASS ] {test_id}: scratch-repo matchet forventet resultat")
                passed += 1
        finally:
            if not args.keep_scratch:
                shutil.rmtree(scratch, ignore_errors=True)
            else:
                print(f"  scratch-repo beholdt: {scratch}")

    print(f"\nSummary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
