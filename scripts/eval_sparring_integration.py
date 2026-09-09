"""Real scratch-repo checks for sparring's read-only and handoff contract."""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_common import delete_eval_session, load_plugin_name, require_copilot_bin, resolve_agent  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]


def run_git(args: list[str], cwd: Path) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True)
    return completed.stdout.strip()


def run_agent(copilot_bin: str, agent: str, prompt: str, scratch: Path, keep_session: bool) -> str:
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
        completed = subprocess.run(command, capture_output=True, text=True, timeout=300)
        if completed.returncode != 0:
            raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
        return completed.stdout.strip()
    finally:
        if not keep_session:
            delete_eval_session(session_id)


def check_no_handoff(copilot_bin: str, agent: str, keep_session: bool) -> list[str]:
    scratch = Path(tempfile.mkdtemp(prefix="dp-brukerdialog-pilot-sparring-"))
    try:
        (scratch / "README.md").write_text("# scratch\n", encoding="utf-8")
        run_git(["init", "-q"], scratch)
        run_git(["config", "user.email", "eval@example.com"], scratch)
        run_git(["config", "user.name", "Eval Harness"], scratch)
        run_git(["add", "-A"], scratch)
        run_git(["commit", "-q", "-m", "init"], scratch)
        before = run_git(["status", "--porcelain"], scratch)
        output = run_agent(
            copilot_bin,
            agent,
            "Vi trenger en ny knapp på forsida, men vi vet ikke hvilket problem den skal løse. "
            "Ikke send noe videre til planlegger ennå.",
            scratch,
            keep_session,
        )
        after = run_git(["status", "--porcelain"], scratch)
        commits = run_git(["rev-list", "--count", "HEAD"], scratch)
        failures: list[str] = []
        if before != after:
            failures.append(f"sparring endret scratch-repoet: {after!r}")
        if commits != "1":
            failures.append(f"sparring opprettet en commit: {commits}")
        if "OPPGAVENOTAT" not in output and "problem" not in output.lower():
            failures.append("sluttsvaret viser ikke problemavklaring eller OPPGAVENOTAT")
        if "planlegger" in output.lower() and "send" in output.lower() and "ja" in output.lower():
            failures.append("sluttsvaret ser ut til å hevde håndoff uten eksplisitt godkjenning")
        return failures
    finally:
        import shutil

        shutil.rmtree(scratch, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run real sparring checks in a scratch repo")
    parser.add_argument("--copilot-bin", default="copilot")
    parser.add_argument("--agent", default="")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--keep-sessions", action="store_true")
    args = parser.parse_args()
    if not args.run:
        parser.error("use --run")
    if not require_copilot_bin(args.copilot_bin):
        return 2
    plugin_name = load_plugin_name(REPO_ROOT)
    agent = resolve_agent(args.agent or f"{plugin_name}:sparring", plugin_name)
    failures = check_no_handoff(args.copilot_bin, agent, args.keep_sessions)
    if failures:
        print("FAIL")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("PASS: sparring gjorde ingen endringer uten eksplisitt håndoff")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
