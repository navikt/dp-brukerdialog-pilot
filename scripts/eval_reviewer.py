#!/usr/bin/env python3
"""Contract eval for the `reviewer` agent.

Feeds `reviewer` a synthetic KODER_BRIEF + koder-report pair (no real
delegation, no real files) and checks that it returns the expected
Reviewer-status verdict. Mirrors eval_koder_brief.py's structure/pattern.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_common import (  # noqa: E402
    EvalResult,
    aggregate_actuals,
    load_json,
    load_plugin_name,
    print_report,
    require_copilot_bin,
    resolve_agent,
    resolve_tests_path,
    run_copilot,
    select_tests,
)

WRAPPER_PREFIX = """Du er reviewer-agenten i en eval-harness.
Ikke bruk verktøy.
Ikke gjør kodeendringer.
Returner kun i dette faste formatet (ingen markdown-gjerder, ingen forklaring før/etter):
Reviewer-status: APPROVED | NEEDS_CHANGES | BLOCKED
Begrunnelse:
- ...
Konkret endring nødvendig (kun ved NEEDS_CHANGES):
- ...

Vurder følgende brief og rapport fra koder:
"""

KEY_FIELDS = ("status",)


def parse_reviewer_status(text: str) -> dict[str, str] | None:
    normalized = text.replace("\r\n", "\n").strip()
    match = re.search(r"Reviewer-status:\s*(APPROVED|NEEDS_CHANGES|BLOCKED)", normalized, flags=re.IGNORECASE)
    if match is None:
        return None
    return {"status": match.group(1).strip().lower()}


def score(expected: dict[str, str], actual: dict[str, str] | None) -> tuple[str, str]:
    if actual is None:
        return "fail", "could not parse Reviewer-status"
    if actual.get("status") != expected.get("status"):
        return "fail", f"status: expected {expected.get('status')!r}, got {actual.get('status')!r}"
    return "pass", "reviewer status matched"


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    plugin_name = load_plugin_name(repo_root)

    parser = argparse.ArgumentParser(description="Run reviewer-status eval harness")
    parser.add_argument("--tests", default="eval/reviewer-tests.json", help="Path to test JSON")
    parser.add_argument("--agent", default=f"{plugin_name}:reviewer", help="Agent name to run")
    parser.add_argument("--copilot-bin", default="copilot", help="Copilot CLI binary")
    parser.add_argument("--suite", choices=("all", "smoke", "policy"), default="all", help="Test suite selector")
    parser.add_argument("--repeats", type=int, default=1, help="How many runs per test")
    parser.add_argument(
        "--keep-sessions",
        action="store_true",
        help="Don't delete the local copilot sessions created by each run (default: delete)",
    )
    parser.add_argument("--run", action="store_true", help="Run tests")
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    args = parser.parse_args()

    if not args.run:
        parser.error("choose --run")
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")

    tests_path = resolve_tests_path(repo_root, args.tests)
    tests = select_tests(load_json(tests_path), args.suite)
    if not tests:
        print(f"error: no tests found for suite={args.suite!r}", file=sys.stderr)
        return 2
    if not require_copilot_bin(args.copilot_bin):
        return 2

    agent = resolve_agent(args.agent, plugin_name)

    results: list[EvalResult] = []
    for test in tests:
        test_id = int(test["id"])
        prompt = str(test["prompt"])
        expected = {k: str(v).lower() for k, v in test["expected"].items()}
        try:
            run_actuals = [
                parse_reviewer_status(run_copilot(args.copilot_bin, agent, f"{WRAPPER_PREFIX}{prompt}", args.keep_sessions))
                for _ in range(args.repeats)
            ]
            actual, majority_note, has_majority = aggregate_actuals(run_actuals, args.repeats, key_fields=KEY_FIELDS)
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

        results.append(EvalResult(test_id=test_id, status=status, notes=notes, expected=expected, actual=actual))

    print_report(results, args.suite, args.repeats, args.json)
    failed = sum(1 for r in results if r.status != "pass")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
