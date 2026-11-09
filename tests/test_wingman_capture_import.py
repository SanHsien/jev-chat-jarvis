from __future__ import annotations

import ctypes
import importlib
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_importing_capture_without_windll_does_not_raise(monkeypatch) -> None:
    # Linux CI 的 ctypes 沒有 windll；匯入 capture 不可因此丟 AttributeError。
    monkeypatch.delattr(ctypes, "windll", raising=False)
    monkeypatch.delitem(sys.modules, "wingman.app.capture", raising=False)
    # CI 沒裝 numpy（本測試只關心 windll），以空模組代替。
    monkeypatch.setitem(sys.modules, "numpy", types.ModuleType("numpy"))

    module = importlib.import_module("wingman.app.capture")

    assert hasattr(module, "find_chat_hwnd")
    monkeypatch.delitem(sys.modules, "wingman.app.capture", raising=False)


def test_importing_fill_on_non_windows_does_not_raise(monkeypatch) -> None:
    # fill.py 曾在模組層級取 ctypes.windll 並設定 argtypes，Linux CI 一匯入就炸。
    monkeypatch.delattr(ctypes, "windll", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delitem(sys.modules, "wingman.app.fill", raising=False)

    module = importlib.import_module("wingman.app.fill")

    assert hasattr(module, "set_clipboard")
    monkeypatch.delitem(sys.modules, "wingman.app.fill", raising=False)
