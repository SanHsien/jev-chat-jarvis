# -*- coding: utf-8 -*-
"""對話副駕 Windows 版入口：python -m wingman（在 repo 根目錄，先 pip install -r requirements-windows.txt）。
父程序：只管介面。截圖 + OCR 在 wingman/app/worker.py 的子程序裡跑，佇列裡收新訊息 →
冒出新的對方訊息才調 engine → 懸浮窗給 3 條候選 → 人點「填入」。傳送永遠手動。靜默期零呼叫。
上下文、結果、聊天記錄都按會話名（子程序 OCR 頭部標題得來）分開存，切會話不串味。

兩個模型（判斷 Jev / 起草語言模型）的來源和 key 在獨立設定頁填寫，不用改程式碼。
"""
import ctypes
import multiprocessing
import queue
import threading
import traceback
from collections import deque

from wingman.app import settings, update, worker
from wingman.app.capture import find_chat_hwnd
from wingman.app.fill import fill
from wingman.app.overlay import Overlay
from wingman.app.version import VERSION
from wingman.core.engine import analyze

# {會話名: {history, result, rev, target, senders}}：每個會話各自的上下文、上次結果和版本號，互不串味
# history 裡是 [(who, text, name)]，engine 只認 her/me，name 是群裡的發言人（單聊/自己說的是 None）；
# 只是緩衝區，實際喂模型幾條由設定裡的「參考上下文」決定
# senders：這個群裡發過言的人，去重、最近的排最前；target：使用者挑的回覆對象（None = 跟著最近那個走）
chats = {}
state = {"area": None, "busy": False, "rerun": None, "hwnd": None, "chat": ""}
results = queue.Queue()
update_result = queue.Queue()  # 獨立小佇列，別跟 results 的 (kind, r, title, revision) 形狀攪在一起


def chat_of(title):
    return chats.setdefault(title, {"history": deque(maxlen=60), "result": None, "rev": 0,
                                    "target": None, "senders": []})


def target_of(title):
    """這個會話現在的回覆對象：使用者挑過且人還在就用它，否則用最近說話的那個；單聊沒有發言人 → None。"""
    chat = chat_of(title)
    if chat["target"] in chat["senders"]:
        return chat["target"]
    return chat["senders"][0] if chat["senders"] else None


def fill_reply(text):
    if state["hwnd"] is None:  # 子程序重開過，hwnd 可能換了，用最新的
        raise RuntimeError("未找到聊天視窗，請確認已經開啟")
    if state["area"] is None:
        raise RuntimeError("輸入區域尚不可用，請確認聊天視窗可見（不要最小化）")
    if settings.reply_target() and ov.at_prefix_enabled():
        target = target_of(ov.current_chat())  # 填進去的是介面上正看著的那個會話的對象
        if target:
            text = f"@{target} " + text  # 純文字，LINE 不認成真正的 @，只是讓群裡看得出在跟誰說
    return fill(state["hwnd"], state["area"], text)


def spawn_worker():
    """開一個採集子程序，它跟著 capture_on 走：置位=採集，清掉=暫停。"""
    p = multiprocessing.Process(target=worker.run,
                                args=(q, state["hwnd"], capture_on, debug_on), daemon=True)
    p.start()
    return p


def set_debug(on):
    """除錯檢視開關：開 → 開窗 + 置位（子程序這才開始送幀，一幀 2~3MB）；關 → 清掉 + 收窗。"""
    global dbg
    if not on:
        debug_on.clear()
        if dbg is not None:
            dbg.hide()
        return
    if dbg is None:
        from wingman.app.debugwin import DebugWindow

        dbg = DebugWindow(on_close=on_debug_closed)
    dbg.show()
    debug_on.set()


def on_debug_closed():
    """使用者直接關了除錯窗 = 把開關也關了，否則設定頁顯示開著但沒窗。"""
    debug_on.clear()
    ov.set_debug_switch(False)
    settings.save(debug_view_on=False)


def on_toggle_capture(on):
    """標題欄開關。啟動時沒找到 LINE 就沒有子程序，這會兒再找一次，找到了才真開得起來。"""
    global child
    if not on:
        capture_on.clear()
        return
    if child is None:
        try:
            state["hwnd"] = find_chat_hwnd()
        except RuntimeError:
            ov.set_capture(False, "未找到聊天視窗，開啟後再開啟採集")
            return
        child = spawn_worker()
    capture_on.set()


def analyze_bg(msgs, title, revision, reply_to=None):
    """背景執行緒只跑網路呼叫，結果丟佇列；UI 只在主執行緒的 tick 裡動（Qt 不能跨執行緒碰）。"""
    try:
        results.put(("ok", analyze(msgs, settings.relationship(), context=settings.context(),
                                   model=settings.draft_model() or None,
                                   provider=settings.draft_provider(),
                                   base_url=settings.draft_base_url() or None,
                                   reply_to=reply_to, style=settings.style(),
                                   thinking=settings.thinking(),
                                   jev_provider=settings.jev_provider(),
                                   jev_model=settings.jev_model() or None),
                     title, revision))
    except Exception as e:
        results.put(("err", f"分析失敗: {e}", title, revision))


def check_update_bg():
    """啟動時背景查一次新版本，跟 analyze_bg 一個套路：網路呼叫在執行緒裡，UI 只在 tick() 裡動。"""
    r = update.check_latest(VERSION)
    if r:
        update_result.put(r)


def start_analyze(title, msgs):
    if not settings.has_jev_key():
        ov.set_status("請先在設定中配置模型", "warning")
        return
    if not settings.has_llm_key():
        ov.set_status(f"起草來源 {settings.draft_provider_name()} 沒填金鑰，去設定裡補上", "warning")
        return
    state["busy"] = True
    ov.set_busy(True)
    reply_to = target_of(title) if settings.reply_target() else None  # 開關關著就是今天的行為
    threading.Thread(target=analyze_bg, args=(msgs, title, chat_of(title)["rev"], reply_to),
                     daemon=True).start()


def on_target_change(title, name):
    """使用者挑了回覆對象：記下來，這個會話裡有對方的話就照新對象重跑一次。"""
    chat = chat_of(title)
    chat["target"] = name
    msgs = list(chat["history"])
    if not any(m[0] == "her" for m in msgs):
        return
    if state["busy"]:
        state["rerun"] = (title, msgs)
        ov.set_busy(True)
    else:
        start_analyze(title, msgs)


def drain():
    """把子程序佇列裡攢的東西全收掉。"""
    global child
    while True:
        try:
            msg = q.get_nowait()
        except queue.Empty:
            return
        kind = msg[0]
        if kind == "area":  # 只是視窗挪了位置，座標跟著更新，別的什麼都不用動
            state["area"] = msg[1]
            continue
        if kind == "chat":  # LINE 切了會話，介面跟過去（使用者正瀏覽別的會話時也跟，LINE 是準的）
            state["chat"] = msg[1]
            ov.set_chat(msg[1])
            continue
        if kind == "debug":  # 除錯檢視的一幀；視窗不在就直接丟掉
            if dbg is not None:
                dbg.show_packet(msg[1])
            continue
        if kind == "status":  # 單幀識別失敗/報錯，提示一下就好，別把正在跑的分析和已知座標清掉
            ov.set_status(msg[1], "warning")
            ov.log(msg[1])
            continue
        if kind == "paused":  # 子程序確認已暫停
            ov.set_capture(False)
            continue
        if kind == "resumed":  # 子程序重新開始採集
            ov.set_capture(True)
            continue
        if kind == "dead":  # 採集徹底停了（LINE 關了之類），這才是真的要清狀態
            state["area"] = None
            for c in chats.values():  # 在跑的分析作廢，回來的結果不再往介面上貼
                c["rev"] += 1
            state["rerun"] = None
            ov.invalidate_replies()
            ov.set_busy(False)
            ov.set_capture(False, msg[1])
            ov.log(msg[1])
            if child is not None:  # 子程序已經不幹活了，收掉引用，下次開啟開關重開一個
                child.terminate()
                child.join()
                child = None
            continue
        _, title, new, area = msg
        state["area"] = area
        chat = chat_of(title)
        chat["rev"] += 1  # 這個會話有新訊息了，它在跑的分析作廢
        if title == ov.current_chat():  # 看的是別的會話就別把人家的候選劃掉
            ov.invalidate_replies()
        for who, name, text in new:
            chat["history"].append((who, text, name))
            ov.log_message(who, text, name, chat=title)
            if who == "her" and name:  # 群裡發過言的人，去重後最近的排最前
                if name in chat["senders"]:
                    chat["senders"].remove(name)
                chat["senders"].insert(0, name)
        ov.set_targets(title, chat["senders"], target_of(title))  # 顯不顯示這一行由懸浮窗按開關決定
        if new[-1][0] == "her":  # 只有對方最新說話才值得分析
            msgs = list(chat["history"])
            if state["busy"]:
                state["rerun"] = (title, msgs)
                ov.set_busy(True)
            else:
                start_analyze(title, msgs)
        else:
            state["rerun"] = None
            ov.set_busy(False)
            ov.set_status("你已回覆，等待對方的新訊息")


def tick():
    try:
        drain()
        while not update_result.empty():
            latest, url = update_result.get()
            ov.set_update(latest, url)
        while not results.empty():
            kind, r, title, revision = results.get()
            state["busy"] = False
            if state["rerun"]:  # 分析期間又來了新訊息，接著跑最新的
                (t, msgs), state["rerun"] = state["rerun"], None
                start_analyze(t, msgs)
                continue
            if revision != chat_of(title)["rev"]:  # 這個會話後來又說話了，這份結果過期了
                ov.set_busy(False)
                continue
            if kind == "ok":
                chat_of(title)["result"] = r  # 先存著；正看著這個會話才立刻貼上去
                if title == ov.current_chat():
                    ov.show(r)
                else:
                    ov.set_busy(False)
            else:
                ov.set_busy(False)
                ov.set_status("生成失敗，請檢查網路和服務設定；新訊息到來後會重試。", "error")
                ov.log(r)
    except Exception:
        traceback.print_exc()  # 一幀出錯不退出
    ov.after(50, tick)


if __name__ == "__main__":  # Windows 的 spawn 會讓子程序重新執行本檔案，沒這行就無限套娃開程序
    multiprocessing.freeze_support()  # 打包成 exe 後 spawn 出來的子程序會重跑一遍 exe，沒這行就無限彈介面
    ctypes.windll.user32.SetProcessDPIAware()
    q = multiprocessing.Queue()
    capture_on = multiprocessing.Event()  # 父子程序共用的開關，置位=採集
    debug_on = multiprocessing.Event()  # 同上，置位=子程序往佇列裡送整幀給除錯窗
    ov = Overlay(on_fill=fill_reply, on_toggle_capture=on_toggle_capture,
                 on_target_change=on_target_change, on_toggle_debug=set_debug,
                 result_of=lambda t: chats.get(t, {}).get("result"))
    child = dbg = None
    try:
        state["hwnd"] = find_chat_hwnd()
    except RuntimeError:
            ov.set_capture(False, "未找到聊天視窗，開啟後再開啟採集")
    else:
        capture_on.set()
        child = spawn_worker()
    if settings.debug_view():  # 上次開著就直接開回來
        set_debug(True)
    if not settings.has_jev_key():
        ov.set_status("請先在設定中配置模型", "warning")
        ov.after(0, ov.open_settings)
    if settings.check_update() and update.parse_version(VERSION):  # 開發版沒有版本號，不查也不煩原始碼使用者
        threading.Thread(target=check_update_bg, daemon=True).start()
    ov.after(50, tick)
    try:
        ov.run()
    finally:
        if child is not None:
            child.terminate()
