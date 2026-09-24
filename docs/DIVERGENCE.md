# 分岔登記表

本檔登記本 fork 對**上游持有檔案**的每一筆修改：上游原本就有這個檔案，本 fork 動了它。
新增的檔案（上游沒有對應版本，例如 `AGENTS.md`、`FORK.md`、`tools/` 底下的維護工具）不算
分岔，不登記在這裡；那些檔案的清單見 [`FORK.md`](../FORK.md)。

## 維護契約

**改動任何一個上游持有的檔案，就必須在這裡加一列。** 這件事由
[`tools/check_divergence.py`](../tools/check_divergence.py) 機器強制：它比對「上游基準
commit（`tools/upstream_baseline.json` 的 `reviewed_through`）到現在，哪些上游持有的檔案
被改過或刪過」與「這張表登記了哪些路徑」，兩邊對不上就非 0 退出。這個檢查接在
`tools/dev_check.ps1`、`.github/workflows/ci.yml` 與 `.github/workflows/upstream-check.yml`；
合約測試在 [`tests/test_fork_divergence.py`](../tests/test_fork_divergence.py)。

最後一欄「跟進上游時怎麼處理」寫成**可執行的判準**，同步上游時照欄位做決定，不必重新評估。

| 上游檔案 | 上游原狀 | 本 fork 狀態 | 為什麼分岔 | 跟進上游時怎麼處理 |
|---|---|---|---|---|
| `README.md` | 簡中 README：介紹、截圖、平台支援、快速開始、功能、FAQ、架構、已知限制、交流群、贊助、打賞。 | 改寫為繁中精簡版：fork 聲明、功能、平台支援（含 LINE 現況）、快速開始、建置、授權；贊助／交流群／打賞不收。 | 公開入口改以繁中為主；上游原文整份保留在 `README.zh-CN.md`。 | 上游改 `README.md` 時，原文同步貼進 `README.zh-CN.md`；只把**產品事實**（平台支援、安裝檔名、權限步驟）人工合併進本檔；不要整份覆蓋。 |
| `README.zh-CN.md` | 不存在；上游原文就是 `README.md`。 | `git mv README.md README.zh-CN.md`，內容＝上游原文。 | 保留上游簡中原文鏡像。`check_divergence.py` 用寫死的別名把它算成 `README.md` 的分岔。 | 上游更新 `README.md` 時，整份照抄進本檔（本檔不加任何 fork 內容）。 |
| `.gitignore` | Android / Python / IDE / 密鑰忽略規則。 | 尾端 append `# Fork maintenance (SanHsien)` 區塊：`.venv/`、`.pytest_cache/`、兩份生成報告。 | 維護工具會在本機／CI 產生報告與快取，不該入版控。 | 上游新增規則直接合併在 fork 區塊之上；上游若自己忽略同名路徑，刪掉 fork 區塊裡重複的那行。 |
| `app/src/main/java/com/jev/probe/core/Prefs.kt` | 新安裝預設 OpenRouter；回覆／視覺預設 OpenRouter。 | 新增 `seedVercelDefaultIfFresh()`：**全新**設定（沒選過 provider、沒有任何金鑰、回覆／視覺位址沒寫過）一次性把三路都設成 Vercel AI Gateway；新增常數 `VERCEL_OPENAI_BASE`、`VERCEL_REPLY_MODEL`、`VERCEL_VISION_MODEL`。 | 維護者主要用 Vercel（次選 OpenRouter），一把 Vercel 金鑰要能涵蓋判斷、回覆、視覺三路；已有設定的使用者完全不動。 | 上游改 `init` 或新增 seed／unseed 函式時，保留 `seedVercelDefaultIfFresh()` 呼叫排在最後；上游若自己改預設為 Vercel 且涵蓋三路，刪掉本 fork 的 seed 與常數並刪除本列。 |
| `app/src/main/java/com/jev/probe/SettingsActivity.kt` | 回覆接口預設項：OpenRouter／DeepSeek 官方／通義兼容／自定義；視覺：OpenRouter／通義兼容／自定義。 | 回覆與視覺各加一個「Vercel」預設（`VERCEL_OPENAI_BASE` + 對應模型），排在「自定義」之前。 | 讓 Vercel 在設定頁可一鍵切換，與判斷接口的 Vercel 預設一致。 | 上游改這兩組 pills 時，在新清單的「自定義」前重新插入 Vercel 一項並同步 index 對照；上游若自己加了 Vercel 預設，改用上游版本並刪除本列。 |
| `app/src/main/java/com/jev/probe/capture/ChatAppAdapter.kt` | QQ／微信（停用）／飛書／X 四個適配器。 | 檔尾新增 `LineAdapter`（`jp.naver.line.android`）骨架；`VERIFIED = false` 時一律回 `null`。 | 維護者的主要用途是 LINE；等真機 `uiautomator dump` 確認 resource-id 後再啟用。 | 上游改此檔時保留檔尾的 `LineAdapter` 區塊；上游若自己加了 LINE 適配器，比較兩者後採用較完整者並刪除本列。 |
| `app/src/main/java/com/jev/probe/capture/ChatCaptureService.kt` | `adapters = listOf(QQAdapter(), XAdapter(), FeishuAdapter())`。 | 改成 `listOfNotNull(...)`，`LineAdapter` 只在 `LineAdapter.VERIFIED` 為真時加入。 | 未驗證前 LINE 行為必須與「無適配器的 App」完全相同（懸浮球 + 手動 OCR）。 | 上游改 `adapters` 清單時，照上游新清單再把 `LineAdapter().takeIf { LineAdapter.VERIFIED }` 接在最後。 |
