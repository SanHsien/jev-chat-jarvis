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

CI（`.github/workflows/ci.yml`）跑同樣的檢查：Linux 跑維護工具與 APK 建置，Windows 跑 `dev_check.ps1 -Quick -SkipUpstream`。

## 判斷接口（本 fork 預設 Vercel）

全新安裝時三路接口一次性預設為 Vercel AI Gateway（見 `Prefs.seedVercelDefaultIfFresh()`），只要在
設定頁「判斷接口」填一把 [Vercel AI Gateway](https://vercel.com/ai-gateway) 金鑰，回覆與視覺留空即繼承：

| 路線 | Base URL | 模型 |
|---|---|---|
| 判斷 | `https://ai-gateway.vercel.sh/typesafe`（POST `/v1/systemone`） | `typesafe-ai/jev` |
| 回覆 | `https://ai-gateway.vercel.sh/v1` | `deepseek/deepseek-v3.1` |
| 視覺 | `https://ai-gateway.vercel.sh/v1` | `google/gemini-2.5-flash` |

次選 OpenRouter：三張卡各選「OpenRouter」，填 OpenRouter 金鑰。已有設定（升級、手動選過）的安裝不會被改動。

## LINE 支援

| 模式 | 狀態 |
|---|---|
| 手動：懸浮球選單「截屏識別一次」 | 可用（整屏 OCR，不分我／對方） |
| 自動：`LineAdapter` | 骨架已在 `capture/ChatAppAdapter.kt`，`VERIFIED = false`，尚未接入 |

完成自動模式需要一份 LINE 聊天室的無障礙樹：

```powershell
adb shell uiautomator dump /sdcard/line.xml
adb pull /sdcard/line.xml docs/line/line.xml
```

依 dump 結果三選一：

1. 訊息節點有文字與 resource-id → 填 `MESSAGE_ID` / `INPUT_ID` / `TITLE_ID`，`VERIFIED = true`。
2. 只有氣泡、沒有文字 → 比照 `FeishuAdapter` 回傳空訊息清單 + 氣泡矩形走 OCR。
3. 聊天畫面 `FLAG_SECURE`（截圖全黑）→ 自動與手動都不可行，記入 `docs/DECISIONS.md`。

dump 可能含聊天內容，放進 repo 前先把對話文字換成假資料。

電腦版 LINE 不在本 repo 範圍（本 repo 只做 Android）：上游姊妹專案
[`jev-chat-windows`](https://github.com/jev-chat/jev-chat-windows) 的「視窗截圖 + 本機 OCR」做法可移植到 LINE PC。
