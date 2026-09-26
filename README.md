<div align="center">

<img src="docs/images/logo.svg" width="150" alt="對話副駕" />

# 對話副駕

**手機與電腦上的聊天幫手：你在聊天，它在旁邊讀懂對方、告訴你該怎麼回，一鍵填進輸入框，發不發由你。**

中文 | [English](README.en.md)

</div>

> 基於 Jev 聊天助手（[https://github.com/jev-chat/jev-chat-jarvis](https://github.com/jev-chat/jev-chat-jarvis)）二次開發：本 repo fork 自 [`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis)（MIT），非原作者出品或背書。
> **LINE 支援是本 fork 的原創功能**，上游沒有。微信、飛書與 QQ 的支援已從本 fork 移除。
> **Windows 版**基於 JevChat-Windows（[https://github.com/jev-chat/jev-chat-windows](https://github.com/jev-chat/jev-chat-windows)）二次開發，改為只支援 LINE 電腦版，見〈[Windows 版](#windows-版line-電腦版預覽)〉。
> 維護說明見 [`FORK.md`](FORK.md)，與上游的逐檔差異見 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)、[`docs/DIVERGENCE-windows.md`](docs/DIVERGENCE-windows.md)。

## 為什麼用它

- **先判斷，再寫字。** 判斷模型先給出對方真實意圖、危險等級、該不該馬上回，再據此起草回覆。
- **不動你的聊天軟體。** 不 hook、不改包、不走任何 App 的介面或帳號、不讀資料庫，只用系統無障礙服務讀「螢幕上正在顯示的對話」。
- **發送權永遠在你手裡。** 只把回覆填進輸入框，從不自動發送；不碰轉帳、紅包、收款、LINE Pay。
- **它認識你的人和事。** 本機知識庫與聯絡人檔案，分析時自動帶上命中的筆記和這個人的歷史。
- **接口自己配。** 判斷／回覆／視覺三路分別可填，用你自己的金鑰，不經過任何中間伺服器。
- **隱私在本機。** 金鑰存在 App 私有空間；聊天內容只在分析那一刻送到你設定的接口，不落盤、不進日誌。

## 平台支援

| 平台 | 狀態 | 讀取方式 | 備註 |
|---|---|---|---|
| **LINE** | ✅ 全鏈路 | 無障礙讀節點（`LineAdapter`） | **本 fork 原創**。2026-09-25 真機 dump 驗證（1:1 聊天、繁中介面）；照片與貼圖以「[照片]」「[貼圖]」帶入 |
| X / Twitter 私訊 | ✅ 全鏈路 | 解析 Compose 節點的 content-desc | 12.25 上游實測，中文介面 |
| 其他 App | ✅ 手動 | 懸浮窗選單「截屏識別一次」整屏 OCR | 不分我／對方，全部當作對方所說並在面板標註 |
| **Windows：LINE 電腦版** | 🧪 預覽 | 視窗截圖 + 本機 OCR（見〈[Windows 版](#windows-版line-電腦版預覽)〉） | 基於 jev-chat-windows 二次開發；LINE 版面未實機驗證，「填入」暫時只複製到剪貼簿 |

本專案只讀你自己裝置上、你自己有權查看的聊天。

## 快速開始（Android）

**1. 取得 APK。** 到 [Releases](https://github.com/SanHsien/jev-chat-jarvis/releases) 下載最新版的 `jev-assistant-v*.apk`（Android 11+，僅 ARM64），附 `.sha256` 可核對；或自己建置（見下方〈建置〉）。

```bash
adb install -r jev-assistant-v1.4.11.apk   # debug 簽章的版本檔名結尾是 -debug.apk
```

**2. 填金鑰。** App → 設定 →「接口」。全新安裝時三路接口預設為 [Vercel AI Gateway](https://vercel.com/ai-gateway)，只要在「判斷接口」填一把 Vercel 金鑰，回覆與視覺留空會自動繼承。次選 OpenRouter：三張卡各選「OpenRouter」並填 OpenRouter 金鑰。每張卡都有一鍵連通測試。

**3. 開權限。** 從瀏覽器或檔案管理員安裝的 App，Android 13 以後開無障礙或懸浮窗會出現「應用程式存取權已遭拒絕」：先到 設定 → 應用程式 → 對話副駕 → 右上角 ⋮ →「允許受限制的設定」，驗證後再開（看不到 ⋮ 就先去無障礙設定點一次 對話副駕）。改用 `adb install` 安裝則不受此限制。接著依主頁引導開啟：
- 無障礙（讀訊息；升級後要把無障礙關掉再開一次，截圖能力才會生效）
- 懸浮窗／顯示在其他應用程式上層
- 自啟動 + 省電無限制（小米／HyperOS 必開，否則背景被凍結）

## 功能

### 半自動分析（預設）
- 懸浮窗**不會自己展開**（捲動 LINE 對話也不會跳出來）。點懸浮球才展開，顯示**分析對象**（群組裡是最新發言者）與對方最新一則訊息，按「分析」才送出判斷與起草，按「略過」收起。
- Windows 版同理：對方有新訊息時只在狀態列顯示分析對象並出現「分析」按鈕，按了才呼叫模型。
- **為什麼**：貼圖、照片、「好」「哈哈」這類訊息多半不需要分析，每則都自動送出會白花 token；面板自己跳出來也會擋住聊天。想要每則都自動分析，到設定開「對方發訊息時自動分析」。

### 判斷與候選回覆
- 判斷模型一次給出：對方真實意圖、危險等級（1–9）、對方要什麼、該不該馬上回、最佳動作，約 1 秒。
- 生成模型起草 3 條口語化候選，判斷模型依「最合適」排序。
- 懸浮窗點一下即複製或填入；填入用 `ACTION_SET_TEXT`，失敗自動改用剪貼簿貼上，**任何情況下都不發送**。

### 知識庫與聯絡人
- **筆記**：常駐筆記每次都帶；其他筆記要標籤或標題出現在會話標題或最近 6 則訊息裡才帶，最多 5 條。
- **聯絡人**：姓名／別名／關係／備註，會話標題命中姓名或任一別名即生效。
- **歷史**：「記錄聊天歷史（只存本機）」預設關閉。
- 知識庫與歷史都在 App 私有目錄，設定裡可一鍵清除。

### 接口與模型
- 判斷／回覆／視覺三路的位址、金鑰、模型分別可填；回覆與視覺留空就繼承判斷接口的金鑰。
- 判斷接口內建：OpenRouter、TypeSafe 直連、Vercel、OpenCode Zen、自訂。
- 回覆接口與視覺接口內建：OpenRouter、Vercel、自訂；預設模型皆為 `google/gemini-2.5-flash`。

### 群組聊天
- 在 LINE 群組裡，每則訊息會標上發言者（取自頭像的「某某的個人圖片」；同一人連發的後續訊息沿用同一人）。X 的群組私訊直接用發件人名稱。
- **分析對象是對方最新一則訊息的發言者**，其他人的發言只當背景；面板會顯示「群組：分析對象是「某某」」，候選回覆也以該人為回覆對象。
- 出現兩位以上具名發言者，或標題帶人數（例如「讀書會(12)」）時視為群組；一對一聊天的判斷內容與先前完全相同。

### 讀取與 OCR
- 一個 App 一個適配器，服務依前景套件名分派，適配器只負責把目前視窗變成「標題 + 訊息清單」。
- 無障礙樹沒有正文時，自動截圖並用 ML Kit 中文離線模型辨識，不上傳圖片。
- 任何 App 都能在懸浮窗選單手動觸發「截屏識別一次」。

## Windows 版（LINE 電腦版，預覽）

> **出處**：基於 JevChat-Windows（[https://github.com/jev-chat/jev-chat-windows](https://github.com/jev-chat/jev-chat-windows)，作者 rezoch340 與 jev-chat 貢獻者，MIT）二次開發，
> 程式已拆進本 repo：套件 [`wingman/`](wingman/)、依賴 `requirements-windows.txt`、打包 [`tools/windows/`](tools/windows/)、上游授權 [`docs/licenses/jev-chat-windows/`](docs/licenses/jev-chat-windows/)；逐檔對照見 [`docs/DIVERGENCE-windows.md`](docs/DIVERGENCE-windows.md)。非原作者出品或背書。

掛在 LINE 電腦版旁邊的回覆輔助：本機離線 OCR 讀畫面上的對話 → Jev 判斷 → 3 條排好序的候選。判斷內核、題目與三段式流程和 Android 版相同。

### 目前狀態
- **只認 LINE 電腦版**（行程 `LINE.exe`），其他聊天軟體一律不讀、不截圖、不填入。
- **LINE 版面尚未實機驗證**：訊息區定位、「我／對方」（綠色氣泡＝我）與群組發言人名沿用上游的像素規則，可開「除錯檢視」確認。
- **「填入」目前只複製到剪貼簿**，在 LINE 輸入框按 `Ctrl+V`；驗證 LINE 輸入框位置後才會改成自動貼上（`wingman/app/fill.py` 的 `VERIFIED`）。

### 安裝與執行
- 需求：Windows 10 1903+／11（Windows Graphics Capture）；LINE 電腦版開著、不要最小化（被其他視窗蓋住沒關係）。
- 到 [Releases](https://github.com/SanHsien/jev-chat-jarvis/releases) 下載 `chat-wingman-windows-v*.zip`（與 APK 同一個版本），解壓到固定資料夾後執行 `chat-wingman.exe`；exe 沒有簽章，SmartScreen 請選「其他資訊」→「仍要執行」。
- 原始碼執行（在 repo 根目錄，Python 3.10–3.12；3.13 不行，RapidOCR 1.4 不支援）：`python -m venv .venv`、`.venv\Scripts\Activate.ps1`、`pip install -r requirements-windows.txt`、`python -m wingman`。
- 第一次啟動會開設定頁，填兩把金鑰（只寫進登錄檔 `HKCU\Environment`，不落任何檔案）：
  - **判斷 · Jev**（`JEV_API_KEY`）：OpenRouter（預設，`typesafe/jev-1.13`）或 TypeSafe 直連（`jev-latest`）。
  - **起草 · 語言模型**（`LLM_API_KEY`）：預設 OpenRouter 的 `google/gemini-2.5-flash`；也可選 Vercel AI Gateway、OpenAI、Anthropic、Google Gemini，或自訂 OpenAI／Anthropic 相容地址（沒有預設模型的來源按「取得模型」挑）。
- 其餘設定存在 exe 旁（原始碼執行時在 `wingman/`）的 `config.json`：你們的關係、說話風格、參考上下文（3–30 則，預設 10）、群聊指定回覆對象、啟動時檢查更新（查本 repo 的 Release）、除錯檢視、起草思考模式（預設關）。

### 使用方式
- 對方來新訊息 → 懸浮窗顯示分析對象與「分析」按鈕（設定可改成自動分析）→ 按下後給判斷摘要（建議動作、可能意圖、對方需要、緊張度 0–9）與三條候選（附 Jev 勝出機率）→「填入」→ **你自己看過、改過再按發送**。
- 懸浮窗跟著目前聊天室走（聊天室名稱從視窗頭部 OCR 取得），記錄與候選按聊天室分開；群組會帶發言人名，可指定回覆對象並在填入時加「@名字 」（純文字）。
- 標題列開關可暫停採集；底部可展開即時聊天記錄，看 OCR 讀到什麼。只有對方有新訊息才呼叫模型，沒人說話就是零呼叫。

## 運作方式

```
LINE / X ──(無障礙讀節點或截圖 OCR)──▶ 取得最近訊息
                                  │
              ┌───────────────────┴───────────────────┐
              ▼                                        ▼
   Jev 判斷（一次 7 題）                      生成模型起草 3 條候選
   意圖／危險／需求／動作／該不該回                      │
              └───────────────────┬───────────────────┘
                                  ▼
                        Jev 為 3 條候選排序
                                  ▼
                半透明懸浮窗顯示 → 複製／填入（不發送）
```

Windows 版的採集方式不同，後段相同：

```
Windows Graphics Capture 截 LINE 視窗（被遮住也能截，最小化不行）
  → 像素錨點定位訊息區（底色、分隔線；深淺主題通用）→ OCR 頭部取聊天室名稱
  → RapidOCR 本機辨識訊息區，依氣泡顏色分我／對方，灰字（時間、引用、發言人名）另外處理，捲動去重
  → 對方有新訊息 → Jev 判斷 → 起草 3 條 → Jev 排序 → 懸浮窗 →「填入」（目前＝複製）
```

截圖與 OCR 在獨立子行程跑，畫面只在記憶體裡，不落盤、不進日誌、不上傳。

## 建置

JDK 17 + Android SDK（platform 35／build-tools 35），路徑需全 ASCII。

```powershell
python -m pip install -r requirements-dev.txt
pwsh -NoProfile -File tools/dev_check.ps1          # 完整 gate（含 gradlew :app:assembleDebug）
pwsh -NoProfile -File tools/dev_check.ps1 -Quick   # 不建 APK
```

Windows 版（在 Windows、repo 根目錄）：雙擊 `tools\windows\build.bat`，或 `pip install -r requirements-windows.txt pyinstaller` 再 `pyinstaller --noconfirm --clean tools/windows/wingman.spec`，產物在 `dist\chat-wingman\`。各模組自測：`python -m wingman.core.providers`（`wingman.core.jev_client`、`wingman.core.llm`、`wingman.core.draft`、`wingman.core.engine`、`wingman.app.update` 同理）；CI 的 `windows` workflow 會在 windows-latest 跑自測並打包，release 時一起附上 zip。

目錄：`app/`（Android 應用程式）、`wingman/`（Windows 版）、`tools/windows/`（Windows 版打包）、`tools/`（本 fork 維護工具）、`tools/jev/`（Jev 題目與校準腳手架）、`docs/`（開發與維護文件）、`tests/`（維護工具測試）。

## 已知限制

- **微信完全不讀取**：上游使用者回報，截取微信畫面後微信可能對該裝置開啟防截圖，解除安裝本 App 也不會恢復（上游 issue #42、#46、#47、#52）。因此在微信裡懸浮球不出現，也無法手動截屏識別。
- **LINE 只以真機驗證過 1:1 聊天與繁中介面**：群組、其他語言介面、檔案與語音訊息尚未驗證。
- **國產 ROM 背景凍結**：小米／HyperOS 可能殺背景，懸浮球短暫消失，在聊天裡再互動一下即可恢復。
- **X 只在中文介面驗證過**。
- **群組**：以最新發言者為分析對象，但「關係」設定是整個會話共用的；LINE 群組畫面尚未以真機 dump 驗證，頭像被捲出畫面的連續訊息會標為未知發言者。
- **OCR**：需要系統允許截圖；受保護視窗（`FLAG_SECURE`）截不到；只認得螢幕上看得見的部分。
- **Windows 版**：LINE 版面未驗證（見上）；Win10 的 WGC 採集黃框系統不給關（Win11 可以，暫停採集也會消失）；輸入框拉高超過面板一半會認錯訊息區；框內底色不平的字（頭像、照片、貼圖上的字）會被丟掉；群組名字行被 OCR 漏掉時訊息會掛到上一個人；聊天室靠頭部標題認，名字只差一字的兩個聊天室會併成一個；同一人連發兩句一模一樣的會吞一句；判斷題口徑是一對一，群組多人混說時會偏；沒有系統匣，關視窗就是結束。
- **APK 體積**：ML Kit 中文離線模型使 APK 約 27 MB，只打包 arm64-v8a。

## 版本

`versionName` 為 `上游主.次.fork 序號`（目前 `1.4.11`，基於上游 1.4）；變更紀錄見 [`CHANGELOG.md`](CHANGELOG.md)。

## 授權

MIT，Copyright © 2026 Finderchangchang 與 jev-chat 貢獻者；本 fork 的修改由 SanHsien 維護。見 [`LICENSE`](LICENSE)、[`NOTICE`](NOTICE)、[`NOTICE.md`](NOTICE.md)、[`CONTRIBUTORS.md`](CONTRIBUTORS.md)。隱私政策見 [`PRIVACY.md`](PRIVACY.md)。

Windows 版（`wingman/`）：MIT，Copyright © 2026 rezoch340 與 jev-chat 貢獻者，見 [`docs/licenses/jev-chat-windows/LICENSE`](docs/licenses/jev-chat-windows/LICENSE)、[`NOTICE`](docs/licenses/jev-chat-windows/NOTICE)（打包檔內為 `LICENSE-jev-chat-windows`、`NOTICE-jev-chat-windows`）。**打包後的 exe 內含 PySide6-Fluent-Widgets（GPLv3，非商用免費，商用需另購授權），發布包整體受 GPLv3 約束**；其他第三方元件的授權見該 NOTICE。發布的 zip 內保留 `LICENSE`、`NOTICE` 與 `LICENSE-jev-chat-windows`、`NOTICE-jev-chat-windows`；程式設定頁〈關於與授權〉與 Release 說明都寫明來源。

**致謝**：[Jev 聊天助手](https://github.com/jev-chat/jev-chat-jarvis)（Android 原版，Jev 判斷內核與題目來源）、[JevChat-Windows](https://github.com/jev-chat/jev-chat-windows)（Windows 版來源）、[RapidOCR](https://github.com/RapidAI/RapidOCR)（離線中文 OCR）、[windows-capture](https://github.com/NiiightmareXD/windows-capture)（Windows Graphics Capture 的 Python 綁定）、[PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets)（Windows 版介面元件）、[ML Kit](https://developers.google.com/ml-kit)（Android 離線 OCR）。

**免責聲明**：本專案只處理你自己裝置上、你自己有權查看的聊天。請在自己的裝置上自用，不要裝到別人的手機或電腦上讀別人的聊天。請遵守各聊天軟體的使用條款與當地法規；聊天軟體改版可能讓介面辨識失效。使用本專案造成的後果由使用者自行承擔。
