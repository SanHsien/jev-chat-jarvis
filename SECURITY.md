# 安全政策

## 範圍

本 repo 是 [`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis) 的
SanHsien 維護 fork。影響**本 fork** 的漏洞請透過本 repo 的 Security 分頁回報；上游也存在的問題，
請另外依上游管道通知原作者。

## 回報方式

請**不要**開公開 issue。使用 GitHub 私密漏洞回報：本 repo → **Security** → **Report a vulnerability**。
請附：受影響的 commit、最小重現步驟、觀察到的影響。

## 使用者須知

- 金鑰只存在 App 私有空間；任何檔案不得出現 `sk-or-` 開頭字串（`tools/dev_check.ps1` 會掃）。
- 簽章檔（`*.jks`、`keystore.properties`）永不入 repo。
- 本 App 只讀螢幕上顯示的對話、絕不自動發送、不碰轉帳／紅包／收款介面；發現違反這些約束的行為一律視為安全問題。
