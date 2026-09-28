#!/usr/bin/env python3
"""Vis hva en oppgave faktisk har endret utover en BASELINE-snapshot.

Bruk sammen med `capture-worktree-baseline.py`. Tar snapshot-mappen som
argument og skriver ut kun det som er endret **etter** at snapshotet ble
tatt — brukerens allerede-eksisterende endringer i arbeidstreet blir ikke
en del av resultatet.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True)
    if result.returncode not in (0, 1):
        # git diff/diff-files returnerer 1 når det finnes forskjeller — ikke en feil.
        raise RuntimeError(f"git {' '.join(args)} feilet: {result.stderr.strip()}")
    return result.stdout


def run_diff(old: Path, new: Path, rel_path: str) -> str:
    result = subprocess.run(
        ["diff", "-u", f"--label=a/{rel_path}", f"--label=b/{rel_path}", str(old), str(new)],
        capture_output=True,
        text=True,
    )
    return result.stdout


def load_meta(snapshot_dir: Path) -> dict:
    meta_path = snapshot_dir / "meta.json"
    if not meta_path.exists():
        raise SystemExit(f"error: fant ikke {meta_path} — er stien en gyldig baseline-snapshot-mappe?")
    return json.loads(meta_path.read_text(encoding="utf-8"))


def diff_tracked(repo_root: Path, baseline_commit: str | None, head_sha: str) -> str:
    ref = baseline_commit or head_sha
    return run_git(repo_root, "diff", "--binary", ref)


def diff_untracked(repo_root: Path, snapshot_dir: Path, baseline_paths: list[str]) -> tuple[str, list[str]]:
    untracked_backup = snapshot_dir / "untracked"
    current_listing = run_git(repo_root, "ls-files", "--others", "--exclude-standard")
    current_paths = {line for line in current_listing.splitlines() if line}
    baseline_paths_set = set(baseline_paths)

    changed_files: list[str] = []
    diff_text_parts: list[str] = []

    for rel_path in sorted(current_paths - baseline_paths_set):
        # Ny untracked fil lagt til av oppgaven.
        current_file = repo_root / rel_path
        diff_text = run_diff(Path("/dev/null"), current_file, rel_path)
        if diff_text:
            diff_text_parts.append(diff_text)
        changed_files.append(rel_path)

    for rel_path in sorted(current_paths & baseline_paths_set):
        backup_file = untracked_backup / rel_path
        current_file = repo_root / rel_path
        diff_text = run_diff(backup_file, current_file, rel_path)
        if diff_text:
            diff_text_parts.append(diff_text)
            changed_files.append(rel_path)

    removed = sorted(baseline_paths_set - current_paths)

    return "".join(diff_text_parts), changed_files + ([f"(fjernet: {p})" for p in removed] if removed else [])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", help="Sti til baseline-snapshot-mappen (fra capture-worktree-baseline.py)")
    parser.add_argument("--repo", default=".", help="Sti til arbeidstreet (default: cwd)")
    args = parser.parse_args()

    snapshot_dir = Path(args.snapshot).resolve()
    meta = load_meta(snapshot_dir)
    repo_root = Path(args.repo).resolve()

    current_branch = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD").strip()
    if current_branch != meta["branch"]:
        print(
            f"ADVARSEL: branch er byttet siden baseline ble tatt "
            f"({meta['branch']!r} -> {current_branch!r}). Diffen under kan være misvisende.",
            file=sys.stderr,
        )

    tracked_diff = diff_tracked(repo_root, meta["baseline_commit"], meta["head_sha"])
    untracked_diff, untracked_changed = diff_untracked(repo_root, snapshot_dir, meta.get("untracked_paths", []))

    tracked_changed = run_git(repo_root, "diff", "--name-only", meta["baseline_commit"] or meta["head_sha"])
    tracked_changed_files = [line for line in tracked_changed.splitlines() if line]

    all_changed = tracked_changed_files + untracked_changed

    if not all_changed:
        print("INGEN_ENDRING_UTOVER_BASELINE")
        return 0

    print("OPPGAVE_DIFF")
    print("Filer endret utover baseline:")
    for path in all_changed:
        print(f"- {path}")
    print()
    if tracked_diff:
        print("--- Diff (tracked filer) ---")
        print(tracked_diff)
    if untracked_diff:
        print("--- Diff (untracked filer) ---")
        print(untracked_diff)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
