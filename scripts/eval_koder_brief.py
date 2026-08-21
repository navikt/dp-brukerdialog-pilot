#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


WRAPPER_PREFIX = """Du er planlegger-agenten i en eval-harness.
Ikke bruk verktøy.
Ikke deleger.
Returner kun KODER_BRIEF som ren tekst (ingen markdown-gjerder, ingen forklaring før/etter).
Bruk dette formatet:
KODER_BRIEF
Mål: ...
Sti: ...
Krever planreview: ...
Scope: ...
Ikke gjør: ...
Akseptkriterier:
- ...
Berørte filer:
- ...
Verifisering:
- ...
Nye avhengigheter: ...
Risiko: ...
Git-policy: ...
Oppgave:
"""

REQUIRED_FIELDS = (
    "Mål:",
    "Sti:",
    "Krever planreview:",
    "Scope:",
    "Ikke gjør:",
    "Akseptkriterier:",
    "Berørte filer:",
    "Verifisering:",
    "Nye avhengigheter:",
    "Risiko:",
    "Git-policy:",
)


@dataclass
class Result:
    test_id: int
    status: str
    notes: str
    expected: dict[str, str]
    actual: dict[str, str] | None


def load_json(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_plugin_name(repo_root: Path) -> str:
    plugin_manifest = repo_root / "plugin" / "plugin.json"
    with plugin_manifest.open("r", encoding="utf-8") as file:
        return str(json.load(file)["name"])


def run_copilot(copilot_bin: str, agent: str, prompt: str) -> str:
    command = [
        copilot_bin,
        "--agent",
        agent,
        "-p",
        f"{WRAPPER_PREFIX}{prompt}",
        "-s",
        "--no-ask-user",
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        error_text = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise RuntimeError(error_text)
    return completed.stdout.strip()


def select_tests(tests: list[dict[str, Any]], suite: str) -> list[dict[str, Any]]:
    if suite == "all":
        return tests
    return [test for test in tests if str(test.get("suite", "policy")) == suite]


def parse_brief(text: str) -> dict[str, str] | None:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized.startswith("KODER_BRIEF"):
        return None

    missing = [field for field in REQUIRED_FIELDS if field not in normalized]

    sti_match = re.search(r"^Sti:\s*(.+)$", normalized, flags=re.MULTILINE)
    review_match = re.search(r"^Krever planreview:\s*(.+)$", normalized, flags=re.MULTILINE)
    if sti_match is None or review_match is None:
        return None

    return {
        "sti": sti_match.group(1).strip().lower(),
        "planreview": review_match.group(1).strip().lower(),
        "missing_fields": ",".join(missing),
    }


def aggregate_actuals(actuals: list[dict[str, str] | None], repeats: int) -> tuple[dict[str, str] | None, str, bool]:
    normalized: list[tuple[str, str, str]] = []
    for actual in actuals:
        if actual is None:
            continue
        normalized.append(
            (
                actual.get("sti", ""),
                actual.get("planreview", ""),
                actual.get("missing_fields", ""),
            )
        )

    if not normalized:
        return None, "could not parse brief in any run", False

    counts = Counter(normalized)
    winner, winner_count = counts.most_common(1)[0]
    total_valid = len(normalized)
    has_majority = winner_count > (repeats / 2)
    return {
        "sti": winner[0],
        "planreview": winner[1],
        "missing_fields": winner[2],
    }, f"majority {winner_count}/{total_valid}", has_majority


def score(expected: dict[str, str], actual: dict[str, str] | None) -> tuple[str, str]:
    if actual is None:
        return "fail", "could not parse KODER_BRIEF"

    missing = actual.get("missing_fields", "")
    if missing:
        return "fail", f"missing brief fields: {missing}"

    mismatches: list[str] = []
    for key in ("sti", "planreview"):
        if actual.get(key) != expected.get(key):
            mismatches.append(f"{key}: expected {expected.get(key)!r}, got {actual.get(key)!r}")
    if mismatches:
        return "fail", "; ".join(mismatches)
    return "pass", "brief contract matched"


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    plugin_name = load_plugin_name(repo_root)

    parser = argparse.ArgumentParser(description="Run KODER_BRIEF eval harness for planlegger")
    parser.add_argument("--tests", default="eval/koder-brief-tests.json", help="Path to test JSON")
    parser.add_argument("--agent", default=f"{plugin_name}:planlegger", help="Agent name to run")
    parser.add_argument("--copilot-bin", default="copilot", help="Copilot CLI binary")
    parser.add_argument("--suite", choices=("all", "smoke", "policy"), default="all", help="Test suite selector")
    parser.add_argument("--repeats", type=int, default=1, help="How many runs per test")
    parser.add_argument("--run", action="store_true", help="Run tests")
    args = parser.parse_args()

    if not args.run:
        parser.error("choose --run")
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")

    tests_path = Path(args.tests)
    if not tests_path.is_absolute():
        candidate = (repo_root / tests_path).resolve()
        if candidate.exists():
            tests_path = candidate
        else:
            tests_path = tests_path.resolve()

    tests = select_tests(load_json(tests_path), args.suite)
    if not tests:
        print(f"error: no tests found for suite={args.suite!r}", file=sys.stderr)
        return 2

    if shutil.which(args.copilot_bin) is None:
        print(f"error: {args.copilot_bin!r} not found in PATH", file=sys.stderr)
        return 2

    agent = args.agent if ":" in args.agent else f"{plugin_name}:{args.agent}"

    results: list[Result] = []
    for test in tests:
        test_id = int(test["id"])
        prompt = str(test["prompt"])
        expected = {k: str(v).lower() for k, v in test["expected"].items()}
        try:
            run_actuals: list[dict[str, str] | None] = []
            for _ in range(args.repeats):
                raw = run_copilot(args.copilot_bin, agent, prompt)
                run_actuals.append(parse_brief(raw))

            actual, majority_note, has_majority = aggregate_actuals(run_actuals, args.repeats)
            if not has_majority:
                status = "fail"
                notes = f"inconclusive: {majority_note}"
            else:
                status, notes = score(expected, actual)
                notes = f"{notes} ({majority_note})"
        except Exception as error:  # noqa: BLE001
            actual = None
            status = "error"
            notes = str(error)

        results.append(Result(test_id=test_id, status=status, notes=notes, expected=expected, actual=actual))

    passed = sum(1 for result in results if result.status == "pass")
    failed = len(results) - passed

    for result in results:
        print(f"[{result.status.upper():5}] {result.test_id}: {result.notes}")
    print(f"\nSummary: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
