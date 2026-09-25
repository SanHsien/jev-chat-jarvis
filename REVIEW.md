# 倉庫審查（Windows-first）

- 審查日期：2026-09-24
- 審查起點：`4608acf`（fork 維護面落地後）
- 上游 `reviewed_through`：`a3026e2cbb4b576401358b1f7b51566f5ab6363d`（`v1.4` + 7 個文件 commit）
- 狀態：可當作 LINE／Vercel 的維護線使用。**不是**產品安全審計通過證明。本輪**不回貢**。

## 結論

維護面已補齊（上游查驗、分岔登記、依賴新鮮度、CodeQL、Windows gate、Android 建置）。產品改動：LINE 支援（本 fork 原創）、移除微信與飛書、
新安裝預設 Vercel、AGP 9／Gradle 9 升級、版本號 `1.4.0`。兩者都登記在 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md)。
LINE 自動模式要等真機 dump 才算完成；在那之前 LINE 走手動 OCR。

## 本輪實證

```text
git remote -v
origin    https://github.com/SanHsien/jev-chat-jarvis
upstream  https://github.com/jev-chat/jev-chat-jarvis.git

GitHub Actions @ 4608acf
ci       success   (Fork tooling / Windows gate -Quick -SkipUpstream / Android assembleDebug)
CodeQL   success   (java-kotlin manual build / python / actions)

GitHub Actions @ 0502489
Upstream check          success
Dependency freshness    success

本機（Linux 容器）
pytest -q                          57 passed
ruff check . / ruff format --check All checks passed / 8 files already formatted
tools/check_divergence.py          7 upstream file(s) diverge; 7 registered. OK
tools/check_links.py               18 份維護文件，0 份有缺檔
git grep sk-or-                    無命中
```

## 已修正

| 問題 | 修正 |
|---|---|
| 上游 tag 是兩段式（`v1.4`），範本正則只吃三段 → 檢查器會回報「沒有 release」 | `check_upstream_updates.py` 放寬為 `major.minor[.patch]`，並加測試 |
| Linux runner 建置失敗：`gradlew` 沒有執行權限；`app/build.gradle.kts` 預設簽章路徑 `H:/…` 在 Linux 被 Gradle 當成 URL | CI 改用 `bash ./gradlew`，並設 `JEV_KEYSTORE_PROPS` 指向不存在的檔案（不改上游檔） |
| 判斷接口選 Vercel 時，回覆／視覺繼承的 Vercel 金鑰會被送到 OpenRouter | 回覆／視覺各加 Vercel 預設；新安裝三路一次性設為 Vercel |

| Dependabot #1（AGP 9）與 #2（Gradle 9）各自必紅 | 合併驗證、移除 `kotlin.android` 外掛改用 AGP 內建 Kotlin，`39adee3` CI 全綠；gradle 改單一群組 |

| `check_divergence.py` 在 git 預設開啟 rename 偵測時，被 `git mv` 的上游檔案會漏登記 | 改用 `--no-renames`，加測試並做突變驗證 |

## 未驗證（自驗缺口）

- 本機沒有 Android SDK（下載被網路政策擋），Kotlin 改動只由 CI 的 `assembleDebug` 驗證編譯，**沒有在真機跑過**。
- Vercel 三個模型 ID 已由 `tools/check_vercel_models.py` 確認在 gateway 目錄內（`Vercel models` workflow，每週重查）；
  但沒有帶金鑰實際呼叫過，仍需在設定頁按「測試」確認。
- `seedVercelDefaultIfFresh()` 只靠程式閱讀確認「已有設定不受影響」，沒有做升級安裝測試。
- `LineAdapter` 以 2026-09-25 真機 dump 驗證（1:1、繁中介面），`LineExtractorTest` 在 CI 通過；群組聊天、其他語言介面、實機填入未驗證。
- 上游 PR／issue 已全數分診到 #55（見 `docs/UPSTREAM.md`）。
- 升級到 AGP 9.4.1／Gradle 9.7.1、移除微信與飛書、無障礙服務改名後的 APK 沒有在真機跑過（改名後需重新開啟無障礙）。
- 正式簽章已啟用：維護者本機以 `tools/new_signing_key.ps1` 產生金鑰並設好 `JEV_*` secrets，v1.4.3 為第一個正式簽章版（從 debug 版換裝須先解除安裝）。
- Vercel AI Gateway 金鑰已由維護者建立（Hobby 帳號，`typesafe-ai/jev` 在免費額度內）；手機端三張卡的「測試」尚待維護者確認。
