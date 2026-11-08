from __future__ import annotations

import queue
import sys
import unittest.mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wingman.app.pending import PendingAnalysis, should_rerun_on_target_change  # noqa: E402


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


def test_should_rerun_on_target_change_semi_auto_with_active_result() -> None:
    # 半自動下，若當前會話已分析過且結果仍有效，換回覆對象應自動以新對象重跑
    assert (
        should_rerun_on_target_change(
            auto_analyze=False,
            has_her_message=True,
            has_active_result=True,
        )
        is True
    )


def test_should_rerun_on_target_change_semi_auto_without_active_result() -> None:
    # 半自動下，若尚未分析過（或新訊息進來後舊結果已作廢），換回覆對象不應重跑，只更新 pending
    assert (
        should_rerun_on_target_change(
            auto_analyze=False,
            has_her_message=True,
            has_active_result=False,
        )
        is False
    )


def test_should_rerun_on_target_change_no_her_message() -> None:
    # 會話中沒有對方的訊息時，不論是否全自動或有無結果，都不應重跑
    assert (
        should_rerun_on_target_change(
            auto_analyze=True,
            has_her_message=False,
            has_active_result=True,
        )
        is False
    )


def test_should_rerun_on_target_change_auto_analyze_mode() -> None:
    # 全自動模式下，只要有對方訊息，換對象即重跑
    assert (
        should_rerun_on_target_change(
            auto_analyze=True,
            has_her_message=True,
            has_active_result=False,
        )
        is True
    )


def _setup_wingman():
    for mod in [
        "PySide6",
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "qfluentwidgets",
        "rapidocr_onnxruntime",
        "numpy",
        "windows_capture",
    ]:
        sys.modules.setdefault(mod, unittest.mock.MagicMock())
    import wingman.__main__ as wm

    wm.q = queue.Queue()
    mock_ov = unittest.mock.MagicMock()
    mock_ov.current_chat.return_value = "chat1"
    mock_ov.is_pending.return_value = False
    wm.ov = mock_ov
    wm.chats.clear()
    wm.state["busy"] = False
    wm.state["rerun"] = None
    return wm, mock_ov


def test_drain_clears_result_preventing_rerun_on_target_change() -> None:
    # 關鍵行為：收到新訊息時清空 chat["result"]。
    # 若刪除 wingman/__main__.py 的 chat["result"] = None，
    # 舊結果未清空，半自動模式下換對象會被誤判為「已有有效結果」而觸發 start_analyze。
    wm, mock_ov = _setup_wingman()
    chat = wm.chat_of("chat1")
    chat["result"] = {"candidates": ["prev_suggestion"]}
    chat["history"].append(("her", "Alice", "prev_msg"))
    chat["senders"] = ["Alice", "Bob"]
    mock_ov.is_pending.return_value = True

    # 新訊息到達
    wm.q.put(("chat_msg", "chat1", [("her", "Alice", "new_msg")], (0, 0, 10, 10)))
    wm.drain()

    # 驗證 1：舊結果必須被清空（若刪除該行則此處失敗）
    assert chat["result"] is None

    # 驗證 2：換對象時不應觸發分析
    start_mock = unittest.mock.MagicMock()
    wm.start_analyze = start_mock
    wm.on_target_change("chat1", "Bob")
    assert start_mock.call_count == 0


def test_drain_user_reply_clears_result_and_clears_pending() -> None:
    # 使用者自己回覆訊息後，快取結果應被清空（show_cached 切換時回傳 None 顯示空態，而非過期建議），
    # 且應呼叫 clear_pending 清除待處理狀態。
    wm, mock_ov = _setup_wingman()
    chat = wm.chat_of("chat1")
    chat["result"] = {"candidates": ["prev_suggestion"]}
    chat["history"].append(("her", "Alice", "prev_msg"))
    chat["senders"] = ["Alice", "Bob"]

    wm.q.put(("chat_msg", "chat1", [("me", None, "I replied")], (0, 0, 10, 10)))
    wm.drain()

    assert chat["result"] is None
    mock_ov.clear_pending.assert_called_with("chat1")
    mock_ov.set_status.assert_called_with("你已回覆，等待對方的新訊息")


def test_on_target_change_after_reply_does_not_resurrect_pending() -> None:
    # 邊界：自己回覆後（非 pending），使用者在下拉選單切換回覆對象，
    # 不得錯誤重新呼叫 set_pending 讓「分析」待處理按鈕復現。
    wm, mock_ov = _setup_wingman()
    chat = wm.chat_of("chat1")
    chat["history"].append(("her", "Alice", "hello"))
    chat["history"].append(("me", None, "hi"))
    chat["senders"] = ["Alice", "Bob"]
    chat["result"] = None
    mock_ov.is_pending.return_value = False

    start_mock = unittest.mock.MagicMock()
    wm.start_analyze = start_mock

    wm.on_target_change("chat1", "Bob")

    assert mock_ov.set_pending.call_count == 0
    assert start_mock.call_count == 0
    assert chat["target"] == "Bob"


def test_on_target_change_when_pending_updates_target() -> None:
    # 正處於 pending 狀態時（對方有新訊息等待分析），
    # 切換回覆對象應更新 pending 提示中的對象名稱，且不重跑分析
    wm, mock_ov = _setup_wingman()
    chat = wm.chat_of("chat1")
    chat["history"].append(("her", "Alice", "hello"))
    chat["senders"] = ["Alice", "Bob"]
    chat["result"] = None
    mock_ov.is_pending.return_value = True

    start_mock = unittest.mock.MagicMock()
    wm.start_analyze = start_mock

    wm.on_target_change("chat1", "Bob")

    mock_ov.set_pending.assert_called_with("chat1", "Bob")
    assert start_mock.call_count == 0
    assert chat["target"] == "Bob"
