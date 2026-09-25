# AGENTS.md

給 Codex、Claude Code、Cursor 與其他自動化代理在本專案工作時的指引。

## 專案定位

這是 [`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis) 的 MIT fork。
專案核心為 Android 非侵入式「對話副駕」：無障礙服務／截屏 OCR 讀取聊天畫面，
呼叫 Jev 判斷模型（選擇／評分／是非）分析對方意圖與風險，再產生候選回覆，一鍵填入輸入框，發送由人決定。

`origin` 是 `SanHsien/jev-chat-jarvis`，`upstream` 是原作者 repo，預設分支皆為 `main`。
本 fork 的維護差異記在 [`FORK.md`](FORK.md) 與 [`docs/DECISIONS.md`](docs/DECISIONS.md)。

主要開發與完整驗收環境是 **Windows 11 + PowerShell 7**。

## 產品硬約束（所有人必須遵守）

1. **不 hook、不 Xposed、不改目標 App、不讀其資料庫**。只用系統無障礙服務與截圖。
2. **絕不自動發送訊息**，絕不點任何 App 的發送按鈕。填入輸入框後停手。
3. **不碰錢**：不觸碰轉帳、紅包、收款碼、LINE Pay 相關的任何介面元素。
4. **路徑全 ASCII**：Android 建置工具在 Windows 上不接受中文路徑。
5. **金鑰不落盤、不進日誌、不進 git**：任何檔案不得出現 `sk-or-` 開頭字串；簽章檔（`*.jks`、`keystore.properties`）不進 repo。
6. 編碼一律 UTF-8。Windows 用 pwsh 7+；Python 讀寫檔案必須顯式 `encoding='utf-8'`。
7. `com.tencent.mm`（微信）在 `ChatCaptureService.BLOCKED_PKGS`：上游使用者回報截取微信畫面會讓微信對該裝置開啟防截圖，
   解除安裝也不恢復（上游 issue #42、#46、#47、#52）。任何情況都不讀、不截圖、不填入。
8. **移除或放寬有上游使用者回報支撐的保護措施之前，必須先向維護者說明風險、附上回報出處，並取得明確同意**；
   即使指示本身聽起來已包含該動作，也要先提醒、再問。（2026-09-24 起）

## 技術棧與關鍵背景

- Kotlin，傳統 View + XML，**不用 Compose**；minSdk 30，compileSdk／targetSdk 35；JDK 17；AGP 9（內建 Kotlin，不套 `kotlin.android` 外掛）。
- 模型客戶端分三路：`jev/JudgeClient`（判斷）、`jev/ReplyClient`（回覆）、`jev/VisionClient`（視覺），共用 `jev/HttpJson`；設定在 `core/Prefs`。
- Jev 只回答選擇題／打分／是非，不生成文字。**題目的 instructions 和 criteria 用英文寫，state 裡的聊天內容保留原文。**
- 採集層按 App 分派：`capture/ChatAppAdapter.kt` 一個 App 一個適配器，`ChatCaptureService` 依前景套件名查表；下游通用。
  適配器契約：`extract` 回 `null` = 不在聊天窗；回空訊息清單 = 在聊天窗但樹裡沒正文，只有後者觸發 OCR 兜底。
- **判斷「是否在聊天窗」一律看樹裡有沒有輸入框等節點，不看 Activity 名**（X 全程只有一個 Activity）。
- 判「我／對方」比較氣泡左右兩緣離頭像欄的距離，不用中心點（長訊息的中心會超過半屏）。任何發送鈕都**絕不 performAction**。
- X 12.25.2 私信是 Compose：訊息節點沒有 resource-id，資訊全在 content-desc（`發件人：正文。時間。Read。`）；對話頁靠唯一的 EditText 判定。
- **LINE（本 fork 原創）**：規則在 `capture/LineExtractor.kt`（與 Android 型別無關，可在 JVM 單元測試），`LineAdapter` 只是包裝。
  2026-09-25 真機 dump 驗證：正文 `id/chat_ui_message_text`、訊息列 `id/chat_ui_row_contentview_container`、標題 `id/header_title`、
  輸入框 `id/chat_ui_message_edit`；我方列帶 `id/chat_ui_linear_layout_meta_data`／「已讀」，對方列帶 `id/chat_ui_row_layout_metadata`。
  發送鈕 `id/chat_ui_send_button_image` **絕不 performAction**。
  群組：發言者取自頭像 content-desc「某某的個人圖片」（`Msg.speaker`），連發沿用、我方訊息後重置；群組判定與分析對象在 `core/GroupChat.kt`，
  只有群組才在 Jev state 加 `name`／`focus_person`，一對一的 state 必須維持與校準時相同。改規則時先用新 dump 更新 `app/src/test/resources/line/` 的測試資料（姓名與內容換成假資料）。
- OCR 在 `capture/ocr`：`ScreenCapture` 限頻 ≥1s + 失敗退避（1→2→4→8→16→30s）；`MlKitOcr` 用 bundled 中文模型。
  無障礙設定 `config_accessibility.xml` 有 `canTakeScreenshot="true"`，**改完要把無障礙關掉再開才生效**。
- 知識庫在 `filesDir/kb`（`notes.json`／`contacts.json`／`logs/<contactId>.json`），`KbStore` 單鎖 + 原子寫；
  `ContextBuilder` 只做常駐筆記 + 標籤／標題包含匹配；**歷史預設關閉**。
- Kotlin 字串模板 `$x` 後面緊接中文標點會被當成識別字的一部分而編譯失敗，**一律寫 `${x}`**。

## 硬性邊界

- **對外只打維護者的 repo。** PR、push、release 一律指向 `SanHsien/jev-chat-jarvis`。
  對上游開 PR 或 push 預設絕對禁止，除非維護者在當次對話明確同意。
- 每個工作環境先確認 `gh repo set-default SanHsien/jev-chat-jarvis`。
- 日常開發推送到 `origin/main` 前，必須通過 Windows 閘門：
  `pwsh -NoProfile -File tools/dev_check.ps1 -Quick`（或完整無參數版本，含 Gradle 建置）。
- 保持乾淨工作目錄，不隨意刪除上游核心程式、資源或依賴。
- **改到上游持有的檔案，同一個 commit 在 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md) 加一列**；
  `tools/check_divergence.py` 會擋未登記的改動。
- commit／push：完成且 gate 通過即 commit 並推 `origin/main`，不開分支、不開 PR。維護者要求時把 `main` squash 成**單一根 commit**（不接上游歷史，基準只以 SHA 記在 `tools/upstream_baseline.json`、`docs/DIVERGENCE-windows.md`）。repo 只留 `main`、最新 release 與其 tag（`repo cleanup` workflow 會自動清理）。

## 驗證

完整指令與各步驟見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。最少要跑：

```powershell
python -m pip install -r requirements-dev.txt
pwsh -NoProfile -File tools/dev_check.ps1 -Quick
```

動到 `app/` 時跑完整版（含 `gradlew :app:assembleDebug`）；本機沒有 Android SDK 時，以 CI 的
`Android build` job 為準，並在回報中說明未本機建置。

## 本 fork 的產品差異

- **LINE 支援為本 fork 原創**，上游沒有。
- **Windows 版在 `wingman/`**：[`jev-chat/jev-chat-windows`](https://github.com/jev-chat/jev-chat-windows)（remote `upstream-windows`）拆進本 repo 結構——套件 `wingman/`（`python -m wingman`）、`requirements-windows.txt`、打包 `tools/windows/`、上游授權 `docs/licenses/jev-chat-windows/`，不在 repo 裡另立子專案；
  只認 LINE 電腦版（`LINE.exe`），原版目標聊天軟體的程式全刪；改動與跟進方式記在 [`docs/DIVERGENCE-windows.md`](docs/DIVERGENCE-windows.md)。
  LINE 版面未驗證前 `wingman/app/fill.py` 的 `VERIFIED = False`（只寫剪貼簿，不動滑鼠鍵盤）。使用說明寫在根目錄 README（中英）的〈Windows 版〉章節；release 的 `windows` job 把 zip 附到同一個 Release。Python 風格跟上游，根目錄 ruff 排除 `wingman/`、`tools/windows/`。
- **移除微信、飛書與 QQ**：三者的適配器、偽裝無障礙服務名與相關說明已刪除；微信另列 `BLOCKED_PKGS`（見硬約束 7）。
- **判斷接口預設 Vercel**：全新安裝三路接口皆為 Vercel AI Gateway（`Prefs.seedVercelDefaultIfFresh()`），次選 OpenRouter。
- **接口預設白名單**（2026-09-25 起，維護者決定）：只內建 OpenRouter、Vercel AI Gateway、TypeSafe、OpenCode Zen 與自定義；上游新增其他服務商的預設、模型或說明不收（上游 PR #41 類）；對外文件只陳述白名單，不寫排除理由、不點名其他服務商；舊設定由 `Prefs.dropRemovedVendors()` 遷移。
- **半自動分析**（Android 預設）：對方新訊息只顯示分析對象與「分析」按鈕，點了才呼叫模型（`Prefs.autoAnalyze` 預設 `false`）；理由是省 token，見 `docs/DECISIONS.md`。
- **產品名「對話副駕」**（英文 Chat Wingman）：介面、通知、README 一律用此名；「Jev」只指判斷模型。套件名 `com.jev.probe` 與 APK 檔名不變。
- **上游出處**：依上游 NOTICE，README、設定頁「關於與隱私」與 release 說明都要寫「基於 Jev 聊天助手（https://github.com/jev-chat/jev-chat-jarvis）二次開發」，APK 內附 `LICENSE`／`NOTICE`；不得以上游名稱暗示原作者出品。Windows 版另依 JevChat-Windows 的〈版權與許可〉：README、設定頁〈關於與授權〉與 release 說明寫「基於 JevChat-Windows（https://github.com/jev-chat/jev-chat-windows）二次開發」，zip 內保留其 `LICENSE`／`NOTICE`，並註明 GPLv3 元件（PySide6-Fluent-Widgets）使發布包整體受 GPLv3 約束。
- **App 介面繁體中文**：新增或修改介面字串一律用繁體（台灣用語）；比對其他 App 介面文字的清單要同時列簡、繁兩種寫法；`JevQuestions.kt` 的判斷題目不改。
- **版本號**：`versionName` 為 `上游主.次.fork 序號`（例如 `1.4.0`、`1.4.1`），`versionCode` 為 `上游 versionCode × 100 + fork 序號`。
