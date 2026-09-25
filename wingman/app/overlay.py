# -*- coding: utf-8 -*-
"""淺色置頂回覆助手：回覆建議和獨立設定頁。傳送始終由使用者確認。"""
import threading
from datetime import datetime
from math import isfinite
from types import SimpleNamespace

from PySide6.QtCore import QObject, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QPushButton, QSizeGrip, QSizePolicy,
    QStackedWidget, QVBoxLayout, QWidget,
)
from qfluentwidgets import (
    BodyLabel, CardWidget, CheckBox, ComboBox, EditableComboBox, FluentIcon as FIF,
    HyperlinkButton, IndeterminateProgressBar, LineEdit, PasswordLineEdit, PlainTextEdit,
    PrimaryPushButton, PushButton, ScrollArea, SpinBox, SwitchButton, Theme, TransparentToolButton,
    setCustomStyleSheet, setFont, setTheme, setThemeColor,
)

from wingman.app import settings
from wingman.app.version import VERSION
from wingman.core import jev_client, llm, providers
from wingman.core.questions import CHOICE_LABELS

_LOG_LINES = 300
_MUTED = "#68776f"
_GREEN = "#18794e"
_RELATIONSHIPS = [
    ("戀人", "romantic partners"), ("朋友", "friends"), ("同事", "colleagues"),
    ("家人", "family"), ("自定義", None),
]


def _choice(answers, name):
    return CHOICE_LABELS[name].get((answers.get(name) or {}).get("choice"), "暫未判斷")


class _FitCombo(ComboBox):
    """長名字不撐開窄佈局。按鈕上按當前寬度省略；條目仍是全文，findText 靠它。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full = ""
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def setText(self, text):
        self._full = text or ""
        QPushButton.setText(self, self._elide(self._full))
        if self._full and self.text() != self._full:
            self.setToolTip(self._full)

    def minimumSizeHint(self):
        hint = QPushButton.minimumSizeHint(self)
        return QSize(48, hint.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        shown = self._elide(self._full)
        if shown != self.text():
            QPushButton.setText(self, shown)
        if self._full and shown != self._full:
            self.setToolTip(self._full)

    def _elide(self, text):
        # 右側箭頭大約 28px。還沒排上版時先按一個窄寬度省略，避免最小寬度被整句名字撐開。
        avail = self.width() - 36 if self.width() > 64 else 120
        return self.fontMetrics().elidedText(text, Qt.ElideRight, max(24, avail))


def _label(text="", size=14, color=None, bold=False, parent=None):
    label = BodyLabel(text, parent)
    label.setTextFormat(Qt.PlainText)
    label.setWordWrap(True)
    label.setMinimumWidth(0)
    label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
    setFont(label, size, QFont.DemiBold if bold else QFont.Normal)
    if color:
        qss = f"BodyLabel {{ color: {color}; background: transparent; }}"
        setCustomStyleSheet(label, qss, qss)
    return label


def _tool(icon, title, callback, parent=None):
    button = TransparentToolButton(icon, parent)
    button.setFixedSize(32, 32)
    button.setToolTip(title)
    button.setAccessibleName(title)
    button.clicked.connect(callback)
    return button


class _Surface(CardWidget):
    def __init__(self, parent=None, accent=False):
        self.accent = accent
        super().__init__(parent)
        self.setBorderRadius(12)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def _normalBackgroundColor(self):
        return QColor("#edf7f0" if self.accent else "#ffffff")

    def _hoverBackgroundColor(self):
        return self._normalBackgroundColor()

    def _pressedBackgroundColor(self):
        return self._normalBackgroundColor()


class _Fetched(QObject):
    """取模型列表的背景執行緒 → 主執行緒：哪一組（SimpleNamespace）、取回來的模型 id、失敗原因（成功是空串）。
    Qt 不讓跨執行緒碰控制元件，訊號是跨執行緒唯一干淨的路。"""
    done = Signal(object, list, str)


class _TitleBar(QWidget):
    """只有標題欄可拖動，選擇正文或按按鈕不會意外移動視窗。"""
    def __init__(self, parent):
        super().__init__(parent)
        self._drag = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag = event.globalPosition().toPoint() - self.window().pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag is not None and event.buttons() & Qt.LeftButton:
            self.window().move(event.globalPosition().toPoint() - self._drag)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag = None
        super().mouseReleaseEvent(event)


class _MainWindow(QWidget):
    """視窗大小變了就叫 Overlay 重新排布；斷點沒跨過時 _relayout 自己不做事，這裡不用防抖。"""
    def __init__(self, relayout):
        super().__init__()
        self._relayout = relayout

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._relayout(event.size().width(), event.size().height())


class _ReplyCard(_Surface):
    def __init__(self, owner, index, recommended=False, number=1, score=None):
        super().__init__(accent=recommended)
        box = QVBoxLayout(self)
        self.box = box
        box.setSpacing(10)
        top = QHBoxLayout()
        label = "推薦回覆" if recommended else f"備選 {number}"
        if score is not None:
            label += f" · {round(score * 100)}%"
        top.addWidget(_label(label, 12, _GREEN if recommended else _MUTED, True))
        self.copyButton = _tool(FIF.COPY, "複製這條回覆", lambda: owner._copy(index), self)
        self.copyButton.setFixedSize(24, 24)
        top.addWidget(self.copyButton)
        box.addLayout(top)
        self.text = _label(owner.cands[index], 15)
        self.text.setTextInteractionFlags(Qt.TextSelectableByMouse)
        box.addWidget(self.text)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        self.fillButton = (PrimaryPushButton if recommended else PushButton)("填入", self)
        self.fillButton.setAccessibleName(f"填入{'推薦回覆' if recommended else f'備選 {number}'}")
        self.fillButton.clicked.connect(lambda: owner._fill(index))
        bottom.addWidget(self.fillButton)
        box.addLayout(bottom)
        self.set_compact(owner._compact)

    def set_available(self, enabled):
        self.fillButton.setEnabled(enabled)
        self.copyButton.setEnabled(enabled)

    def set_compact(self, compact):
        self.box.setContentsMargins(12, 8, 12, 8) if compact else self.box.setContentsMargins(16, 12, 16, 12)
        self.fillButton.setMinimumWidth(80 if compact else 100)


class Overlay:
    def __init__(self, on_fill, on_toggle_capture=None, on_target_change=None, result_of=None,
                 on_toggle_debug=None):
        """result_of(會話名) → 那個會話上次的結果或 None；切著看別的會話時用它把舊結果放回來。
        on_target_change(會話名, 人名) → 使用者在群裡挑了回覆對象。
        on_toggle_debug(開不開) → 開關除錯檢視那個獨立視窗。"""
        self.app = QApplication.instance() or QApplication([])
        setTheme(Theme.LIGHT)
        setThemeColor(_GREEN, save=False)
        self.on_fill = on_fill
        self.on_toggle_capture = on_toggle_capture
        self.on_target_change = on_target_change
        self.on_toggle_debug = on_toggle_debug
        self.result_of = result_of
        self.cands = []
        self.cards = []
        self._busy = False
        self._current = False
        self._compact = None  # 斷點模式：None 保證 _relayout 第一次呼叫必定生效
        self._pageLayouts = []
        self._hintLabels = []
        self.feeds = {}  # {會話名: [排好版的記錄]}
        self.counts = {}  # {會話名: 訊息條數}
        self.hers = {}  # {會話名: 對方最近一句}
        self.targets = {}  # {會話名: ([發言人], 當前回覆對象)}
        self._chat = ""  # LINE 當前開著的會話
        self._shown = ""  # 介面上正在看的會話（瀏覽時和上面不一樣）
        self.win = _MainWindow(self._relayout)
        self.win.setObjectName("assistantWindow")
        self.win.setWindowTitle("對話副駕")
        self.win.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.win.setStyleSheet(
            "QWidget#assistantWindow { background: #f5f7f6; border: 1px solid #dce3de; border-radius: 14px; }"
        )
        self.win.setMinimumWidth(320)
        self.win.setMaximumWidth(640)
        outer = QVBoxLayout(self.win)
        outer.setContentsMargins(1, 1, 1, 1)
        outer.setSpacing(0)
        header = _TitleBar(self.win)
        title = QHBoxLayout(header)
        title.setContentsMargins(18, 12, 10, 10)
        title.setSpacing(8)
        name = _label("對話副駕", 18, "#233c2f", True)
        name.setAttribute(Qt.WA_TransparentForMouseEvents)
        title.addWidget(name)
        self.subtitle = _label("Windows · LINE", 12, _MUTED)
        self.subtitle.setAttribute(Qt.WA_TransparentForMouseEvents)
        title.addWidget(self.subtitle, 1)
        self.captureSwitch = SwitchButton(header)
        self.captureSwitch.setOnText("採集中")
        self.captureSwitch.setOffText("已暫停")
        self.captureSwitch.setToolTip("開啟或暫停採集")
        self.captureSwitch.setAccessibleName("開啟或暫停採集")
        self.captureSwitch.setChecked(True)
        self.captureSwitch.checkedChanged.connect(self._capture_toggled)
        title.addWidget(self.captureSwitch)
        self.settingsButton = _tool(FIF.SETTING, "設定", self.open_settings, header)
        title.addWidget(self.settingsButton)
        title.addWidget(_tool(FIF.REMOVE, "最小化", self.win.showMinimized, header))
        title.addWidget(_tool(FIF.CLOSE, "關閉助手", self.win.close, header))
        outer.addWidget(header)
        self.updateBar = QWidget(self.win)
        update_row = QHBoxLayout(self.updateBar)
        update_row.setContentsMargins(18, 4, 8, 4)
        update_row.setSpacing(8)
        self.updateLabel = _label("", 12, _GREEN, True)
        update_row.addWidget(self.updateLabel, 1)
        self.updateLink = HyperlinkButton("", "去下載", self.updateBar)
        self.updateLink.setFixedHeight(24)
        update_row.addWidget(self.updateLink)
        closeUpdate = TransparentToolButton(FIF.CLOSE, self.updateBar)
        closeUpdate.setFixedSize(20, 20)
        closeUpdate.setToolTip("關閉更新提示")
        closeUpdate.setAccessibleName("關閉更新提示")
        closeUpdate.clicked.connect(lambda: self.updateBar.hide())
        update_row.addWidget(closeUpdate)
        self.updateBar.setFixedHeight(32)
        self.updateBar.hide()
        outer.addWidget(self.updateBar)
        self.pages = QStackedWidget(self.win)
        outer.addWidget(self.pages, 1)
        self._build_home()
        self._build_settings()
        footer = QHBoxLayout()
        footer.setContentsMargins(20, 9, 8, 8)
        footer.addWidget(_label(f"僅填入輸入框 · 傳送由你確認 · v{VERSION}", 11, _MUTED), 1)
        grip = QSizeGrip(self.win)
        grip.setFixedSize(16, 16)
        footer.addWidget(grip, 0, Qt.AlignBottom)
        outer.addLayout(footer)
        screen = self.app.primaryScreen().availableGeometry()
        self.win.setMinimumHeight(min(360, screen.height() - 32))
        self.win.resize(min(440, screen.width() - 32), min(820, screen.height() - 48))
        self.win.move(screen.right() - self.win.width() - 20, screen.top() + 24)
        self._relayout(self.win.width(), self.win.height())  # resizeEvent 補不到構造時這一次
        self.set_status("等待新訊息" if settings.has_key() else "需要配置模型",
                        "idle" if settings.has_key() else "warning")
        self.win.show()

    def _scroll_page(self):
        scroll = ScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        scroll.viewport().setAutoFillBackground(False)
        content = QWidget()
        content.setObjectName("pageContent")
        content.setStyleSheet("QWidget#pageContent { background: transparent; }")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(20, 8, 20, 12)
        layout.setSpacing(14)
        scroll.setWidget(content)
        self.pages.addWidget(scroll)
        self._pageLayouts.append(layout)
        return scroll, layout

    def _relayout(self, w, h):
        """寬度跨過斷點才重新擺佈局（省事）；高度每次都重算，反正只是設個定高。"""
        compact = w < 400
        if compact != self._compact:
            self._compact = compact
            self._apply_compact(compact)
        self.feed.setFixedHeight(max(100, min(240, int(h * 0.25))))

    def _apply_compact(self, compact):
        """緊湊/常規兩套間距和可見性；斷點沒變時不會被呼叫。"""
        self.subtitle.setVisible(not compact)
        self.captureSwitch.setOnText("" if compact else "採集中")
        self.captureSwitch.setOffText("" if compact else "已暫停")
        for label in self._hintLabels:
            label.setVisible(not compact)
        self.referenceNote.setVisible(bool(self.cands) and not compact)
        self._sync_model_fields()
        margins = (12, 8, 12, 12) if compact else (20, 8, 20, 12)
        for layout in self._pageLayouts:
            layout.setContentsMargins(*margins)
        for card in self.cards:
            card.set_compact(compact)

    def _build_home(self):
        self.home, body = self._scroll_page()
        heading = QHBoxLayout()
        heading.addWidget(_label("回覆建議", 23, "#24382d", True), 1)
        self.updated = _label("", 11, _MUTED)
        self.updated.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        heading.addWidget(self.updated)
        body.addLayout(heading)
        chat_row = QHBoxLayout()
        chat_row.setSpacing(8)
        prefix = _label("當前會話", 12, _MUTED)
        prefix.setFixedWidth(56)
        chat_row.addWidget(prefix)
        self.chatBox = _FitCombo()
        self.chatBox.setPlaceholderText("尚未識別到會話")
        self.chatBox.setAccessibleName("當前會話")
        self.chatBox.setToolTip("聊天視窗切到哪個會話這裡就跟到哪個；也可以自己選一個，只看它的記錄和建議")
        self.chatBox.currentIndexChanged.connect(self._on_chat_selected)
        chat_row.addWidget(self.chatBox, 1)
        self.chatFollow = _label("", 11, _MUTED)
        self.chatFollow.setFixedWidth(52)
        self.chatFollow.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        chat_row.addWidget(self.chatFollow)
        body.addLayout(chat_row)
        self.targetRow = QWidget()  # 只有開了「群聊指定回覆對象」且這個會話是群聊才露出來
        target_row = QHBoxLayout(self.targetRow)
        target_row.setContentsMargins(0, 0, 0, 0)
        target_row.setSpacing(8)
        target_prefix = _label("回覆對象", 12, _MUTED)
        target_prefix.setFixedWidth(56)
        target_row.addWidget(target_prefix)
        self.targetBox = _FitCombo()
        self.targetBox.setAccessibleName("回覆對象")
        self.targetBox.setToolTip("三條候選都按這個人來寫；不選就跟著最近說話的那位")
        self.targetBox.currentIndexChanged.connect(self._on_target_selected)
        target_row.addWidget(self.targetBox, 1)
        self.atCheck = CheckBox("填入時帶 @")
        self.atCheck.setChecked(True)
        self.atCheck.setToolTip("填入時在開頭加「@名字 」。只是普通文字，不會變成真正的 @")
        target_row.addWidget(self.atCheck)
        self.targetRow.hide()
        body.addWidget(self.targetRow)
        self.status = _label("", 12, _MUTED)
        body.addWidget(self.status)
        self.progress = IndeterminateProgressBar()
        self.progress.setFixedHeight(3)
        self.progress.hide()
        body.addWidget(self.progress)
        self.context = QWidget()
        context_box = QVBoxLayout(self.context)
        context_box.setContentsMargins(0, 0, 0, 0)
        context_box.setSpacing(5)
        context_box.addWidget(_label("對方最近說", 11, _MUTED))
        self.latest = _label("", 14, "#42574a")
        self.latest.setTextInteractionFlags(Qt.TextSelectableByMouse)
        context_box.addWidget(self.latest)
        self.context.hide()
        body.addWidget(self.context)

        self.insight = _Surface()
        insight_box = QVBoxLayout(self.insight)
        insight_box.setContentsMargins(14, 12, 14, 12)
        insight_box.setSpacing(7)
        row = QHBoxLayout()
        self.insightTitle = _label("對話參考", 12, _MUTED)
        row.addWidget(self.insightTitle, 1)
        self.tension = _label("", 11)
        self.tension.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        row.addWidget(self.tension)
        insight_box.addLayout(row)
        self.summary = _label("", 14, "#304c3c", True)
        insight_box.addWidget(self.summary)
        self.intent = _label("", 12, _MUTED)
        insight_box.addWidget(self.intent)
        self.insight.setToolTip("根據當前聊天片段推測，可能理解有偏差。緊張度為 0–9 的參考評分。")
        self.insight.hide()
        body.addWidget(self.insight)

        self.empty = _Surface()
        empty_box = QVBoxLayout(self.empty)
        empty_box.setContentsMargins(24, 36, 24, 36)
        empty_box.setSpacing(14)
        symbol = _label("…", 30, _GREEN, True)
        symbol.setAlignment(Qt.AlignCenter)
        empty_box.addWidget(symbol)
        self.emptyTitle = _label("等待對方的新訊息", 17, "#304c3c", True)
        self.emptyTitle.setAlignment(Qt.AlignCenter)
        empty_box.addWidget(self.emptyTitle)
        self.emptyHint = _label("保持聊天視窗開啟。\n收到新訊息後，回覆建議會出現在這裡。", 13, _MUTED)
        self.emptyHint.setAlignment(Qt.AlignCenter)
        empty_box.addWidget(self.emptyHint)
        self.setupButton = PrimaryPushButton("前往設定")
        self.setupButton.clicked.connect(self.open_settings)
        self.setupButton.setVisible(not settings.has_key())
        empty_box.addWidget(self.setupButton, 0, Qt.AlignHCenter)
        if not settings.has_key():
            self.emptyTitle.setText("先設定，再開始")
            self.emptyHint.setText("配置模型和關係背景，\n讓建議更貼近你們的對話。")
        body.addWidget(self.empty)
        self.replyBox = QVBoxLayout()
        self.replyBox.setSpacing(10)
        body.addLayout(self.replyBox)
        self.referenceNote = _label("AI 建議僅供參考，按你的語氣調整後再傳送。", 11, _MUTED)
        self.referenceNote.hide()
        body.addWidget(self.referenceNote)

        self.historyButton = PushButton(FIF.HISTORY, "聊天記錄")
        self.historyButton.clicked.connect(self._toggle_history)
        self.historyButton.setAccessibleName("展開或收起聊天記錄")
        body.addWidget(self.historyButton)
        self.feed = PlainTextEdit()
        self.feed.setReadOnly(True)
        self.feed.setPlaceholderText("識別到的聊天內容會顯示在這裡")
        self.feed.setMaximumBlockCount(_LOG_LINES)
        self.feed.setFixedHeight(160)
        self.feed.hide()
        body.addWidget(self.feed)
        self._history_title()
        body.addStretch(1)

    def _build_settings(self):
        self.settingsPage, body = self._scroll_page()
        heading = QHBoxLayout()
        heading.addWidget(_tool(FIF.RETURN, "返回回覆建議", self._back_home))
        heading.addWidget(_label("設定", 23, "#24382d", True), 1)
        body.addLayout(heading)
        body.addWidget(_label("調整關係背景，配置判斷和起草用的兩個模型。", 13, _MUTED))
        preference = _Surface()
        box = QVBoxLayout(preference)
        box.setContentsMargins(16, 16, 16, 18)
        box.setSpacing(12)
        box.addWidget(_label("回覆偏好", 16, "#304c3c", True))
        relation_label = _label("你們的關係", 13)
        box.addWidget(relation_label)
        self.relationshipBox = ComboBox()
        self.relationshipBox.setMinimumWidth(0)
        self.relationshipBox.addItems([name for name, value in _RELATIONSHIPS])
        self.relationshipBox.setAccessibleName("你們的關係")
        relation_label.setBuddy(self.relationshipBox)
        box.addWidget(self.relationshipBox)
        self.relEdit = LineEdit()
        self.relEdit.setPlaceholderText("例如：剛認識的朋友，正在慢慢熟悉")
        self.relEdit.setAccessibleName("自定義關係背景")
        box.addWidget(self.relEdit)
        self.relationshipBox.currentIndexChanged.connect(
            lambda index: self.relEdit.setVisible(_RELATIONSHIPS[index][1] is None)
        )
        box.addWidget(self._hint("幫助助手把握稱呼、語氣和回應分寸。"))
        style_label = _label("說話風格（可選）", 13)
        box.addWidget(style_label)
        self.styleEdit = LineEdit()
        self.styleEdit.setPlaceholderText("例如：話少、不用標點、偶爾用 doge、不說客套話")
        self.styleEdit.setAccessibleName("說話風格")
        style_label.setBuddy(self.styleEdit)
        box.addWidget(self.styleEdit)
        box.addWidget(self._hint("候選本來就照著你最近發的訊息模仿；這裡可以再補一句你自己的口吻。"))
        context_label = _label("參考上下文", 13)
        box.addWidget(context_label)
        self.contextBox = SpinBox()
        self.contextBox.setRange(3, 30)
        self.contextBox.setAccessibleName("參考的最近訊息條數")
        context_label.setBuddy(self.contextBox)
        box.addWidget(self.contextBox)
        box.addWidget(self._hint(
            "生成和判斷時看最近這麼多條訊息。太少會丟上下文，太多會稀釋重點，建議 6–12。"
        ))
        target_row = QHBoxLayout()
        target_row.addWidget(_label("群聊指定回覆對象", 13), 1)
        self.targetSwitch = SwitchButton()
        self.targetSwitch.setOnText("開")
        self.targetSwitch.setOffText("關")
        self.targetSwitch.setAccessibleName("群聊指定回覆對象")
        target_row.addWidget(self.targetSwitch)
        box.addLayout(target_row)
        box.addWidget(self._hint(
            "開了以後群聊裡可以選回覆給誰，候選會針對 TA 寫，填入時可帶 @。關了就正常回覆。"
        ))
        update_row = QHBoxLayout()
        update_row.addWidget(_label("啟動時檢查更新", 13), 1)
        self.updateSwitch = SwitchButton()
        self.updateSwitch.setOnText("開")
        self.updateSwitch.setOffText("關")
        self.updateSwitch.setAccessibleName("啟動時檢查更新")
        update_row.addWidget(self.updateSwitch)
        box.addLayout(update_row)
        box.addWidget(self._hint(
            "只向 GitHub 查最新版本號，不傳送任何資料。不需要的話關掉也行。"
        ))
        debug_row = QHBoxLayout()
        debug_row.addWidget(_label("除錯檢視", 13), 1)
        self.debugSwitch = SwitchButton()
        self.debugSwitch.setOnText("開")
        self.debugSwitch.setOffText("關")
        self.debugSwitch.setAccessibleName("除錯檢視")
        self.debugSwitch.checkedChanged.connect(self._debug_toggled)  # 這個開關立刻生效，不等「儲存設定」
        debug_row.addWidget(self.debugSwitch)
        box.addLayout(debug_row)
        box.addWidget(self._hint(
            "另開一個視窗實時顯示截到的畫面和識別框：綠 = 我、藍 = 對方、灰 = 過濾掉的灰字、"
            "紅 = 當成圖片丟掉、黃 = 小字丟掉。只在記憶體裡畫，不存圖。"
        ))
        body.addWidget(preference)

        models = _Surface()
        box = QVBoxLayout(models)
        box.setContentsMargins(16, 16, 16, 18)
        box.setSpacing(12)
        box.addWidget(_label("模型", 16, "#304c3c", True))
        self._fetched = _Fetched()
        self._fetched.done.connect(self._models_fetched)
        self.jev = self._model_group(box, "判斷 · Jev", "jev", providers.JEV_PROVIDERS)
        box.addWidget(self._hint(
            "判斷意圖、緊張度，並給三條候選排序。兩家給的是同一個 Jev，必填。"
        ))
        self.draft = self._model_group(box, "起草 · 語言模型", "draft", providers.DRAFT_PROVIDERS)
        box.addWidget(self._hint(
            "寫那三條候選。OpenAI / Anthropic / Gemini 三種接口都走各自官方 SDK。"
            "預設 OpenRouter，也可改用 Vercel AI Gateway 或其他來源。"
        ))
        think_row = QHBoxLayout()
        think_row.addWidget(_label("起草時開啟思考模式", 13), 1)
        self.thinkingSwitch = SwitchButton()
        self.thinkingSwitch.setOnText("開")
        self.thinkingSwitch.setOffText("關")
        self.thinkingSwitch.setAccessibleName("起草時開啟思考模式")
        think_row.addWidget(self.thinkingSwitch)
        box.addLayout(think_row)
        box.addWidget(self._hint(
            "關：秒回，夠用。開：模型先想再寫，更斟酌但慢好幾倍、貴一些。"
            "只有 " + " / ".join(providers.THINKING) + " 認這個開關。"
        ))
        body.addWidget(models)
        self.settingsFeedback = _label("", 13, _GREEN)
        self.settingsFeedback.hide()
        body.addWidget(self.settingsFeedback)
        actions = QHBoxLayout()
        back = PushButton("返回")
        back.clicked.connect(self._back_home)
        actions.addWidget(back)
        actions.addStretch(1)
        self.saveButton = PrimaryPushButton("儲存設定")
        self.saveButton.clicked.connect(self._save)
        actions.addWidget(self.saveButton)
        body.addLayout(actions)
        body.addWidget(self._hint("儲存後用於下一次生成的回覆。"))
        # Fork：上游〈版權與許可〉要求在「關於」頁寫明來源，發布包保留 LICENSE 與 NOTICE。
        body.addWidget(_label("關於與授權", 16, "#304c3c", True))
        body.addWidget(_label(
            "基於 JevChat-Windows（https://github.com/jev-chat/jev-chat-windows）二次開發；"
            "Jev 判斷內核與題目來自 Jev 聊天助手（https://github.com/jev-chat/jev-chat-jarvis）。"
            "MIT 授權，Copyright © 2026 rezoch340 與 jev-chat 貢獻者；本版本由 SanHsien 修改與維護，"
            "非原作者出品或背書。發布包內含 GPLv3 的 PySide6-Fluent-Widgets（非商用免費，商用需另購授權），"
            "整體受 GPLv3 約束；授權全文見程式資料夾內的 LICENSE-jev-chat-windows 與 NOTICE-jev-chat-windows。",
            12, _MUTED))
        links = QHBoxLayout()
        links.addWidget(HyperlinkButton("https://github.com/SanHsien/jev-chat-jarvis", "本專案", self.settingsPage))
        links.addWidget(HyperlinkButton("https://github.com/jev-chat/jev-chat-windows", "上游 JevChat-Windows",
                                        self.settingsPage))
        links.addStretch(1)
        body.addLayout(links)
        body.addStretch(1)
        self._load_settings()

    def _hint(self, text):
        """設定頁欄位下面的灰字說明：記下來，緊湊模式一起隱藏。"""
        label = _label(text, 12, _MUTED)
        self._hintLabels.append(label)
        return label

    def _model_group(self, box, title, kind, table):
        """一組「來源 / 金鑰 / 模型」控制元件，判斷和起草各一份。table 是 core/providers.py 裡那張表。"""
        group = SimpleNamespace(kind=kind, table=table, ids=list(table),
                                keyTitle="判斷" if kind == "jev" else "起草",
                                stored_key=lambda k=kind: (settings.jev_key() if k == "jev"
                                                           else settings.llm_key()))
        heading = QHBoxLayout()
        heading.addWidget(_label(title, 14, "#304c3c", True), 1)
        group.keyState = _label("", 12, _GREEN)
        group.keyState.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        heading.addWidget(group.keyState)
        box.addLayout(heading)
        source_label = _label("來源", 13)
        box.addWidget(source_label)
        group.providerBox = ComboBox()
        group.providerBox.setMinimumWidth(0)  # 選項文字長短不一，別讓它撐開設定頁
        group.providerBox.addItems([table[i].name for i in group.ids])
        group.providerBox.setAccessibleName(f"{title} 來源")
        source_label.setBuddy(group.providerBox)
        box.addWidget(group.providerBox)
        if kind == "draft":  # 只有兩個「自定義」來源要自己填地址，別的來源這一行藏著
            self.baseLabel = _label("Base URL", 13)
            box.addWidget(self.baseLabel)
            self.baseEdit = LineEdit()
            self.baseEdit.setPlaceholderText("https://你的服務/v1")
            self.baseEdit.setAccessibleName("自定義來源 Base URL")
            self.baseLabel.setBuddy(self.baseEdit)
            box.addWidget(self.baseEdit)
        key_label = _label("金鑰", 13)
        box.addWidget(key_label)
        group.keyEdit = PasswordLineEdit()
        group.keyEdit.setAccessibleName(f"{title} API 金鑰")
        key_label.setBuddy(group.keyEdit)
        group.keyEdit.returnPressed.connect(self._save)
        box.addWidget(group.keyEdit)
        box.addWidget(self._hint(
            "OpenRouter 的 key 或 TypeSafe 的 key，看上面選的來源。" if kind == "jev"
            else "上面選哪家就填哪家的 key；換來源重填一次，只存這一把。"))
        model_label = _label("模型", 13)
        box.addWidget(model_label)
        row = QHBoxLayout()
        row.setSpacing(8)
        group.modelBox = EditableComboBox()  # 能選也能手打，接口新出的模型不用等我改程式碼
        group.modelBox.setMinimumWidth(0)
        group.modelBox.setAccessibleName(f"{title} 模型")
        model_label.setBuddy(group.modelBox)
        row.addWidget(group.modelBox, 1)
        group.fetchButton = PushButton("獲取模型")
        group.fetchButton.setAccessibleName(f"獲取{title}的可用模型列表")
        group.fetchButton.clicked.connect(lambda: self._fetch_models(group))
        row.addWidget(group.fetchButton)
        box.addLayout(row)
        group.status = _label("", 12, _MUTED)
        box.addWidget(group.status)
        group.providerBox.currentIndexChanged.connect(lambda _: self._provider_changed(group))
        return group

    @staticmethod
    def _provider_of(group):
        return group.ids[max(0, group.providerBox.currentIndex())]

    def _provider_changed(self, group):
        """換來源：模型框回到這家該有的值（存的就是這家才用存的，否則用它的預設），狀態清掉。"""
        provider = self._provider_of(group)
        saved = settings.jev_provider() if group.kind == "jev" else settings.draft_provider()
        stored = settings.jev_model() if group.kind == "jev" else settings.draft_model()
        group.modelBox.clear()
        group.modelBox.setText(stored if provider == saved else group.table[provider].default)
        group.status.setText("")
        self._sync_model_fields()

    def _sync_model_fields(self):
        """兩組共用：金鑰已配置/未配置、佔位文案、自定義 Base URL 行的顯隱，
        外加緊湊模式下把來源按鈕上的文字省略——ComboBox 是 QPushButton，
        minimumSizeHint 按整段文字算，不會自動換行/省略，長名字會把設定頁撐寬。"""
        for group in (self.jev, self.draft):
            provider = self._provider_of(group)
            name = group.table[provider].name
            configured = bool(group.stored_key())
            group.keyState.setText("已配置" if configured else "未配置")
            group.keyEdit.setPlaceholderText(
                "已配置，留空保留" if configured else f"輸入 {name} API 金鑰")
            if self._compact:
                name = group.providerBox.fontMetrics().elidedText(name, Qt.ElideRight, 180)
            group.providerBox.setText(name)
        custom = self._provider_of(self.draft) in providers.CUSTOM
        self.baseLabel.setVisible(custom)
        self.baseEdit.setVisible(custom)

    def _fetch_models(self, group):
        """「獲取模型」：拿填的 key（沒填就拿存的）去問接口，網路呼叫丟背景執行緒。"""
        provider = self._provider_of(group)
        custom = group.kind == "draft" and provider in providers.CUSTOM
        base = self.baseEdit.text().strip() if custom else None
        key = group.keyEdit.text().strip() or group.stored_key()
        if not key:
            group.status.setText("先填金鑰")
            return
        if custom and not base:
            group.status.setText("先填 Base URL")
            return
        group.status.setText("獲取中…")
        group.fetchButton.setEnabled(False)
        threading.Thread(target=lambda: self._list_models(group, provider, key, base),
                         daemon=True).start()

    def _list_models(self, group, provider, key, base):
        """背景執行緒：判斷走 jev_client，起草按協議走 llm；失敗把原因一起送回主執行緒。"""
        try:
            if group.kind == "jev":
                models = jev_client.list_models(provider, key)
            else:
                spec = providers.DRAFT_PROVIDERS[provider]
                models = llm.list_models(spec.protocol, base or spec.base, key, headers=spec.headers)
                if spec.keep:  # 目錄裡混了別的協議時，只留這條路打得通的
                    models = [m for m in models if spec.keep(m)]
            reason = "" if models else "這個來源沒返回任何模型"
        except Exception as exc:  # 執行緒裡漏異常會靜默吞掉，按鈕就永遠停在禁用態
            models, reason = [], str(exc)[:120]
        self._fetched.done.emit(group, models, reason)

    def _models_fetched(self, group, models, reason):
        """回到主執行緒：填進下拉框，原來選中的還在列表裡就留著。"""
        group.fetchButton.setEnabled(True)
        if not models:
            group.status.setText(reason or "獲取失敗，檢查金鑰、網路或 Base URL")
            return
        current = group.modelBox.text().strip()
        group.modelBox.clear()
        group.modelBox.addItems(models)
        if current in models:
            group.modelBox.setCurrentIndex(models.index(current))
        else:
            group.modelBox.setText(current)  # 手打的沒在列表裡也不清掉
        group.status.setText(f"共 {len(models)} 個")

    def _set_group(self, group, provider, model):
        """把存下來的來源和模型放回一組控制元件裡；填充不算使用者操作，別觸發換來源的重置。"""
        group.providerBox.blockSignals(True)
        group.providerBox.setCurrentIndex(group.ids.index(provider))
        group.providerBox.blockSignals(False)
        group.keyEdit.clear()
        group.modelBox.clear()
        group.modelBox.setText(model)
        group.status.setText("")

    def _load_settings(self):
        relationship = settings.relationship()
        index = next((i for i, (_, value) in enumerate(_RELATIONSHIPS) if value == relationship),
                     len(_RELATIONSHIPS) - 1)
        self.relationshipBox.setCurrentIndex(index)
        self.relEdit.setText(relationship if _RELATIONSHIPS[index][1] is None else "")
        self.relEdit.setVisible(_RELATIONSHIPS[index][1] is None)
        self.styleEdit.setText(settings.style())
        self.contextBox.setValue(settings.context())
        self.targetSwitch.setChecked(settings.reply_target())
        self._set_group(self.jev, settings.jev_provider(), settings.jev_model())
        self._set_group(self.draft, settings.draft_provider(), settings.draft_model())
        self.baseEdit.setText(settings.draft_base_url())
        self.thinkingSwitch.setChecked(settings.thinking())
        self.updateSwitch.setChecked(settings.check_update())
        self.set_debug_switch(settings.debug_view())  # 遮蔽訊號地撥，別在載入時開關一遍視窗
        self._sync_model_fields()  # 上面遮蔽了訊號，這裡補一次
        self.settingsFeedback.hide()

    def _save(self):
        relationship = _RELATIONSHIPS[self.relationshipBox.currentIndex()][1]
        relationship = relationship or self.relEdit.text().strip()
        jev_provider = self._provider_of(self.jev)
        draft_provider = self._provider_of(self.draft)
        base = self.baseEdit.text().strip()
        if not relationship:
            self._settings_feedback("請填寫關係背景，或選擇一個已有選項。", error=True)
            self.relEdit.setFocus()
            return
        if draft_provider in providers.CUSTOM and not base:
            self._settings_feedback("自定義來源要填 Base URL。", error=True)
            self.baseEdit.setFocus()
            return
        for group, provider in ((self.jev, jev_provider), (self.draft, draft_provider)):
            name = group.table[provider].name
            if not group.keyEdit.text().strip() and not group.stored_key():
                self._settings_feedback(f"請先填寫 {group.keyTitle} 的 API 金鑰。", error=True)
                group.keyEdit.setFocus()
                return
            if not group.modelBox.text().strip():
                self._settings_feedback(f"{name} 請先獲取並選擇一個模型。", error=True)
                group.modelBox.setFocus()
                return
        try:
            settings.save(relationship, self.contextBox.value(),
                          jev_provider_text=jev_provider,
                          jev_key_text=self.jev.keyEdit.text().strip() or None,
                          jev_model_text=self.jev.modelBox.text().strip(),
                          draft_provider_text=draft_provider,
                          llm_key_text=self.draft.keyEdit.text().strip() or None,
                          draft_model_text=self.draft.modelBox.text().strip(),
                          draft_base_url_text=base,
                          reply_target_on=self.targetSwitch.isChecked(),
                          style_text=self.styleEdit.text().strip(),
                          thinking_on=self.thinkingSwitch.isChecked(),
                          check_update_on=self.updateSwitch.isChecked())
        except Exception:
            self._settings_feedback("儲存失敗，請檢查配置檔案是否可寫後重試。", error=True)
            return
        self._load_settings()
        self._render_targets()  # 開關剛改過，回到首頁時這一行該顯該藏得重算一次
        self._settings_feedback("設定已儲存，將用於下一次回覆。")
        self.setupButton.hide()
        if not self.cands and not self._busy:
            self._empty_text()
            self.set_status("設定已就緒，等待新訊息", "idle")

    def _debug_toggled(self, on):
        """除錯檢視獨立於「儲存設定」：撥一下就開窗/收窗，順手落盤，重啟還在。"""
        settings.save(debug_view_on=on)
        if self.on_toggle_debug:
            self.on_toggle_debug(on)

    def set_debug_switch(self, on):
        """除錯窗被使用者直接關掉時把開關撥回去；遮蔽訊號，免得又回撥一圈。"""
        self.debugSwitch.blockSignals(True)
        self.debugSwitch.setChecked(on)
        self.debugSwitch.blockSignals(False)

    def _settings_feedback(self, text, error=False):
        color = "#b44832" if error else _GREEN
        qss = f"BodyLabel {{ color: {color}; background: transparent; }}"
        setCustomStyleSheet(self.settingsFeedback, qss, qss)
        self.settingsFeedback.setText(text)
        self.settingsFeedback.show()

    def open_settings(self):
        if self.pages.currentWidget() != self.settingsPage:
            self._load_settings()
        self.pages.setCurrentWidget(self.settingsPage)
        self.settingsButton.setEnabled(False)
        (self.relationshipBox if settings.has_key() else self.jev.keyEdit).setFocus()

    def _back_home(self):
        self.jev.keyEdit.clear()
        self.draft.keyEdit.clear()
        self.pages.setCurrentWidget(self.home)
        self.settingsButton.setEnabled(True)

    def _fill(self, index):
        if self._busy or not self._current or index >= len(self.cands):
            return
        try:
            pasted = self.on_fill(self.cands[index])
        except Exception as e:
            # 狀態列保持友好文案；真實原因和壓縮堆疊進聊天記錄，認得出是哪一步炸的
            import traceback
            self.set_status("未能填入，請確認聊天視窗可用後重試，或複製回覆。", "error")
            self.log(f"[填入失敗] {type(e).__name__}: {e}")
            self.log(f"[填入失敗堆疊] {' '.join(traceback.format_exc().split())[:300]}")
            return
        if pasted is False:  # Fork：LINE 輸入框位置未驗證，只寫了剪貼簿
            self.set_status("已複製，請在 LINE 輸入框按 Ctrl+V，確認後再傳送。", "success")
            return
        self.set_status("已嘗試填入，請確認內容後傳送。", "success")

    def _copy(self, index):
        if self._busy or not self._current or index >= len(self.cands):
            return
        self.app.clipboard().setText(self.cands[index])
        self.set_status("回覆已複製，可貼上並修改。", "success")

    def _capture_toggled(self, on):
        """使用者自己撥的開關：介面先改，再通知父程序去開/停採集。"""
        self._capture_text(on)
        if self.on_toggle_capture:
            self.on_toggle_capture(on)

    def set_update(self, latest, url):
        """__main__.py 背景執行緒查到比當前新的版本才會調這個。只顯示版本號和 Release 連結，別的什麼都沒有。"""
        self.updateLabel.setText(f"有新版本 v{latest}")
        self.updateLink.setUrl(url)
        self.updateBar.show()

    def set_capture(self, on, reason=""):
        """父程序回報的狀態：只改介面，不回撥（不然和父程序來回打架）。reason 為空用預設說明。"""
        self.captureSwitch.blockSignals(True)
        self.captureSwitch.setChecked(on)
        self.captureSwitch.blockSignals(False)
        self._capture_text(on, reason)

    def _capture_text(self, on, reason=""):
        """開關狀態對應的狀態行和空態文案。已有的候選不受影響，暫停了照樣能填入/複製。"""
        configured = settings.has_key()
        if not on:
            self.set_status(reason or "採集已暫停，聊天內容不再讀取", "warning")
        elif configured:
            self.set_status("等待新訊息", "idle")
        else:
            self.set_status("請先在設定中配置模型", "warning")
        if self._busy or self.cands:  # 正在生成或已有候選時，空態卡片本來就看不見
            return
        if not on:
            self.emptyTitle.setText("採集已暫停")
            self.emptyHint.setText("聊天內容暫時不再讀取。\n開啟標題欄的開關，繼續接收新訊息。")
            self.setupButton.setVisible(not configured)
        else:
            self._empty_text()

    def set_busy(self, busy):
        self._busy = busy
        self.progress.setVisible(busy)
        if busy:
            self.invalidate_replies()
            self.progress.start()
            self.set_status("正在根據新訊息整理回覆…", "busy")
            if not self.cands:
                self.emptyTitle.setText("正在想一句合適的回覆")
                self.emptyHint.setText("正在結合上下文生成建議，稍等一下。")
                self.setupButton.hide()
        else:
            self.progress.stop()
            if not self.cands:
                self._empty_text()
        for card in self.cards:
            card.set_available(self._current and not busy)

    def _empty_text(self):
        """空態卡片的預設文案，配好沒配好兩套說法。"""
        configured = settings.has_key()
        self.emptyTitle.setText("等待對方的新訊息" if configured else "先設定，再開始")
        self.emptyHint.setText("保持聊天視窗開啟。\n收到新訊息後，回覆建議會出現在這裡。"
                               if configured else "配置模型和關係背景，\n讓建議更貼近你們的對話。")
        self.setupButton.setVisible(not configured)

    def invalidate_replies(self):
        self._current = False
        if self.cands:
            self.updated.setText("上次建議")
        for card in self.cards:
            card.set_available(False)

    def set_status(self, text, kind="idle"):
        colors = {"idle": _MUTED, "busy": _GREEN, "success": _GREEN,
                  "warning": "#93611d", "error": "#b44832"}
        markers = {"idle": "●", "busy": "●", "success": "✓", "warning": "!", "error": "!"}
        qss = f"BodyLabel {{ color: {colors.get(kind, _MUTED)}; background: transparent; }}"
        setCustomStyleSheet(self.status, qss, qss)
        self.status.setText(f"{markers.get(kind, '●')}  {text}")
        if kind == "error" and self._busy:
            self.set_busy(False)
        if kind == "error" and not self.cands:
            self.emptyTitle.setText("暫時沒有可用的回覆")
            self.emptyHint.setText("請按上方提示處理。收到新的對方訊息後會再次嘗試。")
            self.setupButton.setVisible(not settings.has_key())

    def _toggle_history(self):
        self.feed.setVisible(self.feed.isHidden())
        self._history_title()

    def _history_title(self):
        action = "展開" if self.feed.isHidden() else "收起"
        count = self.counts.get(self._shown, 0)
        self.historyButton.setText(f"{action}聊天記錄" + (f" · {count}" if count else ""))

    def log(self, line):
        """採集狀態行：只進正在看的那個會話，不按會話存。"""
        bar = self.feed.verticalScrollBar()
        follow = self.feed.isHidden() or bar.value() >= bar.maximum() - 4
        self.feed.appendPlainText(line)
        if follow:
            bar.setValue(bar.maximum())

    def log_message(self, who, text, name="", timestamp=None, chat=None):
        """按會話存一份；只有正在看的那個會往顯示區裡寫。"""
        chat = chat or self._shown
        speaker = (name or "對方") if who == "her" else "我"
        timestamp = timestamp or datetime.now().strftime("%H:%M")
        self.counts[chat] = self.counts.get(chat, 0) + 1
        lines = self.feeds.setdefault(chat, [])
        lines.append(f"{timestamp}  {speaker}\n{text}\n")
        del lines[:-_LOG_LINES]
        if who == "her":
            self.hers[chat] = text
        self._add_chat(chat)
        if chat != self._shown:
            return
        self.log(lines[-1])
        if who == "her":
            self._show_latest(text)
        self._history_title()

    def _show_latest(self, text):
        self.latest.setText(text if len(text) <= 120 else text[:120] + "…")
        self.latest.setToolTip(text)
        self.context.show()

    def current_chat(self):
        """介面上正在看的會話（不一定是 LINE 當前開著的那個）。"""
        return self._shown

    def set_chat(self, title):
        """LINE 切到了哪個會話：登記進下拉框並自動跟過去，不觸發使用者選擇的回撥。"""
        if not title:
            return
        browsing = self._shown != self._chat  # 正看著的就是它、但之前是「瀏覽中」：也得重畫，把填入放開
        self._chat = title
        self._add_chat(title)
        if title != self._shown or browsing:
            self.chatBox.blockSignals(True)
            self.chatBox.setCurrentIndex(self.chatBox.findText(title))
            self.chatBox.blockSignals(False)
            self._switch_to(title)
        self._follow_text()

    def _add_chat(self, title):
        """新會話自動進下拉框；addItem 添第一條時會自己選中，別讓它觸發切換。"""
        if not title or self.chatBox.findText(title) >= 0:
            return
        self.chatBox.blockSignals(True)
        self.chatBox.addItem(title)
        self.chatBox.blockSignals(False)

    def _on_chat_selected(self, index):
        """使用者自己挑了一個會話：只換看的內容，LINE 那邊不動。"""
        title = self.chatBox.itemText(index)
        if title and title != self._shown:
            self._switch_to(title)

    def _switch_to(self, title):
        """換正在看的會話：記錄、對方最近說、條數、上次的建議一起換過去。"""
        self._shown = title
        self.feed.clear()
        for line in self.feeds.get(title, []):
            self.feed.appendPlainText(line)
        her = self.hers.get(title)
        if her:
            self._show_latest(her)
        else:
            self.context.hide()
        self._history_title()
        self._follow_text()
        self._render_targets()
        self.show_cached(self.result_of(title) if self.result_of else None)

    def set_targets(self, chat, senders, current):
        """某個會話的發言人名單（最近的在前）和當前回覆對象；正看著它才重畫。"""
        self.targets[chat] = (list(senders), current)
        if chat == self._shown:
            self._render_targets()

    def _render_targets(self):
        """開關關著、或這個會話沒有發言人（單聊），這一行就不出現。
        重填下拉框時遮蔽訊號，別把自己的填充當成使用者挑的。"""
        senders, current = self.targets.get(self._shown, ([], None))
        visible = bool(senders) and settings.reply_target()
        self.targetRow.setVisible(visible)
        if not visible:
            return
        self.targetBox.blockSignals(True)
        self.targetBox.clear()
        self.targetBox.addItems(senders)
        self.targetBox.setCurrentIndex(senders.index(current) if current in senders else 0)
        self.targetBox.blockSignals(False)

    def _on_target_selected(self, index):
        """使用者挑了回覆對象。瀏覽別的會話時改的就是那個會話的對象——記錄、候選也都按會話走，口徑一致。"""
        name = self.targetBox.itemText(index)
        if not name:
            return
        senders, _ = self.targets.get(self._shown, ([], None))
        self.targets[self._shown] = (senders, name)
        self.set_status(f"按「{name}」重新生成…", "busy")
        if self.on_target_change:
            self.on_target_change(self._shown, name)

    def at_prefix_enabled(self):
        """填入時要不要帶「@名字 」字首（只記在介面上，不落盤）。"""
        return self.atCheck.isChecked()

    def _follow_text(self):
        self.chatFollow.setText(("跟隨" if self._shown == self._chat else "瀏覽中") if self._chat else "")

    def show_cached(self, result):
        """把某個會話上次的結果放回介面；沒有就回到空態。瀏覽別的會話時只給看不給填——
        LINE 當前開著的不是它，填進去就串會話了。"""
        if result:
            self.show(result)
        else:
            self.cands = []
            self._clear_cards()
            self.insight.hide()
            self.referenceNote.hide()
            self.empty.show()
            self.updated.setText("")
            self._empty_text()
        if self._shown != self._chat:
            self.invalidate_replies()
            self.set_status(f"正在瀏覽「{self._shown}」，只看不填；切回這個會話才能用。")

    def show(self, result):
        """按推薦順序展示，按鈕始終繫結 candidates 的原始索引。"""
        self.cands = result["candidates"]
        self.set_busy(False)
        self._current = bool(self.cands)
        self._clear_cards()
        best = result.get("best_index", 0)
        if best not in range(len(self.cands)):
            best = 0
        raw_scores = result.get("scores") or []
        scores = [raw_scores[i] if i < len(raw_scores) else None for i in range(len(self.cands))]
        if not any(scores):  # 全 0/None（舊結果或接口未返回）就不展示百分比
            scores = [None] * len(self.cands)
        # 按機率降序排，推薦位（API 給的 choice）強制第一，同分按原索引
        order = sorted(range(len(self.cands)), key=lambda i: (i != best, -(scores[i] or 0), i))
        for position, index in enumerate(order):
            card = _ReplyCard(self, index, recommended=index == best, number=position, score=scores[index])
            self.replyBox.addWidget(card)
            self.cards.append(card)
        reply_to = result.get("reply_to")
        self.insightTitle.setText(f"對話參考 · 回覆給 {reply_to}" if reply_to else "對話參考")
        answers = result.get("answers") or {}
        self.summary.setText("建議：" + _choice(answers, "best_action"))
        self.intent.setText("可能意圖 · " + _choice(answers, "true_intent") +
                            "\n可能需要 · " + _choice(answers, "she_needs"))
        score = (answers.get("danger_level") or {}).get("score")
        valid_score = isinstance(score, (int, float)) and isfinite(score) and 0 <= score <= 9
        self.tension.setText(f"緊張度 {score:.0f}/9" if valid_score else "緊張度待判斷")
        color = "#996819" if valid_score and score >= 3 else _MUTED
        if valid_score and score >= 6:
            color = "#b44832"
        qss = f"BodyLabel {{ color: {color}; background: transparent; }}"
        setCustomStyleSheet(self.tension, qss, qss)
        self.empty.setVisible(not self.cands)
        self.insight.setVisible(bool(self.cands))
        self.referenceNote.setVisible(bool(self.cands) and not self._compact)
        self.updated.setText(datetime.now().strftime("%H:%M") + " 更新")
        if self.cands:
            self.set_status("建議已更新，選一句適合你的回覆", "success")
        else:
            self.set_status("未生成可用回覆，請等待下一條新訊息。", "error")

    def _clear_cards(self):
        for card in self.cards:
            self.replyBox.removeWidget(card)
            card.hide()
            card.deleteLater()
        self.cards = []

    def after(self, ms, fn):
        QTimer.singleShot(ms, fn)

    def run(self):
        self.app.exec()
