# -*- coding: utf-8 -*-
"""端到端冒煙：截圖裡那段真實對話跑一遍完整鏈，列印判斷 + 排好序的候選。

鏈路是三段式：Jev 判斷（7 道題） → 帶著判斷起草 3 條 → Jev 排序，兩次 Jev 呼叫。

全程只要兩把 key：判斷一把 JEV_API_KEY（OpenRouter 或 TypeSafe 的），起草一把 LLM_API_KEY。

    set JEV_API_KEY=...   &  set LLM_API_KEY=...    (Windows)
    export JEV_API_KEY=... && export LLM_API_KEY=...(mac/Linux)
    python tools/windows/demo.py   （在 repo 根目錄）

預設：判斷和起草都走 OpenRouter。換別家改下面兩個常量
（可選的來源見 core/providers.py 的兩張表）。
"""
from __future__ import annotations

import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from wingman.core.engine import analyze
from wingman.core.jev_client import JevError
from wingman.core.questions import guidance_text

MESSAGES = [
    ("her", "你今天是不是又忘了我跟你說過什麼？"),
    ("me", "記得，你先別提示我，讓我自己說。"),
    ("her", "那你說。"),
    ("me", "等一下，我想說完整一點。"),
    ("her", "你最好是。"),
]
RELATIONSHIP = "romantic partners"
PROVIDER = "openrouter"      # 起草來源，見 core.providers.DRAFT_PROVIDERS
JEV_PROVIDER = "openrouter"  # 判斷來源：openrouter 或 typesafe


def fmt(name: str, ans: dict) -> str:
    t = ans.get("type")
    if t == "noul":
        return f"{name}: {ans.get('noul'):.2f}"
    if t == "choice":
        return f"{name}: {ans.get('choice')} (conf {ans.get('confidence'):.2f})"
    if t == "score":
        return f"{name}: {ans.get('score'):.1f}/9 (conf {ans.get('confidence'):.2f})"
    return f"{name}: {ans}"


def main() -> int:
    print("對話:")
    for w, t in MESSAGES:
        print(f"  {w}: {t}")
    try:
        r = analyze(MESSAGES, RELATIONSHIP, provider=PROVIDER, jev_provider=JEV_PROVIDER)
    except JevError as e:
        print(f"\n失敗: {e}")
        return 1

    print("\n判斷:")
    for name in ("literal_question", "true_intent", "danger_level",
                 "should_reply_now", "best_action", "she_needs", "tension_resolved"):
        if name in r["answers"]:
            print("  " + fmt(name, r["answers"][name]))

    block = guidance_text(r["answers"])  # 起草時喂進去的那張小抄
    if block:
        print("\n" + block)

    print("\n候選（Jev 排序，★ = 推薦）:")
    scores = r.get("scores")
    for i, c in enumerate(r["candidates"]):
        pct = f"  {scores[i]:.0%}" if scores else ""
        print(f"  {'★' if i == r['best_index'] else ' '} {c}{pct}")

    u = r["usage"]
    if u:
        print(f"\nusage: in={u.get('input_tokens')} out={u.get('output_tokens')} "
              f"cost=${u.get('cost')}")
    print("\n期望核對: true_intent≈confirm_you_care, best_action≈check_history, danger_level 中高檔")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
