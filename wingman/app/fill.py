# -*- coding: utf-8 -*-
"""把選中的候選填進 LINE 輸入框：寫剪貼簿 → 點輸入框 → Ctrl+V。絕不發回車、絕不點傳送。

Fork（SanHsien）：點輸入框的座標是按原版目標視窗的佈局算的，LINE 電腦版還沒實機驗證。
驗證前 VERIFIED = False：只寫剪貼簿、不動滑鼠鍵盤，由人自己在 LINE 輸入框按 Ctrl+V。"""
import ctypes
import ctypes.wintypes as w
import time

u32, k32 = ctypes.windll.user32, ctypes.windll.kernel32

# LINE 電腦版輸入框位置實機驗證後才改 True；False 時 fill() 只寫剪貼簿
VERIFIED = False

# 64 位下 ctypes.windll 預設 restype 是 32 位 c_int，而 GlobalAlloc 返回 64 位 HGLOBAL——
# 不宣告型別控制代碼會被截斷成垃圾值，GlobalLock(垃圾) 返回 NULL，memmove(NULL,…) 就是
# "access violation writing 0x0"。所有帶控制代碼/指標的函式必須顯式宣告。
k32.GlobalAlloc.restype = ctypes.c_void_p
k32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
k32.GlobalLock.restype = ctypes.c_void_p
k32.GlobalLock.argtypes = [ctypes.c_void_p]
k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
k32.GlobalFree.argtypes = [ctypes.c_void_p]
u32.SetClipboardData.restype = ctypes.c_void_p
u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]


def set_clipboard(text):
    """寫剪貼簿。剪貼簿可能被別的程式佔著（剪貼簿管理器、截圖工具），重試幾次。"""
    data = text.encode("utf-16-le") + b"\0\0"
    for attempt in range(10):
        if not u32.OpenClipboard(None):
            time.sleep(0.05)
            continue
        try:
            u32.EmptyClipboard()
            h = k32.GlobalAlloc(0x2, len(data))  # GMEM_MOVEABLE
            if not h:
                raise RuntimeError("GlobalAlloc 失敗")
            p = k32.GlobalLock(h)
            if not p:
                k32.GlobalFree(h)
                raise RuntimeError("GlobalLock 失敗")
            ctypes.memmove(p, data, len(data))
            k32.GlobalUnlock(h)
            if not u32.SetClipboardData(13, h):  # CF_UNICODETEXT；成功後控制代碼歸系統，不能 Free
                k32.GlobalFree(h)
                raise RuntimeError(f"SetClipboardData 失敗 (attempt {attempt})")
            return
        finally:
            u32.CloseClipboard()
    raise RuntimeError("OpenClipboard 連續失敗，剪貼簿被其他程式佔用")


def fill(hwnd, area, text):
    """area = 訊息區 (x0, y0, x1, y1)；輸入框就在底線 y1 下面。
    返回 True = 已貼進輸入框；False = 只寫了剪貼簿（VERIFIED 為 False）。"""
    from wingman.app.capture import unminimize

    set_clipboard(text)
    if not VERIFIED:
        return False
    r = w.RECT()
    if ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) != 0:  # 擴充套件邊界，跟 WGC 幀對齊
        u32.GetWindowRect(hwnd, ctypes.byref(r))
    x0, _, _, y1 = area
    cx, cy = r.left + x0 + 60, r.top + y1 + 40  # 分隔線下 40px = 輸入框文字區；工具欄和「傳送」在輸入區最底下，碰不到
    unminimize(hwnd)

    # SetForegroundWindow 有前臺視窗保護，普通背景程序會被拒；AttachThreadInput 繞過
    fg = u32.GetForegroundWindow()
    if fg != hwnd:
        fg_tid = u32.GetWindowThreadProcessId(fg, None)
        our_tid = k32.GetCurrentThreadId()
        u32.AttachThreadInput(our_tid, fg_tid, True)
        u32.SetForegroundWindow(hwnd)
        u32.AttachThreadInput(our_tid, fg_tid, False)
        time.sleep(0.15)  # 給 LINE 一點時間響應前臺切換

    old = w.POINT()
    u32.GetCursorPos(ctypes.byref(old))
    u32.SetCursorPos(cx, cy)
    time.sleep(0.05)
    # Fork：左撇子把主鍵換成右鍵時，系統會把注入的「左鍵」也對調成右鍵（開出右鍵選單）。
    # 對調了就送右鍵事件，系統換回來剛好是主鍵點擊（上游 issue #34）。
    down, up = (0x8, 0x10) if u32.GetSystemMetrics(23) else (0x2, 0x4)  # SM_SWAPBUTTON
    u32.mouse_event(down, 0, 0, 0, 0)  # 主鍵按下
    u32.mouse_event(up, 0, 0, 0, 0)  # 抬起
    time.sleep(0.05)
    u32.SetCursorPos(old.x, old.y)
    time.sleep(0.05)
    # 游標移到已有文字的絕對末尾：點選落在文字中間時 caret 會插在中間，
    # 連續多次填入就序列錯亂；Ctrl+End 保證新內容永遠追加在最後
    u32.keybd_event(0x11, 0, 0, 0)  # Ctrl 按下
    u32.keybd_event(0x23, 0, 0, 0)  # End 按下（VK_END）
    u32.keybd_event(0x23, 0, 2, 0)  # End 抬起
    u32.keybd_event(0x11, 0, 2, 0)  # Ctrl 抬起
    time.sleep(0.05)
    u32.keybd_event(0x11, 0, 0, 0)  # Ctrl
    u32.keybd_event(0x56, 0, 0, 0)  # V
    u32.keybd_event(0x56, 0, 2, 0)
    u32.keybd_event(0x11, 0, 2, 0)
    # 到此為止。發不發、改不改，人來。
    return True
