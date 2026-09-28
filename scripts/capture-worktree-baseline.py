#!/usr/bin/env python3
"""Ta et innholdsbasert snapshot av arbeidstreet før planlegger delegerer.

Erstatter `git status --porcelain` som BASELINE: den forteller bare *hvilke*
filer som er endret, ikke *hva* som er endret i dem. Hvis brukeren allerede
har endret en fil før oppgaven starter, og `koder` også endrer samme fil, kan
`git status` ikke skille de to endringene fra hverandre.

Snapshotet består av:
- branch og HEAD-sha
- en commit laget med `git stash create` som representerer tracked filers
  index+arbeidstre-tilstand, uten å røre index, arbeidstre eller stash-listen
- en rå kopi av alle untracked (ikke-ignorerte) filer, slik at
  `diff-from-baseline.py` senere kan diffe dem direkte med `diff -u`

Alt lagres under `.git/pilot-baseline/<id>/` — aldri i det sporede
arbeidstreet, og skal ikke committes.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path


def run_git(repo_root: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo_root), *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} feilet: {result.stderr.strip()}")
    return result.stdout.strip()


def resolve_repo_root(start: Path) -> Path:
    try:
        return Path(run_git(start, "rev-parse", "--show-toplevel"))
    except RuntimeError as error:
        raise SystemExit(f"error: ikke et git-repo: {start} ({error})") from error


def capture_baseline_commit(repo_root: Path) -> str | None:
    """Commit-sha som representerer tracked filers nåværende innhold, uten å
    røre index/arbeidstre/stash-refs. `None` hvis arbeidstreet er identisk
    med HEAD (ingenting å stashe)."""
    sha = run_git(repo_root, "stash", "create", "pilot-baseline-snapshot")
    return sha or None


def backup_untracked(repo_root: Path, dest: Path) -> list[str]:
    listing = run_git(repo_root, "ls-files", "--others", "--exclude-standard")
    paths = [line for line in listing.splitlines() if line]
    for rel_path in paths:
        src = repo_root / rel_path
        target = dest / rel_path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, target)
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".", help="Sti til arbeidstreet (default: cwd)")
    parser.add_argument("--label", default=None, help="Fritekst-etikett for oppgaven (valgfritt)")
    args = parser.parse_args()

    repo_root = resolve_repo_root(Path(args.repo).resolve())
    branch = run_git(repo_root, "rev-parse", "--abbrev-ref", "HEAD")
    head_sha = run_git(repo_root, "rev-parse", "HEAD")

    try:
        baseline_commit = capture_baseline_commit(repo_root)
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    snapshot_id = f"baseline-{int(time.time())}"
    snapshot_dir = repo_root / ".git" / "pilot-baseline" / snapshot_id
    untracked_dir = snapshot_dir / "untracked"
    untracked_dir.mkdir(parents=True, exist_ok=True)

    untracked_paths = backup_untracked(repo_root, untracked_dir)

    meta = {
        "version": 1,
        "repo_root": str(repo_root),
        "branch": branch,
        "head_sha": head_sha,
        "baseline_commit": baseline_commit,
        "untracked_paths": untracked_paths,
        "label": args.label,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (snapshot_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"BASELINE_SNAPSHOT={snapshot_dir}")
    print(f"Branch={branch}")
    print(f"Head={head_sha}")
    print(f"Baseline-commit={baseline_commit or '(ingen endringer i tracked filer, lik HEAD)'}")
    print(f"Untracked-filer-fanget={len(untracked_paths)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
