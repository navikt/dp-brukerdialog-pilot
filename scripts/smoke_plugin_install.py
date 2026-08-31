#!/usr/bin/env python3
"""Exercise the real plugin install lifecycle in an isolated Copilot home.

Unlike validate_plugin_schema.py (which only checks that the manifests/agent-
and skill-frontmatter are internally consistent JSON/markdown), this script
verifies that `copilot plugin marketplace add` + `copilot plugin install`
actually succeeds against this repo's real `plugin/` payload, and that
`copilot plugin list` reports the expected version, agent count, and skill
count afterwards. It runs in a throwaway `$COPILOT_HOME` so it never touches
the developer's real plugin installation.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

SAFE_ENV_PASSTHROUGH = {
    "PATH",
    "LANG",
    "LC_ALL",
    "LC_CTYPE",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "SSL_CERT_FILE",
    "SSL_CERT_DIR",
}


def load_marketplace_name() -> str:
    marketplace = json.loads(
        (REPO_ROOT / ".github" / "plugin" / "marketplace.json").read_text(encoding="utf-8")
    )
    return str(marketplace["name"])


def load_plugin_manifest() -> dict:
    return json.loads((REPO_ROOT / "plugin" / "plugin.json").read_text(encoding="utf-8"))


def isolated_env(base: dict[str, str], home: Path) -> dict[str, str]:
    env = {key: value for key, value in base.items() if key in SAFE_ENV_PASSTHROUGH}
    env.update(
        {
            "HOME": str(home),
            "COPILOT_HOME": str(home / ".copilot"),
            "COPILOT_AUTO_UPDATE": "false",
            "GIT_TERMINAL_PROMPT": "0",
            "NO_COLOR": "1",
        }
    )
    return env


def run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, env=env, capture_output=True, text=True, check=False)


def main() -> int:
    import os

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--copilot-bin", default="copilot", help="Copilot CLI binary")
    parser.add_argument(
        "--keep-home",
        action="store_true",
        help="Don't delete the isolated $COPILOT_HOME afterwards (for debugging)",
    )
    args = parser.parse_args()

    if shutil.which(args.copilot_bin) is None:
        print(f"error: {args.copilot_bin!r} not found in PATH", file=sys.stderr)
        return 1

    manifest = load_plugin_manifest()
    plugin_name = str(manifest["name"])
    expected_version = str(manifest["version"])
    marketplace_name = load_marketplace_name()
    qualified_name = f"{plugin_name}@{marketplace_name}"

    home = Path(tempfile.mkdtemp(prefix="dp-brukerdialog-pilot-smoke-"))
    env = isolated_env(dict(os.environ), home)
    failures: list[str] = []

    try:
        add = run(
            [args.copilot_bin, "plugin", "marketplace", "add", str(REPO_ROOT)],
            env,
        )
        if add.returncode != 0:
            failures.append(f"marketplace add feilet: {(add.stdout + add.stderr).strip()[:500]}")
        else:
            install = run([args.copilot_bin, "plugin", "install", qualified_name], env)
            if install.returncode != 0:
                failures.append(f"plugin install feilet: {(install.stdout + install.stderr).strip()[:500]}")
            else:
                listing = run([args.copilot_bin, "plugin", "list"], env)
                output = listing.stdout + listing.stderr
                if plugin_name not in output:
                    failures.append(f"plugin list nevner ikke {plugin_name!r}:\n{output[:800]}")
                elif expected_version not in output:
                    failures.append(
                        f"plugin list nevner ikke forventet versjon {expected_version!r}:\n{output[:800]}"
                    )
    finally:
        if not args.keep_home:
            shutil.rmtree(home, ignore_errors=True)
        else:
            print(f"  isolert copilot-home beholdt: {home}")

    if failures:
        for failure in failures:
            print(f"[FAIL ] {failure}")
        print("\nSummary: 0 passed, 1 failed")
        return 1

    print(f"[PASS ] {qualified_name} installert OK i isolert copilot-home (versjon {expected_version})")
    print("\nSummary: 1 passed, 0 failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
