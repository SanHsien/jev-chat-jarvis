"""Check that the Vercel AI Gateway model ids this fork ships as defaults exist.

`Prefs.kt` seeds fresh installs to Vercel AI Gateway for the reply and vision routes
(see docs/DIVERGENCE.md). A model id that the gateway does not list fails only at
runtime, on the user's phone, as an HTTP error in the settings page's test button.
This reads the ids straight out of `Prefs.kt` and asks the gateway's public model
catalog (`GET /v1/models`, no key needed) whether each one is listed.

The judge route (`typesafe-ai/jev`) goes through the gateway's TypeSafe-compatible
path rather than the OpenAI-compatible catalog, so it is reported but never gates.

    python tools/check_vercel_models.py [--catalog FILE]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PREFS_PATH = REPO_ROOT / "app/src/main/java/com/jev/probe/core/Prefs.kt"
CATALOG_URL = "https://ai-gateway.vercel.sh/v1/models"
GATED = ("VERCEL_REPLY_MODEL", "VERCEL_VISION_MODEL")
INFORMATIONAL = ("DEFAULT_JUDGE_MODEL_VERCEL",)

_CONST_RE = re.compile(r'const val (\w+)\s*=\s*"([^"]*)"')


def read_constants(text: str) -> dict[str, str]:
    return dict(_CONST_RE.findall(text))


def parse_catalog(payload: dict) -> set[str]:
    return {
        item["id"] for item in payload.get("data", []) if isinstance(item, dict) and "id" in item
    }


def fetch_catalog(timeout: float = 20.0) -> dict:
    request = urllib.request.Request(
        CATALOG_URL, headers={"User-Agent": "jev-chat-jarvis-vercel-models"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def check(constants: dict[str, str], catalog: set[str]) -> tuple[list[str], list[str]]:
    """Return (report lines, missing gated names)."""
    lines: list[str] = []
    missing: list[str] = []
    for name in GATED + INFORMATIONAL:
        model = constants.get(name)
        if model is None:
            lines.append(f"MISSING CONST {name} (not found in Prefs.kt)")
            if name in GATED:
                missing.append(name)
            continue
        listed = model in catalog
        tag = "OK  " if listed else ("FAIL" if name in GATED else "INFO")
        lines.append(f"{tag} {name} = {model} ({'listed' if listed else 'not listed'})")
        if not listed and name in GATED:
            missing.append(name)
    return lines, missing


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, help="Read the catalog JSON from a file.")
    args = parser.parse_args()

    constants = read_constants(PREFS_PATH.read_text(encoding="utf-8"))
    try:
        if args.catalog:
            payload = json.loads(args.catalog.read_text(encoding="utf-8"))
        else:
            payload = fetch_catalog()
    except (OSError, ValueError) as exc:
        print(f"ERROR: could not read the Vercel model catalog: {exc}")
        return 2
    catalog = parse_catalog(payload)
    if not catalog:
        print("ERROR: the Vercel model catalog came back empty")
        return 2

    lines, missing = check(constants, catalog)
    print("\n".join(lines))
    if missing:
        print(f"\n{len(missing)} shipped Vercel model id(s) are not in the gateway catalog.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
