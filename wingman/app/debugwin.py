# -*- coding: utf-8 -*-
"""識別除錯窗：把子程序送來的幀和每個 OCR 框按分類畫出來，看識別到底哪兒錯了。
幀只在記憶體裡畫（QImage 拿 bytes 建），不存圖、不進日誌。"""
from datetime import datetime

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import PlainTextEdit

# (kind, 畫框的色, 色的中文, 這類是什麼)：跟設定頁那條提示一個口徑
_KINDS = (("me", "#18794e", "綠", "我"), ("her", "#1f6fd0", "藍", "對方"),
          ("gray", "#8a8a8a", "灰", "過濾掉的灰字"), ("name", "#e08b18", "橙", "當成發言人名"),
          ("image", "#d0342c", "紅", "當成圖片丟掉"), ("tiny", "#d4b106", "黃", "小字丟掉"))
_COLOR = {k: c for k, c, _, _ in _KINDS}
_NAME = {k: n for k, _, _, n in _KINDS}
_AREA = "#1f6fd0"  # 訊息區
_HEAD = "#8b5cf6"  # 頭部（會話名那條）


class _Canvas(QWidget):
    """左邊那塊畫布：整幀等比縮放鋪滿，再按同一個倍率把各種框套上去。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.img = None
        self.pkt = None
        self.setMinimumSize(320, 240)

    def paintEvent(self, event):
        p = QPainter(self)
        p.fillRect(self.rect(), QColor("#1b1f1d"))
        if self.img is None:
            p.setPen(QColor("#9aa6a0"))
            p.drawText(self.rect(), Qt.AlignCenter, "等待畫面…\n開著採集，聊天視窗有動靜就會有幀")
            return
        # 等比鋪滿 + 居中；s 是「縮小後的幀 → 控制元件」的倍率，k 是子程序縮了多少
        s = min(self.width() / self.img.width(), self.height() / self.img.height())
        w, h = self.img.width() * s, self.img.height() * s
        ox, oy = (self.width() - w) / 2, (self.height() - h) / 2
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        p.drawImage(QRectF(ox, oy, w, h), self.img)
        k = self.pkt.get("scale", 1) or 1
        f = lambda x, y: (ox + x * s / k, oy + y * s / k)  # 原幀座標 → 控制元件座標
        area = self.pkt.get("area")
        if not area:
            p.setPen(QColor("#d0342c"))
            p.drawText(QRectF(ox, oy, w, 30), Qt.AlignCenter, "認不出訊息區")
            return
        x0, y0, x1, y1 = area
        p.setPen(QPen(QColor(_HEAD), 1))
        p.drawRect(QRectF(*f(x0, self.pkt.get("pane_top", 0)),
                          (x1 - x0) * s / k, (y0 - self.pkt.get("pane_top", 0)) * s / k))
        p.setPen(QPen(QColor(_AREA), 2))
        p.drawRect(QRectF(*f(x0, y0), (x1 - x0) * s / k, (y1 - y0) * s / k))
        tag = QFont(self.font())
        tag.setPointSizeF(7.5)
        p.setFont(tag)
        fm = QFontMetricsF(tag)
        for bx0, by0, bx1, by1, kind, _text in self.pkt.get("boxes", ()):
            color = QColor(_COLOR.get(kind, "#ffffff"))
            p.setPen(QPen(color, 2))
            left, top = f(x0 + bx0, y0 + by0)
            p.drawRect(QRectF(left, top, (bx1 - bx0) * s / k, (by1 - by0) * s / k))
            # 小標籤貼在框左上角外側；寬度按文字實際寬度來，別糊住旁邊的框
            label = QRectF(left, top - 12, fm.horizontalAdvance(kind) + 6, 12)
            p.fillRect(label, color)
            p.setPen(QColor("#ffffff"))
            p.drawText(label, Qt.AlignCenter, kind)


class DebugWindow(QWidget):
    """獨立小窗，Qt.Tool 不佔工作列。show_packet() 喂一幀就重畫一次；關窗回撥把設定裡的開關撥回去。"""

    def __init__(self, on_close=None):
        super().__init__()
        self.on_close = on_close
        self.setWindowTitle("識別除錯")
        self.setWindowFlags(Qt.Tool)
        self.resize(900, 650)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 8)
        outer.setSpacing(8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.canvas = _Canvas(self)
        row.addWidget(self.canvas, 1)
        self.info = PlainTextEdit(self)
        self.info.setReadOnly(True)
        self.info.setFixedWidth(300)
        self.info.setPlainText(_legend())
        row.addWidget(self.info)
        outer.addLayout(row)
        self.status = QLabel("最近一幀 —— · 等待中…", self)
        self.status.setStyleSheet("color: #68776f;")
        outer.addWidget(self.status)

    def show_packet(self, pkt):
        """子程序送來的一幀：RGB 裸位元組 → QImage（copy 一份，原 bytes 之後就回收了）。"""
        self.canvas.img = QImage(pkt["rgb"], pkt["w"], pkt["h"], pkt["w"] * 3,
                                 QImage.Format_RGB888).copy()
        self.canvas.pkt = pkt
        self.canvas.update()
        area = pkt.get("area")
        counts = {}
        for b in pkt.get("boxes", ()):
            counts[b[4]] = counts.get(b[4], 0) + 1
        text = [
            f"會話：{pkt.get('title') or '（未識別）'}",
            "訊息區：" + (f"x {area[0]}–{area[2]} · y {area[1]}–{area[3]}" if area else "認不出訊息區"),
            f"頭部頂：y {pkt.get('pane_top', 0)}",
            f"OCR 耗時：{pkt.get('ocr_ms', 0)} ms",
            f"幀：{pkt['w']}×{pkt['h']}（原幀縮了 1/{pkt.get('scale', 1)} 再過佇列）",
            "框：" + ("、".join(f"{_NAME.get(k, k)} {v}" for k, v in counts.items()) or "無"),
            "",
            f"本幀 {len(pkt.get('lines', ()))} 行",
        ]
        for who, name, line in pkt.get("lines", ()):
            text.append(f"{who}({name})：{line}" if name else f"{who}：{line}")
        text += ["", _legend()]
        self.info.setPlainText("\n".join(text))
        stamp = datetime.fromtimestamp(pkt.get("ts") or 0).strftime("%H:%M:%S")
        self.status.setText(f"最近一幀 {stamp} · 共 {len(pkt.get('boxes', ()))} 個框")

    def closeEvent(self, event):
        if self.on_close:
            self.on_close()
        super().closeEvent(event)


def _legend():
    return ("圖例（藍粗框 = 訊息區，紫細框 = 頭部會話名）\n"
            + "\n".join(f"  {word} = {what}（{k}）" for k, _, word, what in _KINDS))
