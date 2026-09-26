# 分岔登記表

本檔登記本 fork 對**上游持有檔案**的每一筆修改：上游原本就有這個檔案，本 fork 動了它。
新增的檔案（上游沒有對應版本，例如 `AGENTS.md`、`FORK.md`、`tools/` 底下的維護工具）不算
分岔，不登記在這裡；那些檔案的清單見 [`FORK.md`](../FORK.md)。

## 維護契約

**改動任何一個上游持有的檔案，就必須在這裡加一列。** 這件事由
[`tools/check_divergence.py`](../tools/check_divergence.py) 機器強制：它比對「上游基準
commit（`tools/upstream_baseline.json` 的 `reviewed_through`）到現在，哪些上游持有的檔案
被改過或刪過」與「這張表登記了哪些路徑」，兩邊對不上就非 0 退出。這個檢查接在
`tools/dev_check.ps1`、`.github/workflows/ci.yml` 與 `.github/workflows/upstream-check.yml`；
合約測試在 [`tests/test_fork_divergence.py`](../tests/test_fork_divergence.py)。

最後一欄「跟進上游時怎麼處理」寫成**可執行的判準**，同步上游時照欄位做決定，不必重新評估。
一列可以登記整個目錄（結尾 `/`）或 glob（含 `*`），用於整批刪除。

**全域分岔：App 介面文字繁體化（2026-09-25）。** `app/src/main` 內所有簡體中文字串與註解以 OpenCC `s2twp` 轉為繁體（台灣用語），
「接口」「對象」保留原詞；比對其他 App 介面文字的清單（暫時標題、已讀尾字、X 私信標籤）同時保留簡、繁兩種寫法；
`JevQuestions.kt` 的判斷題目不轉（校準過）。下表各列不再逐一註記此項；只因這項而分岔的檔案列在表尾。
**跟進上游時**：上游改到這些檔案的中文字串，合併後再對該檔跑一次 `s2twp`（同樣保留「接口」「對象」與比對清單）。

**全域分岔：接口預設白名單（2026-09-25）。** 維護者決定只內建 OpenRouter、Vercel、TypeSafe、OpenCode Zen 與自定義；博查 Jev（`jev.bocha.cn`）、DeepSeek（`api.deepseek.com`、`deepseek/*` 模型）、
阿里雲百鍊／通義（`dashscope.aliyuncs.com`、`qwen*` 模型）的預設、常數、說明與隱私政策連結全部移除；回覆與視覺預設模型改為 `google/gemini-2.5-flash`；
`Prefs.dropRemovedVendors()` 一次性把舊設定遷離這些服務。見 `docs/DECISIONS.md`。
**跟進上游時**：上游新增或修改白名單以外服務商的預設、模型或說明一律不收；同一 commit 的其他改動照收。

**全域分岔：產品名改為「對話副駕」／Chat Wingman（2026-09-25）。** 上游 NOTICE 不允許以「Jev 聊天助手」名稱暗示原作者出品，
`strings.xml` 的 `app_name`、`MainActivity` 首頁標題與說明、`KeepAliveService` 通知、`HttpJson` 的 OpenRouter `X-Title`、README／PRIVACY 標題改用本名（英文 Chat Wingman）。
**跟進上游時**：上游改到這些字串時保留本 fork 名稱；出處聲明（「基於 Jev 聊天助手…二次開發」）照舊。

| 上游檔案 | 上游原狀 | 本 fork 狀態 | 為什麼分岔 | 跟進上游時怎麼處理 |
|---|---|---|---|---|
| `README.md` | 簡中 README：介紹、截圖、平台支援（含微信、飛書、QQ）、FAQ、交流群、贊助、打賞。 | 全文改寫為繁中；與 `README.en.md` 段落一一對應；標明 LINE 為本 fork 原創、已移除微信、飛書、QQ；不收交流群、贊助、打賞。 | 公開入口以繁中為主；本 fork 產品範圍與上游不同。 | 上游改 README 時只把仍適用的**產品事實**（X 行為、權限步驟、限制）人工合併進本檔與 `README.en.md`，兩份同步；其餘不收。 |
| `CLAUDE.md` | 上游產品硬約束與大量微信／飛書／QQ 實測紀錄（簡中）。 | 改為只匯入 `AGENTS.md` 的薄檔；仍適用的硬約束與 X／OCR／知識庫背景整理進 `AGENTS.md`。 | fleet 慣例：`AGENTS.md` 為單一真相源；微信、飛書、QQ 內容已不適用。 | 衝突時保留本 fork 版本；上游新增的、與 X／OCR／知識庫有關的事實，人工整理進 `AGENTS.md`。 |
| `CHANGELOG.md` | 上游 1.0–1.4 的簡中更新日誌（多處微信說明）。 | 改為本 fork 的變更紀錄（Keep a Changelog），英文鏡像為 `CHANGELOG.en.md`；上游歷史指向上游 repo。 | 版本號改為 `上游主.次.fork 序號`，需要 fork 自己的紀錄。 | 衝突時保留本 fork 版本；上游新版的內容若被本 fork 採納，寫成本 fork 的一筆變更。 |
| `CONTRIBUTORS.md` | 上游三端（Android／macOS／Windows）維護者、平台支援表（含微信）與貢獻流程。 | 繁中；保留上游 Android 原作者與測試者署名，加上本 fork 維護者；移除微信平台表與 macOS／Windows 名單。 | 署名要保留，但平台範圍已不同。 | 上游新增 Android 貢獻者時補進「上游原作者」表；其餘不收。 |
| `PRIVACY.md` | 適用範圍為上游；預設 OpenRouter；連結指向上游與 chatjevs.com；截圖說明以飛書為例。 | 適用範圍改為本 fork；預設改 Vercel AI Gateway（加 Vercel 隱私政策連結）；連結改指本 fork；拿掉飛書例子與官網連結；移除 DeepSeek、阿里雲百鍊的預設與連結、公眾號聯絡方式，回覆預設改 Gemini。全文轉為繁體中文（s2twp）；新增第 11 節 Windows 版。 | 隱私權政策必須描述本 fork 實際行為。 | 上游改政策時逐段比對：資料處理方式的變更照收，網址、預設服務商與平台範圍維持本 fork 版本。 |
| `.gitignore` | Android／Python／IDE／金鑰忽略規則，並刻意追蹤 `apk/*.apk`。 | 刪除追蹤 `apk/*.apk` 的例外；尾端加 `# Fork maintenance (SanHsien)` 區塊。 | 本 fork 不附預建 APK；維護工具會產生報告與快取。 | 上游新規則合併在 fork 區塊之上；上游恢復 `!/apk/*.apk` 時不收。 |
| `apk/` | 上游預建的 release APK（含微信／飛書程式碼）。 | 刪除。改由 CI 上傳 debug APK。 | APK 內容與本 fork 程式碼不一致。 | 上游新增或更新 `apk/` 一律不收（`git rm` 解衝突）。 |
| `site/` | 上游官網（chatjevs.com）原始碼。 | 刪除。 | 本 fork 不架官網；使用上游網域會暗示由原作者背書。 | 上游改 `site/` 一律不收。 |
| `docs/acceptance.md` | 上游微信探針驗收標準。 | 刪除。 | 內容為微信專用。 | 上游再改一律不收。 |
| `docs/probe_spec.md` | 上游微信探針規格。 | 刪除。 | 內容為微信專用。 | 上游再改一律不收。 |
| `docs/v1.3-*.md` | 上游 v1.3 內部規劃與晨間檢查清單（大量微信／飛書內容）。 | 刪除。 | 上游內部工作文件；仍適用的事實已整理進 `AGENTS.md`。 | 上游再改一律不收。 |
| `docs/images/logo.png` | 上游吉祥物 logo。 | 刪除；README 改用本 fork 的 `docs/images/logo.svg`。 | 上游 NOTICE 要求不得以其名稱暗示原作者出品；維護者要求重新設計。 | 上游換 logo 不收。 |
| `docs/images/overlay.png` | README 截圖：微信群、簡中介面、DeepSeek。 | 刪除，README 移除截圖段。 | 內容是微信群與真人暱稱頭像，與本 fork（LINE、繁中、接口預設白名單）不符。 | 不收；本 fork 需要截圖時用 LINE 假資料重拍。 |
| `docs/images/settings.png` | README 截圖：簡中設定頁、OpenRouter + DeepSeek。 | 刪除。 | 同上。 | 同上。 |
| `docs/images/sponsors/` | 贊助商圖（含博查）。 | 刪除。 | README 未引用。 | 上游新增贊助圖一律不收。 |
| `app/src/main/res/drawable/ic_launcher_foreground.xml` | 白色對話框 + 三點。 | 改為與 `docs/images/logo.svg` 相同的對話框 + 星芒。 | App 圖示與 README logo 一致。 | 上游改圖示不收。 |
| `docs/images/wechat-*.png` | 微信群、公眾號 QR 圖。 | 刪除。 | 微信相關宣傳圖。 | 上游新增同類圖片一律不收。 |
| `docs/images/donate/` | 微信讚賞碼。 | 刪除。 | 微信相關。 | 同上。 |
| `docs/images/mascot/` | 微信吉祥物圖。 | 刪除。 | 微信相關。 | 同上。 |
| `tools/jev/TASK.md` | 要求先讀 `CLAUDE.md` 與 `docs/acceptance.md`，背景寫「掛在微信旁」。 | 改為先讀 `AGENTS.md`，背景改為 LINE、X 等聊天 App。 | 原本引用的文件已刪除。 | 上游改此檔時保留這兩句的本 fork 版本，其餘照收。 |
| `app/build.gradle.kts` | 套用 `kotlin.android` 外掛；`kotlinOptions`；簽章設定預設讀 `H:/android/keys/jev-release.properties`；versionCode `5`、versionName `1.4`；appcompat `1.7.0`、material `1.12.0`、constraintlayout `2.1.4`；無單元測試依賴。 | AGP 9 內建 Kotlin（頂層 `kotlin { compilerOptions }`）；簽章只在 `JEV_KEYSTORE_PROPS` 指定時啟用（採上游 PR #32）；versionCode `500`、versionName `1.4.0`；把 `LICENSE`／`NOTICE` 打包進 APK 的 `assets/legal/`（`LegalAssets` 任務，上游 NOTICE 要求再散布保留）；appcompat `1.8.0`、material `1.14.0`、constraintlayout `2.2.2`；`testImplementation("junit:junit:4.13.2")`（上游 PR #6／#21／#35 的測試需要）。 | AGP 9 遷移；Windows 路徑在 Linux／macOS 建置失敗；版本號公式；單元測試。 | 上游改版號時依公式重算；依賴取兩者較新者；保留無外掛 + 頂層 `kotlin {}` 與 `JEV_KEYSTORE_PROPS` 寫法；上游合併 #32 或自己完成 AGP 9 遷移後改用上游寫法。 |
| `build.gradle.kts` | AGP `8.7.3`、`kotlin.android` `1.9.24`。 | AGP `9.4.1`；移除 Kotlin 外掛宣告。 | AGP 9 拒絕 `kotlin.android` 外掛。 | 上游升到 AGP ≥ 9.4.1 就採用上游並刪除本列；上游仍在 8.x 時保留本 fork 版本。 |
| `gradle/wrapper/gradle-wrapper.properties` | Gradle `8.9`。 | Gradle `9.7.1`。 | AGP 9 需要 Gradle 9。 | 與 `build.gradle.kts` 同進退：上游升到 ≥ 9.7.1 就採用上游並刪除本列。 |
| `gradle/wrapper/gradle-wrapper.jar` | Gradle 8.9 的 wrapper jar。 | Gradle 9.7.1 產生的 wrapper jar。 | 同上，由 `gradle wrapper` 產生。 | 衝突時以 `gradle wrapper --gradle-version <較新版>` 重新產生，不手動挑選。 |
| `gradlew` | Gradle 8.9 的啟動腳本，模式 `100644`。 | Gradle 9.7.1 的版本，模式 `100755`。 | 同上。 | 同上，重新產生。 |
| `gradlew.bat` | Gradle 8.9 的 Windows 啟動腳本。 | Gradle 9.7.1 的版本。 | 同上。 | 同上，重新產生。 |
| `app/src/main/AndroidManifest.xml` | 無障礙服務註冊為 `com.google.android.accessibility.selecttospeak.SelectToSpeakService`，設定 `@xml/config_disguised`。 | 直接註冊 `.capture.ChatCaptureService`，設定 `@xml/config_accessibility`。 | 偽裝系統元件名只為了讓微信吐出節點樹；微信已移除。 | 上游改 Manifest 時照收，但服務名與設定檔名維持本 fork 版本。 |
| `app/src/main/java/com/google/android/accessibility/selecttospeak/SelectToSpeakService.kt` | 偽裝成系統元件的無障礙服務子類別。 | 刪除。 | 同上。 | 上游再改一律不收。 |
| `app/src/main/res/xml/config_disguised.xml` | 無障礙服務設定（檔名帶 disguised）。 | 改名為 `config_accessibility.xml`（本 fork 新增檔），描述字串改用 `a11y_desc`。 | 同上。 | 上游改此檔的屬性時，同步套用到 `config_accessibility.xml`。 |
| `app/src/main/res/values/strings.xml` | `a11y_desc_disguised`。 | 改名為 `a11y_desc`（文字不變）。 | 同上。 | 上游新增字串照收；此鍵名維持本 fork 版本。 |
| `app/src/main/java/com/jev/probe/capture/ChatCaptureService.kt` | `open class`；`adapters` 含 QQ、X、飛書；微信短路提示；飛書專用氣泡重量測；未回報服務連線狀態；非同步分析結果不綁定發起的對話，單一 `analyzing` 旗標由兩段非同步共用，暫時標題直接沿用上一個標題。 | 非 open；`adapters` = LINE、X；微信改為 `BLOCKED_PKGS`；氣泡重量測改由適配器提供；OCR 尾字另去除 `已讀`／`未讀`／`既読`；`CaptureHealth` 回報（上游 PR #35）；每次分析帶 run id，結果與填入只作用於原對話，分析中到達的新訊息結束後補跑（上游 issue #61）；暫時標題只在同一對話時沿用；未開自動分析時對方新訊息只顯示懸浮球，點懸浮球經 `onPanelOpened` 才解析分析對象並呼叫 `showPending()`（半自動）。 | 移除微信、飛書、QQ；微信封鎖是保護措施（上游 issue #42／#46／#47／#52／#59）；LINE 讀回條；首頁健康狀態；結果錯置與填錯聊天室（#61）。 | 上游改此檔時保留：`BLOCKED_PKGS`、無飛書／QQ 適配器、LINE 註冊行、適配器提供的重量測、run 綁定與暫時標題規則；其餘照收。移除 `BLOCKED_PKGS` 須先經維護者同意（`AGENTS.md` 硬約束 8）。 |
| `app/src/main/java/com/jev/probe/capture/ChatAppAdapter.kt` | QQ／微信／飛書／X 四個適配器與微信標題、飛書氣泡工具函式。 | 刪除 `QQAdapter`、`WeChatAdapter`、`findWeChatTitle`、`FeishuAdapter`、`collectFeishuBubbleRects`；`XAdapter` 保留發件人名稱為 `speaker`；檔尾新增 `LineAdapter`／`A11yUiNode`（本 fork 原創，規則在 `LineExtractor.kt`，群組時設定面板提示）。 | 移除微信、飛書、QQ；新增 LINE；群組分辨發言者。 | 上游改 X 適配器時照收並保留 `speaker`；上游再改微信／飛書／QQ 部分不收；保留檔尾 `LineAdapter`／`A11yUiNode`。 |
| `app/src/main/java/com/jev/probe/MainActivity.kt` | 首頁寫「已支援 QQ、X、飛書」；無障礙檢查比對偽裝元件名（字串包含）；只看授權不看服務是否連線；隱私權連結指 chatjevs.com。 | 改為「已支援 LINE、X」；比對 `ChatCaptureService`（`unflattenFromString` 正規化，完整與短名都認得）；每秒檢查 `CaptureHealth` 區分「已授權」與「已連線」（採上游 PR #35）；隱私權連結指本 fork。 | 服務名與產品範圍改變；無障礙斷線後首頁不該仍顯示就緒。 | 上游改首頁時保留平台範圍、服務名與連結的本 fork 版本；上游合併 #35 後健康檢查部分改用上游寫法。 |
| `app/src/main/java/com/jev/probe/SettingsActivity.kt` | 回覆／視覺預設無 Vercel；OCR 說明以飛書為例；隱私與 repo 連結指上游。 | 回覆與視覺各加 Vercel 預設；移除博查 Jev、DeepSeek 官方、通義相容 pills 與博查推廣區塊、DeepSeek 視覺防呆；OCR 說明改為通用敘述；連結改指本 fork；「關於與隱私」加上游出處聲明、「上游專案」與「授權條款與聲明」（讀 APK 內的 LICENSE／NOTICE）。 | Vercel 為本 fork 預設；飛書移除；接口預設白名單；上游 NOTICE 要求「關於」頁註明出處。 | 上游改 pills 時，在「自定义」前重新插入 Vercel、不收白名單以外的預設；保留出處聲明與兩顆按鈕；上游自己加了 Vercel 預設就改用上游版本。 |
| `app/src/main/java/com/jev/probe/KnowledgeActivity.kt` | `appLabel` 對應 QQ／飛書／X。 | 只剩 LINE（`jp.naver.line.android`）與 X。 | 移除飛書與 QQ、加入 LINE。 | 上游新增 App 標籤照收；QQ、飛書兩行不收。 |
| `app/src/main/java/com/jev/probe/core/Prefs.kt` | 新安裝預設 OpenRouter。 | 新增 `seedVercelDefaultIfFresh()` 與 `VERCEL_*` 常數：全新設定一次性三路皆 Vercel；移除 `PROVIDER_BOCHA`、`DEEPSEEK_*`、`DASHSCOPE_*` 與 `unseedBochaDefaultIfUnconfigured()`，改為 `dropRemovedVendors()` 一次性遷移；`DEFAULT_REPLY_MODEL`／`DEFAULT_VISION_MODEL` 改 `google/gemini-2.5-flash`；`autoAnalyze` 預設 `false`，`switchToSemiAutoOnce()` 升級時關一次。 | 維護者主要用 Vercel；已有設定不動；接口預設白名單。 | 上游改 `init` 時保留 seed 呼叫排在最後；上游自己改成 Vercel 預設並涵蓋三路時刪除本 fork 的 seed。 |
| `app/src/main/java/com/jev/probe/core/ChatModels.kt` | `Msg(side, text)`；`BubbleRect` 註解以飛書為例；`signature()` 只看最後 6 則訊息。 | `Msg` 加 `speaker: String? = null`（群組發言者）；註解改為通用敘述；`signature()` 納入會話標題並以長度前綴分隔欄位（採上游 PR #6）。 | 群組分辨發言者；移除飛書；切換聯絡人不沿用舊分析。 | 保留 `speaker` 欄位（預設 null，上游呼叫端不受影響）；上游合併 #6 後簽章部分改用上游版本。 |
| `app/src/main/java/com/jev/probe/core/kb/KbModels.kt` | 聯絡人註解以微信／QQ／飛書與 `com.tencent.mm` 為例。 | 改為 LINE／X 與 `jp.naver.line.android`。 | 同上。 | 照收上游，只保留這段註解的本 fork 版本。 |
| `app/src/main/java/com/jev/probe/overlay/OverlayController.kt` | 兩處註解提到微信。 | 改為通用敘述；新增 `showPending()`（半自動：分析對象 + 「分析」「略過」，不自己展開）與 `onPanelOpened`（點懸浮球時才解析分析對象）。 | 同上；維護者要求省 token。 | 照收上游，保留 `showPending()`。 |
| `app/src/main/java/com/jev/probe/jev/VisionClient.kt` | 註解指向 `docs/v1.3-plan.md`；註解提到 DeepSeek／DashScope；`supportsVision()` 擋 `api.deepseek.com`。 | 拿掉已刪除文件的引用；註解改為通用敘述；刪除 `supportsVision()`。 | 文件已刪除；DeepSeek 預設已移除。 | 照收上游，不收 DeepSeek／DashScope 相關判斷。 |
| `app/src/main/java/com/jev/probe/capture/ocr/OcrEngine.kt` | 註解指向 `docs/v1.3-plan.md`。 | 拿掉已刪除文件的引用。 | 同上。 | 同上。 |
| `app/src/main/java/com/jev/probe/jev/ReplyClient.kt` | 備援解析會吃掉回覆開頭的數字；對話一律標「我／对方」。 | 改呼叫 `ReplyLineParser.parse`（採上游 PR #21）；群組時每行標發言者並指明回覆對象。 | 「1.5 小時」開頭數字被刪；群組分辨發言者。 | 上游合併 #21 後解析部分改用上游版本；保留群組標註（只在 `isGroupChat()` 時生效）。 |
| `app/src/main/java/com/jev/probe/capture/KeepAliveService.kt` | `startForeground` 失敗時沒有回報。 | 失敗時記到 `CaptureHealth` 並 `stopSelf()`（採上游 PR #35）。 | 首頁要能顯示保活失敗。 | 上游合併 #35 後採用上游版本並刪除本列。 |
| `app/src/main/java/com/jev/probe/jev/JevQuestions.kt` | `buildState` 每則訊息只有 `from`／`text`。 | 群組時加 `name`、`type`、`participants`、`focus_person`、`note`；一對一 state 不變。 | 群組分析對象。 | 上游改 `buildState` 時照收，再把群組區塊接回（只在 `isGroupChat()` 時加欄位）；題目文字不動。 |
| `app/src/main/java/com/jev/probe/capture/ocr/ScreenCapture.kt` | 截圖失敗訊息為簡中。 | 轉為繁體（見上方「全域分岔」）。 | 介面文字繁體化。 | 上游改中文字串時合併後重跑 `s2twp`；其餘照收。 |
| `app/src/main/java/com/jev/probe/core/kb/KbSelfCheck.kt` | 自檢訊息為簡中。 | 轉為繁體（見上方「全域分岔」）。 | 介面文字繁體化。 | 上游改中文字串時合併後重跑 `s2twp`；其餘照收。 |
| `app/src/main/java/com/jev/probe/core/kb/KbStore.kt` | 聯絡人提示為簡中。 | 轉為繁體（見上方「全域分岔」）。 | 介面文字繁體化。 | 上游改中文字串時合併後重跑 `s2twp`；其餘照收。 |
| `app/src/main/java/com/jev/probe/jev/HttpJson.kt` | 錯誤訊息的接口名稱為簡中。 | 轉為繁體（見上方「全域分岔」）。 | 介面文字繁體化。 | 上游改中文字串時合併後重跑 `s2twp`；其餘照收。 |
| `app/src/main/java/com/jev/probe/jev/JudgeClient.kt` | 錯誤訊息為簡中。 | 轉為繁體（見上方「全域分岔」）。 | 介面文字繁體化。 | 上游改中文字串時合併後重跑 `s2twp`；其餘照收。 |
