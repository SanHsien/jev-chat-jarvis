# Windows 版分岔登記（`wingman/`）

Windows 版來自 [`jev-chat/jev-chat-windows`](https://github.com/jev-chat/jev-chat-windows) `main` 的 `946d3d1`（2026-09-24，v0.1.11），
先以 `git subtree` 匯入，再拆進本 repo 結構。上游 remote：`upstream-windows`；基準 commit 是本 repo 歷史的祖先之一。

## 路徑對照

| 上游路徑 | 本 repo 路徑 |
|---|---|
| `main.py` | `wingman/__main__.py`（`python -m wingman`） |
| `app/*` | `wingman/app/*`（import 改 `wingman.app`） |
| `core/*` | `wingman/core/*`（import 改 `wingman.core`） |
| `requirements.txt` | `requirements-windows.txt` |
| `jev.spec` | `tools/windows/wingman.spec`（在 repo 根目錄執行） |
| `build.bat` | `tools/windows/build.bat` |
| `tools/demo.py` | `tools/windows/demo.py` |
| `LICENSE`、`NOTICE` | `docs/licenses/jev-chat-windows/`（打包檔內為 `LICENSE-jev-chat-windows`、`NOTICE-jev-chat-windows`） |
| `docs/icon.ico` | `docs/images/wingman.ico`（改由 `docs/images/logo.svg` 產生） |
| `.gitignore` | 併入根目錄 `.gitignore` |
| `README.md` | 刪除；說明在根目錄 `README.md`／`README.en.md`〈Windows 版〉與 `PRIVACY.md` 第 11 節 |
| `.github/workflows/release.yml` | 刪除；改由根目錄 `windows.yml`（自測 + artifact）與 `release.yml` 的 `windows` job（附到同一個 Release） |
| `probe/`、`tools/preview_ui.py`、`tools/make_icon.py`、`docs/KICKOFF.md`、`docs/*.png` | 刪除（原版目標聊天軟體的探針、截圖、宣傳圖與舊圖示產生器） |

## 跟進上游

檔案已搬家，`git subtree pull` 不再適用。做法：

```bash
git fetch upstream-windows main
git log --oneline 946d3d1..upstream-windows/main
git diff 946d3d1 upstream-windows/main -- app core main.py requirements.txt jev.spec
```

依上表換路徑後手動套用，並依下方「跟進上游時怎麼處理」決定收不收；套用後把本檔與 `docs/UPSTREAM.md` 的基準 commit 更新。

## 全域

- **只認 LINE**：採集只找 `LINE.exe` 的視窗；原版目標聊天軟體的採集、填入、偵測程式與說明全部移除，上游再加也不收（`AGENTS.md` 硬約束 7）。
- **接口預設白名單**：起草只內建 OpenRouter、Vercel AI Gateway、OpenAI、Anthropic、Google Gemini 與自訂；判斷維持 OpenRouter、TypeSafe。上游新增其他來源不收。
- **介面繁體中文**：`*.py` 與 spec 的中文以 OpenCC `s2twp` 轉換（保留「接口」「對象」）；`wingman/core/questions.py` 的 Jev 題目英文段不動。上游改到中文字串時，合併後對該檔重跑一次。
- **產品名**：視窗標題與標題列為「對話副駕」，exe 為 `chat-wingman`（上游 NOTICE 不允許以其名稱暗示原作者出品）。

## 逐檔

| 本 repo 檔案 | 相對上游的改動 | 跟進上游時怎麼處理 |
|---|---|---|
| `wingman/app/capture.py` | `find_wechat_hwnd` 改名 `find_chat_hwnd`，只認 `CHAT_EXES = ("line.exe",)`，主視窗標題「LINE」。 | 照收其他改動，保留只認 LINE。 |
| `wingman/app/fill.py` | 新增 `VERIFIED = False`：未實機驗證 LINE 輸入框位置前只寫剪貼簿，`fill()` 回傳是否已貼上；主鍵對調（左撇子）時送右鍵事件（上游 issue #34）。 | 照收；LINE 驗證後改 `True`。 |
| `wingman/__main__.py` | 改呼叫 `find_chat_hwnd`；`fill_reply` 回傳 `fill()` 的結果；註解改為 LINE。 | 照收。 |
| `wingman/app/overlay.py` | 只複製時提示按 `Ctrl+V`；移除公眾號橫幅；標題改「對話副駕」；起草預設說明改 OpenRouter；設定頁加〈關於與授權〉（依上游〈版權與許可〉）。 | 照收，橫幅不收，保留〈關於與授權〉。 |
| `wingman/app/update.py`、`wingman/app/settings.py` | 檢查更新查本 repo 的最新 Release（與 APK 同版號），不查上游；起草預設 `openrouter`。 | 保留指向本 repo。 |
| `wingman/core/providers.py`、`engine.py`、`draft.py`、`llm.py` | 白名單以外的來源與其自測移除；起草預設 OpenRouter + `google/gemini-2.5-flash`；起草要求繁體中文（台灣用語）輸出。 | 白名單以外不收。 |
| `tools/windows/wingman.spec`、`build.bat`、`requirements-windows.txt` | exe 名 `chat-wingman`；hiddenimports 改 `wingman.*`；加 `httpx[socks]`／收 `socksio`（上游 PR #15）；入口 `wingman/__main__.py`；不打包公眾號圖；註解改白名單。 | 照收。 |
