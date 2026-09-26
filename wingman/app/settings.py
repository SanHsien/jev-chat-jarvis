# -*- coding: utf-8 -*-
"""設定持久化。key 硬約束（AGENTS.md 產品硬約束 5）：只進環境變數，絕不落檔案；其餘設定落 config.json。

key 的持久化走 Windows 使用者環境變數（登錄檔 HKCU\\Environment，跟 setx 寫的是同一個地方）。
全程只有兩把：判斷 JEV_API_KEY、起草 LLM_API_KEY，跟選哪家來源無關。
讀的時候先看程序環境，沒有就直接讀登錄檔——IDE 啟動時把環境快照拿走了，之後再 Run 繼承的還是舊環境，
只靠 os.environ 會「儲存了下次開啟還是沒有」。"""
from __future__ import annotations

import ctypes
import json
import os
import sys  # 只為下面這一處：打包後 __file__ 指向臨時解包目錄，config.json 得放在 exe 旁邊才存得住

from wingman.core.providers import CUSTOM, DRAFT_PROVIDERS, JEV_ENV, JEV_PROVIDERS, LEGACY, LLM_ENV

_ROOT = (os.path.dirname(sys.executable) if getattr(sys, "frozen", False)
         else os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG = os.path.join(_ROOT, "config.json")
_DEFAULT_RELATIONSHIP = "romantic partners"
_DEFAULT_CONTEXT = 10
_DEFAULT_JEV = "openrouter"
_DEFAULT_DRAFT = "openrouter"


def _read(name: str, default=None):
    """讀 config.json 裡的一個欄位；每次都重新讀檔案，改設定不用重啟程序。"""
    try:
        with open(_CONFIG, encoding="utf-8") as f:
            value = json.load(f).get(name)
    except (OSError, ValueError):
        return default
    return default if value is None else value

def relationship() -> str:
    return str(_read("relationship") or _DEFAULT_RELATIONSHIP)

def context() -> int:
    """參考上下文條數：起草和判斷各看最近多少條訊息。3~30，缺失/髒資料一律退預設值。"""
    try:
        n = int(_read("context", _DEFAULT_CONTEXT))
    except (TypeError, ValueError):
        return _DEFAULT_CONTEXT
    return max(3, min(30, n))

def style() -> str:
    """使用者自己描述的說話風格（可選，自由文字），只餵給起草模型。預設空 = 只照著最近的訊息模仿。"""
    return str(_read("style") or "")

def jev_provider() -> str:
    """判斷模型走哪家：openrouter（預設）或 typesafe 直連。"""
    v = _read("jev_provider")
    return v if v in JEV_PROVIDERS else _DEFAULT_JEV

def jev_model() -> str:
    """判斷模型 id；空 = 用該來源的預設模型。"""
    return str(_read("jev_model") or "") or JEV_PROVIDERS[jev_provider()].default

def draft_provider() -> str:
    """起草走哪家（見 core/providers.DRAFT_PROVIDERS）。不在表裡的（含已移除的來源）退回預設。"""
    v = _read("draft_provider")
    return v if v in DRAFT_PROVIDERS else _DEFAULT_DRAFT

def draft_provider_name() -> str:
    return DRAFT_PROVIDERS[draft_provider()].name

def draft_model() -> str:
    """起草模型 id；空 = 用該來源的預設模型（有的來源沒有預設，那就得自己選）。"""
    return str(_read("draft_model") or "") or DRAFT_PROVIDERS[draft_provider()].default

def draft_base_url() -> str:
    """自定義來源的 Base URL；其餘來源用表裡的，這裡返回空。"""
    return str(_read("draft_base_url") or "") if draft_provider() in CUSTOM else ""

def reply_target() -> bool:
    """群聊指定回覆對象：開了才在介面上選回覆給誰、才把對象餵給模型。預設關。"""
    return bool(_read("reply_target", False))

def auto_analyze() -> bool:
    """對方一來新訊息就自動分析。Fork：預設關（半自動），只顯示分析對象，按「分析」才呼叫模型，省 token。"""
    return bool(_read("auto_analyze", False))

def thinking() -> bool:
    """起草時是否開思考模式：慢且貴，預設關。只有 OpenRouter / Anthropic / Gemini 吃它。"""
    return bool(_read("thinking", False))

def check_update() -> bool:
    """啟動時要不要去 GitHub 查一次最新版本號：預設開，只出這一次網，設定裡能關。Fork：查本 repo 的 Release。"""
    return bool(_read("check_update", True))

def debug_view() -> bool:
    """除錯檢視：另開一個視窗實時畫識別框。預設關，開了子程序才往佇列裡送幀。"""
    return bool(_read("debug_view", False))

def _read_env(env_name: str) -> str:
    """程序環境優先；沒有就讀登錄檔並帶進程序環境，之後 core/ 裡按 os.environ 讀就有了。"""
    v = os.environ.get(env_name, "").strip()
    if not v:
        try:
            import winreg

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                v = str(winreg.QueryValueEx(k, env_name)[0]).strip()
        except Exception:  # 非 Windows / 沒這個值
            v = ""
        if v:
            os.environ[env_name] = v
    return v

def _get_key(env_name: str) -> str:
    """兩把 key 之一。新名字空著就退回老版本按來源存的變數（下次儲存會抄進新名字）。"""
    return _read_env(env_name) or _read_env(LEGACY[env_name])

def _set_key(env_name: str, value: str) -> None:
    """只寫程序環境 + HKCU\\Environment，不寫任何檔案。"""
    os.environ[env_name] = value
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment", 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, env_name, 0, winreg.REG_SZ, value)
    except Exception:
        pass  # 非 Windows（本機 Mac 開發）走不到，忽略


def _notify_env() -> None:
    """告訴別的程序環境變數變了。不能用 SendMessageTimeout 對 HWND_BROADCAST：
    它會逐個視窗等回覆，超時 5 秒還按視窗數累加，儲存按鈕在介面執行緒上就卡死。
    SendNotifyMessage 把訊息交出去就返回。"""
    try:
        fn = ctypes.windll.user32.SendNotifyMessageW
        fn.argtypes = (ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_wchar_p)
        fn.restype = ctypes.c_int
        fn(0xFFFF, 0x001A, 0, "Environment")  # HWND_BROADCAST, WM_SETTINGCHANGE
    except Exception:
        pass

def jev_key() -> str:
    """判斷那把 key，兩家來源共用。"""
    return _get_key(JEV_ENV)

def has_jev_key() -> bool:
    return bool(jev_key())

def llm_key() -> str:
    """起草那把 key，所有語言模型來源共用。"""
    return _get_key(LLM_ENV)

def has_llm_key() -> bool:
    return bool(llm_key())

has_key = has_jev_key  # 舊名字：介面上「配沒配好」問的就是判斷模型這把 key

def save(relationship_text: str | None = None, context_n: int | None = None, *,
         jev_provider_text: str | None = None, jev_key_text: str | None = None,
         jev_model_text: str | None = None, draft_provider_text: str | None = None,
         llm_key_text: str | None = None, draft_model_text: str | None = None,
         draft_base_url_text: str | None = None, reply_target_on: bool | None = None,
         style_text: str | None = None, thinking_on: bool | None = None,
         check_update_on: bool | None = None, debug_view_on: bool | None = None,
         auto_analyze_on: bool | None = None) -> None:
    """每個引數為空/None = 保留當前值。兩把 key 寫程序環境 + HKCU\\Environment，不寫任何檔案。"""
    jev = jev_provider_text if jev_provider_text in JEV_PROVIDERS else jev_provider()
    draft = draft_provider_text if draft_provider_text in DRAFT_PROVIDERS else draft_provider()
    # 沒重填就把老變數裡的值抄進新名字，遷移一次性做完（_get_key 已經退回讀過老的了）
    wrote_key = False
    for env, typed in ((JEV_ENV, jev_key_text), (LLM_ENV, llm_key_text)):
        value = typed or ("" if _read_env(env) else _get_key(env))
        if value:
            _set_key(env, value)
            wrote_key = True
    if wrote_key:
        _notify_env()
    n = context() if context_n is None else max(3, min(30, int(context_n)))
    # 空串 = 清掉，None = 原樣留著（讀原始欄位，別讀補過預設值的那個）
    keep = lambda new, name: str(_read(name) or "") if new is None else str(new).strip()
    flag = lambda new, now: now() if new is None else bool(new)
    # 整個 dict 必須在 open(..., "w") **之前**拼好：open 一上來就把檔案截斷，
    # 之後再 _read() 讀到的是空檔案，None 那幾項就不是「保留」而是被清空了。
    data = {
        # 關係為空 = 只改別的開關（除錯檢視那種單項儲存），別把它寫沒了
        "relationship": relationship_text or relationship(), "context": n,
        "style": keep(style_text, "style"),
        "jev_provider": jev, "jev_model": keep(jev_model_text, "jev_model"),
        "draft_provider": draft, "draft_model": keep(draft_model_text, "draft_model"),
        "draft_base_url": keep(draft_base_url_text, "draft_base_url"),
        "reply_target": flag(reply_target_on, reply_target),
        "thinking": flag(thinking_on, thinking),
        "check_update": flag(check_update_on, check_update),
        "debug_view": flag(debug_view_on, debug_view),
        "auto_analyze": flag(auto_analyze_on, auto_analyze),
    }
    with open(_CONFIG, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
