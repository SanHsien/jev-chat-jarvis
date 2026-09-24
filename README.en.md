<div align="center">

<img src="docs/images/logo.png" width="150" alt="Jev Chat Assistant" />

# Jev Chat Assistant (SanHsien fork)

**A "conversation co-pilot" on your phone: while you chat in any messaging app, it reads the other side, tells you how to reply, and fills your pick into the input box. Sending is always up to you.**

[中文版](README.md) | English | [简体中文原文（上游）](README.zh-CN.md)

</div>

> This repository is a fork of [`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis) (MIT). It is not made or endorsed by the original authors.
> Fork maintenance: [`FORK.md`](FORK.md). Rules for AI agents: [`AGENTS.md`](AGENTS.md).

## What it does

A non-intrusive assistant that sits beside a chat app: reads the latest incoming message → asks the Jev judgment model → shows an analysis and 3 ranked candidate replies in a floating overlay → fills the chosen one into the input box. **It never sends; a human always taps send.**

- **Judge first, then write.** Jev (choice / score / yes-no model) rates intent, risk and urgency before a generative model drafts replies.
- **Does not touch the chat app.** No hooks, no repackaging, no database reads; only the system accessibility service and screenshots.
- **Never touches money.** Transfer, red-packet and payment UI is off limits.
- **Bring your own endpoints.** Judge / reply / vision routes are configured separately with your own keys; no middle server.

## Platform support (upstream v1.4)

| Platform | Status | How it reads |
|---|---|---|
| QQ Android | ✅ Full | Accessibility nodes |
| X / Twitter DMs | ✅ Full | Compose `content-desc` |
| Feishu / Lark | ✅ OCR fallback | Bubble rects + ML Kit offline OCR |
| WeChat Android | ⏸ Dropped | WeChat hides node text and blocks screenshots on some devices |
| LINE | ✅ Manual; auto in progress | Manual full-screen OCR works; `LineAdapter` skeleton awaits device verification ([`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md)) |
| Any other app | ✅ Manual | Overlay menu "screenshot OCR once" (no me/them split) |

## Quick start

1. Install [`apk/jev-assistant-v1.4-release.apk`](apk/jev-assistant-v1.4-release.apk) (Android 11+, ARM64 only).
2. Keys: App → Settings → endpoints. Fresh installs of this fork default all three routes to Vercel AI Gateway; one Vercel key in the judge card is inherited by reply and vision. OpenRouter is the second choice.
3. Permissions: accessibility, overlay, autostart + unrestricted battery (required on Xiaomi / HyperOS).

## Build

JDK 17 + Android SDK (platform 35 / build-tools 35); the checkout path must be ASCII-only.

```powershell
pwsh -NoProfile -File tools/dev_check.ps1          # full gate (includes gradlew :app:assembleDebug)
pwsh -NoProfile -File tools/dev_check.ps1 -Quick   # quick gate
```

## License

MIT, Copyright © 2026 Finderchangchang and the jev-chat contributors. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`NOTICE.md`](NOTICE.md).
