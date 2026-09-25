# -*- coding: utf-8 -*-
"""找聊天視窗 + Windows Graphics Capture 盯著它 + 從幀裡定位訊息區。幀全程記憶體，絕不落盤。"""
import ctypes
import os
import time

import numpy as np

u32 = ctypes.windll.user32

# Fork（SanHsien）：LINE 電腦版的程序名。只認它，別的聊天軟體一律不碰。
CHAT_EXES = ("line.exe",)


def find_chat_hwnd():
    """列舉可見頂層視窗，按程序名 LINE.exe 挑主視窗（標題「LINE」），沒有就取第一個。
    同程序還可能有獨立聊天窗和看圖窗，面積可能更大，所以不能按面積挑。
    Fork（SanHsien）：只認 LINE，不認任何其他聊天軟體的程序。"""
    k32 = ctypes.windll.kernel32
    found = []

    def exe_of(pid):
        h = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return ""
        buf, size = ctypes.create_unicode_buffer(1024), ctypes.c_uint(1024)
        ok = k32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
        k32.CloseHandle(h)
        return os.path.basename(buf.value).lower() if ok else ""

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if not u32.IsWindowVisible(hwnd):
            return True
        pid = ctypes.c_ulong()
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if exe_of(pid.value) in CHAT_EXES:
            title = ctypes.create_unicode_buffer(256)
            u32.GetWindowTextW(hwnd, title, 256)
            found.append((hwnd, title.value))
        return True

    u32.EnumWindows(cb, 0)
    if not found:
        raise RuntimeError("沒找到聊天視窗，開著嗎？")
    return next((h for h, t in found if t == "LINE"), found[0][0])


def unminimize(hwnd):
    """Windows 不渲染最小化的視窗，什麼截圖法都拿不到畫面。發現被最小化就無啟用還原，再壓到所有視窗最底下——
    看著跟收起來一樣，但 DWM 繼續畫。不搶焦點、不動大小位置。返回是否動了手。"""
    if not u32.IsIconic(hwnd):
        return False
    u32.ShowWindow(hwnd, 4)  # SW_SHOWNOACTIVATE
    u32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, 0x13)  # HWND_BOTTOM, SWP_NOSIZE|SWP_NOMOVE|SWP_NOACTIVATE
    return True


def chat_area(full, header_h=60):
    """訊息列表區 (x0, y_top, x1, y_in, 面板底色, y_pane)，全靠畫素錨點，不寫死座標，深淺主題通用：
    - 面板底色 = 右半邊最常見的顏色（抽樣算，全量 np.unique 在 2560 寬的圖上要半秒）
    - 面板左/右邊界 = 第一/最後一根「底色佔比 > 30%」的列（聯絡人列表是另一種底色，佔比 0）
    - y_pane = 面板第一行；會話名就印在 y_pane~y_top 這條頭部裡（公告條也在裡面）
    - 橫向分隔線 = 整行單色且非底色；輸入框頂 y_in = 面板 45% 高度以下第一根；
      公告條下面那根（有的話）= 訊息區頂 y_top，沒有就用 header_h
    認不出（視窗太小 / 拖到一半佈局沒鋪好）返回 None。
    ponytail: 輸入框拉高超過面板一半會認錯；header_h 按 100% DPI 給的，縮放了按比例調。"""
    H, W = full.shape[:2]
    right = full[::8, W // 2::8].reshape(-1, 3)
    vals, cnt = np.unique(right, axis=0, return_counts=True)
    bg = vals[cnt.argmax()]
    isbg = np.abs(full.astype(int) - bg).sum(-1) <= 6
    col = isbg[H // 4: H * 3 // 4].mean(0)
    x0 = int(np.argmax(col > 0.3))
    x1 = W - int(np.argmax(col[::-1] > 0.3))
    row = isbg[:, x0:x1].mean(1)
    y0 = int(np.argmax(row > 0.9))
    y1 = H - int(np.argmax(row[::-1] > 0.9))
    band = full[y0:y1, x0:x1].astype(int)
    seps = y0 + np.where((band.std(axis=(1, 2)) < 4) & (row[y0:y1] < 0.1))[0]
    seps = [int(s) for i, s in enumerate(seps) if i == 0 or s - seps[i - 1] > 3]
    below = [s for s in seps if s > y0 + 0.45 * (y1 - y0)]
    y_in = below[0] if below else y1
    above = [s for s in seps if y0 + header_h < s < y_in - 50]
    y_top = above[-1] if above else y0 + header_h
    if x1 - x0 < 100 or y_in - y_top < 40:
        return None
    return x0, y_top, x1, y_in, bg, y0


class Capture:
    """WGC 盯視窗。採集執行緒只做「跟上一幀比」；settled() 在畫面停穩後交出整幀，中間幀（滾動動畫、
    新訊息滑入的半截氣泡）全跳過。動圖表情永遠停不穩，所以最多等 max_wait 秒照樣交。"""

    def __init__(self, hwnd, settle=0.25, max_wait=1.0):
        from windows_capture import WindowsCapture

        self.settle, self.max_wait = settle, max_wait
        self.shape = self.area = self.last = self.pending = None
        self.t = self.t0 = 0.0
        # 包裝層預設 cursor_capture=True，會去調 SetIsCursorCaptureEnabled。
        # 這個屬性要 Win10 2004（build 19041）才有，1909 及更早直接拋 CursorConfigUnsupported。
        # 顯式 None 走系統預設，不去切換；draw_border 同理。
        cap = WindowsCapture(cursor_capture=None, draw_border=None, window_hwnd=hwnd)
        cap.event(self.on_frame_arrived)
        cap.event(self.on_closed)
        self.ctl = cap.start_free_threaded()

    def on_frame_arrived(self, frame, control):
        full = np.ascontiguousarray(frame.frame_buffer[:, :, :3][:, :, ::-1])  # BGRA → RGB；緩衝區回撥後就沒了，必須拷
        if full.max() == 0:
            return
        if self.area is None or full.shape != self.shape:
            self.shape, self.area = full.shape, chat_area(full)
        if self.area is None:
            return
        x0, y0, x1, y1 = self.area[:4]  # 拿上一次的訊息區做 diff 就夠了，游標閃爍在輸入框裡，不算變化
        # ponytail: diff 不含頭部——公告條會滾動，帶上它就永遠停不穩。切會話時訊息區必然也變，照樣出幀。
        chat = full[y0:y1, x0:x1]
        if self.last is not None and np.array_equal(chat, self.last):
            return
        self.last = chat
        if self.pending is None:
            self.t0 = time.perf_counter()
        self.pending, self.t = full, time.perf_counter()

    def on_closed(self):
        pass

    def settled(self):
        """停穩了就返回整幀，否則 None。"""
        if self.pending is None:
            return None
        now = time.perf_counter()
        if now - self.t < self.settle and now - self.t0 < self.max_wait:
            return None
        full, self.pending = self.pending, None
        return full

    def alive(self):
        return not self.ctl.is_finished()

    def stop(self):
        self.ctl.stop()

    def wait(self):
        self.ctl.wait()  # 採集執行緒若是報錯死的，這裡把錯誤丟擲來
