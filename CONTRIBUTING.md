# 貢獻指南

本 repo 是單一維護者的 fork（`SanHsien/jev-chat-jarvis`），上游是
[`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis)。

- 沒有分支／PR 流程：維護者在本機跑 [`tools/dev_check.ps1`](tools/dev_check.ps1) 通過後直接推 `origin/main`。
- 外部 PR 歡迎，但依維護者判斷合併，無服務承諾。
- 本 fork 不會主動對上游開 PR；判準見 [`FORK.md`](FORK.md)。

## 回報問題

- **產品**（App 行為、適配器、判斷題目）的 bug 多半上游也有，可考慮同時回報上游。
- **本 fork 自有**的維護工具（`tools/*.py`、fork 的 workflows、fork 文件）或 LINE 支援，在本 repo 開 issue。

## 動手前

1. 讀 [`AGENTS.md`](AGENTS.md)（含產品硬約束）與 [`FORK.md`](FORK.md)。
2. 改到上游持有的檔案，同一個 commit 在 [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md) 加一列。
3. 跑 `pwsh -NoProfile -File tools/dev_check.ps1` 保持全綠。
