"""Contract eval for the sparring agent.

The harness asks the agent to classify its own response as JSON. It checks the
observable contract without requiring a real repository or board connection:
the note fields, question count, and whether handoff was explicitly allowed.
Real file-safety and handoff checks live in eval_sparring_integration.py.
"""
from __future__ import annotations

import argparse
import json
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
    print_report,
    require_copilot_bin,
    resolve_agent,
    resolve_tests_path,
    run_copilot,
    select_tests,
)

REPO_ROOT = Path(__file__).resolve().parents[1]

WRAPPER_PREFIX = """Du er sparring-agenten i en eval-harness.
Vurder brukerprompten som om du var sparring-agenten i normal drift.
Ikke bruk verktøy, ikke gjør filendringer og ikke kall andre agenter.
Svar kun med gyldig JSON på én linje:
{
  "notat": "hele OPPGAVENOTAT-blokken hvis du kom så langt, ellers kort status",
  "spurte_om_problem": "ja|nei",
  "spurte_om_effekt": "ja|nei",
  "antall_spørsmål": 0,
  "håndoff": "ja|nei"
}
`håndoff` skal være "ja" bare hvis brukerprompten uttrykkelig godkjenner
at notatet sendes til planlegger. Ikke tell agentens interne vurdering som
et spørsmål. Bruk `notat` til å vise feltnavnene du faktisk fylte ut.
Brukerprompt:
"""

KEY_FIELDS = ("spurte_om_problem", "spurte_om_effekt", "antall_spørsmål", "håndoff")


def extract_json(text: str) -> dict[str, Any] | None:
    text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match is None:
            return None
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(parsed, dict):
        return None
    return {
        "notat": str(parsed.get("notat", "")),
        "spurte_om_problem": str(parsed.get("spurte_om_problem", "")).strip().lower(),
        "spurte_om_effekt": str(parsed.get("spurte_om_effekt", "")).strip().lower(),
        "antall_spørsmål": int(parsed.get("antall_spørsmål", -1)),
        "håndoff": str(parsed.get("håndoff", "")).strip().lower(),
    }


def score(expected: dict[str, Any], actual: dict[str, Any] | None) -> tuple[str, str]:
    if actual is None:
        return "fail", "could not parse JSON"

    mismatches: list[str] = []
    for key in KEY_FIELDS:
        if key in expected and key not in ("spurte_om_effekt", "antall_spørsmål"):
            if actual.get(key) != expected.get(key):
                mismatches.append(f"{key}: expected {expected.get(key)!r}, got {actual.get(key)!r}")
        elif key in expected and actual.get(key) != expected.get(key):
            mismatches.append(f"{key}: expected {expected.get(key)!r}, got {actual.get(key)!r}")

    if expected.get("requires_effect_handling"):
        note = actual.get("notat", "").lower()
        asked = actual.get("spurte_om_effekt") == "ja"
        recorded = any(term in note for term in ("åpne spørsmål", "antakelse", "målepunkt", "effekt"))
        if not asked and not recorded:
            mismatches.append("manglende effekt må enten utløse ett spørsmål eller bli registrert som åpent")

    note = actual.get("notat", "")
    for required_field in expected.get("notat_contains", []):
        if required_field not in note:
            mismatches.append(f"notat mangler {required_field!r}")

    if mismatches:
        return "fail", "; ".join(mismatches)
    return "pass", "matched sparring contract"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run eval harness for sparring agent")
    parser.add_argument("--tests", default="eval/sparring-tests.json")
    parser.add_argument("--agent", default="")
    parser.add_argument("--copilot-bin", default="copilot")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--emit-prompts", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--keep-sessions", action="store_true")
    parser.add_argument("--suite", choices=("all", "smoke", "policy"), default="all")
    args = parser.parse_args()

    plugin_name = load_plugin_name(REPO_ROOT)
    tests = select_tests(load_json(resolve_tests_path(REPO_ROOT, args.tests)), args.suite)
    if not tests:
        print(f"error: no tests found for suite={args.suite!r}", file=sys.stderr)
        return 2
    if args.emit_prompts and not args.run:
        for test in tests:
            print(f"## {test['id']}\n{test['prompt']}\n")
        return 0
    if not args.run:
        parser.error("choose --run or --emit-prompts")
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")
    if not require_copilot_bin(args.copilot_bin):
        return 2

    agent = resolve_agent(args.agent or f"{plugin_name}:sparring", plugin_name)
    results: list[EvalResult] = []
    for test in tests:
        expected = dict(test["expected"])
        actuals = [
            extract_json(run_copilot(args.copilot_bin, agent, f"{WRAPPER_PREFIX}{test['prompt']}", args.keep_sessions))
            for _ in range(args.repeats)
        ]
        actual, majority_note, has_majority = aggregate_actuals(
            actuals,
            args.repeats,
            key_fields=KEY_FIELDS,
            passthrough_fields=("notat",),
        )
        if not has_majority:
            status, notes = "fail", f"inconclusive: {majority_note}"
        else:
            status, notes = score(expected, actual)
            notes = f"{notes} ({majority_note})"
        results.append(
            EvalResult(
                test_id=int(test["id"]),
                status=status,
                notes=notes,
                expected=expected,
                actual=actual,
            )
        )

    print_report(results, args.suite, args.repeats, args.json)
    return 0 if all(result.status == "pass" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
