#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from eval_common import (  # noqa: E402
    EvalResult,
    aggregate_actuals,
    load_json,
    load_plugin_name,
    parse_brief,
    print_report,
    require_copilot_bin,
    resolve_agent,
    resolve_tests_path,
    run_copilot,
    select_tests,
)

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

KEY_FIELDS = ("sti", "planreview", "missing_fields")


def score(expected: dict[str, str], actual: dict[str, str] | None) -> tuple[str, str]:
    if actual is None:
        return "fail", "could not parse KODER_BRIEF"

    missing = actual.get("missing_fields", "")
    if missing:
        return "fail", f"missing brief fields: {missing}"

    mismatches = [
        f"{key}: expected {expected.get(key)!r}, got {actual.get(key)!r}"
        for key in ("sti", "planreview")
        if actual.get(key) != expected.get(key)
    ]
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
                parse_brief(run_copilot(args.copilot_bin, agent, f"{WRAPPER_PREFIX}{prompt}"), REQUIRED_FIELDS)
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
