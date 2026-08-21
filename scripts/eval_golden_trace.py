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


@dataclass
class TraceResult:
    test_id: int
    status: str
    notes: str


def load_tests(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def select_tests(tests: list[dict[str, Any]], suite: str) -> list[dict[str, Any]]:
    if suite == "all":
        return tests
    return [test for test in tests if str(test.get("suite", "policy")) == suite]


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
        prompt,
        "-s",
        "--no-ask-user",
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        error_text = completed.stderr.strip() or completed.stdout.strip() or "unknown error"
        raise RuntimeError(error_text)
    return completed.stdout.strip()


def parse_brief(text: str) -> dict[str, str] | None:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized.startswith("KODER_BRIEF"):
        return None

    missing = [field for field in REQUIRED_BRIEF_FIELDS if field not in normalized]
    sti_match = re.search(r"^Sti:\s*(.+)$", normalized, flags=re.MULTILINE)
    review_match = re.search(r"^Krever planreview:\s*(.+)$", normalized, flags=re.MULTILINE)
    if sti_match is None or review_match is None:
        return None

    return {
        "sti": sti_match.group(1).strip().lower(),
        "planreview": review_match.group(1).strip().lower(),
        "missing_fields": ",".join(missing),
        "raw": normalized,
    }


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
) -> dict[str, str] | None:
    brief_raw = run_copilot(copilot_bin, planlegger_agent, f"{PLANLEGGER_WRAPPER}{user_prompt}")
    brief = parse_brief(brief_raw)
    if brief is None:
        return None

    koder_raw = run_copilot(copilot_bin, koder_agent, f"{KODER_WRAPPER}{brief['raw']}")
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


def aggregate_runs(actuals: list[dict[str, str] | None], repeats: int) -> tuple[dict[str, str] | None, str, bool]:
    normalized: list[tuple[str, str, str, str, str]] = []
    for actual in actuals:
        if actual is None:
            continue
        normalized.append(
            (
                actual.get("sti", ""),
                actual.get("planreview", ""),
                actual.get("missing_brief_fields", ""),
                actual.get("koder_status", ""),
                actual.get("missing_koder_sections", ""),
            )
        )

    if not normalized:
        return None, "could not parse trace in any run", False

    counts = Counter(normalized)
    winner, winner_count = counts.most_common(1)[0]
    total_valid = len(normalized)
    has_majority = winner_count > (repeats / 2)
    return {
        "sti": winner[0],
        "planreview": winner[1],
        "missing_brief_fields": winner[2],
        "koder_status": winner[3],
        "missing_koder_sections": winner[4],
    }, f"majority {winner_count}/{total_valid}", has_majority


def score(expected: dict[str, Any], actual: dict[str, str] | None) -> tuple[str, str]:
    if actual is None:
        return "fail", "could not parse planlegger->koder trace"

    missing_brief = actual.get("missing_brief_fields", "")
    if missing_brief:
        return "fail", f"missing brief fields: {missing_brief}"

    missing_koder = actual.get("missing_koder_sections", "")
    if missing_koder:
        return "fail", f"missing koder status sections: {missing_koder}"

    mismatches: list[str] = []
    for key in ("sti", "planreview"):
        expected_value = str(expected.get(key, "")).lower()
        if actual.get(key) != expected_value:
            mismatches.append(f"{key}: expected {expected_value!r}, got {actual.get(key)!r}")

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
    parser.add_argument("--run", action="store_true", help="Run tests")
    args = parser.parse_args()

    if not args.run:
        parser.error("choose --run")
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")
    if shutil.which(args.copilot_bin) is None:
        print(f"error: {args.copilot_bin!r} not found in PATH", file=sys.stderr)
        return 2

    tests_path = Path(args.tests)
    if not tests_path.is_absolute():
        candidate = (repo_root / tests_path).resolve()
        if candidate.exists():
            tests_path = candidate
        else:
            tests_path = tests_path.resolve()

    tests = select_tests(load_tests(tests_path), args.suite)
    if not tests:
        print(f"error: no tests found for suite={args.suite!r}", file=sys.stderr)
        return 2

    results: list[TraceResult] = []
    for test in tests:
        test_id = int(test["id"])
        prompt = str(test["prompt"])
        expected = dict(test["expected"])

        try:
            actuals: list[dict[str, str] | None] = []
            for _ in range(args.repeats):
                actuals.append(
                    run_trace_once(
                        copilot_bin=args.copilot_bin,
                        planlegger_agent=args.planlegger_agent,
                        koder_agent=args.koder_agent,
                        user_prompt=prompt,
                    )
                )

            actual, majority_note, has_majority = aggregate_runs(actuals, args.repeats)
            if not has_majority:
                status = "fail"
                notes = f"inconclusive: {majority_note}"
            else:
                status, notes = score(expected, actual)
                notes = f"{notes} ({majority_note})"
        except Exception as error:  # noqa: BLE001
            status = "error"
            notes = str(error)

        results.append(TraceResult(test_id=test_id, status=status, notes=notes))

    passed = sum(1 for result in results if result.status == "pass")
    failed = len(results) - passed

    for result in results:
        print(f"[{result.status.upper():5}] {result.test_id}: {result.notes}")
    print(f"\nSummary: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
