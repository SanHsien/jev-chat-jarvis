# AGENTS.md

給 Codex、Claude Code、Cursor 與其他自動化代理在本專案工作時的指引。

## 專案定位

這是 [`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis) 的 MIT fork。
專案核心為 Android 非侵入式「對話副駕」：無障礙服務／截屏 OCR 讀取聊天畫面，
呼叫 Jev 判斷模型（選擇／評分／是非）分析對方意圖與風險，再產生候選回覆，一鍵填入輸入框，發送由人決定。

`origin` 是 `SanHsien/jev-chat-jarvis`，`upstream` 是原作者 repo，預設分支皆為 `main`。
本 fork 的維護差異記在 [`FORK.md`](FORK.md) 與 [`docs/fork/DECISIONS.md`](docs/fork/DECISIONS.md)。

主要開發與完整驗收環境是 **Windows 11 + PowerShell 7**。

## 與上游 CLAUDE.md 的關係

上游 [`CLAUDE.md`](CLAUDE.md) 原樣保留，其產品硬約束（不 hook、不自動發送、不碰錢、密鑰不落盤、
路徑全 ASCII、UTF-8）在本 fork **全部照常適用**。

以下兩條在本 fork 另有規定：

- 上游第 7 條「禁止 `git commit` / `git push`」：本 fork 改為「維護者明確要求時才 commit / push，且只推 `origin`」。
- 上游第 4 條固定路徑 `H:\ai_tool\jev-android`：本 fork 不限定路徑，但仍必須全 ASCII。

## 硬性邊界

- **對外只打主人的 repo。** PR、push、release 一律指向 `SanHsien/jev-chat-jarvis`。
  對上游開 PR 或 push 預設絕對禁止，除非維護者在當次對話明確同意。
- 每個工作環境先確認 `gh repo set-default SanHsien/jev-chat-jarvis`。
- 日常開發推送到 `origin/main` 前，必須通過 Windows 閘門：
  `pwsh -NoProfile -File tools/dev_check.ps1 -Quick`（或完整無參數版本，含 Gradle 建置）。
- 保持乾淨工作目錄，不隨意刪除上游核心程式、資源或依賴。
- 任何檔案不得出現 `sk-or-` 開頭字串或其他密鑰；簽章檔（`*.jks`、`keystore.properties`）不進 repo。
