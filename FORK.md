# Fork 維護說明

本 repo fork 自 [`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis)，
沿用 MIT License（`LICENSE`、`NOTICE`）與完整 Git 歷史。

## 為什麼維護 fork

- 追蹤與使用 Jev 聊天助手（Android 非侵入式對話副駕：無障礙讀畫面 → Jev 判斷 → 候選回覆 → 人工發送）。
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
| `tools/dev_check.ps1` | Windows 本機一鍵 gate（Python 腳手架 + Gradle 建置 + UpstreamCheck） |
| `tools/check_upstream_updates.py` | 上游 release / PR / Issue 增量檢查 |
| `tools/upstream_baseline.json` | 上游已審核水位紀錄 |
| `.github/workflows/upstream-check.yml` | 每週對上游檢查新 release 與 ticket |
| `docs/fork/DECISIONS.md`、`docs/fork/UPSTREAM.md` | fork 維護決策與同步指引 |
| `.cursor/rules/no-upstream-pr.mdc` | 防呆規則：禁止誤對上游開 PR 或推送 |

## 分支與 remote

- `origin/main`：`SanHsien/jev-chat-jarvis`，主要維護線。
- `upstream/main`：`jev-chat/jev-chat-jarvis` 原專案，只追蹤、不推送。
- 日常修改在本機跑 gate（`pwsh -NoProfile -File tools/dev_check.ps1 -Quick` 或完整版）後推 `origin/main`。

不要 `git push upstream`。同步方式見 [`docs/fork/UPSTREAM.md`](docs/fork/UPSTREAM.md)。

## 開發環境指引

前置：JDK 17、Android SDK（compileSdk 35）、Python 3.12、PowerShell 7、`gh`。
路徑必須全 ASCII（上游硬約束），機器相關設定放 `env.ps1`（已 gitignore）。

```powershell
git clone https://github.com/SanHsien/jev-chat-jarvis.git
cd jev-chat-jarvis
git remote add upstream https://github.com/jev-chat/jev-chat-jarvis.git
gh repo set-default SanHsien/jev-chat-jarvis
pwsh -NoProfile -File tools/dev_check.ps1 -Quick
```

`env.ps1` 範例（依本機路徑調整）：

```powershell
$env:JAVA_HOME = "H:\android\jdk"
$env:ANDROID_HOME = "H:\android\sdk"
$env:GRADLE_USER_HOME = "H:\android\gradle-home"
```
