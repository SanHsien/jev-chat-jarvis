# Fork 決策紀錄 (DECISIONS.md)

本文件記錄本 fork 相對於上游的所有架構決策、取捨與已審核變更。

## 2026-09-24: Fork 建立與 Windows 開發環境初始化

- **背景**：Fork `jev-chat/jev-chat-jarvis`，建立 Windows-first 治理與自動化驗證機制。
- **基準版本**：fork 點為上游 `main` `a3026e2`（`v1.4` 之後 7 個文件類 commit，已隨 fork 一併納入）；
  `reviewed_through` 記 `a3026e2`、`reviewed_release` 記 `v1.4`。
- **治理決策**：
  1. 對外只打維護者的 repo（`SanHsien/jev-chat-jarvis`），嚴禁自動向上游開 PR 或 push。
  2. （2026-09-24 稍後推翻，見下方「移除微信與飛書」）上游 `CLAUDE.md` 原樣保留，fork 規則放 `AGENTS.md`，由 `.claude/CLAUDE.md` 匯入。
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

## 2026-09-25: `main` 改為單一根 commit

- **背景**：先前的 squash commit 以兩個上游（`45a0876`、`946d3d1`）為父，GitHub 因而顯示 143 個 commit（上游 83 + 60）。維護者要求只留本 fork 的歷史。
- **決策**：`main` 改為沒有父的單一根 commit。上游基準只以 SHA 記錄（`tools/upstream_baseline.json`、`docs/DIVERGENCE-windows.md`）；
  `check_divergence.py` 在本機沒有基準 commit 時自動 `git fetch <上游> <SHA>`（`fetch_base_commit()`，有測試）。上游改寫歷史時不再需要 `merge -s ours`。
- **代價**：`git merge upstream/main` 沒有共同祖先，不能直接合併；本 fork 本來就逐筆分診後手動套用，影響不大。

## 2026-09-25: Android 預設改為半自動分析

- **背景**：維護者認為每則對方訊息都自動分析會浪費 token；很多訊息（貼圖、照片、「好」「哈哈」）不需要分析。
- **決策**：`Prefs.autoAnalyze` 預設改 `false`，升級時由 `switchToSemiAutoOnce()` 關掉一次（之後使用者再打開就尊重）。
  偵測到對方新訊息時 `OverlayController.showPending()` 展開面板，顯示分析對象（`focusSpeaker()`，沒有就用會話標題）與最新一則訊息，
  按「分析」才走 `onManualAnalyze`，按「略過」收起；貼圖／照片另提示「通常不必分析」。OCR 模式自動分析仍需兩個開關都開。
- **取捨**：多一次點擊換省 token；想要全自動的人到設定打開即可。

## 2026-09-25: 匯入 Windows 版（`wingman/`）

- **背景**：維護者要把上游 Windows 版（`jev-chat/jev-chat-windows`）fork 進本 repo。原版只支援微信（截取 `Weixin.exe` 視窗並自動貼上），
  與硬約束 7 衝突；起草預設多為白名單以外的來源；發布包含 GPLv3 元件。
- **決策（維護者選 A）**：`git subtree add --prefix=windows`（不 squash，保留歷史）；刪除原版目標聊天軟體的採集、填入、探針與宣傳圖，
  改為只認 `LINE.exe`；起草改白名單；介面 `s2twp`；產品名與 exe 改為「對話副駕」／`chat-wingman`。
- **同日補充**：說明整合進根目錄 README 與 PRIVACY（不只放在 `windows/`）；Windows zip 附在與 APK 同一個 Release（repo 只留最新 Release，不另開）；檢查更新改查本 repo。
- **未驗證**：LINE 電腦版的訊息區定位、我／對方顏色判斷、輸入框位置都沿用原版規則，未實機驗證；
  驗證前 `fill.py` 只寫剪貼簿。需要維護者在 Windows 上實際跑一次（可開「除錯檢視」看辨識框）。
- **再補充（維護者要求「整個融合進 repo」）**：不再保留 `windows/` 子專案結構：`app/`、`core/`、`main.py` 成為 `wingman/` 套件（`python -m wingman`，import 改 `wingman.app`／`wingman.core`），
  `requirements.txt` → `requirements-windows.txt`，`jev.spec`／`build.bat`／`demo.py` → `tools/windows/`，上游 `LICENSE`／`NOTICE` → `docs/licenses/jev-chat-windows/`，
  `.gitignore` 併入根目錄，README 刪除（說明在根目錄 README），圖示改由新 logo 產生（`docs/images/wingman.ico`）。因檔案搬家，跟進上游改用 `git diff` 比對後手動套用（見 `DIVERGENCE-windows.md`）。
- **根目錄工具**：ruff 排除 `wingman/`、`tools/windows/`（跟上游風格）；`.github/workflows/windows.yml` 在 windows-latest 跑自測並打包 artifact。

## 2026-09-25: 接口預設白名單；補齊上游出處標示

- **背景**：維護者決定接口預設只保留 OpenRouter、Vercel、TypeSafe、OpenCode Zen 與自定義，其餘服務商的預設、模型相關程式碼與說明移除。
  上游 NOTICE 要求再散布時保留 LICENSE／NOTICE，並在「關於」頁、說明文件或發布頁註明出處，且不得暗示原作者出品。
- **決策**：
  1. 移除博查 Jev、DeepSeek（官方與 `deepseek/*` 模型）、阿里雲百鍊／通義（含 `qwen*` 模型）的預設、常數與說明；
     回覆／視覺預設模型改 `google/gemini-2.5-flash`（已在 Vercel 目錄，由 `check_vercel_models.py` 每週確認）。
  2. `Prefs.dropRemovedVendors()` 一次性遷移舊設定：指向已移除主機的接口改 Vercel 並清掉該接口金鑰（金鑰屬於已移除的服務）；
     OpenRouter／Vercel 上的 DeepSeek／Qwen 模型換成該接口預設；自訂接口的模型尊重使用者，不動。不在執行期封鎖這些主機。
  3. 上游 README 截圖（微信群、真人暱稱頭像、簡中、DeepSeek）與吉祥物 logo 刪除，改用本 fork 的 `logo.svg`，App 圖示同步。
  4. 出處：README 開頭加「基於 Jev 聊天助手（連結）二次開發」；設定頁「關於與隱私」加出處、上游連結與 APK 內附的 LICENSE／NOTICE；
     release 說明自動附出處。
- **改名（2026-09-25 維護者決定）**：App 名稱、首頁標題、常駐通知、README 標題改為「LINE 對話副駕」（英文 LINE Chat Copilot），同日再改為不限 LINE 的「對話副駕」（英文 Chat Wingman；避開 Copilot 商標），
  不再以上游名稱當產品名；套件名 `com.jev.probe`、repo 名與 APK 檔名不變（可覆蓋升級）。「Jev」仍指判斷模型，出處聲明照舊寫上游名稱。
- **OpenCode Zen 保留**：在白名單內。
- **對外措辭**：文件只陳述白名單，不寫排除理由、不點名其他服務商（維護者要求，2026-09-25）。

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

## 2026-09-24: Dependabot #1／#2 以合併驗證方式納入（AGP 9、Gradle 9）

- **問題**：Dependabot 把 AGP＋Kotlin（#1）與 Gradle wrapper＋AndroidX（#2）拆成兩個 PR，各自都不可能綠：
  AGP 9 需要 Gradle 9，而 Gradle 9 跑不動 AGP 8.7。兩個 PR 的 CI 也跑在修好 Linux 建置之前的舊 main 上。
- **驗證**：在暫時分支 `verify/gradle-deps` 合併兩者，CI 報 `The 'org.jetbrains.kotlin.android' plugin is no
  longer required for Kotlin support since AGP 9.0`；移除該外掛、`kotlinOptions` 改為頂層
  `kotlin { compilerOptions }` 後 `assembleDebug` 通過。
- **決策**：以一個 commit 併入 main，六個上游檔案登記進 `docs/DIVERGENCE.md`；關閉 #1、#2；
  Dependabot 的 gradle 改成單一群組，避免再拆出兩個必紅的 PR。
- **未驗證**：只驗證到編譯與打包；沒有在真機跑過升級後的 APK。

## 2026-09-24: 移除微信與飛書、LINE 為本 fork 主線、版本號

- **決策**（維護者指示）：刪除微信與飛書的適配器、相關程式碼與說明；README 只留繁中與英文且內容一致；
  LINE 支援明示為本 fork 原創。
- **連帶處理**：
  - 無障礙服務原本註冊成 `com.google.android.accessibility.selecttospeak.SelectToSpeakService`，
    這個偽裝只為了讓微信吐出節點樹；改為直接註冊 `com.jev.probe.capture.ChatCaptureService`，設定檔改名
    `config_accessibility.xml`。舊版使用者升級後需要重新開啟無障礙。
  - 微信沒有了適配器就會變成「未適配 App」，手動 OCR 會截它的畫面，而上游實測這會觸發微信的帳號風控。
    因此保留 `BLOCKED_PKGS = setOf("com.tencent.mm")`：不顯示懸浮球、不讀、不截圖。這是保護措施，不是微信支援。
  - 逐氣泡 OCR（`BubbleRect`）原本只給飛書用，但 LINE 若是「氣泡畫出來」的情況也需要，保留為通用機制，
    重新量測改由對應適配器的 `extract` 提供。
  - 上游 `CLAUDE.md`（大量微信／飛書實測紀錄）改寫為只匯入 `AGENTS.md`；仍然適用的產品硬約束與 QQ／X／OCR／知識庫背景整理進 `AGENTS.md`。
  - 刪除上游的 `apk/`（內含微信／飛書的預建 APK）、`site/`（上游官網）、`docs/{acceptance,probe_spec,v1.3-*}.md`（上游內部規劃）、
    微信群／公眾號／打賞 QR 圖片。CI 改為上傳 debug APK 當作取得 APK 的方式。
  - `CHANGELOG.md` 改為本 fork 的雙語變更紀錄；`CONTRIBUTORS.md` 保留上游原作者署名並加上本 fork 維護者。
  - `check_divergence.py` 支援目錄（結尾 `/`）與 glob 登記列，讓整批刪除用一列登記。
- **版本號**：`versionName` = `上游主.次.fork 序號`（`1.4.0` 起），`versionCode` = `上游 versionCode × 100 + fork 序號`（`500`）。

## 2026-09-24: 再移除 QQ、取消微信封鎖

- **決策**（維護者指示）：移除 QQ 適配器與說明；取消 `BLOCKED_PKGS`（上一節保留的微信封鎖作廢）。
- **影響**：微信、QQ、飛書現在都是「未適配 App」：懸浮球照常出現，可以手動「截屏識別一次」。
  上游實測截取微信畫面可能觸發其帳號風控；是否在微信裡使用手動 OCR，由使用者自行判斷。
- 目前自動模式只剩 X；LINE 自動模式等真機驗證。

## 2026-09-24: 上游分診、Release 發佈

- 上游全部分支（6）、PR（19）、issue（35）逐筆分診，結論與重看條件記在 `docs/UPSTREAM.md`〈分診紀錄〉；
  水位推到 PR／issue #55。
- 採用上游未合併 PR：#6（會話去重含標題）、#21（回覆開頭數字）、#32（簽章路徑）、#35（服務連線健康）。
  連同上游附的 JUnit 測試併入，CI 的 Android job 加跑 `testDebugUnitTest`。
- 暫緩：#22、#23、#45（衝突面大且需真機），各自寫明重看條件。
- 因為取消了微信封鎖，而上游 issue #42／#47／#52 回報截取微信會導致其防截圖，README 加上警告。
- Release：`release.yml` 以 tag 或手動版本號觸發，tag 必須等於 `versionName`；有簽章 secrets 發正式 APK，
  否則發 debug APK。`v1.4.0` 已以 debug APK 發佈。

## 2026-09-24: 恢復微信封鎖；有使用者回報支撐的保護措施不得未經確認移除

- **決策**（維護者指示）：恢復 `BLOCKED_PKGS = setOf("com.tencent.mm")`，1.4.2 發佈。
- **檢討**：前一輪依「不用設微信封鎖」直接移除，只在事後的報告裡提到風險。維護者要求：
  凡是有上游使用者回報支撐的保護措施，移除或放寬之前要先說明風險與出處、取得明確同意。已寫進 `AGENTS.md` 硬約束 8。

## 2026-09-25: 完成 LineAdapter

- **依據**：維護者提供的 LINE 1:1 聊天室 `uiautomator dump`（1440×3120，繁中介面）。節點未混淆、正文有文字，走「讀節點」路線，不需 OCR。
- **設計**：規則抽到 `LineExtractor`（只依賴 `UiNode` 介面），`LineAdapter` 包裝 AccessibilityNodeInfo；
  如此能用 dump 檔在 JVM 上測試。測試資料保留 id、層級與座標，姓名與內容換成假資料（公開 repo）。
- **「我／對方」**：用訊息列內的標記節點判斷，不用頭像（同一人連續第二則沒有頭像）；沒有標記才看幾何位置。
- **照片／貼圖**：以「[照片]」「[貼圖]」帶入，讓判斷知道對方傳了東西；對方最後傳貼圖也會觸發分析。
- **未驗證**：群組聊天（可能有發送者名稱節點）、其他語言介面、檔案與語音訊息、實機填入。

## 2026-09-25: 正式簽章啟用、群組聊天的現況

- 維護者在本機用 `tools/new_signing_key.ps1` 產生 RSA 4096 金鑰（`%USERPROFILE%\jev-signing\`）並寫入 4 個 `JEV_*` secrets；
  v1.4.3 是第一個正式簽章的 Release。金鑰備份由維護者負責。
- 群組聊天：上游沒有群組專屬邏輯（上游 README：「群聊按一對一分析，『對方』與關係設定對群聊不準」），
  所有非我方訊息一律當成同一個「對方」，不記發送者。本 fork 的 `LineExtractor` 目前同樣如此，群組畫面也尚未 dump 驗證。

## 2026-09-25: 群組聊天分辨發言者

- **做法**：`Msg` 加 `speaker`；LINE 從頭像 content-desc 取名、連發沿用、我方訊息後重置（寧可未知也不猜錯）；X 用發件人名稱。
  `core/GroupChat.kt` 判定群組（≥2 位具名發言者或標題帶人數）與分析對象（對方最新一則的發言者）。
- **Jev 判斷**：只有群組才在 state 加 `name`、`participants`、`focus_person` 與一句英文說明（「the other person」指 focus_person）；
  一對一 state 與校準時逐字相同，題目本身不改。
- **未驗證**：沒有 LINE 群組的真機 dump；頭像 content-desc 的格式是依 1:1 dump 推定群組相同。拿到群組 dump 後要加測試案例。

## 2026-09-25: 上游第二輪分診、#61 修正、repo 只留 main 與最新 release

- 上游第二輪分診記在 `docs/UPSTREAM.md`（水位 #63）：上游 `main` 新 commit 全是文件／官網，不採用；
  上游關閉了多數舊 PR，已採用的 #6／#21／#32／#35 轉為長期分岔。
- 修正上游 issue #61（1.4.5）：分析 run id 綁定對話、候選只填進原對話、分析中的新訊息補跑、暫時標題不借用別人的名字。
- 維護者指示 repo 只留 `main`、最新 release 與其 tag：新增 `repo-cleanup.yml`（手動或發版後自動）；
  開著 PR 的分支（如 Dependabot）保留並提示，因為刪掉會讓 PR 被關閉。之後不再推送工作分支。

## 2026-09-25: 上游改寫歷史，重新錨定基準

- 上游 force-push 改寫了整段歷史：本 fork 的基準 `a3026e2` 已不在上游，`v1.4` tag 也指向新歷史的 `4ff8407`。
  新歷史中 `45a0876`（「docs: 在安装说明中明确 ARM64 架构要求」）與 `a3026e2` 的 tree 完全相同。
- 處理：`git merge -s ours --allow-unrelated-histories 45a0876`（檔案不變，只讓新歷史成為祖先），
  `reviewed_through` 改為 `45a0876`；審核的版本仍是 `v1.4`，分岔登記的比對結果不變（tree 相同）。
- `check_upstream_updates.py` 新增 `history_rewritten()`：基準不在上游歷史上時直接報錯並說明處理方式，
  不再把上游整段歷史列成待審。
