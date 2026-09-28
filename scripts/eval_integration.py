"""Real end-to-end integration test for the plugin.

Unlike eval_planlegger.py / eval_koder_brief.py / eval_golden_trace.py, this
script does NOT simulate a contract test with "ikke bruk verktøy". It spins up
a real scratch git repo, runs `planlegger` against it with tools enabled, and
checks that the resulting file changes on disk actually match what was asked
for. This is the only harness that exercises real tool use (file edits, git),
so it catches things the simulated contract tests structurally cannot.

Each test case describes:
- fixture: files to seed in a throwaway git repo (committed as the initial state)
- dirty: files to overwrite AFTER the commit, WITHOUT committing -- simulates
  the user's own pre-existing uncommitted edits to an already-tracked file
  (used for testing the content-based BASELINE mechanism: see
  "Baseline før delegasjon" in planlegger.agent.md)
- untracked: brand new files that are never committed -- simulates the user's
  own untracked work-in-progress present before the agent starts
- prompt: the real task given to planlegger
- expect_contains: substrings that must appear in named files afterwards
- expect_unchanged: exact file content (path -> full expected content) that
  must remain byte-for-byte identical afterwards -- used to prove the agent
  chain never touched the user's own dirty/untracked work that BASELINE was
  supposed to shield
- expect_no_commit: if true, assert no new commit was made (since the prompt
  doesn't ask for one, and agent policy says no auto-commit unless asked)
- expect_no_file_changes: if true, assert the working tree is completely
  unchanged (used for stopp-punkt tests, where planlegger should refuse to
  delegate/edit anything without explicit confirmation it can't get since
  the harness runs with --no-ask-user)
- expect_output_contains: substrings that must appear in planlegger's final
  response text (e.g. its required `Reviewer: <status>` summary line), used
  to verify the reviewer-step actually ran as part of the real flow
- expect_planreview_reported: same principle, but for the planreview gate on
  komplisert sti -- verifies a `Planreview: <verdikt>` line is present,
  proving a real review call happened and was reported instead of silently
  skipped (see "Slik kjøres planreview" in planlegger.agent.md)
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
    run_parallel,
    select_tests,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return completed.stdout.strip()


def setup_scratch_repo(fixture: dict[str, str], dirty: dict[str, str] | None = None, untracked: dict[str, str] | None = None) -> Path:
    """Set up a scratch repo. `fixture` files are committed as the repo's initial
    state. `dirty` overwrites already-committed files afterwards WITHOUT
    committing (simulates the user's own uncommitted edits before the agent
    starts). `untracked` adds brand new, never-committed files (simulates the
    user's own untracked work-in-progress)."""
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
    for rel_path, content in (dirty or {}).items():
        target = scratch / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    for rel_path, content in (untracked or {}).items():
        target = scratch / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
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


def check_test(test: dict[str, Any], scratch: Path, output: str = "") -> list[str]:
    """Return a list of failure reasons (empty means the test passed)."""
    failures: list[str] = []

    for needle in test.get("expect_output_contains", []):
        if needle not in output:
            failures.append(f"agentens sluttsvar mangler forventet tekst: {needle!r}")

    for rel_path, needles in test.get("expect_contains", {}).items():
        target = scratch / rel_path
        if not target.exists():
            failures.append(f"{rel_path} finnes ikke")
            continue
        content = target.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in content:
                failures.append(f"{rel_path} mangler forventet innhold: {needle!r}")

    for rel_path, expected_content in test.get("expect_unchanged", {}).items():
        # Brukes for filer som allerede var endret av brukeren (dirty/untracked)
        # før agenten startet: verifiserer at agentkjeden ikke rørte brukerens
        # eget, urelaterte arbeid ved en feiltakelse.
        target = scratch / rel_path
        if not target.exists():
            failures.append(f"{rel_path} finnes ikke (skulle vært uendret brukerinnhold)")
            continue
        actual = target.read_text(encoding="utf-8")
        if actual != expected_content:
            failures.append(
                f"{rel_path} ble endret selv om det skulle forbli brukerens uendrede "
                f"innhold: forventet {expected_content!r}, fant {actual!r}"
            )

    if test.get("expect_no_commit", True):
        commit_count = run_git(["rev-list", "--count", "HEAD"], scratch)
        if commit_count != "1":
            failures.append(f"forventet ingen ny commit (fortsatt 1 commit), fant {commit_count}")

    if test.get("expect_no_file_changes"):
        status = run_git(["status", "--porcelain"], scratch)
        if status:
            failures.append(f"forventet ingen filendringer (stopp-punkt skal blokkere), fant:\n{status}")

    if test.get("expect_reviewer_verdict_if_changed"):
        # Semantisk sjekk, ikke bare tekst-substring: hvis filer faktisk ble
        # endret, skal reviewer ha kjørt med et ekte verdikt (APPROVED/
        # NEEDS_CHANGES/BLOCKED) -- planlegger skal aldri kunne skrive
        # "Reviewer: hoppet over" når git faktisk viser endringer.
        status = run_git(["status", "--porcelain"], scratch)
        files_changed = bool(status.strip())
        # Fjern markdown-uthevingstegn før sjekk: modellen skriver noen ganger
        # "**Reviewer:** APPROVED" i stedet for "Reviewer: APPROVED", og en ren
        # substring-sjekk skal ikke feile bare pga. fet skrift rundt kolonet.
        output_plain = output.replace("*", "")
        real_verdicts = ["Reviewer: APPROVED", "Reviewer: NEEDS_CHANGES", "Reviewer: BLOCKED",
                          "Reviewer-status: APPROVED", "Reviewer-status: NEEDS_CHANGES",
                          "Reviewer-status: BLOCKED"]
        has_real_verdict = any(v in output_plain for v in real_verdicts)
        claims_skipped = "hoppet over" in output.lower()
        if files_changed and claims_skipped and not has_real_verdict:
            failures.append(
                "reviewer-steg ble feilaktig hoppet over: git status viser faktiske "
                f"filendringer ({status.strip()!r}), men output hevder "
                "'Reviewer: hoppet over' uten et ekte verdikt"
            )
        elif files_changed and not has_real_verdict:
            failures.append(
                "filer ble endret, men output mangler et ekte reviewer-verdikt "
                "(APPROVED/NEEDS_CHANGES/BLOCKED)"
            )

    if test.get("expect_planreview_reported"):
        # Samme prinsipp som expect_reviewer_verdict_if_changed: planlegger skal
        # aldri kunne skrive "Krever planreview=ja" og bare fortsette uten å
        # rapportere et faktisk verdikt fra det delegerte review-kallet. Sjekker
        # kun at kontrakten (en Planreview-linje finnes) holdes, ikke hvilken
        # agent som ble kalt -- se "Slik kjøres planreview" i planlegger.agent.md
        # for hvorfor akkurat hvilken agent ikke kan tvinges/testes pålitelig.
        output_plain = output.replace("*", "")
        if "Planreview:" not in output_plain and "Planreview-status:" not in output_plain:
            failures.append(
                "oppgaven skal utløse planreview på komplisert sti, men output "
                "mangler en 'Planreview: <verdikt>'-linje"
            )

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
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Run this many test cases concurrently (default: 1, sequential). "
        "Each test case is an independent scratch repo/session, so this is safe; "
        "it mainly cuts wall-clock time since each real agent run can take minutes.",
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

    def run_one(test: dict[str, Any]) -> tuple[int, bool, str, str | None]:
        """Returns (test_id, passed, message, kept_scratch_path_or_None)."""
        test_id = int(test["id"])
        prompt = str(test["prompt"])
        fixture = dict(test.get("fixture", {}))
        dirty = dict(test.get("dirty", {}))
        untracked = dict(test.get("untracked", {}))

        scratch = setup_scratch_repo(fixture, dirty=dirty, untracked=untracked)
        kept_path = str(scratch) if args.keep_scratch else None
        try:
            ok, output = run_real_task(args.copilot_bin, agent, prompt, scratch, args.timeout, args.keep_sessions)
            if not ok:
                return test_id, False, f"copilot-kjøring feilet: {output[:300]}", kept_path

            failures = check_test(test, scratch, output)
            if failures:
                return test_id, False, "; ".join(failures), kept_path
            return test_id, True, "scratch-repo matchet forventet resultat", kept_path
        finally:
            if args.keep_scratch:
                pass  # kept path reported below, directory not removed
            else:
                shutil.rmtree(scratch, ignore_errors=True)

    def on_progress(done: int, total: int, test: dict[str, Any], result: tuple[int, bool, str, str | None]) -> None:
        test_id, passed, message, kept_path = result
        status_label = "PASS " if passed else "FAIL "
        print(f"  ({done}/{total}) [{status_label}] {test_id}: {message}")
        if kept_path:
            print(f"    scratch-repo beholdt: {kept_path}")

    results = run_parallel(tests, run_one, args.parallel, on_progress=on_progress)
    results.sort(key=lambda r: r[0])

    passed = sum(1 for _, ok, _, _ in results if ok)
    failed = len(results) - passed

    print()
    for test_id, ok, message, kept_path in results:
        print(f"[{'PASS ' if ok else 'FAIL '}] {test_id}: {message}")
        if kept_path:
            print(f"  scratch-repo beholdt: {kept_path}")

    print(f"\nSummary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
