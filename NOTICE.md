# NOTICE

This repository is a maintained fork of [jev-chat-jarvis](https://github.com/jev-chat/jev-chat-jarvis).

- Original Author: Finderchangchang and the [jev-chat](https://github.com/jev-chat) contributors
- Upstream Repository: https://github.com/jev-chat/jev-chat-jarvis
- License: MIT License (see LICENSE and NOTICE)

Modifications and fork maintenance infrastructure by SanHsien:
- Windows-first verification tooling and dev check gates (`tools/dev_check.ps1`)
- Upstream synchronization review ledger and automation (`tools/check_upstream_updates.py`)
- AI governance policies and documentation (`AGENTS.md`, `CLAUDE.md`, `FORK.md`)
- Divergence registry and contract tests (`docs/DIVERGENCE.md`, `tools/check_divergence.py`, `tests/`)
- Vercel AI Gateway as the fresh-install default for all three endpoints
- LINE (`jp.naver.line.android`) support, original to this fork
- Removal of WeChat, Feishu and QQ support
- Endpoint presets trimmed to OpenRouter, Vercel, TypeSafe and OpenCode Zen
- New logo and app icon

The Windows version (`wingman/`, `tools/windows/`, `requirements-windows.txt`) is based on
[jev-chat-windows](https://github.com/jev-chat/jev-chat-windows) (MIT, Copyright (c) 2026 rezoch340 and the
jev-chat contributors; see `docs/licenses/jev-chat-windows/LICENSE` and `NOTICE`), merged into this repository
and adapted by SanHsien to LINE desktop only. Its packaged exe bundles
PySide6-Fluent-Widgets (GPLv3).
