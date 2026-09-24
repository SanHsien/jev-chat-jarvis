# 上游同步指引 (UPSTREAM.md)

## 上游 Remote 設定

```powershell
git remote -v
# 應確認包含：
# origin    https://github.com/SanHsien/jev-chat-jarvis.git
# upstream  https://github.com/jev-chat/jev-chat-jarvis.git
```

## 檢查上游更新

```powershell
python tools/check_upstream_updates.py
```

- 若上游已 release 新版本（新 `vX.Y` tag）或有新 PR / Issue，報告會產出在 `upstream-review-report.md`。
- 逐筆審閱後，在 `docs/DECISIONS.md` 記錄採納／略過決策。
- 合併：`git fetch upstream --tags` → `git merge <tag>`（用 merge commit，不 rebase、不 force-push `main`）。
- 推進 `tools/upstream_baseline.json` 的水位線，並執行 `tools/dev_check.ps1` 驗證。

## 注意

- 上游會把 release APK 放在 `apk/`（刻意追蹤），合併時保留。
- 上游 `CLAUDE.md` 衝突時以上游版本為準；fork 規則只改 `AGENTS.md`。
