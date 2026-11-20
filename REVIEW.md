# 倉庫審查（Windows-first）

- 審查日期：2026-11-20（增量審查 `c84c250..e612f0e`，50 個檔案：Android app、`wingman/`、workflows、`tools/check_upstream_updates.py`、tests）
- 狀態：可當作 LINE／Vercel 的維護線使用。**不是**產品安全審計通過證明。本輪**不回貢**。
- 只保留最新一輪；每項標修復 commit 與日期，沒修的寫原因。

## confirmed

| # | 問題 | 狀態 |
|---|---|---|
| C1 | 自動分析模式下，`showLoading()` 展開面板時 `toggle()` 觸發 `onPanelOpened` → `showPending()` 把「分析中…」換成可再按的「分析」，按下會對同一快照再跑一次付費分析（`OverlayController.kt` toggle／showLoading、`ChatCaptureService.kt` onPanelOpened）。 | 已修 `67412b7`（2026-11-20）：`analyzing` 為真時 `onPanelOpened` 直接返回。**未本機編譯、未真機驗證**（本機無 Android SDK），以 CI `Android build` 為準。 |
| C2 | wingman 半自動：A 分析中切到 B 按「分析」，`tick()` 先處理 rerun 再存結果，A 仍有效的結果被丟、A 的「分析」按鈕已被 `take()` 用掉回不來。 | 已修 `6b480a8`（2026-11-20）：排隊的是別的會話且 `rev` 相符時先存結果再跑排隊的；同會話 rerun 維持上游丟棄行為。測試 `test_finished_result_is_kept_when_analyze_is_queued_for_another_chat`（修前失敗、修後通過）、`test_stale_result_is_still_dropped_when_rerun_is_queued`。Qt 介面未實跑。 |
| C3 | `tests/test_wingman_pending.py` 讀開發者本機 `wingman/config.json`，`auto_analyze: true` 時 3 個測試失敗。 | 已修 `d06ec43`（2026-11-20）：`wingman_env` fixture 把 `settings._CONFIG` 指到 tmp。在放了 `{"auto_analyze": true}` 的副本上跑 wingman 測試：19 passed。 |

## needs_validation

| # | 問題 | 狀態 |
|---|---|---|
| N1 | 同組測試在 drain 時可能呼叫真的 `start_analyze`（真網路、真金鑰）；直接改模組屬性不還原；numpy 被 Mock 換掉影響後續測試。 | 已修 `d06ec43`（2026-11-20）：`start_analyze` 在任何呼叫前換成紀錄器、`engine.analyze` 換成直接拋錯；全部改 monkeypatch 自動還原；numpy 只在沒安裝時才 stub；在 stub 下首次匯入的 `wingman.*` 模組測後移除。 |
| N2 | 使用者已回覆後點懸浮球，仍顯示「新訊息 · 分析對象」（`onPanelOpened` 沒看 `latestFrom`）。 | 未修：UX 文案問題、影響低，需真機確認實際畫面再決定改法。 |

## hardening

| # | 問題 | 狀態 |
|---|---|---|
| H1 | `HardTimeout.kt` 用無上限 `newCachedThreadPool`，DNS 卡住的執行緒會累積。 | 未修：改 pool 上限要決定滿載時的行為，且無法本機編譯測試，不算瑣碎。 |
| H2 | 硬上限 120s 短於 `HttpJson` 單次呼叫重試預算（約 168s），`draftAndRank` 第二次重試幾乎用不到。 | 未修：設計取捨，待在註解或 `docs/DECISIONS.md` 寫明。 |
| H3 | `ScreenCapture.kt` 逾時與 onSuccess 在 3s 邊界互搶，搶輸的 bitmap 未 recycle；`windowBounds` 跨執行緒無 volatile。 | 未修：實際風險低，且無法本機編譯／真機驗證。 |
| H4 | `gradle-wrapper.properties` 沒有 `distributionSha256Sum`（既有，非本輪引入）。 | 未修：需從官方取得並核對 checksum，改的是上游檔（要登記分岔），留待升 Gradle 時一併處理。 |

## 本輪已確認沒問題

- 5 個新釘選的 action SHA 與 tag 一致；workflow 無 `pull_request_target`，`persist-credentials: false` 不變。
- `gradle-wrapper.jar` sha256 與官方 9.9.1 wrapper 相同。
- `MlKitOcr` 非同步後的 bitmap 生命週期正確；`wingman/app/capture.py`、`fill.py` 延遲取 windll 後無殘留模組層參照。

## 未驗證（自驗缺口）

- 本機沒有 Android SDK，Kotlin 改動（含 C1 修正、`HardTimeoutTest`）只由 CI 的 `assembleDebug` 驗證編譯，**沒有在真機跑過**。
- wingman 的 Qt 介面（按鈕顯示／隱藏時機）沒有實際跑 GUI。
- `tools/check_upstream_updates.py`（+985 行）只粗看 None／「未檢查」處理，沒有逐行審；`gradlew.bat` 未與官方 9.9.1 逐字比對。
- Vercel 三個模型 ID 由 `tools/check_vercel_models.py` 每週確認在 gateway 目錄內，但沒有帶金鑰實際呼叫過；手機端三張卡的「測試」尚待維護者確認。
- `seedVercelDefaultIfFresh()` 只靠程式閱讀確認「已有設定不受影響」，沒有做升級安裝測試。
- `LineAdapter` 以 2026-09-25 真機 dump 驗證（1:1、繁中介面）；群組聊天、其他語言介面、實機填入未驗證。
