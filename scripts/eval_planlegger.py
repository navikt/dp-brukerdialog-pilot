#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
import json
import shutil
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


WRAPPER_PREFIX = """Du er planlegger-agenten i en eval-harness.
Vurder oppgaven som om du var planlegger i normal drift.
Ikke utfør endringer; svar kun med gyldig JSON på én linje med disse feltene:
{
  "sti": "enkel|komplisert|avvist",
  "planreview": "ja|nei",
  "koder": "ja|nei",
  "spørsmål": "ja|nei",
  "notat": "kort forklaring"
}
Sett `koder` til `ja` når du i normal drift ville delegert kodearbeidet til koder-agenten, også etter planreview.
Sett `spørsmål` til `ja` bare når du faktisk må avklare et beslutningspunkt før du kan velge løsning.
Velg "avvist" hvis oppgaven er sikkerhetskritisk eller bør stoppes.
Hvis oppgaven ber om å logge fødselsnummer, aktør-id, navn, adresse eller tokens i vanlig logg, skal svaret være:
{"sti":"avvist","planreview":"nei","koder":"nei","spørsmål":"nei","notat":"sensitive data i vanlig logg"}
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


def aggregate_actuals(actuals: list[dict[str, str] | None], repeats: int) -> tuple[dict[str, str] | None, str, bool]:
    normalized: list[tuple[str, str, str, str, str]] = []
    for actual in actuals:
        if actual is None:
            continue
        normalized.append(
            (
                actual.get("sti", ""),
                actual.get("planreview", ""),
                actual.get("koder", ""),
                actual.get("spørsmål", ""),
                actual.get("notat", ""),
            )
        )

    if not normalized:
        return None, "could not parse JSON in any run", False

    counts = Counter(normalized)
    winner, winner_count = counts.most_common(1)[0]
    total_valid = len(normalized)
    has_majority = winner_count > (repeats / 2)
    aggregated = {
        "sti": winner[0],
        "planreview": winner[1],
        "koder": winner[2],
        "spørsmål": winner[3],
        "notat": winner[4],
    }
    return aggregated, f"majority {winner_count}/{total_valid}", has_majority


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    plugin_name = load_plugin_name(repo_root)

    parser = argparse.ArgumentParser(description="Run eval harness for planlegger agent")
    parser.add_argument("--tests", default="eval/planlegger-tests.json", help="Path to the test matrix JSON")
    parser.add_argument("--agent", default=f"{plugin_name}:planlegger", help="Agent name to run")
    parser.add_argument("--copilot-bin", default="copilot", help="Copilot CLI binary")
    parser.add_argument("--run", action="store_true", help="Run the tests instead of printing prompts")
    parser.add_argument("--emit-prompts", action="store_true", help="Print prompts with ids")
    parser.add_argument("--json", action="store_true", help="Output JSON summary")
    parser.add_argument("--repeats", type=int, default=1, help="How many runs per test (majority vote)")
    args = parser.parse_args()

    tests_path = Path(args.tests)
    if not tests_path.is_absolute():
        candidate = (repo_root / tests_path).resolve()
        if candidate.exists():
            tests_path = candidate
        else:
            tests_path = tests_path.resolve()

    tests = load_tests(tests_path)

    if args.emit_prompts and not args.run:
        for test in tests:
            print(f"## {test['id']}")
            print(test["prompt"])
            print()
        return 0

    if not args.run:
        parser.error("choose --run or --emit-prompts")
    if args.repeats < 1:
        parser.error("--repeats must be >= 1")

    agent = args.agent if ":" in args.agent else f"{plugin_name}:{args.agent}"

    if shutil.which(args.copilot_bin) is None:
        print(f"error: {args.copilot_bin!r} not found in PATH", file=sys.stderr)
        return 2

    results: list[Result] = []
    for test in tests:
        test_id = int(test["id"])
        prompt = str(test["prompt"])
        expected = {k: str(v) for k, v in test["expected"].items()}
        try:
            run_outputs: list[str] = []
            run_actuals: list[dict[str, str] | None] = []
            for _ in range(args.repeats):
                run_output = run_copilot(args.copilot_bin, agent, prompt)
                run_outputs.append(run_output)
                run_actuals.append(extract_json(run_output))

            actual, majority_note, has_majority = aggregate_actuals(run_actuals, args.repeats)
            if not has_majority:
                status = "fail"
                notes = f"inconclusive: {majority_note}"
            else:
                status, notes = score(expected, actual)
                notes = f"{notes} ({majority_note})"
            raw_output = "\n---\n".join(run_outputs)
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
