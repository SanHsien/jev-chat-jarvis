from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wingman.core import llm  # noqa: E402


@pytest.fixture
def sent(monkeypatch):
    """Stand-in `anthropic` SDK that records the messages.create request."""
    captured: dict = {}

    class FakeClient:
        def __init__(self, **kwargs):
            self.messages = SimpleNamespace(create=self.create)

        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                content=[
                    SimpleNamespace(type="thinking", thinking=""),
                    SimpleNamespace(type="text", text="好"),
                ]
            )

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(Anthropic=FakeClient))
    return captured


def draft(model: str, thinking: bool) -> str:
    # draft.py passes temperature=1.2 and max_tokens=400 when thinking is off
    return llm.chat(
        "anthropic",
        None,
        "k",
        model,
        "sys",
        ["hi"],
        temperature=1.2,
        max_tokens=400,
        thinking=thinking,
    )


@pytest.mark.parametrize("model", ["claude-opus-5-5", "claude-haiku-5-5", "claude-sonnet-4-5"])
def test_anthropic_never_sends_temperature(sent, model) -> None:
    # 1.2 is outside Anthropic's 0-1 range, and current models 400 on any non-default value
    assert draft(model, thinking=False) == "好"
    assert "temperature" not in sent
    assert sent["max_tokens"] >= 4096  # thinking counts toward max_tokens on current models


@pytest.mark.parametrize(
    "model", ["claude-opus-5-5", "claude-sonnet-5-5", "claude-haiku-5-5", "claude-opus-4-7"]
)
def test_current_models_get_adaptive_thinking_not_a_budget(sent, model) -> None:
    draft(model, thinking=True)
    assert sent["thinking"] == {"type": "adaptive"}


def test_older_model_keeps_manual_budget(sent) -> None:
    # Claude Haiku 4.5 supports only manual extended thinking
    draft("claude-haiku-4-5", thinking=True)
    assert sent["thinking"]["type"] == "enabled"
    assert sent["max_tokens"] > sent["thinking"]["budget_tokens"]
