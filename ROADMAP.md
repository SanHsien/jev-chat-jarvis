# 路線圖

> 本 repo 後續工作的單一真相源。做完一項，就在同一個 commit 刪掉那一列；新工作只加在這裡。
> 現況段的數字是 2026-10-29 依 `main` `fcd34e656731` 查的快照，開工前先重查 GitHub。

## 現況

LINE（Android 與 Windows）的對話副駕 fork，上游是 `jev-chat/jev-chat-jarvis`；2026-10-29 無 open issue／PR、Dependabot 與 Code scanning 告警皆 0，`main` 上 ci、CodeQL、windows、Upstream check 最近一次皆 success（2026-10-29 `gh` 查詢）。上游已審到 v1.7（`tools/upstream_baseline.json`）；`CHANGELOG.md` 的 `[未發佈]` 累積了 `[1.4.11]`（2026-09-26）之後的修正與 120 秒硬逾時，尚未發版；Android 截圖／OCR 執行緒與逾時只有編譯加單元測試，沒有實機驗證（`REVIEW.md`「未驗證」段）。

## 近期：可以直接動手
| 項目 | 為什麼 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 實機驗收 `[未發佈]` 的 Android 改動，通過後發 1.4.12 | 截圖回呼與 OCR 改到背景執行緒、判斷／候選 120 秒硬逾時、`stream:false` 都只有編譯＋單元測試；發版前需有人在手機上跑過 | 在實機的 LINE 完成一輪「分析→填入」；斷網或 DNS 卡住時 120 秒內顯示逾時而非一直轉圈；通過後 `CHANGELOG.md` 的 `[未發佈]` 變成 `[1.4.12]`，`app/build.gradle.kts` 版號同步，release workflow 成功並出現 APK | 維護者 | `CHANGELOG.md:9-20`；`app/build.gradle.kts:32-33`；`REVIEW.md` 未驗證段 |
| 決定半自動「換回覆對象後是否重跑」的語意並寫進 `docs/DECISIONS.md` | `chat["result"]` 在新訊息後不清空，已分析過的會話換對象仍會自動重跑；CHANGELOG 1.4.11 寫「該會話已經分析過」，意圖含糊 | `docs/DECISIONS.md` 有一節寫明語意（維持或改成只針對當前這則訊息）；若要改，補一項釘住該行為的 pytest，`pwsh -NoProfile -File tools\dev_check.ps1` 全綠 | 維護者 | `CHANGELOG.md:27`；深掃報告（2026-10-26）「刻意不修」 |

## 中期：等條件成立再做
| 項目 | 觸發條件 | 驗收方式 | 建議執行者 | 證據 |
| --- | --- | --- | --- | --- |
| 修上游 Android 程式的觀察清單項目（401／429 不重送、`InterruptedException` 不被吞、`parseThree` 容忍前文 `[笑]`） | 維護者決定本 fork 要修（每修一項 `docs/DIVERGENCE.md` 會多一列）或實機撞到金鑰錯／限流多打請求 | 對應單元測試（修前紅、修後綠）；`python tools/check_divergence.py` 通過；`gradlew :app:testDebugUnitTest :app:assembleDebug` 成功 | Claude Sonnet | 深掃報告觀察清單；`docs/DIVERGENCE.md` |
| 審上游 `c57ecc1`（v1.7）之後的新 commit／release，並把 `app/` 對映到上游 `cn/app/` 再比 | Upstream check workflow 出現 failure（代表上游有未審項目），或上游發新 release | `docs/UPSTREAM.md` 新增當次審查一節；`tools/upstream_baseline.json` 的 `reviewed_through` 推進；`python tools/check_upstream_updates.py --strict` 綠 | Claude Sonnet | `tools/upstream_baseline.json`；`docs/UPSTREAM.md` 2026-10-25 一節；接續開發報告「刻意不做」 |
| LINE 群組聊天的測試案例 | 取得 LINE 群組畫面的真機 dump | `LineExtractorTest` 新增群組案例並通過；`docs/DECISIONS.md` 2026-09-25 群組一節的「未驗證」改為已驗證或更正 | 維護者（取得 dump）→ Claude Sonnet（寫測試） | `docs/DECISIONS.md:205-211` |
| 重新考慮 v1.7 的「換一組」、常駐卡片、回覆語言跟隨 | 維護者實際使用後覺得需要，或改變「半自動、不自動展開」的定案 | 先在 `docs/DECISIONS.md` 改定案並說明理由，再開工；實作後實機驗收 | 維護者 | `docs/UPSTREAM.md` 2026-10-25 一節 |

## 刻意不做
| 不做什麼 | 理由 | 什麼情況下重新考慮 |
| --- | --- | --- |
| 採用 WhatsApp／Soul／抖音支援與上游 `global/`、`feat/vision-judge` | 本 fork 範圍是 LINE＋X；`feat/vision-judge` 的區域設定與接口白名單衝突（`docs/UPSTREAM.md` #81 列） | 維護者要擴大支援的聊天軟體時 |
| 回貢上游 | 回貢須在當次對話取得維護者明確同意（`FORK.md:19`） | 維護者在當次對話明說要回貢某個修正 |
| 改寫歷史或與上游重新接上共同祖先 | `main` 是單一根 commit 屬已知事實（`FORK.md:4`），強推有 fork 風險 | 不重新考慮 |
| 為 Android 截圖／OCR 加本機自動化實機測試 | 本機測不到無障礙與截圖行為，只能實機驗收 | 有可用的 Android 模擬器／實機 CI 時 |

## 維護方式

上游每週一由 Upstream check 自動查（failure＝有未審項目，不是工具壞）；採用與否的判準與回來重看條件記在 `docs/UPSTREAM.md`。依賴更新由 Dependabot 與月度 Dependency freshness 處理，合併前看 ci 綠；發版依 `CHANGELOG.md` 版號規則（上游主.次.fork 序號）。
