# CLAUDE.md

本 repo 的規則以 [`AGENTS.md`](AGENTS.md) 為單一真相源（產品硬約束、技術背景、fork 邊界、驗證方式都在那裡）：

@AGENTS.md

Claude Code 專屬補充：

- 回覆用繁體中文，直接給結果。
- 動到 `app/` 時，本機沒有 Android SDK 就以 CI 的 `Android build (assembleDebug)` 為準，並在回報中說明未本機建置。
