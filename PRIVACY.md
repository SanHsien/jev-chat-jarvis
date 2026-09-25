# 隱私政策

**對話副駕在你的裝置上讀取你正在看的聊天，把內容發給你自己配置的模型接口做判斷和起草回覆。作者不運營伺服器，收不到你的任何資料。**

版本 v1.1，生效日期 2026-09-25。適用範圍：本 fork [SanHsien/jev-chat-jarvis](https://github.com/SanHsien/jev-chat-jarvis) 的 Android 應用與 Windows 版（`wingman/`，見第 11 節）。上游 [jev-chat/jev-chat-jarvis](https://github.com/jev-chat/jev-chat-jarvis) 及其姊妹專案是各自獨立的倉庫和安裝包，不在本政策範圍內。

如果你更習慣先看結論：本專案**不是**"零資料收集"產品——它確實會把你正在看的聊天文字發給一個第三方模型接口，但那個接口地址是你自己在設定裡填的，不是作者的伺服器。除此之外的資料只留在你手機裡，刪應用或點一鍵清空都能刪乾淨。下面逐項說清楚"發了什麼、發給誰、什麼時候發、存在哪、怎麼刪"。

---

## 1. 一句話總覽

- 會離開你裝置的，只有「用於生成判斷和回覆」這一批聊天文字和背景資訊，且只發往**你自己在設定頁填寫的模型接口地址**。
- 作者不運營任何後端伺服器，程式碼裡也沒有向作者或任何固定第三方回傳資料的邏輯；你的聊天內容作者看不到，也拿不到。
- 截圖本身從不上傳，識別文字（OCR）全部在手機本地完成。
- 金鑰、設定、知識庫、聊天曆史都只存在手機本地的 App 私有目錄，其它 App 讀不到；解除安裝即清空。
- 無廣告、無第三方統計 SDK、不用 Cookie 或廣告識別符號、不讀通訊錄、不讀位置、不讀其它 App 列表。

## 2. 會離開你裝置的資料

只發往一個地方：**你自己在設定頁配置的模型接口地址**（全新安裝預設是 Vercel AI Gateway，你可以改成 OpenRouter、TypeSafe 直連、OpenCode Zen，或任意 OpenAI 相容地址）。作者的伺服器不在這條鏈路上，作者收不到、也看不到這些內容。

| 接口 | 預設服務商（可自行更換） | 每次傳送的內容 | 觸發時機 |
|---|---|---|---|
| 判斷接口 | Vercel AI Gateway 轉發 TypeSafe Jev | 當前聊天視窗最近 10 條訊息的文字與方向（我方/對方）+ 你自己填寫的關係描述 +（若開啟知識庫）命中的筆記與聯絡人備註 +（若開啟歷史記錄）該聯絡人最近 N 條歷史訊息（N 預設 30，可調 0–100） | 你觸發一次分析（自動或手動） |
| 回覆接口 | Vercel AI Gateway 上的 Google Gemini 2.5 Flash | 同一批最近 10 條訊息拼成的對話文字 + 同一份背景資訊 + 生成提示詞 | 判斷完成後起草候選回覆時 |
| 視覺接口 | 可配置，預設與判斷接口一致 | 僅在你於設定頁主動點選「測試視覺」時，傳送一張 1×1 白色測試圖；**不在日常採集主路徑裡** | 你手動點「測試視覺」 |

API 金鑰會作為請求頭（`Authorization`）隨對應請求發給你自己配置的那個接口，只用於身份校驗，不發往其它任何地方。

**不會傳送的內容**：截圖本身（識別文字在手機本地完成，見第 4 節）、通訊錄、裝置識別符號、位置資訊、其它 App 的列表或使用情況。

模型服務商拿到這些內容後如何處理，由它們各自的隱私政策決定，需要你自己去看：

- Vercel：https://vercel.com/legal/privacy-policy
- OpenRouter：https://openrouter.ai/privacy
- Google（Gemini，經 Vercel 或 OpenRouter 轉發）：https://policies.google.com/privacy
- OpenCode Zen：以其官網公示的隱私政策為準
- TypeSafe：以其官網公示的隱私政策為準

如果你自己填的是別的接口地址，那家服務商的政策同樣適用，作者無法替它們承諾任何事。

## 3. 只存在本機的資料

以下內容全部存放在 App 的私有目錄（`/data/data/<包名>/`），其它 App 無法訪問；應用私有目錄內的資料不會隨任何背景同步離開手機。

| 資料 | 用途 | 存放位置 | 保留時長 | 如何刪除 |
|---|---|---|---|---|
| API 金鑰、三路接口地址與模型名 | 連線你自己配置的模型服務 | SharedPreferences | 直到你修改或清除 | 設定頁裡改寫，或解除安裝應用 |
| 關係描述、會話白名單、各項開關、懸浮窗位置與透明度 | 記住你的個性化配置 | SharedPreferences | 直到你修改 | 設定頁裡改，或解除安裝應用 |
| 知識庫筆記（標題、內容、標籤） | 你手動建的背景資料，供判斷時檢索引用 | `filesDir/kb/notes.json` | 直到你刪除 | 設定頁「清空知識庫與歷史」，或逐條刪除 |
| 聯絡人檔案（名稱、別名、關係、備註） | 你手動建的聯絡人背景資訊 | `filesDir/kb/contacts.json` | 直到你刪除 | 同上 |
| 聊天曆史 | 供判斷時參考該聯絡人過往對話（預設關閉） | `filesDir/kb/logs/<聯絡人>.json` | 每位聯絡人最多保留 300 條，開啟後才開始記錄 | 設定頁關閉該開關不再新增，「清空知識庫與歷史」一鍵清空 |

設定頁的「清空知識庫與歷史」會刪除 `kb` 目錄下的全部內容，不影響金鑰與其它設定；解除安裝應用會連同上述所有資料一起刪除，沒有云端備份。

日誌（logcat）只輸出訊息條數、字元長度、異常類名這類除錯資訊，**不輸出聊天正文**。

## 4. 權限與用途

| 權限 | 用途 | 不做什麼 |
|---|---|---|
| 無障礙服務 | 讀取當前聊天視窗的文字，把選中的回覆填進輸入框 | 不點傳送鍵，不操作轉賬/紅包/收款，不讀取其它應用的資料庫 |
| 截圖能力（無障礙服務附帶） | 控制元件樹讀不到正文時，擷取當前視窗做本地 OCR | 截圖只在記憶體中處理，識別完即釋放，不儲存、不上傳 |
| 懸浮窗 | 在聊天上方顯示分析面板 | 不採集其它應用介面 |
| 網路 | 訪問你自己配置的模型接口 | 不連線作者的任何伺服器，無遙測、無埋點上報 |
| 前臺服務 + 通知 | 保持服務不被系統凍結、清理 | 不推送營銷通知 |

## 5. 我們不做什麼

- 不自動傳送訊息：程式只把候選回覆填進輸入框，最後一步永遠由你手動點傳送。
- 不碰轉賬、紅包、收款相關操作。
- 只處理你自己裝置上、你自己有權檢視的聊天，不處理其它人的裝置。
- 無廣告、無第三方分析或統計 SDK（不含 Google Analytics、Firebase、友盟等）、不使用 Cookie 或廣告識別符號。
- 作者不運營任何伺服器，不接收、不留存、不出售、不用於訓練任何模型你的聊天內容——因為這些內容壓根不經過作者。
- 開源：以上每一條說法，都可以在 GitHub 倉庫裡對照原始碼核實：https://github.com/SanHsien/jev-chat-jarvis

## 6. 你的控制權

- **關閉歷史記錄**：設定頁裡關掉「記錄聊天曆史」開關，之後不再新增；已有記錄仍在本機，需手動清空。
- **清空知識庫與歷史**：設定頁「清空知識庫與歷史」一鍵刪除 `kb` 目錄全部內容。
- **更換或自建接口**：判斷、回覆、視覺三路接口地址、金鑰、模型名都可以在設定頁單獨改成你信任的服務商，甚至自建的 OpenAI 相容閘道器。
- **只用手動分析**：關閉自動分析開關後，只有你主動點選才會觸發一次判斷/生成，不會在背景持續讀取。
- **會話白名單**：只對你加入白名單的會話生效，未加入的聊天不會被讀取和分析。
- **解除安裝即清空**：解除安裝應用會刪除本機儲存的全部資料（金鑰、設定、知識庫、歷史），沒有云端賬號或備份需要額外登出。

## 7. 第三方模型服務商

你在設定頁填寫的接口地址決定了聊天內容最終發給誰。內建預設包括 Vercel AI Gateway、OpenRouter、TypeSafe（直連）、OpenCode Zen，你也可以填任意 OpenAI 相容地址。這些服務商如何儲存、使用、是否用於訓練由它們自己的政策決定，請在使用前自行閱讀對應服務商的隱私政策（見第 2 節連結）。作者不對第三方服務商的資料處理行為負責，也無法替它們做出承諾。

## 8. 兒童

本專案面向成年人，不面向 13 歲以下兒童，不主動收集年齡資訊。如果你判斷自己或被監護人不適合使用需要傳送聊天內容到第三方接口的工具，請不要安裝或使用本應用。

## 9. 變更

本政策如有修改，會同步更新本檔案（GitHub 倉庫）；涉及資料處理方式的重大變更，會在對應版本的釋出說明（Release Notes / CHANGELOG）中提示。建議以倉庫中的最新版本為準。

## 10. 聯絡

- GitHub Issues：https://github.com/SanHsien/jev-chat-jarvis/issues

## 11. Windows 版

Windows 版（基於 [jev-chat-windows](https://github.com/jev-chat/jev-chat-windows) 二次開發）的資料處理：

- **只截 LINE 電腦版視窗**（行程 `LINE.exe`），用 Windows Graphics Capture 取得畫面，在本機以 RapidOCR 離線辨識。畫面只在記憶體裡（numpy 陣列），不寫磁碟、不進日誌、不上傳；除錯檢視也只在記憶體裡畫。
- **會離開電腦的資料**：只有對方有新訊息（或你在群組換了回覆對象）時，才把以下內容送到你在設定裡選的判斷接口與起草接口——最近 N 則對話文字（N＝參考上下文，預設 10；群組帶發言人名）、關係設定、你自己最近 12 則 60 字以內的短訊息（當口吻樣本）、你填的說話風格、指定的回覆對象名。
- **檢查更新**（可在設定關閉）：啟動時向 GitHub Releases API 查一次本 repo 的最新版本號，只帶 User-Agent 與目前版本號，不帶任何聊天內容。
- **只存在本機**：兩把金鑰（`JEV_API_KEY`、`LLM_API_KEY`）只寫進 Windows 使用者環境變數（登錄檔 `HKCU\Environment`），任何檔案都不出現金鑰，報錯文字一律遮蔽；其他設定存在程式旁的 `config.json`。聊天記錄只在執行期間的記憶體裡，關掉程式即消失。
- **刪除**：刪掉程式資料夾即刪除 `config.json`；金鑰可在設定頁清空，或用 `setx JEV_API_KEY ""`、`setx LLM_API_KEY ""` 清除。
- 同樣絕不自動發送、不碰轉帳／紅包／收款相關畫面，本專案沒有任何自建伺服器。

---

## English summary

Chat Wingman (Android) reads the chat you are currently viewing on your device and sends that text to a **model endpoint you configure yourself** (fresh-install default: Vercel AI Gateway routing to TypeSafe Jev / Google Gemini 2.5 Flash; you may switch to OpenRouter, TypeSafe direct, OpenCode Zen, or any OpenAI-compatible URL) so it can judge intent and draft reply candidates.

- **No servers are operated by the author.** The author cannot receive, store, or see your chat content — it never passes through any author-controlled infrastructure.
- **Chat text goes only to your own configured model endpoint**, along with a relationship description you write, optionally matched knowledge-base notes/contact notes, and optionally recent history for that contact (default 30 messages, 0–100 adjustable, off by default).
- **Screenshots are never uploaded.** When a chat app's accessibility tree lacks readable text, the screen is captured and OCR'd entirely on-device; the image is processed in memory and discarded, never saved or sent anywhere.
- **Local-only storage**: API keys, endpoint settings, knowledge-base notes/contacts, and (if enabled) per-contact chat history live only in the app's private storage on your device. Nothing syncs to the cloud. Uninstalling the app deletes all of it; a one-tap "clear knowledge base & history" option is also available.
- **No ads, no third-party analytics SDKs (no Google Analytics, Firebase, etc.), no cookies or advertising identifiers.**
- The app never sends messages automatically — you always press send yourself — and it never touches money transfers, red packets, or payments.
- The project is open source; every claim above can be verified against the source at https://github.com/SanHsien/jev-chat-jarvis.
- Third-party model providers you choose to use are governed by their own privacy policies, which you should review separately.

**Windows version** (`wingman/`, based on jev-chat-windows): captures only the LINE desktop window and OCRs it on-device with RapidOCR; frames stay in memory and are never written to disk, logged or uploaded. Only when the other side sends a new message are the last N messages (default 10, with speaker names in groups), your relationship setting, up to 12 of your own short recent messages (as a style sample), your style note and the chosen reply target sent to the judge and draft endpoints you picked. On start it may ask GitHub's Releases API for this repository's latest version (User-Agent and current version only; can be turned off). The two keys are stored only in the Windows user environment (`HKCU\Environment`); other settings live in `config.json` next to the exe; chat history is kept in memory only.

Version 1.1, effective 2026-09-25. Scope: the Android app and the Windows version.
