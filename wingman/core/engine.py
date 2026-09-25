# -*- coding: utf-8 -*-
"""整條鏈的唯一入口：對話 → Jev 判斷 → 帶著判斷起草 3 條 → Jev 排序 → 結構化結果。

平臺無關。SSE 消費者、懸浮窗、命令列 demo 都只調 analyze()。
"""
from __future__ import annotations

try:
    from .draft import draft_candidates
    from .jev_client import JevError, ask
    from .questions import JUDGE_QUESTIONS, build_rank_question, build_state, guidance_text
except ImportError:
    from draft import draft_candidates
    from jev_client import JevError, ask
    from questions import JUDGE_QUESTIONS, build_rank_question, build_state, guidance_text

_REPLY_IDX = {"reply_a": 0, "reply_b": 1, "reply_c": 2}


def _add_usage(total: dict, one: dict | None) -> None:
    """兩次 Jev 呼叫的 usage 相加（tokens、cost）；非數字的欄位後來的蓋掉前面的。"""
    for k, v in (one or {}).items():
        total[k] = total.get(k, 0) + v if isinstance(v, (int, float)) else v


def analyze(messages: list, relationship: str, model: str | None = None,
            timeout: float = 30, context: int = 10, provider: str = "openrouter",
            base_url: str | None = None, reply_to: str | None = None, style: str = "",
            thinking: bool = False, jev_provider: str = "openrouter",
            jev_model: str | None = None) -> dict:
    """messages: [(from, text)] from ∈ {her, me}，最新一條在最後；
    群聊裡可以帶第三項 name（說這句話的人），單聊不帶。
    context: 起草和判斷各看最近多少條訊息（使用者設定裡的「參考上下文」）。
    provider: 起草走哪家（core.providers.DRAFT_PROVIDERS），base_url 只有自定義來源要傳。
    jev_provider / jev_model: 判斷和排序走哪家、哪個模型（core.providers.JEV_PROVIDERS）。
    reply_to: 群聊裡指定回覆給誰；None = 正常回覆。
    style: 使用者自己描述的說話風格，隻影響起草。
    thinking: 起草時是否開思考模式，隻影響起草，預設關。
    model / jev_model = None 用該來源的預設模型。

    返回 {candidates, best_index, best_reply, scores, answers, usage, reply_to}。
    scores 是每條候選的勝出機率（0~1），取自 best_reply.probabilities，取不到記 0.0。
    只有對方最新說話時才有意義調它——是不是該觸發由呼叫方判斷（看 latest_from）。

    三段式（issue #4）：先讓 Jev 答 7 道判斷題，把判斷當小抄餵給起草，最後 Jev 只排序。
    判斷那次掛了就退回老路：盲起草 + 判斷和排序一次問完，行為跟以前一樣。usage 是兩次之和。
    """
    state = build_state(messages, relationship, keep=context, reply_to=reply_to)
    usage: dict = {}
    answers: dict = {}
    judged = False
    try:
        first = ask(state, dict(JUDGE_QUESTIONS), timeout=timeout,
                    provider=jev_provider, model=jev_model)
        answers = first.get("answers") or {}
        _add_usage(usage, first.get("usage"))
        judged = True
    except JevError:
        pass  # 退回盲起草 + 老的一次合問；錯誤不打日誌（裡面可能帶請求內容）

    candidates = draft_candidates(messages, relationship, provider=provider, model=model,
                                  base_url=base_url, timeout=timeout, keep=context,
                                  reply_to=reply_to, style=style, thinking=thinking,
                                  guidance=guidance_text(answers) if judged else None)
    if not candidates:  # 注入過濾可以把起草結果全扔掉；接著取 [0] 會 IndexError
        raise JevError("起草結果沒有可用候選回覆")

    questions = {} if judged else dict(JUDGE_QUESTIONS)
    if len(candidates) >= 2:  # 起草只給了 1 條就沒什麼可排的，判斷題照問
        questions.update(build_rank_question(candidates))
    if questions:
        try:
            second = ask(state, questions, timeout=timeout,
                         provider=jev_provider, model=jev_model)
        except JevError:
            if not judged:  # 老路只有這一次呼叫，掛了就是掛了
                raise
            second = {}  # 判斷還在，只是沒排上序：下面按第一條推薦
        answers = {**answers, **(second.get("answers") or {})}
        _add_usage(usage, second.get("usage"))

    best_key = (answers.get("best_reply") or {}).get("choice")
    best_index = _REPLY_IDX.get(best_key, 0)  # 解析不出就退第一條
    if best_index >= len(candidates):
        best_index = 0

    probabilities = (answers.get("best_reply") or {}).get("probabilities") or {}
    scores = [0.0, 0.0, 0.0]
    for key, idx in _REPLY_IDX.items():
        try:
            scores[idx] = float(probabilities.get(key, 0.0))
        except (TypeError, ValueError):
            scores[idx] = 0.0  # 髒資料一律按 0 處理

    return {
        "candidates": candidates,
        "best_index": best_index,
        "best_reply": candidates[best_index],
        "scores": scores,
        "answers": answers,
        "usage": usage,
        "reply_to": reply_to,
    }


if __name__ == "__main__":
    # 候選被過濾光時要拋 JevError，不能在取第一條時 IndexError。
    from unittest.mock import patch

    with patch("__main__.ask", return_value={"answers": {}, "usage": {}}), \
         patch("__main__.draft_candidates", return_value=[]):
        try:
            analyze([("her", "hello")], "friends")
            raise SystemExit("應當拋錯")
        except JevError as e:
            assert "沒有可用候選" in str(e)
    print("engine ok")
