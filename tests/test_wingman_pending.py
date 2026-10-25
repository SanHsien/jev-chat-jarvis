from __future__ import annotations

from wingman.app.pending import PendingAnalysis


def test_new_message_in_another_chat_keeps_the_first_chat_pending() -> None:
    # 正瀏覽 A（A 有新訊息等分析），LINE 那邊 B 又來了新訊息：A 不能因此被忘掉。
    pending = PendingAnalysis()
    pending.mark("A")
    pending.mark("B")

    assert pending.is_pending("A")
    assert pending.is_pending("B")


def test_analyze_click_consumes_only_the_chat_being_viewed() -> None:
    pending = PendingAnalysis()
    pending.mark("A")
    pending.mark("B")

    assert pending.take("A") is True
    assert not pending.is_pending("A")
    assert pending.is_pending("B")  # B 還在等，沒被 A 的點擊吃掉


def test_take_refuses_a_chat_that_is_not_pending() -> None:
    pending = PendingAnalysis()
    pending.mark("A")

    assert pending.take("B") is False
    assert pending.take(None) is False
    assert pending.is_pending("A")


def test_clear_only_affects_the_named_chat() -> None:
    pending = PendingAnalysis()
    pending.mark("A")
    pending.mark("B")

    assert pending.clear("B") is True
    assert pending.clear("B") is False
    assert pending.is_pending("A")
