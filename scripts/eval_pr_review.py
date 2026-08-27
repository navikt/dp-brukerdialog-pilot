"""Real end-to-end eval for the `pr-reviewer` agent.

Unlike the contract tests (eval_koder_brief.py, eval_reviewer.py), this spins
up a real scratch git repo and runs `pr-reviewer` against it with tools
enabled, same pattern as eval_integration.py. The key difference: pr-reviewer
is a read-only agent (it reviews other people's diffs; it never edits files
or commits), so the core assertion here is that the diff is byte-for-byte
IDENTICAL before and after the run, not that files changed as expected.

Each test case describes:
- base_files: files committed as the repo's starting point ("main")
- pr_files: files written on top, WITHOUT committing, simulating an
  uncommitted/PR diff for pr-reviewer to review
- prompt: the real task given to pr-reviewer
- expect_output_contains: substrings that must appear in pr-reviewer's final
  response (e.g. a flagged keyword for a planted issue)
- gh_mode (optional, default "absent"): controls the `gh` CLI the agent sees
  during the run — "absent" (no gh on PATH, host's real gh is hidden too, so
  this is portable regardless of whether the machine running the harness has
  gh installed), "unauthenticated" (a fake gh exists but `gh auth status`
  fails), or "authenticated" (fake gh succeeds and captures any `gh pr
  comment` call for verification).
- pr_number (optional): PR number referenced in the prompt; used to name/find
  the fake gh's captured comment file.
- expect_posted (optional bool): when set, asserts whether a `gh pr comment`
  call was actually captured by the fake gh, independent of what the agent's
  text output claims (mirrors the "don't trust the substring, check the real
  state" pattern used in eval_integration.py's expect_reviewer_verdict_if_changed).
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_common import (  # noqa: E402
    delete_eval_session,
    load_json,
    load_plugin_name,
    require_copilot_bin,
    resolve_agent,
    resolve_tests_path,
    select_tests,
)
from eval_integration import run_git  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

# A single fake `gh` used for both "unauthenticated" and "authenticated" modes;
# behavior branches on FAKE_GH_MODE so we don't need two near-identical scripts.
# Only implements the subcommands pr-reviewer.agent.md actually documents using
# (`auth status`, `pr diff`, `pr view`, `pr comment --body-file`).
FAKE_GH_SCRIPT = """#!/usr/bin/env bash
set -euo pipefail
MODE="${FAKE_GH_MODE:-authenticated}"
CAPTURE_DIR="${FAKE_GH_CAPTURE_DIR:-}"

cmd="${1:-}"; shift || true
sub="${1:-}"; shift || true

if [[ "$cmd" == "auth" && "$sub" == "status" ]]; then
  if [[ "$MODE" == "authenticated" ]]; then
    echo "Logged in to github.com as fake-eval-user"
    exit 0
  fi
  echo "You are not logged into any GitHub hosts." >&2
  exit 1
fi

if [[ "$cmd" == "pr" && "$sub" == "diff" ]]; then
  git diff
  exit 0
fi

if [[ "$cmd" == "pr" && "$sub" == "view" ]]; then
  echo '{"title":"fake pr","body":"","baseRefName":"main","headRefName":"feature"}'
  exit 0
fi

if [[ "$cmd" == "pr" && "$sub" == "comment" ]]; then
  pr_number="${1:-unknown}"; shift || true
  body_file=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --body-file) body_file="$2"; shift 2 ;;
      *) shift ;;
    esac
  done
  if [[ -n "$CAPTURE_DIR" && -n "$body_file" ]]; then
    mkdir -p "$CAPTURE_DIR"
    cp "$body_file" "$CAPTURE_DIR/comment-${pr_number}.txt"
  fi
  echo "https://github.com/fake/repo/pull/${pr_number}#issuecomment-1"
  exit 0
fi

echo "fake gh (eval harness): unhandled command: $cmd $sub $*" >&2
exit 1
"""


def _dir_has_real_gh(entry: str) -> bool:
    candidate = Path(entry) / "gh"
    return candidate.exists() and os.access(candidate, os.X_OK)


def sanitize_path_without_gh(path_value: str) -> str:
    """Strip any PATH entry that has a real `gh` binary.

    Makes the "absent" gh_mode portable: it behaves the same whether or not
    the machine actually running the eval harness has `gh` installed,
    instead of "passing" only by accident on gh-less environments.
    """
    kept = [entry for entry in path_value.split(os.pathsep) if entry and not _dir_has_real_gh(entry)]
    return os.pathsep.join(kept)


def build_gh_env(mode: str, capture_dir: Path) -> tuple[dict[str, str], Path | None]:
    """Return (env, fake_bin_dir) for the given gh_mode.

    fake_bin_dir is None for "absent" (nothing to clean up afterwards).
    """
    env = dict(os.environ)
    sanitized_path = sanitize_path_without_gh(env.get("PATH", ""))

    if mode == "absent":
        env["PATH"] = sanitized_path
        return env, None

    fake_bin_dir = Path(tempfile.mkdtemp(prefix="dp-brukerdialog-pilot-fake-gh-"))
    script_path = fake_bin_dir / "gh"
    script_path.write_text(FAKE_GH_SCRIPT, encoding="utf-8")
    script_path.chmod(0o755)

    env["PATH"] = f"{fake_bin_dir}{os.pathsep}{sanitized_path}"
    env["FAKE_GH_MODE"] = mode
    env["FAKE_GH_CAPTURE_DIR"] = str(capture_dir)
    return env, fake_bin_dir


def setup_pr_review_fixture(base_files: dict[str, str], pr_files: dict[str, str]) -> Path:
    scratch = Path(tempfile.mkdtemp(prefix="dp-brukerdialog-pilot-pr-eval-"))
    run_git(["init", "-q"], scratch)
    run_git(["config", "user.email", "eval@example.com"], scratch)
    run_git(["config", "user.name", "Eval Harness"], scratch)
    for rel_path, content in base_files.items():
        target = scratch / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    run_git(["add", "-A"], scratch)
    run_git(["commit", "-q", "-m", "init"], scratch)

    # Uncommitted on top of "main" -- this is the diff pr-reviewer should review.
    for rel_path, content in pr_files.items():
        target = scratch / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return scratch


def run_real_task(
    copilot_bin: str,
    agent: str,
    prompt: str,
    scratch: Path,
    timeout: int,
    keep_session: bool,
    env: dict[str, str] | None = None,
) -> tuple[bool, str]:
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
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, env=env)
        ok = completed.returncode == 0
        output = completed.stdout.strip() or completed.stderr.strip()
        return ok, output
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout}s"
    finally:
        if not keep_session:
            delete_eval_session(session_id)


def check_test(test: dict[str, Any], scratch: Path, output: str, diff_before: str, capture_dir: Path) -> list[str]:
    """Return a list of failure reasons (empty means the test passed)."""
    failures: list[str] = []

    for needle in test.get("expect_output_contains", []):
        if needle not in output:
            failures.append(f"agentens sluttsvar mangler forventet tekst: {needle!r}")

    diff_after = run_git(["diff"], scratch)
    if diff_after != diff_before:
        failures.append("pr-reviewer skal være read-only, men diffen endret seg under kjøringen")

    commit_count = run_git(["rev-list", "--count", "HEAD"], scratch)
    if commit_count != "1":
        failures.append(f"forventet ingen ny commit (fortsatt 1 commit), fant {commit_count}")

    expect_posted = test.get("expect_posted")
    if expect_posted is not None:
        # Check the fake gh's actual capture, not just what the agent's text
        # claims -- same "verify real state, not the substring" principle as
        # expect_reviewer_verdict_if_changed in eval_integration.py.
        captured_files = list(capture_dir.glob("comment-*.txt")) if capture_dir.exists() else []
        posted = bool(captured_files)
        if expect_posted and not posted:
            failures.append("forventet at pr-reviewer postet en kommentar (fake gh), men ingen ble fanget opp")
        if not expect_posted and posted:
            failures.append(
                f"forventet at pr-reviewer IKKE postet noen kommentar, men fake gh fanget opp: {[f.name for f in captured_files]}"
            )

    return failures


def main() -> int:
    plugin_name = load_plugin_name(REPO_ROOT)

    parser = argparse.ArgumentParser(description="Run real end-to-end eval for pr-reviewer against a scratch repo")
    parser.add_argument("--tests", default="eval/pr-reviewer-tests.json", help="Path to test matrix JSON")
    parser.add_argument("--agent", default=f"{plugin_name}:pr-reviewer", help="Agent name to run")
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
        base_files = dict(test.get("base_files", {}))
        pr_files = dict(test.get("pr_files", {}))
        gh_mode = str(test.get("gh_mode", "absent"))

        scratch = setup_pr_review_fixture(base_files, pr_files)
        diff_before = run_git(["diff"], scratch)
        capture_dir = scratch / ".fake-gh-capture"
        env, fake_bin_dir = build_gh_env(gh_mode, capture_dir)
        try:
            ok, output = run_real_task(
                args.copilot_bin, agent, prompt, scratch, args.timeout, args.keep_sessions, env=env
            )
            if not ok:
                print(f"[FAIL ] {test_id}: copilot-kjøring feilet: {output[:300]}")
                failed += 1
                continue

            failures = check_test(test, scratch, output, diff_before, capture_dir)
            if failures:
                print(f"[FAIL ] {test_id}: {'; '.join(failures)}")
                failed += 1
            else:
                print(f"[PASS ] {test_id}: review kjørt read-only og matchet forventet resultat (gh_mode={gh_mode})")
                passed += 1
        finally:
            if fake_bin_dir is not None:
                shutil.rmtree(fake_bin_dir, ignore_errors=True)
            if not args.keep_scratch:
                shutil.rmtree(scratch, ignore_errors=True)
            else:
                print(f"  scratch-repo beholdt: {scratch}")

    print(f"\nSummary: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
