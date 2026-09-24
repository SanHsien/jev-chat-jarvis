# Fork 維護說明

本 repo fork 自 [`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis)，
沿用 MIT License（`LICENSE`、`NOTICE`）與完整 Git 歷史。

## 為什麼維護 fork

- 追蹤與使用 Jev 聊天助手（Android 非侵入式對話副駕：無障礙讀畫面 → Jev 判斷 → 候選回覆 → 人工發送）。
- **支援 LINE**（維護者的主要聊天軟體）：`LineAdapter` 骨架待真機驗證，手動 OCR 已可用。
- 判斷接口改以 Vercel AI Gateway 為預設（次選 OpenRouter）。
- 研究 Jev 作為「AI 判斷層」（Choice / Score / 是非機率）嵌入其他 Agent 工作流的用法（`tools/jev/`）。
- 採 Windows-first 維護：Windows 11 + PowerShell 7 是主要開發、建置與驗收環境。
- 建立可重現的 Windows 開發 gate（`tools/dev_check.ps1`）、上游同步檢查與自動化追蹤。

**回貢判準：修的是上游的 bug 就送回去；這裡獨創的文件與 Windows 維護骨架留在這裡。**
回貢前必須在當次對話取得維護者明確同意；「fork」「建開發環境」「開 PR」都不是同意。

## 與上游的差異

| 項目 | 說明 |
|---|---|
| `AGENTS.md` / `.claude/CLAUDE.md` | 本 fork 的 AI 維護規則（上游 `CLAUDE.md` 原樣保留） |
| `NOTICE.md` / `FORK.md` | 來源、授權與同步說明 |
| `README.md` / `README.en.md` / `README.zh-CN.md` | 繁中主檔、英文鏡像、上游簡中原文 |
| `SECURITY.md` / `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` | 回報與協作規則 |
| `docs/DIVERGENCE.md` | 上游持有檔案的分岔登記表（`tools/check_divergence.py` 強制） |
| `docs/DECISIONS.md`、`docs/UPSTREAM.md`、`docs/DEVELOPMENT.md` | 決策紀錄、同步指引、開發指南 |
| `tools/dev_check.ps1` | Windows 一鍵 gate（密鑰掃描、ruff、pytest、連結、分岔、Gradle、上游） |
| `tools/check_upstream_updates.py`、`tools/upstream_baseline.json` | 上游 release / PR / Issue 增量檢查與水位 |
| `tools/check_divergence.py`、`tools/check_links.py`、`tools/check_dependency_freshness.py` | 分岔登記、文件連結、依賴新鮮度檢查 |
| `tests/` | 上述工具的合約測試（pytest） |
| `.github/workflows/ci.yml` | Linux 維護工具 + Windows gate + Android assembleDebug |
| `.github/workflows/codeql.yml` | CodeQL（java-kotlin、python、actions） |
| `.github/workflows/upstream-check.yml`、`dependency-freshness.yml` | 每週上游查驗、每月依賴新鮮度 |
| `.github/dependabot.yml`、`.github/dependency-deferrals.json` | Actions / pip / Gradle 更新與延後紀錄 |
| `.gitattributes`、`.editorconfig`、`pyproject.toml`、`requirements-dev.txt` | 換行、編輯器、ruff/pytest 設定、維護工具依賴 |
| `.cursor/rules/no-upstream-pr.mdc` | 防呆規則：禁止誤對上游開 PR 或推送 |

產品程式碼的改動（Vercel 預設、LINE 適配器）逐檔登記在 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)。

## 分支與 remote

- `origin/main`：`SanHsien/jev-chat-jarvis`，主要維護線。
- `upstream/main`：`jev-chat/jev-chat-jarvis` 原專案，只追蹤、不推送。
- 日常修改在本機跑 gate（`pwsh -NoProfile -File tools/dev_check.ps1 -Quick` 或完整版）後推 `origin/main`。

不要 `git push upstream`。同步方式見 [`docs/UPSTREAM.md`](docs/UPSTREAM.md)。

## 開發環境指引

前置：JDK 17、Android SDK（compileSdk 35）、Python 3.11+、PowerShell 7、`gh`。詳見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。
路徑必須全 ASCII（上游硬約束），機器相關設定放 `env.ps1`（已 gitignore）。

```powershell
git clone https://github.com/SanHsien/jev-chat-jarvis.git
cd jev-chat-jarvis
git remote add upstream https://github.com/jev-chat/jev-chat-jarvis.git
gh repo set-default SanHsien/jev-chat-jarvis
python -m pip install -r requirements-dev.txt
pwsh -NoProfile -File tools/dev_check.ps1 -Quick
```

`env.ps1` 範例（依本機路徑調整）：

```powershell
$env:JAVA_HOME = "H:\android\jdk"
$env:ANDROID_HOME = "H:\android\sdk"
$env:GRADLE_USER_HOME = "H:\android\gradle-home"
```
