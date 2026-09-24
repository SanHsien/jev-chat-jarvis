# Fork 決策紀錄 (DECISIONS.md)

本文件記錄本 fork 相對於上游的所有架構決策、取捨與已審核變更。

## 2026-09-24: Fork 建立與 Windows 開發環境初始化

- **背景**：Fork `jev-chat/jev-chat-jarvis`，建立 Windows-first 治理與自動化驗證機制。
- **基準版本**：fork 點為上游 `main` `a3026e2`；審核水位為 `v1.4`（Commit: `01f65908536d5b1ac76e3ce6cec4bbb5fe667791`）。
  `v1.4` 之後的 7 個 commit 皆為 README / CHANGELOG / 網站文件調整，已隨 fork 一併納入。
- **治理決策**：
  1. 對外只打維護者的 repo（`SanHsien/jev-chat-jarvis`），嚴禁自動向上游開 PR 或 push。
  2. 上游 `CLAUDE.md` 原樣保留以降低同步衝突；fork 規則放 `AGENTS.md`，由 `.claude/CLAUDE.md` 匯入。
  3. 建立 `tools/dev_check.ps1`：`-Quick` 為 `tools/jev` Python 語法檢查 + 上游查驗；完整版加跑 `gradlew :app:assembleDebug`。
     機器相關路徑（JDK / SDK / Gradle home）由 gitignore 的 `env.ps1` 提供。
  4. 上游 tag 為兩段式（`v1.3`、`v1.4`），`check_upstream_updates.py` 的版本解析放寬為 `major.minor[.patch]`。
  5. 採 `release` 追蹤模式（上游 `main` 每日多次文件類 commit）。PR 水位 `#54` 以 `refs/pull/*` 取得；
     issue 與 PR 共用編號，水位先同設 `#54`，首次 `gh` 查驗後再校正。
  6. 建立每週自動執行的 `upstream-check.yml`，對齊 `hypit` fork 的上游查驗水位線架構。
