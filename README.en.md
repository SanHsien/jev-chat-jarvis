<div align="center">

<img src="docs/images/logo.svg" width="150" alt="Chat Wingman" />

# Chat Wingman

**A chat wingman on your phone and PC: while you chat, it reads the other side, tells you how to reply, and fills your pick into the input box. Sending is always up to you.**

[中文](README.md) | English

</div>

> Based on Jev Chat Assistant ([https://github.com/jev-chat/jev-chat-jarvis](https://github.com/jev-chat/jev-chat-jarvis)): this repository is a fork of [`jev-chat/jev-chat-jarvis`](https://github.com/jev-chat/jev-chat-jarvis) (MIT). It is not made or endorsed by the original authors.
> **LINE support is original to this fork**; upstream has none. WeChat, Feishu and QQ support has been removed from this fork.
> **The Windows version** is based on JevChat-Windows ([https://github.com/jev-chat/jev-chat-windows](https://github.com/jev-chat/jev-chat-windows)) and supports LINE desktop only; see [Windows version](#windows-version-line-desktop-preview).
> Maintenance notes: [`FORK.md`](FORK.md). File-by-file differences from upstream: [`docs/DIVERGENCE.md`](docs/DIVERGENCE.md), [`docs/DIVERGENCE-windows.md`](docs/DIVERGENCE-windows.md).

## Why use it

- **Judge first, then write.** A judgment model rates the other side's intent, risk and urgency before replies are drafted.
- **Does not touch your chat app.** No hooks, no repackaging, no app APIs or accounts, no database reads; only the system accessibility service reading what is on screen.
- **You always press send.** Replies are only filled into the input box, never sent; transfer, red-packet, payment and LINE Pay screens are off limits.
- **It knows your people.** An on-device knowledge base and contact profiles are attached to each analysis when they match.
- **Bring your own endpoints.** Judge / reply / vision routes each take your own key; no middle server.
- **Privacy stays on the device.** Keys live in app-private storage; chat text is sent only to the endpoint you configured, at analysis time, and never written to disk or logs.

## Platform support

| Platform | Status | How it reads | Notes |
|---|---|---|---|
| **LINE** | ✅ Full | Accessibility nodes (`LineAdapter`) | **Original to this fork.** Verified against a real device dump on 2026-09-25 (1:1 chat, Traditional Chinese UI); photos and stickers come through as "[照片]" / "[貼圖]" |
| X / Twitter DMs | ✅ Full | Compose node `content-desc` | 12.25, verified upstream, Chinese UI |
| Any other app | ✅ Manual | Overlay menu "screenshot OCR once" | No me/them split; everything is treated as the other side and flagged on the panel |
| **Windows: LINE desktop** | 🧪 Preview | Window capture + on-device OCR (see [Windows version](#windows-version-line-desktop-preview)) | Based on jev-chat-windows; LINE layout not yet verified on a real machine, "Fill" only copies to the clipboard for now |

It only reads chats on your own device that you are entitled to see.

## Quick start (Android)

**1. Get the APK.** Download the latest `jev-assistant-v*.apk` from [Releases](https://github.com/SanHsien/jev-chat-jarvis/releases) (Android 11+, ARM64 only), with a `.sha256` to verify it; or build it yourself (see Build below).

```bash
adb install -r jev-assistant-v1.4.10.apk   # debug-signed builds end in -debug.apk
```

**2. Keys.** App → Settings → endpoints. Fresh installs default all three routes to [Vercel AI Gateway](https://vercel.com/ai-gateway): put one Vercel key in the judge card, and reply and vision inherit it when left blank. Second choice is OpenRouter: pick "OpenRouter" on each card and enter an OpenRouter key. Every card has a one-tap connectivity test.

**3. Permissions.** On Android 13+, an app installed from a browser or file manager gets "App access denied" when you turn on accessibility or the overlay: first go to Settings → Apps → 對話副駕 → ⋮ (top right) → "Allow restricted settings", confirm, then turn them on (if there is no ⋮, tap 對話副駕 once in the accessibility settings first). Installing with `adb install` avoids the restriction. Then follow the home-screen guide:
- Accessibility (reads messages; after an upgrade, turn it off and on again so screenshots work)
- Overlay / display over other apps
- Autostart + unrestricted battery (required on Xiaomi / HyperOS, or the background gets frozen)

## Features

### Semi-automatic analysis (default)
- When a new message from the other side is detected, the overlay only shows **who the analysis is about** (the newest speaker in a group) and that message; tap "分析" (Analyze) to run the judgment and drafting, or "略過" (Skip) to fold the panel.
- **Why**: stickers, photos and one-word replies rarely need analysis, and sending every message automatically wastes tokens. Turn on "對方發訊息時自動分析" (auto-analyze) in Settings to analyze every message again.

### Judgment and candidate replies
- One judgment call returns: the other side's real intent, risk level (1–9), what they want, whether to reply now, and the best action, in about a second.
- A generative model drafts 3 conversational candidates; the judgment model ranks them.
- One tap copies or fills; filling uses `ACTION_SET_TEXT` and falls back to a clipboard paste, and **never sends**.

### Knowledge base and contacts
- **Notes**: pinned notes always go along; other notes go along when a tag or title appears in the conversation title or the last 6 messages, at most 5.
- **Contacts**: name / aliases / relationship / notes, matched against the conversation title.
- **History**: "record chat history (on-device only)" is off by default.
- Knowledge base and history live in app-private storage and can be wiped from Settings.

### Endpoints and models
- Judge / reply / vision each take their own address, key and model; reply and vision inherit the judge key when left blank.
- Judge presets: OpenRouter, TypeSafe direct, Vercel, OpenCode Zen, custom.
- Reply and vision presets: OpenRouter, Vercel, custom; both default to `google/gemini-2.5-flash`.

### Group chats
- In LINE groups each message is tagged with its speaker (from the avatar's "<name>的個人圖片"; follow-up messages in a run inherit it). X group DMs use the sender name directly.
- **The analysis is about the sender of the newest message from the other side**; everyone else's messages are context. The panel shows "群組：分析對象是「name」", and candidate replies address that person.
- A chat counts as a group when two or more named people speak, or the title carries a member count (such as "讀書會(12)"); a 1:1 chat sends exactly the same judgment input as before.

### Reading and OCR
- One adapter per app; the service dispatches by foreground package, and an adapter only turns the current window into "title + message list".
- When the accessibility tree has no text, the screen is captured and read by ML Kit's offline Chinese model; images are never uploaded.
- Any app can trigger "screenshot OCR once" from the overlay menu.

## Windows version (LINE desktop, preview)

> **Source**: based on JevChat-Windows ([https://github.com/jev-chat/jev-chat-windows](https://github.com/jev-chat/jev-chat-windows), by rezoch340 and the jev-chat contributors, MIT),
> its code is merged into this repository: the [`wingman/`](wingman/) package, `requirements-windows.txt`, packaging in [`tools/windows/`](tools/windows/) and upstream licenses in [`docs/licenses/jev-chat-windows/`](docs/licenses/jev-chat-windows/); file mapping and differences: [`docs/DIVERGENCE-windows.md`](docs/DIVERGENCE-windows.md). Not made or endorsed by the original authors.

A reply helper that sits next to LINE desktop: on-device offline OCR reads the conversation on screen → Jev judgment → 3 ranked candidates. The judgment core, question set and three-step flow are the same as the Android app.

### Status
- **LINE desktop only** (process `LINE.exe`); any other chat app is never read, captured or filled.
- **The LINE layout is not yet verified on a real machine**: locating the message area, me/them (green bubble = me) and group speaker names use upstream's pixel rules; turn on the debug view to check.
- **"Fill" only copies to the clipboard for now**; press `Ctrl+V` in LINE's input box. Automatic pasting turns on once LINE's input box position is verified (`VERIFIED` in `wingman/app/fill.py`).

### Install and run
- Requirements: Windows 10 1903+ / 11 (Windows Graphics Capture); LINE desktop open and not minimized (being covered by other windows is fine).
- Download `chat-wingman-windows-v*.zip` from [Releases](https://github.com/SanHsien/jev-chat-jarvis/releases) (same version as the APK), unzip it to a fixed folder and run `chat-wingman.exe`; the exe is unsigned, so in SmartScreen choose "More info" → "Run anyway".
- From source (at the repository root, Python 3.10–3.12; 3.13 does not work because RapidOCR 1.4 does not support it): `python -m venv .venv`, `.venv\Scripts\Activate.ps1`, `pip install -r requirements-windows.txt`, `python -m wingman`.
- The first launch opens Settings; enter two keys (stored only in the registry `HKCU\Environment`, never in a file):
  - **Judge · Jev** (`JEV_API_KEY`): OpenRouter (default, `typesafe/jev-1.13`) or TypeSafe direct (`jev-latest`).
  - **Draft · language model** (`LLM_API_KEY`): defaults to OpenRouter's `google/gemini-2.5-flash`; Vercel AI Gateway, OpenAI, Anthropic, Google Gemini or a custom OpenAI / Anthropic-compatible address also work (pick a model with "取得模型" for sources without a default).
- Other settings live in `config.json` next to the exe (in `wingman/` when run from source): relationship, speaking style, context size (3–30 messages, default 10), group reply target, check for updates on start (this repository's Releases), debug view, thinking mode for drafting (off by default).

### Using it
- A new message from the other side → the overlay shows the judgment summary (suggested action, likely intent, what they need, tension 0–9) and three candidates (with Jev's win probability) → "填入" (Fill) → **review, edit and press send yourself**.
- The overlay follows the current chat (its name is OCR'd from the window header); history and candidates are kept per chat. Groups carry speaker names; you can pick whom to reply to and prefix "@name " (plain text) when filling.
- The title-bar switch pauses capture; the bottom panel shows the live chat log so you can see what OCR read. Models are called only when the other side sends something new.

## How it works

```
LINE / X ──(accessibility nodes or screenshot OCR)──▶ recent messages
                                  │
              ┌───────────────────┴───────────────────┐
              ▼                                        ▼
   Jev judgment (7 questions at once)       generative model drafts 3 candidates
   intent / risk / need / action / reply-now     │
              └───────────────────┬───────────────────┘
                                  ▼
                        Jev ranks the 3 candidates
                                  ▼
                translucent overlay → copy / fill (never send)
```

The Windows version captures differently; the rest is the same:

```
Windows Graphics Capture grabs the LINE window (works when covered, not when minimized)
  → pixel anchors locate the message area (background, separators; light and dark themes)
    → OCR of the header gives the chat name
  → RapidOCR reads the message area on-device; bubble colour splits me / them, grey text
    (times, quotes, speaker names) is handled separately, scrolling is de-duplicated
  → a new message from the other side → Jev judgment → 3 drafts → Jev ranking → overlay
    → "Fill" (currently = copy)
```

Capture and OCR run in a separate child process; frames stay in memory and are never written to disk, logged or uploaded.

## Build

JDK 17 + Android SDK (platform 35 / build-tools 35); the checkout path must be ASCII-only.

```powershell
python -m pip install -r requirements-dev.txt
pwsh -NoProfile -File tools/dev_check.ps1          # full gate (includes gradlew :app:assembleDebug)
pwsh -NoProfile -File tools/dev_check.ps1 -Quick   # no APK build
```

Windows version (on Windows, at the repository root): double-click `tools\windows\build.bat`, or `pip install -r requirements-windows.txt pyinstaller` then `pyinstaller --noconfirm --clean tools/windows/wingman.spec`; the output is `dist\chat-wingman\`. Module self-tests: `python -m wingman.core.providers` (likewise `wingman.core.jev_client`, `wingman.core.llm`, `wingman.core.draft`, `wingman.core.engine`, `wingman.app.update`); CI's `windows` workflow runs them on windows-latest and builds the package, and releases attach the zip.

Layout: `app/` (the Android app), `wingman/` (the Windows version), `tools/windows/` (Windows packaging), `tools/` (this fork's maintenance tools), `tools/jev/` (Jev question set and calibration scaffold), `docs/` (development and maintenance docs), `tests/` (tests for the maintenance tools).

## Known limitations

- **WeChat is never read**: upstream users report that after its screen is captured, WeChat may turn on screenshot blocking for that device, and uninstalling this app does not undo it (upstream issues #42, #46, #47, #52). So the bubble does not appear in WeChat and manual screenshot OCR is unavailable there.
- **LINE is device-verified on 1:1 chats with the Traditional Chinese UI only**: groups, other UI languages, files and voice messages are not verified yet.
- **Background freezing on Chinese ROMs**: Xiaomi / HyperOS may kill the background service; the bubble briefly disappears and comes back after you interact with the chat.
- **X is verified on the Chinese UI only.**
- **Group chats**: the newest speaker is the analysis target, but the "relationship" setting is shared by the whole conversation; LINE group screens are not yet verified against a device dump, and a run whose avatar scrolled off screen is left with an unknown speaker.
- **OCR** needs the system to allow screenshots; protected windows (`FLAG_SECURE`) cannot be captured; only what is visible on screen is read.
- **Windows version**: the LINE layout is not verified yet (see above); Windows 10 draws a yellow WGC capture border that cannot be turned off (Windows 11 can, and pausing capture removes it); an input box taller than half the pane confuses the message-area detection; text on non-flat backgrounds (avatars, photos, stickers) is dropped; if OCR misses a group name line the message is attributed to the previous speaker; chats are keyed by the header title, so two chats whose names differ by one character merge; two identical consecutive messages from one person collapse into one; the judgment questions assume a 1:1 chat and drift in busy groups; there is no tray icon, closing the window quits.
- **APK size**: ML Kit's offline Chinese model makes the APK about 27 MB; only arm64-v8a is packaged.

## Versioning

`versionName` is `upstream major.minor.fork sequence` (currently `1.4.10`, based on upstream 1.4); see [`CHANGELOG.md`](CHANGELOG.md).

## License

MIT, Copyright © 2026 Finderchangchang and the jev-chat contributors; this fork's changes are maintained by SanHsien. See [`LICENSE`](LICENSE), [`NOTICE`](NOTICE), [`NOTICE.md`](NOTICE.md), [`CONTRIBUTORS.md`](CONTRIBUTORS.md). Privacy policy: [`PRIVACY.md`](PRIVACY.md).

Windows version (`wingman/`): MIT, Copyright © 2026 rezoch340 and the jev-chat contributors; see [`docs/licenses/jev-chat-windows/LICENSE`](docs/licenses/jev-chat-windows/LICENSE) and [`NOTICE`](docs/licenses/jev-chat-windows/NOTICE) (shipped in the zip as `LICENSE-jev-chat-windows` and `NOTICE-jev-chat-windows`). **The packaged exe bundles PySide6-Fluent-Widgets (GPLv3, free for non-commercial use, commercial use needs a paid license), so the Windows package as a whole is bound by GPLv3**; other third-party licenses are listed in that NOTICE. The released zip keeps `LICENSE`, `NOTICE`, `LICENSE-jev-chat-windows` and `NOTICE-jev-chat-windows`; the app's Settings → "關於與授權" (About & license) and the release notes credit the source.

**Acknowledgements**: [Jev Chat Assistant](https://github.com/jev-chat/jev-chat-jarvis) (the Android original; source of the Jev judgment core and question set), [JevChat-Windows](https://github.com/jev-chat/jev-chat-windows) (source of the Windows version), [RapidOCR](https://github.com/RapidAI/RapidOCR) (offline Chinese OCR), [windows-capture](https://github.com/NiiightmareXD/windows-capture) (Python bindings for Windows Graphics Capture), [PyQt-Fluent-Widgets](https://github.com/zhiyiYo/PyQt-Fluent-Widgets) (Windows UI components), [ML Kit](https://developers.google.com/ml-kit) (Android offline OCR).

**Disclaimer**: this project only handles chats on your own device that you are entitled to see. Use it on your own devices; do not install it on someone else's phone or computer to read their chats. Follow each chat app's terms of use and your local laws; app updates may break screen recognition. You bear the consequences of using this project.
