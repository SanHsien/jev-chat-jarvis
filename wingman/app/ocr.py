# -*- coding: utf-8 -*-
"""訊息區截圖 → 誰說了什麼。RapidOCR 吃 numpy，不落盤。"""
import difflib
import re
import time

import numpy as np
from rapidocr_onnxruntime import RapidOCR


_ENGINE = None


def _engine():
    """OCR 引擎全程序共用：一個例項 ~40MB，每個會話一個 Reader，不能各帶一個。
    det_limit_type 預設 'min' 會把小圖放大到短邊 736，裁小反而更慢；必須 'max'。"""
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = RapidOCR(intra_op_num_threads=4, det_limit_type="max", det_limit_side_len=4000)
    return _ENGINE


def read_title(header):
    """面板頭部那一條截圖 → 會話名（numpy RGB）。取最靠上的一行，同一行裡取最左的
    （右邊是圖示按鈕，OCR 不出字；下面那行是公告）。群聊的成員數「(422)」去掉，只留名字當 key。
    認不出返回 ""。一次約 60ms，所以呼叫方只在頭部畫素變了時才問。"""
    res, _ = _engine()(header, use_cls=False)
    if not res:
        return ""
    first = min(res, key=lambda r: r[0][0][1])
    row = first[0][0][1] + (first[0][2][1] - first[0][0][1])  # 框底：頂在這之上的算同一行
    text = min((r for r in res if r[0][0][1] < row), key=lambda r: r[0][0][0])[1]
    return re.sub(r"\s*[（(]\d+[)）]\s*$", "", text.strip())


def who_said(chat, box):
    """按 OCR 框裡的顏色分類，不看 x 座標。返回 (誰, 底色, 墨高)：
    先看底色平不平：框裡眾數顏色佔比 <45% 就是圖片（頭像/照片/表情包）裡的字 → None 丟掉。
    綠底 → me；非綠且文字對底色對比度 ≥150 → her；其餘（引用塊、群裡的發言人名、時間戳、系統提示、
    連結卡片描述——都是灰字，對比度 80~95）→ "gray"。
    實測：氣泡正文對比度 178~208，me 綠泡 142~150，灰字 ≤ 93。深淺主題都靠這套。
    墨高 = 框裡最長一段連續有字的行數（OCR 框對小字有固定 padding、還會蹭到上下行，不能拿框高比大小）。"""
    xs, ys = [p[0] for p in box], [p[1] for p in box]
    reg = chat[int(min(ys)):int(max(ys)), int(min(xs)):int(max(xs))].astype(int)
    if reg.size == 0:
        return None, None, 0
    vals, cnt = np.unique(reg.reshape(-1, 3), axis=0, return_counts=True)
    bg = vals[cnt.argmax()]
    if cnt.max() / reg.shape[0] / reg.shape[1] < 0.45:
        # 文字必須落在平底色上：WGC 幀是精確畫素，氣泡/面板裡眾數顏色佔 0.56~0.82，
        # 頭像/照片/表情包裡只有 0.1~0.3——那是圖片裡的字（頭像上的「借仲夏夜之夢」之類），不是訊息。
        # ponytail: 只對精確畫素的幀成立；縮放/壓縮過的截圖（比如拿預覽窗再截一次的圖）底色會糊成幾百種顏色，全會被當圖片。
        return None, bg, 0
    diff = np.abs(reg @ [0.299, 0.587, 0.114] - bg @ [0.299, 0.587, 0.114])
    ink_h = best = 0
    for r in (diff > 60).any(axis=1):
        best = best + 1 if r else 0
        ink_h = max(ink_h, best)
    if bg[1] > bg[0] + 40 and bg[1] > bg[2] + 40:
        return "me", bg, ink_h
    return ("her" if diff.max() >= 150 else "gray"), bg, ink_h


def similar(a, b):
    """同一段畫素挪個位置 OCR 會抖（「傻逼了」↔「傻逼」、「不好意思」↔「不好竟思」），按相似度判同一條。"""
    if a == b or difflib.SequenceMatcher(None, a, b).ratio() >= 0.75:
        return True
    return len(a) == len(b) >= 3 and sum(x != y for x, y in zip(a, b)) <= 1  # 短句錯一個字


class Reader:
    """一個會話一個 Reader：lh/seen 各自算各自的，切走再切回來不會把舊訊息當新的重報一遍。"""

    def __init__(self):
        self.ocr = _engine()
        self.lh = None  # 正常氣泡字高，頭一幀定
        self.seen = []  # [(who, name, text)]，累計，封頂 500
        self.last_boxes = []  # 除錯檢視用：[(x0,y0,x1,y1,kind,text)]，訊息區裁剪座標
        self.last_ms = 0  # 上一幀 OCR 耗時

    def read(self, chat, pane_bg):
        """→ [(who, name, text, y)]，同一氣泡的多行已合併。who ∈ me/her；name 群聊裡是發言人，單聊 None。
        順帶把每個框的分類記進 self.last_boxes（除錯檢視畫框用，幾十個 tuple，不開也不虧）。"""
        t0 = time.perf_counter()
        res, _ = self.ocr(chat, use_cls=False)
        self.last_ms = int((time.perf_counter() - t0) * 1000)
        self.last_boxes = []
        W = chat.shape[1]
        # 群聊：每條 her 氣泡上方一行灰色發言人名（靠左、短、不帶冒號、印在面板底色上），從上往下掃，名字帶給後面的氣泡。
        # 引用塊/時間戳/公告帶冒號，連結卡片灰字印在氣泡底色上，都不會被當成名字。
        # ponytail: 名字行被 OCR 漏掉時會掛到上一個人頭上。
        name, raw = None, []
        for box, text, _ in sorted(res or [], key=lambda r: r[0][0][1]):
            kind, bg, h = who_said(chat, box)
            xs, ys = [p[0] for p in box], [p[1] for p in box]
            rect = (int(min(xs)), int(min(ys)), int(max(xs)), int(max(ys)))
            if kind == "gray":
                on_pane = np.abs(bg - pane_bg).sum() <= 6
                taken = bool(on_pane and box[0][0] < 0.25 * W and len(text) <= 16
                             and not re.search("[:：]", text))
                if taken:
                    name = text
                self.last_boxes.append(rect + ("name" if taken else "gray", text))
                continue
            if kind is None or (self.lh and h < 0.6 * self.lh):
                # 字比正常氣泡小得多 = 圖片訊息（截圖/表情包）裡的字，不是氣泡
                self.last_boxes.append(rect + ("image" if kind is None else "tiny", text))
                continue
            self.last_boxes.append(rect + (kind, text))
            raw.append((kind, name if kind == "her" else None, text, box[0][1], box[2][1], h))
        if not self.lh and len(raw) >= 3:
            self.lh = float(np.median([r[5] for r in raw]))
        # 同一氣泡的多行合併：同人、上一行底到這一行頂的間距不到半個字高（不同氣泡之間至少隔一個字高）
        lines = []
        for who, nm, text, top, bottom, h in raw:
            if lines and lines[-1][0] == who and lines[-1][1] == nm and top - lines[-1][4] < 0.6 * (self.lh or h):
                lines[-1][2] += text
                lines[-1][4] = bottom
            else:
                lines.append([who, nm, text, top, bottom])
        return [(w, n, t, y) for w, n, t, y, _ in lines]

    def new_lines(self, lines):
        """去重（滾動不重複）→ 這一幀裡真正新出現的 [(who, name, text)]。
        本幀有已知行時只要已知行下方的：往上滾翻出來的舊訊息在已知行上方，不算。
        本幀一行已知的都沒有（大圖把舊文字全頂出去了、切了聊天、滾遠了）：全算，寧可多算不能漏。
        ponytail: 同一人連發兩句一模一樣的會吞一句——對觸發分析無害。"""
        known_y = [y for w, n, t, y in lines if self._seen(w, n, t)]
        floor = max(known_y) if known_y else -1
        new = [(w, n, t) for w, n, t, y in lines if y > floor and not self._seen(w, n, t)]
        self.seen.extend((w, n, t) for w, n, t, _ in lines if not self._seen(w, n, t))
        del self.seen[:-500]
        return new

    def _seen(self, who, name, text):
        # 名字不參與判重：名字行滾出畫面後同一條訊息會從 her(LO) 變成 her，不能算新訊息
        return any(w == who and similar(t, text) for w, _, t in self.seen)
