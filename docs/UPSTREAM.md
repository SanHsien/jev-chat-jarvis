# 上游同步指引 (UPSTREAM.md)

## 上游 Remote 設定

```powershell
git remote -v
# 應確認包含：
# origin    https://github.com/SanHsien/jev-chat-jarvis.git
# upstream  https://github.com/jev-chat/jev-chat-jarvis.git
```

### Windows 版（`wingman/`）

```bash
git remote add upstream-windows https://github.com/jev-chat/jev-chat-windows.git
git fetch upstream-windows main
git log --oneline 946d3d1..upstream-windows/main   # 基準之後的上游變動
```

檔案已拆進本 repo 結構，跟進方式與路徑對照見 [`DIVERGENCE-windows.md`](DIVERGENCE-windows.md)；`check_upstream_updates.py` 目前只追 Android 上游，Windows 上游的分診紀錄在下方〈Windows 上游分診紀錄〉。

## 上游改寫歷史時

上游若 force-push 改寫歷史，`check_upstream_updates.py` 會報「upstream rewrote its history」。處理：

```bash
git fetch upstream --tags --force
T=$(git rev-parse <reviewed_through>^{tree})
git log --format='%H %T %s' upstream/main | awk -v t=$T '$2==t'   # 找 tree 相同的新 commit
```

再把 `tools/upstream_baseline.json` 的 `reviewed_through` 改成該 commit，並記進 `docs/DECISIONS.md`。
本 fork 的 `main` 是單一根 commit（不含上游歷史），所以不需要 merge；`check_divergence.py` 會自動 fetch 新的基準 commit。
2026-09-25 已處理一次（`a3026e2` → `45a0876`）。

## 檢查上游更新

```powershell
python tools/check_upstream_updates.py
```

- 若上游已 release 新版本（新 `vX.Y` tag）或有新 PR / Issue，報告會產出在 `upstream-review-report.md`。
- 逐筆審閱後，在 `docs/DECISIONS.md` 記錄採納／略過決策。
- 合併：`git fetch upstream --tags` → `git merge <tag>`（用 merge commit，不 rebase、不 force-push `main`）。
- 推進 `tools/upstream_baseline.json` 的水位線，並執行 `tools/dev_check.ps1` 驗證。

## 注意

- 本 fork 已刪除上游的 `apk/`、`site/`、`docs/{acceptance,probe_spec,v1.3-*}.md`、`README` 簡中原文與微信／飛書程式碼；
  上游再改這些路徑時一律保留刪除（`git rm` 解衝突），判準見 `docs/DIVERGENCE.md`。
- `CLAUDE.md` 衝突時保留本 fork 版本（只匯入 `AGENTS.md`），上游新增的產品事實人工整理進 `AGENTS.md`。

## 分診紀錄

**目的：同一筆不重評。** 上游查驗（`tools/check_upstream_updates.py`）只列出水位之後的新項目；
水位以下的每一筆都在這裡有結論、證據與「什麼情況要回來重看」。重新盤點全部項目時，手動執行
`Upstream inventory` workflow（`.github/workflows/upstream-inventory.yml`），它把所有 PR／issue／分支印成 JSON。

### 2026-09-24（水位：PR／issue #55，分支 6 個）

本 fork 的範圍：Android、LINE（原創）與 X；已移除微信、飛書、QQ；預設 Vercel。判斷依此範圍做。

#### 分支

| 分支 | 狀態 | 結論 |
|---|---|---|
| `main` | `a3026e2` | fork 基準，已納入。 |
| `feat/vercel-judge-preset` | #48 已合併 | 已在基準內。 |
| `feat/39-opencode-zen-preset` | #49 已合併 | 已在基準內。 |
| `docs/update-mac-repo-link` | #54 | 不採用：改的是本 fork 已刪除的簡中 README。 |
| `docs/align-android-wechat-support` | #55 | 不採用：微信說明，本 fork 已移除。 |
| `gh-pages` | 上游官網部署 | 不採用：本 fork 不架官網（`site/` 已刪）。 |

#### Pull requests

| # | 狀態 | 內容 | 結論 | 證據／回來重看的條件 |
|---|---|---|---|---|
| 1 | open | 飛書開放平台 API 作訊息源（+1329） | 不採用 | 飛書已移除。 |
| 4 | open | 自訂 API 位址與 Chat Completions | 不採用 | 基於 v1.3 前；v1.3 起三路接口皆可自訂位址／模型，已涵蓋。 |
| 6 | open | 會話去重納入標題 | **採用** | `ChatSnapshot.signature()` 原本只看最後 6 則，切換聯絡人會沿用舊分析；連同 `ChatSnapshotTest` 併入。上游合併後改用上游版本。 |
| 21 | open | 備援解析保留回覆開頭數字 | **採用** | `trimStart('1','2','3',…)` 會吃掉「1.5 小時」；併入 `ReplyLineParser` 與測試。 |
| 22 | open | 懸浮窗在 HyperOS 消失後自癒（+581，改 `ChatCaptureService`／`ScreenCapture`） | 暫緩 | 與本 fork 大改過的 `ChatCaptureService` 衝突面大，且需真機驗證。**回來重看**：維護者裝置出現懸浮窗消失（上游 #20、#28），或上游合併。 |
| 23 | open | HyperOS／MIUI 省電與自啟動就緒判定 | 暫緩 | 機型特定（紅米 Turbo 4）。**回來重看**：維護者使用小米／紅米，或上游合併。 |
| 24 | open | iOS 原生版（+5978） | 不採用 | 本 fork 只做 Android。 |
| 25 | closed 未合併 | 會話隔離與最新訊息排程（+728） | 不採用 | 上游拒收；切換聯絡人沿用舊分析已由 #6 處理。**回來重看**：仍出現跨會話分析錯置。 |
| 32 | open | 簽章設定改為只看 `JEV_KEYSTORE_PROPS` | **採用** | 原本預設 `H:/…` 在 Linux／macOS 讓 Gradle 失敗，本 fork CI 也踩過；CI 不再需要假路徑。 |
| 34 | open | Vercel 預設（修 #17） | 不採用 | 被已合併的 #48 取代。 |
| 35 | open | 區分無障礙授權與讀屏服務連線 | **採用** | 服務斷線後首頁仍顯示就緒；併入 `CaptureHealth` 與測試，服務名改成本 fork 的 `ChatCaptureService`。 |
| 41 | open | 所有接口加 DeepSeek | 不採用 | 判斷只能是 Jev；DeepSeek 沒有視覺模型；2026-09-25 起接口預設只收白名單（見 DIVERGENCE 全域分岔）。 |
| 45 | open | OCR 校對與懸浮分析介面優化（+327） | 暫緩 | 對 LINE 手動 OCR 有價值，但 `OverlayController` 衝突面大。**回來重看**：LINE 定案走 OCR 路線時優先評估。 |
| 48 | merged | Vercel 判斷預設 | 已在基準內。 | — |
| 49 | merged | OpenCode Zen 判斷預設 | 已在基準內。 | — |
| 51 | open | PR 建置 debug APK 的 CI | 不採用 | 本 fork 的 `ci.yml` 已建置並上傳 APK。 |
| 53 | closed | 誤開的合併 PR | 不採用 | 無內容。 |
| 54 | open | 簡中 README 的 macOS 連結 | 不採用 | 見分支表。 |
| 55 | open | 簡中 README 的微信說明 | 不採用 | 見分支表。 |

#### Issues

| # | 內容 | 結論 |
|---|---|---|
| 2、26 | 為何要 Jev、單 LLM 版本 | 設計討論，不處理。 |
| 3 | 看不到聊天歷史 | 已有：知識庫的「記錄聊天歷史」（預設關閉）。 |
| 5、7 | 支援抖音、Soul | 可用手動「截屏識別一次」；不做專用適配器。 |
| 8、17、12、40 | 自訂／Vercel 接口 HTTP 400、Vercel key | 已解決：Vercel 預設（#48）且本 fork 預設 Vercel。 |
| 9、11、15 | 功能清單、心理學分析、人設／親密度 | 需求，不處理。**回來重看**：維護者提出同類需求時。 |
| 10、16、27、30、33 | 聊天記錄採集器、Windows／iOS 版、狗頭軍師、鴻蒙 | 範圍外。 |
| 13、29 | 電腦端相容、電腦端讀錯 | 範圍外（桌面版）。 |
| 14、37 | 三星 S26U 懸浮框無效、榮耀 Magic7 | 機型相容問題，無修正可移植。**回來重看**：維護者裝置為同品牌。 |
| 18、20、28 | 懸浮窗消失、自動行為問題 | 對應暫緩的 PR #22。 |
| 19、50 | 交流群滿 | 範圍外。 |
| 31 | 法規疑慮 | README 已有免責聲明；本 fork 只讀使用者自己有權查看的聊天。 |
| 36、43 | 微信懸浮窗消失、微信還能用嗎 | 微信已移除。 |
| 38、39 | 內建 Jev 渠道失效、OpenCode Zen | 已由 #49 與多渠道預設處理。 |
| 42、46、47、52 | **使用後微信無法截圖（FLAG_SECURE／sharingType=0），解除安裝也不恢復** | **採用為保護措施**：微信列入 `BLOCKED_PKGS`（1.4.2 恢復）；README〈已知限制〉說明。 |
| 44 | 左撇子滑鼠插入回覆 | 桌面版問題，範圍外。 |

### 2026-09-25（水位：PR／issue #63，分支 6 個）

#### 上游 `main`（`a3026e2..d10019d`，10 個 commit）

全部只動文件、圖片與官網（README、CHANGELOG、PRIVACY、`docs/`、`site/`、`tools/jev/TASK.md`），**沒有 App 程式碼**；
上游 tag 仍是 `v1.4`。本 fork 已改寫或刪除這些檔案，**不採用**。上游同日改寫了歷史，`reviewed_through` 改為 tree 相同的 `45a0876`（見 `docs/DECISIONS.md`）。
**回來重看**：上游出現 `v1.5` 或任何 `app/` 變更（`upstream-check.yml` 會報）。

#### 分支

與上一輪相同 6 個；`docs/align-android-wechat-support`（#55 已合併）與 `gh-pages` 有新 commit，皆為文件／官網，不採用。

#### 上一輪項目的狀態變化

上游把 #1、#4、#6、#21、#22、#23、#24、#32、#34、#35、#41、#45、#51、#54 **關閉未合併**，#55 合併（簡中 README 文件）。

- 已採用的 #6、#21、#32、#35：本 fork 繼續保留；`docs/DIVERGENCE.md` 裡「上游合併後改用上游版本」的條件不會再發生，改為長期分岔。
- 暫緩的 #22、#23、#45：上游已拒收，維持暫緩，重看條件不變（懸浮窗消失、小米裝置、LINE 走 OCR）。

#### 新 Pull requests

| # | 狀態 | 內容 | 結論 | 證據／回來重看的條件 |
|---|---|---|---|---|
| 57 | open | 英文 README（+308） | 不採用 | 本 fork 已有自己的中英 README。 |
| 60 | merged | 修正 README 判斷接口預設值與順序 | 不採用 | 只改上游簡中 README／CHANGELOG；本 fork 預設是 Vercel，README 已自寫。 |
| 62 | open | 越南文 README | 不採用 | 同 #57。 |
| 63 | open | 判斷接口新增 Opper 預設（+31） | 不採用 | 本 fork 預設 Vercel、次選 OpenRouter，不再加預設；「自定義」可手動填 Opper。**回來重看**：維護者想用 Opper 或上游合併。 |

#### 新 Issues

| # | 內容 | 結論 |
|---|---|---|
| 56 | 交流群滿 | 範圍外。 |
| 58 | 「分不出哪一個是我」 | 不適用本 fork：上游的我／對方判斷問題出在微信／QQ 等；本 fork 的 LINE 用每則訊息旁的已讀／時間標記判斷，並有 dump 測試。**回來重看**：LINE 實測出現同樣問題。 |
| 59 | 微信被禁止截圖，重裝後隔天又被禁 | 佐證 `BLOCKED_PKGS` 的必要（併入 #42／#46／#47／#52 同一類）。 |
| 61 | 非同步分析結果沒有綁定到發起的對話 | **採用並修正**（1.4.5）：每次分析有 run id，結果只在「同一個 run 且前景仍是同一個對話與 App」時顯示；候選回覆只填進原對話，否則提示重新分析；分析中到達的新訊息在結束後補跑；判斷與回覆兩段都結束才解除忙碌；暫時標題（如「連線中」）只在畫面仍有上一個對話的最後一則訊息時才沿用舊標題，避免歷史寫進別人的紀錄。 |

### 2026-09-25 第二輪（水位：PR／issue #64）

#### 上游 `main`（`d10019d..ea266e0`）

- `a6c83c3`／`ea266e0`：PR #64 合併（見下）。
- `27a509a`：只改上游 README 友情連結，**不採用**。

上游 tag 仍是 `v1.4`（本 fork 追 release），`reviewed_through` 不動。

#### 新 Pull requests

| # | 狀態 | 內容 | 結論 | 證據／回來重看的條件 |
|---|---|---|---|---|
| 64 | merged | 綁定來源會話，阻止過期分析結果與跨會話填入（+502／−126，新增 `ConversationSession`、`GuardedInputWriter` 與測試） | 暫緩 | 修的是上游 issue #61，本 fork 已在 1.4.5 以 run id 綁定自行修正（結果只顯示在原對話，填入只作用於原對話）；上游版本另在寫入輸入框前再驗證目標節點，較嚴格，但與本 fork 大改過的 `ChatCaptureService`／`OverlayController` 衝突面大。**回來重看**：上游發出含此修正的 release（`v1.5` 等）時，評估以上游的 `GuardedInputWriter` 取代本 fork 的做法。 |

## Windows 上游分診紀錄（`jev-chat/jev-chat-windows`）

盤點方式：`Upstream inventory` workflow 選 `jev-chat/jev-chat-windows`。本 fork 的範圍：只支援 LINE 電腦版（原版目標聊天軟體不讀、不截圖、不填入）、
接口預設白名單、介面繁體中文、絕不自動發送。基準 `946d3d1`（v0.1.11）。

### 2026-09-25（水位：PR／issue #35，分支 1 個）

#### 分支

| 分支 | 狀態 | 結論 |
|---|---|---|
| `main` | `946d3d1` | 基準，已拆進 `wingman/`。 |

#### Pull requests

| # | 狀態 | 內容 | 結論 | 證據／回來重看的條件 |
|---|---|---|---|---|
| 2 | closed | 64 位元填入崩潰、RapidOCR 1.2.3、連續填入錯亂 | 已在基準內 | 上游以 v0.1.7 等 commit 修掉（`fill.py` 已宣告 restype／argtypes、`Ctrl+End`）。 |
| 5 | merged | 註明 rapidocr 1.4.x 需要 Python < 3.13 | 已在基準內 | `requirements-windows.txt` 註解與 README 需求已寫。 |
| 7 | open | 輸入框區干擾線被當訊息區（微信 4.x） | 暫緩 | 針對原版目標視窗的版面。**回來重看**：LINE 實測出現輸入框工具列或語音提示被讀成訊息。 |
| 8 | closed | 候選全被過濾時 IndexError | 已在基準內 | `wingman/core/engine.py` 已在候選為空時拋 `JevError`，並有自測。 |
| 11 | closed | 被 #12 取代 | 不採用 | 同 #12。 |
| 12 | open | 懸浮窗吸附與訊息內氣泡浮層、系統通知過濾、設定原子寫入等（+1665） | 不採用 | 大半綁定原版目標聊天軟體的視窗與通知文字；空候選修正已在基準。**回來重看**：LINE 實測需要吸附視窗，或要做設定檔原子寫入時單獨挑出。 |
| 15 | open | 打包 SOCKS 代理支援（`httpx[socks]`、收 `socksio`） | **採用** | 走 SOCKS 代理的使用者會因缺 `socksio` 無法連線；已加進 `requirements-windows.txt` 與 `tools/windows/wingman.spec`。上游合併後保持一致即可。 |
| 16 | closed | Win10 1909 採集起不來（`cursor_capture=None`） | 已在基準內 | 上游 `4adb581`；`wingman/app/capture.py` 已顯式傳 `None`。 |
| 20 | merged | OpenRouter「取得模型」寫死 Jev 清單 + 金鑰探測 | 已在基準內 | `OPENROUTER_KEY_URL` 與 `_check_openrouter_key()` 已在。 |
| 22 | closed | 社群版：QQ、判斷跟隨起草模型、白名單外來源等（+3306） | 不採用 | 原版目標聊天軟體與 QQ 不收；Jev 判斷不改用一般 LLM；來源不在白名單。 |
| 23 | open | Linux／Ubuntu 支援原版目標聊天軟體 + 白名單外起草來源 | 不採用 | 範圍外（本 fork 只做 LINE 電腦版與 Android）。 |
| 28 | open | 引擎預埋 4 個擴充鉤子（策略庫外掛） | 不採用 | 新架構，本 fork 沒有外掛需求。**回來重看**：要接策略庫或自訂題集時。 |

#### Issues

| # | 內容 | 結論 |
|---|---|---|
| 1 | 機率高就自動回覆 | 不採用：硬約束「絕不自動發送」，上游亦 not planned。 |
| 3、4 | 更多平台、先判斷再起草 | 已在基準內（多來源、三段式流程）。 |
| 6 | 為何用視覺而非讀資料庫 | 說明性問題；與硬約束 1 一致。 |
| 9 | 新增 OpenCode Go 起草來源 | 不採用：上游已加，本 fork 依接口預設白名單移除。 |
| 10、14、26 | 企業版／QQ／多開原版目標聊天軟體 | 不採用：範圍外。 |
| 13 | Win10 1909 無法採集 | 已在基準內（同 PR #16）。 |
| 17 | 自訂 Jev 模型／來源 | 暫緩：判斷仍限 OpenRouter／TypeSafe。**回來重看**：Windows 版要跟 Android 一樣支援 Vercel／自訂判斷接口時。 |
| 18 | 識別不準（聯絡人清單被讀進訊息、手動觸發生成、填入點到外面） | 部分處理：自動填入在 LINE 驗證前停用（只複製），不會點到外面。**回來重看**：LINE 實測出現左側清單被讀入；手動觸發可比照 Android 半自動（`docs/DECISIONS.md`），待維護者決定是否套到 Windows。 |
| 19 | OpenRouter「取得模型」永遠空 | 已在基準內（PR #20）。 |
| 21、24 | Win11 相容、Mac 版 | 說明性問題，無需處理。 |
| 25 | 生成失敗（402 額度不足） | 使用者端設定問題，無需處理。 |
| 27 | 多開、往上捲被當最新、OCR 錯字、關閉後行程殘留 | 暫緩：多開不收；「往上捲」與「關閉殘留」**回來重看**：LINE 實測重現時。 |
| 29 | 穩定性差 | 無具體內容，不處理。 |
| 30 | 開機自動啟動 | 暫緩：**回來重看**：維護者需要常駐時（`HKCU\...\Run`，預設關）。 |
| 31 | 關係／風格設定提到主畫面 | 暫緩：**回來重看**：實際使用覺得切換頻繁時。 |
| 32 | 填入按鈕失靈（併入 #18） | 同 #18。 |
| 33 | 儲存金鑰後卡死 | 已在基準內（`SendNotifyMessage`）。 |
| 34 | 左撇子（主鍵對調）時填入失效 | **採用並修正**：`wingman/app/fill.py` 依 `SM_SWAPBUTTON` 送對應按鍵事件（本 fork 原創修正，自動填入啟用後生效）。 |
| 35 | 希望不用 API 金鑰 | 不採用：Jev 判斷需要金鑰。 |
