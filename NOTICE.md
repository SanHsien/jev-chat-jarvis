# NOTICE

This repository is a maintained fork of [jev-chat-jarvis](https://github.com/jev-chat/jev-chat-jarvis).

- Original Author: Finderchangchang and the [jev-chat](https://github.com/jev-chat) contributors
- Upstream Repository: https://github.com/jev-chat/jev-chat-jarvis
- License: MIT License (see LICENSE and NOTICE)

Modifications and fork maintenance infrastructure by SanHsien:
- Windows-first verification tooling and dev check gates (`tools/dev_check.ps1`)
- Upstream synchronization review ledger and automation (`tools/check_upstream_updates.py`)
- AI governance policies and documentation (`AGENTS.md`, `.claude/CLAUDE.md`, `FORK.md`)
- Divergence registry and contract tests (`docs/DIVERGENCE.md`, `tools/check_divergence.py`, `tests/`)
- Vercel AI Gateway as the fresh-install default for all three endpoints
- LINE (`jp.naver.line.android`) adapter skeleton
