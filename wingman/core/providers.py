# -*- coding: utf-8 -*-
"""兩張來源表：判斷模型 Jev / 起草語言模型。純資料，不聯網、不認 key。

表裡只有協議、地址和預設模型，**絕不出現 key**（AGENTS.md 產品硬約束 5）——
key 一律由呼叫方從環境變數/登錄檔取了再傳進來。協議具體怎麼調見 core/llm.py。

全程只有兩把 key：判斷一把 JEV_API_KEY、起草一把 LLM_API_KEY，跟選哪家來源無關，
換來源就是換同一個槽裡的值。
"""
from __future__ import annotations

from collections import namedtuple

OPENROUTER_BASE = "https://openrouter.ai/api/v1"  # OpenAI 相容；auth/key 探測也掛在它下面
# Jev 判斷只有 OpenRouter 這條路要自己拼 HTTP：typesafe_sdk 把路徑寫死成 /v1/systemone，打不到這個地址
OPENROUTER_DECISIONS = "https://openrouter.ai/api/alpha/decisions"
# 免費的金鑰探測端點：Jev 模型不在 /models 目錄裡（列表寫死），key 對不對靠它驗
OPENROUTER_KEY_URL = "https://openrouter.ai/api/v1/auth/key"
TYPESAFE_BASE = "https://api.typesafe.ai"

JEV_ENV = "JEV_API_KEY"    # 判斷那把，不管選 OpenRouter 還是 TypeSafe
LLM_ENV = "LLM_API_KEY"    # 起草那把，不管選哪家語言模型
# 遷移：老版本按來源各存一個變數。新變數空著、老變數有值就先用老的（儲存時抄進新的）
LEGACY = {JEV_ENV: "OPENROUTER_API_KEY", LLM_ENV: "OPENROUTER_API_KEY"}  # Fork：起草預設也走 OpenRouter

_Jev = namedtuple("_Jev", "name default")
JEV_PROVIDERS = {
    "openrouter": _Jev("OpenRouter", "typesafe/jev-1.13"),
    "typesafe": _Jev("TypeSafe 直連", "jev-latest"),
}

# protocol ∈ {openai, anthropic, gemini}：決定 core/llm.py 用哪個官方 SDK
# base 空 = 用 SDK 自帶的預設地址（gemini），或者等使用者自己填（自定義來源）
# default 空 = 這家沒有欽點的預設模型，使用者得「獲取模型」自己挑一個
# extra：OpenAI 協議下開/關思考模式要額外帶的 body 欄位，各家不一樣；
#        anthropic / gemini 的思考開關是協議自帶的引數，由 llm.py 直接處理，這裡給空
# headers：有的來源要求每個請求帶固定頭（不含 key）。keep：從「獲取模型」結果裡留下哪些 id
_Draft = namedtuple("_Draft", "name protocol base default extra headers keep", defaults=(None, None))
_NONE = lambda on: {}  # noqa: E731 —— 沒有思考開關的來源
# Fork（SanHsien）：起草來源只內建 OpenRouter、Vercel AI Gateway、OpenAI、Anthropic、Google Gemini 與自定義。
DRAFT_PROVIDERS = {  # 第一個就是預設：OpenRouter
    "openrouter": _Draft("OpenRouter", "openai", OPENROUTER_BASE,
                         "google/gemini-2.5-flash", lambda on: {"reasoning": {"enabled": on}}),
    "vercel": _Draft("Vercel AI Gateway", "openai", "https://ai-gateway.vercel.sh/v1",
                     "google/gemini-2.5-flash", _NONE),
    "openai": _Draft("OpenAI", "openai", "https://api.openai.com/v1", "", _NONE),
    "anthropic": _Draft("Anthropic", "anthropic", "https://api.anthropic.com", "", _NONE),
    "gemini": _Draft("Google Gemini", "gemini", "", "", _NONE),
    "custom_openai": _Draft("自定義 · OpenAI 相容", "openai", "", "", _NONE),
    "custom_anthropic": _Draft("自定義 · Anthropic 相容", "anthropic", "", "", _NONE),
}

# 這兩個來源沒有固定地址，設定頁要多露一行 Base URL 出來
CUSTOM = ("custom_openai", "custom_anthropic")
# 起草時認思考開關的來源，設定頁那句提示照著這裡寫
THINKING = ("OpenRouter", "Anthropic", "Gemini")
# 所有可能存 key 的環境變數（新兩把 + 兩個老名字），脫敏時一次全過一遍（jev_client.redact_secrets）
ENV_VARS = sorted({JEV_ENV, LLM_ENV, *LEGACY.values()})


if __name__ == "__main__":
    # ponytail: 純資料，只查幾條不變式——協議打錯字、自定義來源漏配 Base URL、思考欄位寫反最容易出。
    assert {p.protocol for p in DRAFT_PROVIDERS.values()} == {"openai", "anthropic", "gemini"}
    assert all(p.base or key in CUSTOM or p.protocol == "gemini"
               for key, p in DRAFT_PROVIDERS.items())
    assert all(not DRAFT_PROVIDERS[key].base for key in CUSTOM)
    assert next(iter(DRAFT_PROVIDERS)) == "openrouter"  # 預設就是列表第一個
    assert DRAFT_PROVIDERS["openrouter"].extra(True) == {"reasoning": {"enabled": True}}
    assert DRAFT_PROVIDERS["vercel"].extra(True) == {}
    assert DRAFT_PROVIDERS["openrouter"].headers is None and DRAFT_PROVIDERS["openrouter"].keep is None
    # 全程只有兩把 key，脫敏還得管老名字
    assert ENV_VARS == ["JEV_API_KEY", "LLM_API_KEY", "OPENROUTER_API_KEY"]
    print("providers ok")
