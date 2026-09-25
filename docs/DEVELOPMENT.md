# 開發指南

## 環境

| 項目 | 版本 | 說明 |
|---|---|---|
| JDK | 17 | `JAVA_HOME` |
| Android SDK | platform 35 / build-tools 35 | `ANDROID_HOME` |
| Python | 3.11+ | 只用於 `tools/`（維護工具與 `tools/jev` 校準腳手架） |
| PowerShell | 7+ | `tools/dev_check.ps1` |

路徑必須全 ASCII（Android 工具鏈限制）。機器相關設定放 repo 根目錄的 `env.ps1`（已 gitignore），
`dev_check.ps1` 會自動載入：

```powershell
$env:JAVA_HOME = "H:\android\jdk"
$env:ANDROID_HOME = "H:\android\sdk"
$env:GRADLE_USER_HOME = "H:\android\gradle-home"
```

## 一鍵 gate

```powershell
python -m pip install -r requirements-dev.txt
pwsh -NoProfile -File tools/dev_check.ps1                 # 完整：含 gradlew :app:assembleDebug 與上游查驗
pwsh -NoProfile -File tools/dev_check.ps1 -Quick          # 不建 APK
pwsh -NoProfile -File tools/dev_check.ps1 -SkipUpstream   # 不查上游（離線或 CI）
```

| 步驟 | 指令 |
|---|---|
| 密鑰掃描 | `git grep` `sk-or-` |
| Lint / 格式 | `ruff check .`、`ruff format --check .`（只管 `tools/*.py`、`tests/`；`tools/jev` 跟上游） |
| 測試 | `pytest -q` |
| 文件連結 | `python tools/check_links.py` |
| 分岔登記 | `python tools/check_divergence.py` |
| APK | `gradlew :app:assembleDebug` |
| 上游 | `python tools/check_upstream_updates.py --strict` |

正式簽章只在設了 `JEV_KEYSTORE_PROPS`（指向 repo 外的簽章 properties 檔）時啟用；沒設就是未簽章的 release，
任何作業系統都一樣（上游 PR #32 的做法）。App 的單元測試：`gradlew :app:testDebugUnitTest`。

CI（`.github/workflows/ci.yml`）跑同樣的檢查：Linux 跑維護工具與 APK 建置，Windows 跑 `dev_check.ps1 -Quick -SkipUpstream`。

## 取得 APK 與發版

- **正式取得**：GitHub Releases。`release` workflow（`.github/workflows/release.yml`）建置 APK 並附上 `.sha256`。
- **發版**：先把 `app/build.gradle.kts` 的 `versionName`／`versionCode` 與 `CHANGELOG.md`／`CHANGELOG.en.md` 推上 `main`，
  再推 tag `vX.Y.Z`，或在 Actions 手動執行 `release` 並填版本號。tag 與 `versionName` 不一致時 workflow 會失敗。
- **簽章**：repo secrets 有 `JEV_KEYSTORE_B64`（keystore 的 base64）、`JEV_KEYSTORE_PASSWORD`、`JEV_KEY_ALIAS`、
  `JEV_KEY_PASSWORD` 時發正式簽章的 `jev-assistant-vX.Y.Z.apk`；沒有時發 `jev-assistant-vX.Y.Z-debug.apk`。
  debug 簽章每次建置可能不同，換簽章後要先解除安裝舊版。
- **產生正式簽章並設定 secrets**（只做一次，在自己的電腦上）：

  ```powershell
  gh auth login                                   # 若尚未登入
  pwsh -NoProfile -File tools/new_signing_key.ps1  # 金鑰預設存到 $HOME\jev-signing（repo 外）
  ```

  腳本用 JDK 的 `keytool` 產生 RSA 4096 的 PKCS12 金鑰（效期約 27 年，密碼隨機），用 `gh secret set`
  寫入上述四個 secrets，並在同目錄寫一份本機建置用的 `jev-release.properties`。
  **務必備份 `jev-signing` 資料夾**（例如密碼管理器）；遺失金鑰就無法再發可覆蓋安裝的更新。
  已存在金鑰時腳本會拒絕執行，除非加 `-Force`。
- **repo 只留 `main`、最新 release 與其 tag**：`release` 發版成功後會呼叫 `repo cleanup` workflow，刪除舊 release／tag
  與 `main` 以外的分支（開著 PR 的分支會保留並提示，例如 Dependabot）。也可以在 Actions 手動執行 `repo cleanup`。
- **每次 push**：`ci` 的 Android job 也會上傳 debug APK artifact `jev-assistant-debug-apk`（保留 30 天），供測試用。

## 版本號

- `versionName` = `上游主.次.fork 序號`：`1.4.0` 是基於上游 1.4 的第 0 版，之後是 `1.4.1`、`1.4.2`…。跟進上游 1.5 時改為 `1.5.0`。
- `versionCode` = `上游 versionCode × 100 + fork 序號`：上游 1.4 的 versionCode 是 `5`，所以 `1.4.0` = `500`、`1.4.1` = `501`。
- 每次發版同步更新 `CHANGELOG.md` 與 `CHANGELOG.en.md`；tag 用 `v1.4.1` 這種三段式。

## 判斷接口（本 fork 預設 Vercel）

全新安裝時三路接口一次性預設為 Vercel AI Gateway（見 `Prefs.seedVercelDefaultIfFresh()`），只要在
設定頁「判斷接口」填一把 [Vercel AI Gateway](https://vercel.com/ai-gateway) 金鑰，回覆與視覺留空即繼承：

| 路線 | Base URL | 模型 |
|---|---|---|
| 判斷 | `https://ai-gateway.vercel.sh/typesafe`（POST `/v1/systemone`） | `typesafe-ai/jev` |
| 回覆 | `https://ai-gateway.vercel.sh/v1` | `google/gemini-2.5-flash` |
| 視覺 | `https://ai-gateway.vercel.sh/v1` | `google/gemini-2.5-flash` |

次選 OpenRouter：三張卡各選「OpenRouter」，填 OpenRouter 金鑰。已有設定（升級、手動選過）的安裝不會被改動。

## LINE 支援

| 模式 | 狀態 |
|---|---|
| 自動：`LineAdapter` | 可用。2026-09-25 以真機 dump 驗證（1:1 聊天、繁中介面、1440×3120） |
| 手動：懸浮球選單「截屏識別一次」 | 可用（整屏 OCR，不分我／對方） |

- 規則在 `app/src/main/java/com/jev/probe/capture/LineExtractor.kt`；它只依賴一個精簡的 `UiNode` 介面，
  單元測試 `LineExtractorTest` 直接用 dump 檔（`app/src/test/resources/line/chat_1440x3120.xml`）驗證。
- 「我／對方」看訊息列裡的標記節點（我方：`chat_ui_linear_layout_meta_data`、`chat_ui_row_read_count`；
  對方：`chat_ui_row_layout_metadata`、`chat_ui_row_thumbnail`），沒有標記時才用氣泡靠哪一邊判斷。
- LINE 改版或遇到新畫面（群組、其他語言）時，重新 dump 一份：

  ```powershell
  adb shell uiautomator dump /sdcard/line.xml
  adb pull /sdcard/line.xml
  ```

  放進 `app/src/test/resources/line/` 前，把聯絡人姓名與訊息內容換成假資料（repo 是公開的），並在 `LineExtractorTest` 加一個案例。

電腦版 LINE 不在本 repo 範圍（本 repo 只做 Android）：上游姊妹專案
[`jev-chat-windows`](https://github.com/jev-chat/jev-chat-windows) 的「視窗截圖 + 本機 OCR」做法可移植到 LINE PC。

## Windows 版（`wingman/`）

在 Windows 的 repo 根目錄：建 venv、`pip install -r requirements-windows.txt`、`python -m wingman`；打包用 `tools\windows\build.bat`
（或 `pyinstaller --noconfirm --clean tools/windows/wingman.spec`，產物在 `dist\chat-wingman\`）。
各模組自測：`python -m wingman.core.providers`（`wingman.core.jev_client`、`wingman.core.llm`、`wingman.core.draft`、`wingman.core.engine`、`wingman.app.update` 同理）；
core 的自測不需要 Windows，裝好 `openai`、`anthropic`、`google-genai`、`typesafe-sdk` 在 Linux 也能跑。
CI 的 `windows` workflow 在 windows-latest 跑同一組自測並上傳 `chat-wingman-windows` artifact；`release` workflow 的 `windows` job 把 zip 附到同一個 Release。
使用說明見 [`../README.md`](../README.md) 的〈Windows 版〉，與上游的對照見 [`DIVERGENCE-windows.md`](DIVERGENCE-windows.md)。
