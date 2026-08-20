#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


WRAPPER_PREFIX = """Du er planlegger-agenten i en eval-harness.
Ikke deleger til andre agenter.
Ikke bruk verktøy.
Svar kun med gyldig JSON på én linje med disse feltene:
{
  "sti": "enkel|komplisert|avvist",
  "planreview": "ja|nei",
  "koder": "ja|nei",
  "spørsmål": "ja|nei",
  "notat": "kort forklaring"
}
Velg "avvist" hvis oppgaven er sikkerhetskritisk eller bør stoppes.
Oppgave:
"""


@dataclass
class Result:
    test_id: int
    prompt: str
    status: str
    expected: dict[str, str]
    actual: dict[str, str] | None
    raw_output: str
    notes: str


def load_tests(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


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


def extract_json(text: str) -> dict[str, str] | None:
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json\n", "", 1)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return {
                "sti": str(parsed.get("sti", "")).strip().lower(),
                "planreview": str(parsed.get("planreview", "")).strip().lower(),
                "koder": str(parsed.get("koder", "")).strip().lower(),
                "spørsmål": str(parsed.get("spørsmål", "")).strip().lower(),
                "notat": str(parsed.get("notat", "")).strip(),
            }
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if match is None:
            return None
        try:
            parsed = json.loads(match.group(0))
            if isinstance(parsed, dict):
                return {
                    "sti": str(parsed.get("sti", "")).strip().lower(),
                    "planreview": str(parsed.get("planreview", "")).strip().lower(),
                    "koder": str(parsed.get("koder", "")).strip().lower(),
                    "spørsmål": str(parsed.get("spørsmål", "")).strip().lower(),
                    "notat": str(parsed.get("notat", "")).strip(),
                }
        except json.JSONDecodeError:
            return None
    return None


def score(expected: dict[str, str], actual: dict[str, str] | None) -> tuple[str, str]:
    if actual is None:
        return "fail", "could not parse JSON"

    mismatches: list[str] = []
    for key in ("sti", "planreview", "koder", "spørsmål"):
        if actual.get(key) != expected.get(key):
            mismatches.append(f"{key}: expected {expected.get(key)!r}, got {actual.get(key)!r}")

    if mismatches:
        return "fail", "; ".join(mismatches)
    return "pass", "matched expected decision"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run eval harness for planlegger agent")
    parser.add_argument("--tests", default="eval/planlegger-tests.json", help="Path to the test matrix JSON")
    parser.add_argument("--agent", default="planlegger", help="Agent name to run")
    parser.add_argument("--copilot-bin", default="copilot", help="Copilot CLI binary")
    parser.add_argument("--run", action="store_true", help="Run the tests instead of printing prompts")
    parser.add_argument("--emit-prompts", action="store_true", help="Print prompts with ids")
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    args = parser.parse_args()

    tests_path = Path(args.tests)
    tests = load_tests(tests_path)

    if args.emit_prompts and not args.run:
        for test in tests:
            print(f"## {test['id']}")
            print(test["prompt"])
            print()
        return 0

    if not args.run:
        parser.error("choose --run or --emit-prompts")

    if shutil.which(args.copilot_bin) is None:
        print(f"error: {args.copilot_bin!r} not found in PATH", file=sys.stderr)
        return 2

    results: list[Result] = []
    for test in tests:
        test_id = int(test["id"])
        prompt = str(test["prompt"])
        expected = {k: str(v) for k, v in test["expected"].items()}
        try:
            raw_output = run_copilot(args.copilot_bin, args.agent, prompt)
            actual = extract_json(raw_output)
            status, notes = score(expected, actual)
        except Exception as error:  # noqa: BLE001
            raw_output = ""
            actual = None
            status = "error"
            notes = str(error)

        results.append(
            Result(
                test_id=test_id,
                prompt=prompt,
                status=status,
                expected=expected,
                actual=actual,
                raw_output=raw_output,
                notes=notes,
            )
        )

    passed = sum(1 for result in results if result.status == "pass")
    failed = len(results) - passed

    if args.json:
        print(
            json.dumps(
                {
                    "passed": passed,
                    "failed": failed,
                    "results": [
                        {
                            "id": result.test_id,
                            "status": result.status,
                            "notes": result.notes,
                            "expected": result.expected,
                            "actual": result.actual,
                        }
                        for result in results
                    ],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        for result in results:
            print(f"[{result.status.upper():5}] {result.test_id}: {result.notes}")
        print(f"\nSummary: {passed} passed, {failed} failed")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
