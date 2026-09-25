# -*- coding: utf-8 -*-
"""三種接口協議的薄適配層，一律走官方 SDK：
OpenAI Chat Completions（`openai`）/ Anthropic Messages（`anthropic`）/ Gemini（`google-genai`）。

只做兩件事：chat() 發一輪對話拿文字，list_models() 列模型。base_url / key / model 全由呼叫方傳，
這裡不認識任何「來源」——來源表在 core/providers.py。出錯一律轉成 JevError，訊息過脫敏。

SDK 都在函式裡 import：桌面端一次只用到其中一家，啟動時沒必要把另外兩家的依賴也拖起來。
"""
from __future__ import annotations

try:  # 當模組匯入 / 當指令碼直接跑 都能用
    from .jev_client import JevError, _fail
except ImportError:
    from jev_client import JevError, _fail

# Anthropic 開思考模式時的預算：起草三句話用不上更多；max_tokens 必須比它大，下面會兜住
_THINK_BUDGET = 2048


def _turns(user_turns: list[str], assistant: str = "assistant") -> list[dict]:
    """[user, assistant, user, …] 交替；第一條和最後一條都是使用者。"""
    return [{"role": assistant if i % 2 else "user", "content": text}
            for i, text in enumerate(user_turns)]


def chat(protocol: str, base_url: str | None, api_key: str, model: str, system: str,
         user_turns: list[str], *, temperature: float = 1.0, max_tokens: int = 400,
         thinking: bool = False, extra_body: dict | None = None,
         headers: dict | None = None, timeout: float = 30) -> str:
    """發一輪對話，返回模型輸出的純文字。

    user_turns: 使用者/助手交替的文字，奇數條，首尾都是使用者說的（追問補齊候選就是 3 條）。
    thinking: 思考模式。OpenAI 協議沒有統一欄位，各家自己的開關由呼叫方經 extra_body 帶進來；
              anthropic / gemini 是協議自帶的引數，這裡直接處理。
    """
    if protocol == "anthropic":
        return _anthropic(base_url, api_key, model, system, user_turns,
                          temperature, max_tokens, thinking, timeout)
    if protocol == "gemini":
        return _gemini(base_url, api_key, model, system, user_turns,
                       temperature, max_tokens, thinking, timeout)
    return _openai(base_url, api_key, model, system, user_turns,
                   temperature, max_tokens, extra_body, headers, timeout)


def _openai(base_url, api_key, model, system, user_turns, temperature, max_tokens,
            extra_body, headers, timeout) -> str:
    import openai

    try:
        client = openai.OpenAI(base_url=base_url or None, api_key=api_key,
                               timeout=timeout, max_retries=2,
                               **({"default_headers": headers} if headers else {}))
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": system}] + _turns(user_turns),
            temperature=temperature, max_tokens=max_tokens,
            stream=False,  # 有的 OpenAI 相容來源要顯式關；別家無所謂
            **({"extra_body": extra_body} if extra_body else {}))
    except Exception as exc:
        _fail(exc, "起草")
    return resp.choices[0].message.content or ""


def _anthropic(base_url, api_key, model, system, user_turns, temperature, max_tokens,
               thinking, timeout) -> str:
    import anthropic

    extra = {}
    if thinking:
        extra["thinking"] = {"type": "enabled", "budget_tokens": _THINK_BUDGET}
        temperature = 1.0  # 開了思考，Anthropic 只收 temperature=1
        max_tokens = max(max_tokens, _THINK_BUDGET + 1024)  # max_tokens 得裝得下思考 + 正文
    try:
        client = anthropic.Anthropic(base_url=base_url or None, api_key=api_key,
                                     timeout=timeout, max_retries=2)
        message = client.messages.create(model=model, system=system,
                                         messages=_turns(user_turns), max_tokens=max_tokens,
                                         temperature=temperature, **extra)
    except Exception as exc:
        _fail(exc, "起草")
    # 開了思考的話前面還有 thinking 塊，只取文字塊
    return "".join(b.text for b in message.content if getattr(b, "type", "") == "text")


def _gemini_client(base_url, api_key, timeout):
    from google import genai
    from google.genai import types

    # HttpOptions.timeout 的單位是毫秒，不是秒
    options = types.HttpOptions(timeout=int(timeout * 1000))
    if base_url:
        options.base_url = base_url
    return genai.Client(api_key=api_key, http_options=options), types


def _gemini(base_url, api_key, model, system, user_turns, temperature, max_tokens,
            thinking, timeout) -> str:
    try:
        client, types = _gemini_client(base_url, api_key, timeout)
        config = types.GenerateContentConfig(
            system_instruction=system, temperature=temperature, max_output_tokens=max_tokens,
            # thinking_budget=0 才是真的關掉；不傳是讓模型自己定（等於開著）
            thinking_config=None if thinking else types.ThinkingConfig(thinking_budget=0))
        contents = [types.Content(role=m["role"], parts=[types.Part(text=m["content"])])
                    for m in _turns(user_turns, assistant="model")]  # Gemini 那邊助手叫 model
        resp = client.models.generate_content(model=model, contents=contents, config=config)
    except Exception as exc:
        _fail(exc, "起草")
    return resp.text or ""


def list_models(protocol: str, base_url: str | None, api_key: str,
                timeout: float = 10, headers: dict | None = None) -> list[str]:
    """某個地址上能用的模型 id，去重排序。失敗拋 JevError，訊息直接顯示在設定頁上。"""
    if protocol == "anthropic":
        import anthropic

        try:
            client = anthropic.Anthropic(base_url=base_url or None, api_key=api_key,
                                         timeout=timeout, max_retries=1)
            ids = [m.id for m in client.models.list()]
        except Exception as exc:
            _fail(exc, "取模型列表")
    elif protocol == "gemini":
        try:
            client, _ = _gemini_client(base_url, api_key, timeout)
            # 名字帶 models/ 字首，呼叫時用不上，剝掉
            ids = [str(m.name).removeprefix("models/") for m in client.models.list() if m.name]
        except Exception as exc:
            _fail(exc, "取模型列表")
    else:
        import openai

        try:
            client = openai.OpenAI(base_url=base_url or None, api_key=api_key,
                                   timeout=timeout, max_retries=1,
                                   **({"default_headers": headers} if headers else {}))
            ids = [m.id for m in client.models.list()]
        except Exception as exc:
            _fail(exc, "取模型列表")
    return sorted(set(ids))


if __name__ == "__main__":
    # ponytail: 不聯網。在 SDK 邊界上把客戶端換成假的，只驗「餵給 SDK 的引數對不對」——
    # 各家的欄位名和思考開關是這層唯一會壞的東西。config 對象仍用真型別，欄位名寫錯會當場炸。
    import os
    import types as _t

    import anthropic
    import openai
    from google import genai

    seen: dict = {}

    def _fake(kind):
        """記下構造引數和呼叫引數的假客戶端。"""
        def make(**kw):
            seen[kind + ".init"] = kw
            def call(**k):
                seen[kind + ".call"] = k
                if kind == "openai":
                    return _t.SimpleNamespace(choices=[_t.SimpleNamespace(
                        message=_t.SimpleNamespace(content='["甲","乙","丙"]'))])
                if kind == "anthropic":
                    return _t.SimpleNamespace(content=[
                        _t.SimpleNamespace(type="thinking", thinking="…"),
                        _t.SimpleNamespace(type="text", text="嗯")])
                return _t.SimpleNamespace(text="嗯")
            listing = {"openai": [_t.SimpleNamespace(id="b"), _t.SimpleNamespace(id="a"),
                                  _t.SimpleNamespace(id="a")],
                       "anthropic": [_t.SimpleNamespace(id="claude-y"), _t.SimpleNamespace(id="claude-x")],
                       "gemini": [_t.SimpleNamespace(name="models/gemini-2"),
                                  _t.SimpleNamespace(name="models/gemini-1")]}[kind]
            models = _t.SimpleNamespace(list=lambda **_: listing, generate_content=call)
            return _t.SimpleNamespace(
                models=models, messages=_t.SimpleNamespace(create=call),
                chat=_t.SimpleNamespace(completions=_t.SimpleNamespace(create=call)))
        return make

    openai.OpenAI, anthropic.Anthropic, genai.Client = (
        _fake("openai"), _fake("anthropic"), _fake("gemini"))

    # OpenAI 協議：base_url / key / model / 思考欄位都得原樣到位
    out = chat("openai", "https://llm.example/v1", "sk-ex", "model-a", "S", ["U"],
               temperature=1.2, max_tokens=400, extra_body={"thinking": {"type": "disabled"}})
    assert out == '["甲","乙","丙"]'
    assert seen["openai.init"]["base_url"] == "https://llm.example/v1"
    assert seen["openai.init"]["api_key"] == "sk-ex" and seen["openai.init"]["max_retries"] == 2
    assert seen["openai.call"]["model"] == "model-a"
    assert seen["openai.call"]["extra_body"] == {"thinking": {"type": "disabled"}}
    assert seen["openai.call"]["temperature"] == 1.2 and seen["openai.call"]["max_tokens"] == 400
    assert seen["openai.call"]["messages"] == [
        {"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
    # 沒有思考開關的來源（extra_body 空）就不該出現這個欄位
    chat("openai", "https://llm.example/v1", "k", "model-b", "S", ["U"], extra_body={})
    assert "extra_body" not in seen["openai.call"]
    # 來源要求的額外頭要進 SDK，別的來源不帶
    chat("openai", "https://llm.example/v1", "k", "model-a", "S", ["U"],
         headers={"x-session": "sid", "User-Agent": "jev-chat-windows"})
    assert seen["openai.init"]["default_headers"] == {
        "x-session": "sid", "User-Agent": "jev-chat-windows"}
    chat("openai", "https://llm.example/v1", "k", "m", "S", ["U"])
    assert "default_headers" not in seen["openai.init"]
    # 追問補齊：user / assistant / user 三輪
    chat("openai", "", "k", "m", "S", ["U1", "A1", "U2"])
    assert [m["role"] for m in seen["openai.call"]["messages"]] == [
        "system", "user", "assistant", "user"]
    assert seen["openai.init"]["base_url"] is None  # 空 base_url = 用 SDK 預設地址

    # Anthropic：system 單獨傳，思考是協議自帶引數，開了必須 temperature=1 且 max_tokens 裝得下預算
    assert chat("anthropic", "https://api.anthropic.com", "sk-an", "claude-x", "S", ["U"],
                temperature=1.2, max_tokens=400) == "嗯"
    assert seen["anthropic.call"]["system"] == "S" and "thinking" not in seen["anthropic.call"]
    assert seen["anthropic.call"]["messages"] == [{"role": "user", "content": "U"}]
    assert seen["anthropic.call"]["temperature"] == 1.2
    chat("anthropic", "", "k", "claude-x", "S", ["U"], temperature=1.2, max_tokens=400, thinking=True)
    assert seen["anthropic.call"]["thinking"] == {"type": "enabled", "budget_tokens": _THINK_BUDGET}
    assert seen["anthropic.call"]["temperature"] == 1.0
    assert seen["anthropic.call"]["max_tokens"] > _THINK_BUDGET

    # Gemini：助手那一輪叫 model；關思考 = thinking_budget 0，開 = 不傳讓模型自己定
    assert chat("gemini", "", "k", "gemini-2", "S", ["U1", "A1", "U2"], max_tokens=400) == "嗯"
    cfg = seen["gemini.call"]["config"]
    assert cfg.system_instruction == "S" and cfg.max_output_tokens == 400
    assert cfg.thinking_config.thinking_budget == 0
    assert [c.role for c in seen["gemini.call"]["contents"]] == ["user", "model", "user"]
    assert seen["gemini.call"]["contents"][0].parts[0].text == "U1"
    chat("gemini", "https://my.proxy", "k", "gemini-2", "S", ["U"], thinking=True)
    assert seen["gemini.call"]["config"].thinking_config is None
    assert seen["gemini.init"]["http_options"].base_url == "https://my.proxy"
    assert seen["gemini.init"]["http_options"].timeout == 30000  # 毫秒，不是秒

    # 列模型：去重排序；gemini 剝掉 models/ 字首
    assert list_models("openai", "https://x/v1", "k") == ["a", "b"]
    assert "default_headers" not in seen["openai.init"]
    list_models("openai", "https://x/v1", "k", headers={"User-Agent": "jev-chat-windows"})
    assert seen["openai.init"]["default_headers"] == {"User-Agent": "jev-chat-windows"}
    assert list_models("anthropic", "", "k") == ["claude-x", "claude-y"]
    assert list_models("gemini", "", "k") == ["gemini-1", "gemini-2"]

    # 出錯 → 一句人話的 JevError，帶上狀態碼，不洩露 key
    os.environ["LLM_API_KEY"] = "sk-secret"

    class _Boom(Exception):
        status_code = 401

    def _explode(**kw):
        raise _Boom("bad key sk-secret")

    openai.OpenAI = _explode
    try:
        chat("openai", "", "sk-secret", "m", "S", ["U"])
        raise SystemExit("應當拋錯")
    except JevError as e:
        assert e.status == 401 and "金鑰被拒" in str(e) and "sk-secret" not in str(e)
    print("llm ok")
