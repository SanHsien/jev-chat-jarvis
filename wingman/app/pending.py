# -*- coding: utf-8 -*-
"""半自動：哪些會話有對方新訊息、正等使用者按「分析」。

不碰 Qt，方便單獨測試；懸浮窗只管把它的結果畫出來。
"""
from __future__ import annotations


class PendingAnalysis:
    """等按「分析」的會話名。每個會話各記一筆：別的會話來了新訊息，不能把這個會話的待分析擠掉。"""

    def __init__(self) -> None:
        self._titles: set[str] = set()

    def mark(self, title: str) -> None:
        self._titles.add(title)

    def clear(self, title: str) -> bool:
        """這個會話不用分析了；原本就在等才返回 True。"""
        was = title in self._titles
        self._titles.discard(title)
        return was

    def is_pending(self, title: str | None) -> bool:
        return title is not None and title in self._titles

    def take(self, title: str | None) -> bool:
        """使用者在看著 title 時按了「分析」：它在等就消耗掉並返回 True。"""
        if self.is_pending(title):
            self._titles.discard(title)
            return True
        return False
