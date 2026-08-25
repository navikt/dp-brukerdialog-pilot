#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

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

PLANLEGGER_WRAPPER = """Du er planlegger-agenten i en eval-harness.
Ikke bruk verktøy.
Ikke gjør filendringer.
Ikke deleger til underagenter i denne evalen.
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

KODER_WRAPPER = """Du er koder-agenten i en eval-harness.
Ikke bruk verktøy.
Ikke gjør filendringer.
Dette er en simulert kontrakttest: anta at briefen er gyldig, at filer finnes, og at verifisering kan kjøres.
I denne testen skal du ikke returnere BLOCKED kun fordi verktøy/kjøring er slått av.
Hvis briefen er komplett, bruk DONE eller DONE_WITH_CONCERNS.
Hvis briefen faktisk mangler nødvendig informasjon, bruk NEEDS_CONTEXT.
Returner kun statusrapport i dette faste formatet:
Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | NEEDS_DECISION | BLOCKED
Endrede filer:
- <path>
Hva ble gjort:
- <kort punktliste>
Verifisering:
- <kommando + resultat>
Avvik fra brief:
- <ingen> eller konkret avvik
Brief:
"""

REQUIRED_BRIEF_FIELDS = (
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

REQUIRED_KODER_SECTIONS = (
    "Status:",
    "Endrede filer:",
    "Hva ble gjort:",
    "Verifisering:",
    "Avvik fra brief:",
)

KEY_FIELDS = ("sti", "planreview", "missing_brief_fields", "koder_status", "missing_koder_sections")


def parse_koder_status(text: str) -> dict[str, str] | None:
    normalized = text.replace("\r\n", "\n").strip()
    missing = [section for section in REQUIRED_KODER_SECTIONS if section not in normalized]

    status_match = re.search(r"^Status:\s*([A-Z_]+)\s*$", normalized, flags=re.MULTILINE)
    if status_match is None:
        return None

    return {
        "status": status_match.group(1).strip().lower(),
        "missing_sections": ",".join(missing),
    }


def run_trace_once(
    copilot_bin: str,
    planlegger_agent: str,
    koder_agent: str,
    user_prompt: str,
    keep_sessions: bool = False,
) -> dict[str, str] | None:
    brief_raw = run_copilot(copilot_bin, planlegger_agent, f"{PLANLEGGER_WRAPPER}{user_prompt}", keep_sessions)
    brief = parse_brief(brief_raw, REQUIRED_BRIEF_FIELDS, include_raw=True)
    if brief is None:
        return None

    koder_raw = run_copilot(copilot_bin, koder_agent, f"{KODER_WRAPPER}{brief['raw']}", keep_sessions)
    koder = parse_koder_status(koder_raw)
    if koder is None:
        return None

    return {
        "sti": brief["sti"],
        "planreview": brief["planreview"],
        "missing_brief_fields": brief.get("missing_fields", ""),
        "koder_status": koder["status"],
        "missing_koder_sections": koder.get("missing_sections", ""),
    }


def score(expected: dict[str, Any], actual: dict[str, str] | None) -> tuple[str, str]:
    if actual is None:
        return "fail", "could not parse planlegger->koder trace"

    missing_brief = actual.get("missing_brief_fields", "")
    if missing_brief:
        return "fail", f"missing brief fields: {missing_brief}"

    missing_koder = actual.get("missing_koder_sections", "")
    if missing_koder:
        return "fail", f"missing koder status sections: {missing_koder}"

    mismatches = [
        f"{key}: expected {str(expected.get(key, '')).lower()!r}, got {actual.get(key)!r}"
        for key in ("sti", "planreview")
        if actual.get(key) != str(expected.get(key, "")).lower()
    ]

    allowed_statuses = [str(value).lower() for value in expected.get("koder_statuses", [])]
    if allowed_statuses and actual.get("koder_status") not in allowed_statuses:
        mismatches.append(
            f"koder_status: expected one of {allowed_statuses!r}, got {actual.get('koder_status')!r}"
        )

    if mismatches:
        return "fail", "; ".join(mismatches)
    return "pass", "golden trace matched"


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    plugin_name = load_plugin_name(repo_root)

    parser = argparse.ArgumentParser(description="Run golden trace eval for planlegger -> koder flow")
    parser.add_argument("--tests", default="eval/golden-trace-tests.json", help="Path to test matrix JSON")
    parser.add_argument("--copilot-bin", default="copilot", help="Copilot CLI binary")
    parser.add_argument("--planlegger-agent", default=f"{plugin_name}:planlegger", help="Planlegger agent name")
    parser.add_argument("--koder-agent", default=f"{plugin_name}:koder", help="Koder agent name")
    parser.add_argument("--suite", choices=("all", "smoke", "policy"), default="all", help="Test suite selector")
    parser.add_argument("--repeats", type=int, default=1, help="How many runs per test (majority vote)")
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
    if not require_copilot_bin(args.copilot_bin):
        return 2

    tests_path = resolve_tests_path(repo_root, args.tests)
    tests = select_tests(load_json(tests_path), args.suite)
    if not tests:
        print(f"error: no tests found for suite={args.suite!r}", file=sys.stderr)
        return 2

    results: list[EvalResult] = []
    for test in tests:
        test_id = int(test["id"])
        prompt = str(test["prompt"])
        expected = dict(test["expected"])

        try:
            actuals = [
                run_trace_once(args.copilot_bin, args.planlegger_agent, args.koder_agent, prompt, args.keep_sessions)
                for _ in range(args.repeats)
            ]
            actual, majority_note, has_majority = aggregate_actuals(actuals, args.repeats, key_fields=KEY_FIELDS)
            if not has_majority:
                status = "fail"
                notes = f"inconclusive: {majority_note}"
            else:
                status, notes = score(expected, actual)
                notes = f"{notes} ({majority_note})"
        except Exception as error:  # noqa: BLE001
            status = "error"
            notes = str(error)
            actual = None

        results.append(EvalResult(test_id=test_id, status=status, notes=notes, expected=expected, actual=actual))

    print_report(results, args.suite, args.repeats, args.json)
    failed = sum(1 for r in results if r.status != "pass")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
