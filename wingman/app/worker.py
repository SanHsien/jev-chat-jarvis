# -*- coding: utf-8 -*-
"""子程序：截圖 → 定位訊息區 → OCR 頭部會話名和訊息 → 按會話去重，全在這邊跑。
一次 OCR 250~800ms，放父程序的 Qt 主執行緒介面就僵了。
只往佇列裡丟純 tuple/str（底色 bg 是 numpy，留在這邊不過佇列）。幀全程記憶體，絕不落盤。"""
import ctypes
import time
import traceback

import numpy as np

from wingman.app.capture import Capture, chat_area, unminimize
from wingman.app.ocr import Reader, read_title, similar


def _err(q):
    """異常壓成一行發給父程序，子程序的 stderr 一般沒人看得見。"""
    q.put(("status", " ".join(traceback.format_exc().split())[-200:]))


def _packet(full, area, title, reader, lines):
    """除錯檢視的一幀：整幀縮到長邊 ≤1100 再走佇列（原幀 2560 寬裸傳要 20MB），只在記憶體裡傳，不落盤。
    整數步長切片夠用，不引新依賴；框和座標照發原始值，畫的那邊按 scale 折算。"""
    k = max(1, -(-max(full.shape[:2]) // 1100))
    small = np.ascontiguousarray(full[::k, ::k])
    return {"w": small.shape[1], "h": small.shape[0], "rgb": small.tobytes(), "scale": k,
            "area": tuple(int(v) for v in area[:4]) if area else None,
            "pane_top": int(area[5]) if area else 0, "title": title,
            "boxes": reader.last_boxes if reader else [],
            "lines": [(w, n, t) for w, n, t, _ in lines],
            "ocr_ms": reader.last_ms if reader else 0, "ts": time.time()}


def run(q, hwnd, enabled, debug_on):
    """enabled 置位=採集，清掉=暫停。暫停時停掉 WGC 會話（Windows 那圈黃色採集邊框也跟著沒了），
    恢復時重開一個；readers 一直留著，去重狀態不丟，恢復後不會把螢幕上的舊訊息再報一遍。
    debug_on 置位才往佇列裡送整幀（一幀 2~3MB），關著一點額外活都不幹。"""
    ctypes.windll.user32.SetProcessDPIAware()
    cap = None
    readers = {}  # {會話名: Reader}，一個會話一套去重狀態
    title, head = "", None  # 當前會話名 / 上一幀的頭部畫素
    last_area = None  # 上次發給父程序的 4 元組，變了才再發一次
    warned = False  # 訊息區識別失敗是否已經報過，拖視窗時別每幀刷一條
    while True:
        if not enabled.is_set():
            if cap is not None:
                cap.stop()
                cap = None
                q.put(("paused",))
            enabled.wait()
            continue
        if cap is None:
            try:
                cap = Capture(hwnd)
            except Exception as e:
                q.put(("dead", "無法開始採集：" + (" ".join(str(e).split())[:120] or type(e).__name__)))
                enabled.clear()  # 自己清掉，下一圈就去等著，別一秒重試幾十次
                continue
            q.put(("resumed",))
        if not cap.alive():
            break
        try:
            unminimize(hwnd)
            full = cap.settled()
            if full is not None:
                reader, lines = None, []  # 除錯檢視要用，訊息區沒認出來時就是空的
                area = chat_area(full)  # 每次停穩都重算：拖完視窗 LINE 佈局會晚一拍才鋪好，只按尺寸變化算一次會鎖死
                if area is None:
                    if not warned:
                        q.put(("status", "訊息區認不出來（視窗太小？）"))
                        warned = True
                else:
                    warned = False
                    cap.area = area  # 採集執行緒拿它做 diff
                    x0, y0, x1, y1, bg, y_pane = area
                    rect = (x0, y0, x1, y1)
                    if rect != last_area:
                        q.put(("area", rect))
                        last_area = rect
                    crop = full[y_pane:y0, x0:x1]  # 頭部：會話名在這裡
                    if head is None or not np.array_equal(crop, head):  # 名字沒動就別白跑一次 OCR
                        head = crop
                        name = read_title(crop)
                        # OCR 抖一下（「小分隊」↔「小分認」）不能分裂出一個新會話
                        name = next((k for k in readers if similar(k, name)), name) if name else ""
                        # ponytail: 認不出就沿用上次；開頭就認不出給個佔位名，總比把訊息全丟了強
                        name = name or title or "當前會話"
                        if name != title:
                            title = name
                            q.put(("chat", title))
                    reader = readers.setdefault(title, Reader())
                    lines = reader.read(full[y0:y1, x0:x1], bg)
                    new = reader.new_lines(lines)
                    if new:
                        q.put(("lines", title, new, rect))
                if debug_on.is_set():
                    q.put(("debug", _packet(full, area, title, reader, lines)))
        except Exception:
            _err(q)  # 一幀出錯不退出
        time.sleep(0.05)
    q.put(("dead", "採集停了（聊天視窗關了？）"))
    try:
        cap.wait()  # 採集執行緒若是報錯死的，這裡把錯丟擲來
    except Exception:
        _err(q)
