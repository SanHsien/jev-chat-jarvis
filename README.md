<div align="center">

<img src="docs/images/logo.png" width="150" alt="Jev 聊天助手" />

# Jev 聊天助手（SanHsien fork）

**裝在手機上的「對話副駕」：你在任何聊天 App 裡聊天，它在旁邊讀懂對方、告訴你該怎麼回，一鍵填進輸入框，發不發由你。**

中文版 | [English](README.en.md) | [简体中文原文（上游）](README.zh-CN.md)

</div>

> 本 repo fork 自 [`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis)（MIT），非原作者出品或背書。
> fork 維護說明見 [`FORK.md`](FORK.md)，AI 代理規則見 [`AGENTS.md`](AGENTS.md)。

## 它做什麼

掛在聊天 App 旁的非侵入式助手：讀到對方最新訊息 → 呼叫 Jev 判斷 → 懸浮窗給出分析與 3 條候選回覆（Jev 排序）→ 一鍵填入輸入框。**發送永遠由人手動按，程式不自動發送。**

- **先判斷，再寫字。** Jev 判斷模型先給出對方真實意圖、危險等級、該不該馬上回，再據此起草回覆。
- **不動聊天軟體。** 不 hook、不改包、不讀資料庫，只用系統無障礙服務讀「螢幕上正在顯示的對話」。
- **不碰錢。** 不觸碰轉帳、紅包、收款相關介面。
- **介面自己配。** 判斷／回覆／視覺三路接口分別可填，用自己的金鑰，不經過中間伺服器。

## 平台支援（上游 v1.4）

| 平台 | 狀態 | 讀取方式 |
|---|---|---|
| QQ Android | ✅ 全鏈路 | 無障礙讀節點 |
| X / Twitter 私訊 | ✅ 全鏈路 | 解析 Compose 節點 content-desc |
| 飛書 / Lark | ✅ OCR 兜底 | 氣泡矩形 + ML Kit 離線 OCR |
| 微信 Android | ⏸ 已停止支援 | 微信隱藏節點文字且部分啟用防截圖 |
| LINE | ✅ 手動；自動開發中 | 手動整屏 OCR 可用；`LineAdapter` 骨架待真機驗證（見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md#line-支援)） |
| 其他 App | ✅ 手動 | 懸浮窗選單「截屏識別一次」整屏 OCR（不分我／對方） |

## 快速開始

1. 安裝：[`apk/jev-assistant-v1.4-release.apk`](apk/jev-assistant-v1.4-release.apk)（Android 11+，僅 ARM64）。
   ```bash
   adb install -r apk/jev-assistant-v1.4-release.apk
   ```
2. 填金鑰：App → 設定 →「接口」。本 fork 新安裝預設三路皆為 Vercel AI Gateway，只要在判斷接口填一把 Vercel 金鑰，回覆與視覺留空即繼承；次選 OpenRouter。詳見 [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)。
3. 開權限：無障礙、懸浮窗、自啟動 + 省電無限制（小米 / HyperOS 必開）。

## 建置

JDK 17 + Android SDK（platform 35 / build-tools 35），路徑需全 ASCII。

```powershell
pwsh -NoProfile -File tools/dev_check.ps1          # 完整 gate（含 gradlew :app:assembleDebug）
pwsh -NoProfile -File tools/dev_check.ps1 -Quick   # 快速 gate
```

架構、適配新 App、已知限制等完整說明見 [簡中原文 README](README.zh-CN.md) 與 [`CLAUDE.md`](CLAUDE.md)。隱私政策見 [`PRIVACY.md`](PRIVACY.md)。

## 授權

MIT，Copyright © 2026 Finderchangchang 與 jev-chat 貢獻者。見 [`LICENSE`](LICENSE)、[`NOTICE`](NOTICE)、[`NOTICE.md`](NOTICE.md)。
