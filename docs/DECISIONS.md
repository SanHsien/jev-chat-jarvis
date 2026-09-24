# Fork 決策紀錄 (DECISIONS.md)

本文件記錄本 fork 相對於上游的所有架構決策、取捨與已審核變更。

## 2026-09-24: Fork 建立與 Windows 開發環境初始化

- **背景**：Fork `jev-chat/jev-chat-jarvis`，建立 Windows-first 治理與自動化驗證機制。
- **基準版本**：fork 點為上游 `main` `a3026e2`（`v1.4` 之後 7 個文件類 commit，已隨 fork 一併納入）；
  `reviewed_through` 記 `a3026e2`、`reviewed_release` 記 `v1.4`。
- **治理決策**：
  1. 對外只打維護者的 repo（`SanHsien/jev-chat-jarvis`），嚴禁自動向上游開 PR 或 push。
  2. 上游 `CLAUDE.md` 是產品硬約束（不是 fork 規則的薄補丁），原樣保留以降低同步衝突；fork 規則放 `AGENTS.md`，由 `.claude/CLAUDE.md` 匯入。
  3. 建立 `tools/dev_check.ps1`：密鑰掃描、ruff、pytest、連結、分岔登記、上游查驗；完整版加跑 `gradlew :app:assembleDebug`。
     機器相關路徑（JDK / SDK / Gradle home）由 gitignore 的 `env.ps1` 提供。
  4. 上游 tag 為兩段式（`v1.3`、`v1.4`），`check_upstream_updates.py` 的版本解析放寬為 `major.minor[.patch]`。
  5. 採 `release` 追蹤模式（上游 `main` 每日多次文件類 commit）。PR 水位 `#54` 以 `refs/pull/*` 取得；
     issue 與 PR 共用編號，水位先同設 `#54`，首次 `gh` 查驗後再校正。
  6. 建立每週自動執行的 `upstream-check.yml`，對齊 `hypit` fork 的上游查驗水位線架構。

## 2026-09-24: 比照全 fork 艦隊補齊維護面

- **做法**：機械比對 54 個 SanHsien 公開 repo 的根目錄與 `.github`、`tools`、`docs` 結構，
  補上 ≥ 半數 repo 共有且適用 Android 專案的檔案；範本取最接近的 fork `commerce-agents`
  （分岔登記表 + 檢查器 + 合約測試）。
- **不照抄的部分**：
  - `CHANGELOG.md` 是上游產品檔（簡中版本紀錄），不改寫成 fork 的雙語 CHANGELOG；fork 歷史記在本檔。
  - 依賴新鮮度檢查只管 fork 自有的 `requirements-dev.txt` 與 Actions pin；Gradle 依賴交給 Dependabot `gradle`。
  - ruff 排除 `tools/jev/`（上游校準腳手架，跟上游風格）。
  - 決策與同步文件從 `docs/fork/` 移到 `docs/`，與艦隊多數 repo 一致。
- **CI**：Linux 跑維護工具與 `assembleDebug`；Windows 跑 `dev_check.ps1 -Quick -SkipUpstream`；
  上游變動不讓 CI 變紅（交給每週 `upstream-check.yml`）。

## 2026-09-24: 判斷接口預設 Vercel，次選 OpenRouter

- **背景**：維護者主要用 Vercel AI Gateway。上游已有 Vercel 判斷預設，但回覆／視覺沒有，
  而回覆／視覺的金鑰會繼承判斷接口 → 判斷選 Vercel 時，繼承來的 Vercel 金鑰會被送到 OpenRouter 而失敗。
- **決策**：回覆與視覺各加 Vercel 預設（`https://ai-gateway.vercel.sh/v1`，`deepseek/deepseek-v3.1` /
  `google/gemini-2.5-flash`），全新安裝三路一次性預設 Vercel；已有任何設定的安裝一律不動。
- **未驗證**：兩個 Vercel 模型 ID 未在真機以「測試回覆／測試視覺」按鈕驗過；失敗時在設定頁改模型即可，不需改碼。

## 2026-09-24: LINE 支援路線

- **現況**：無適配器的 App 已可用懸浮球選單「截屏識別一次」整屏 OCR，LINE 手動可用。
- **自動模式**：`LineAdapter` 骨架先行，`VERIFIED = false` 且未驗證前不加入 `adapters`，
  行為與無適配器 App 完全相同。需要一份 LINE 聊天室的 `uiautomator dump` 才能定案（讀節點／OCR／不可行三選一）。
- **電腦版 LINE**：不在本 repo 範圍（Android only）；可行路線是移植上游姊妹專案 `jev-chat-windows`
  的「視窗截圖 + 本機 OCR」做法，另開 repo 評估。
