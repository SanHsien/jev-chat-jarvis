from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import check_vercel_models as checker  # noqa: E402


def test_prefs_declares_every_vercel_model_the_checker_reads() -> None:
    constants = checker.read_constants(checker.PREFS_PATH.read_text(encoding="utf-8"))

    for name in checker.GATED + checker.INFORMATIONAL:
        assert constants.get(name), f"{name} missing from Prefs.kt"


def test_an_unlisted_reply_or_vision_model_fails() -> None:
    constants = {
        "VERCEL_REPLY_MODEL": "example/nope",
        "VERCEL_VISION_MODEL": "google/gemini-2.5-flash",
        "DEFAULT_JUDGE_MODEL_VERCEL": "typesafe-ai/jev",
    }
    _, missing = checker.check(constants, {"google/gemini-2.5-flash"})

    assert missing == ["VERCEL_REPLY_MODEL"]


def test_an_unlisted_judge_model_is_informational_only() -> None:
    constants = {
        "VERCEL_REPLY_MODEL": "a/b",
        "VERCEL_VISION_MODEL": "c/d",
        "DEFAULT_JUDGE_MODEL_VERCEL": "typesafe-ai/jev",
    }
    lines, missing = checker.check(constants, {"a/b", "c/d"})

    assert missing == []
    assert any(line.startswith("INFO DEFAULT_JUDGE_MODEL_VERCEL") for line in lines)


def test_parse_catalog_reads_openai_style_model_list() -> None:
    payload = {"object": "list", "data": [{"id": "a/b"}, {"id": "c/d"}, {"name": "x"}]}

    assert checker.parse_catalog(payload) == {"a/b", "c/d"}
