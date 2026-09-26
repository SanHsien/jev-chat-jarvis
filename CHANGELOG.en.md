# Changelog

[中文](CHANGELOG.md) | English

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions are
`upstream major.minor.fork sequence`: `1.4.0` is release 0 of this fork on top of upstream 1.4;
later fork releases are `1.4.1`, `1.4.2`, …. Upstream history for 1.0–1.4 is in the upstream
repository's `CHANGELOG.md`.

## [Unreleased]

## [1.4.11] - 2026-09-26

### Changed
- **The overlay no longer opens by itself**: scrolling a LINE chat does not pop up the panel anymore. Tap the bubble to open it; it then works out who would be analyzed and offers "分析" (Analyze) / "略過" (Skip); models are called only on "分析".
- **Windows is semi-automatic too** (like Android): a new message only shows who would be analyzed plus an "分析" (Analyze) button; Settings gains "對方發訊息時自動分析" (auto-analyze, off by default). Changing the reply target no longer re-runs the analysis in semi-automatic mode unless that chat was already analyzed.
- The repository history is a single root commit (upstream's 143 commits no longer show); the divergence checker fetches the upstream baseline when needed.
- Triaged Android upstream PR #64 (conversation-bound analysis; this fork already fixed the same issue in 1.4.5, adopting upstream's version is deferred).

## [1.4.10] - 2026-09-25

### Added
- **The Windows version ships with the Release**: `chat-wingman-windows-v1.4.10.zip` (same version as the APK), based on jev-chat-windows and limited to LINE desktop; the LINE layout is not yet verified on a real machine, so "Fill" only copies to the clipboard for now.
- The Windows version checks this repository's Releases for updates on start (can be turned off in Settings).
- Windows: SOCKS proxy support (upstream PR #15); filling clicks the primary button correctly when mouse buttons are swapped (upstream issue #34).
- Windows follows its upstream's copyright and license terms: a new "About & license" section in Settings, the READMEs and release notes say "based on JevChat-Windows" and explain the GPLv3 component, and the zip keeps the upstream LICENSE / NOTICE; the READMEs gain acknowledgements and a fuller disclaimer.
- Every branch, PR and issue of the Windows upstream is triaged and recorded in `docs/UPSTREAM.md`.

### Changed
- The Windows version is no longer a project inside the project: its code is the `wingman/` package (`python -m wingman`), and dependencies, packaging, licenses, ignore rules and CI live at the repository root; the icon now uses the new logo.
- The READMEs now cover the Windows version: source, install, settings, usage, how it works, known limitations and license; PRIVACY gains a Windows section.

## [1.4.9] - 2026-09-25

### Added
- **Windows preview**: jev-chat-windows merged into this repository (the `wingman/` package) and adapted to LINE desktop only; drafts default to OpenRouter + `google/gemini-2.5-flash`; Traditional Chinese UI. The LINE layout is not yet verified on a real machine, so "Fill" only copies to the clipboard for now. The `windows` GitHub Actions workflow builds the exe as an artifact.

### Changed
- **Semi-automatic analysis by default**: a new message from the other side shows who would be analyzed and the message, and nothing is sent until you tap "分析" (Analyze); "略過" (Skip) folds the panel. Stickers, photos and messages that need no reply no longer spend tokens. Upgrading turns auto-analyze off once; you can turn it back on in Settings.
- Renamed to "Chat Wingman" (對話副駕), no longer tied to LINE. The package name is unchanged, so it installs over the old version.

## [1.4.8] - 2026-09-25

### Changed
- Renamed to "LINE Chat Copilot" (LINE 對話副駕): app name, home title, the ongoing notification and the READMEs no longer use upstream's "Jev Chat Assistant" as the product name (the attribution stays). The package name is unchanged, so it installs over the old version.

## [1.4.7] - 2026-09-25

### Removed
- Trimmed the endpoint presets to OpenRouter, TypeSafe direct, Vercel, OpenCode Zen and custom (judge) and OpenRouter, Vercel and custom (reply / vision). Removed: Bocha Jev (judge), DeepSeek official and Tongyi-compatible (reply), Tongyi-compatible (vision).
- Reply and vision default to `google/gemini-2.5-flash` (on both OpenRouter and Vercel).
- One-time migration on upgrade: a route still pointing at a removed preset moves to Vercel AI Gateway and its key is cleared (enter a Vercel key again); a DeepSeek / Qwen model on OpenRouter / Vercel becomes that route's default. Models on custom endpoints are left alone.

### Added
- Settings → "About & privacy" credits the upstream project ("based on Jev Chat Assistant") and its license, with "Upstream project" and "License & notice" buttons; the APK ships `LICENSE` and `NOTICE`. Release notes carry the credit too.

### Changed
- New logo and app icon; upstream screenshots that do not match this fork were removed from the README.

## [1.4.6] - 2026-09-25

### Changed
- All app UI text and `PRIVACY.md` are now Traditional Chinese (Taiwan usage); candidate replies and summaries are asked for in Traditional Chinese too.

### Added
- On Android 13+, sideloaded apps hit "restricted settings" when turning on accessibility / the overlay: the home screen now shows a guide while those permissions are off, with a button to App info, where ⋮ → "Allow restricted settings" lifts it.

## [1.4.5] - 2026-09-25

### Fixed (upstream issue #61)
- Analysis results appear only in the conversation that started them; after switching chats an old result no longer shows up, and tapping a candidate can no longer fill another chat (it asks for a fresh analysis instead).
- A message that arrives while an analysis is running is analysed right after it, instead of being dropped.
- While a new chat is still loading (a transient title such as "Connecting…"), it no longer borrows the previous contact's name, so history is not written into someone else's log.

## [1.4.4] - 2026-09-25

### Added
- **Speaker-aware group chats (original to this fork)**: LINE takes each speaker from the avatar's "<name>的個人圖片" and carries it across a run; X group DMs use the sender name.
  The analysis now targets the sender of the newest message from the other side, with everyone else as context; Jev's judgment gets the speakers and the focus person, candidate replies address that person, and the panel names them.
  A 1:1 chat sends exactly the same judgment input as before.

## [1.4.3] - 2026-09-25

### Added
- **LINE automatic reading (original to this fork)**: `LineAdapter` completed and enabled from a real device dump (2026-09-25). Reads the conversation title and text messages; photos and stickers come through as "[照片]" / "[貼圖]"; me/them is decided by LINE's read-receipt and timestamp markers on each row. Covered by a JVM unit test.

## [1.4.2] - 2026-09-24

### Fixed
- WeChat is blocked again: no bubble, no read, no screenshot inside WeChat. Upstream users report that capturing WeChat makes it turn on screenshot blocking for the device (upstream issues #42, #46, #47, #52); lifting the block in 1.4.1 was a mistake.

## [1.4.1] - 2026-09-24

### Fixed (adopted from unmerged upstream PRs)
- Switching contacts no longer reuses the previous conversation's analysis: the dedupe signature includes the title (upstream #6).
- Leading numbers in candidate replies (such as "1.5 hours") are no longer stripped (upstream #21).
- When the accessibility service disconnects, the home screen says "reader not connected" instead of "ready", and a failed keep-alive is reported (upstream #35).
- Signing is enabled only when `JEV_KEYSTORE_PROPS` is set, so Linux / macOS builds no longer fail on a Windows path (upstream #32).

### Changed
- QQ support and the WeChat block list removed; the README warns against manual screenshot OCR inside WeChat.

## [1.4.0] - 2026-09-24

Based on upstream `jev-chat/jev-chat-jarvis` 1.4 (`a3026e2`).

### Added
- **LINE support (original to this fork)**: manual mode works (overlay menu "screenshot OCR once"); the `LineAdapter` auto-mode skeleton is in place and will be enabled after device verification.
- "Vercel" presets for the reply and vision endpoints; fresh installs default all three endpoints to Vercel AI Gateway once.
- GitHub Releases carry the APK and its `.sha256` (`release` workflow); every CI build also uploads a debug APK.

### Changed
- Build toolchain upgraded: AGP 9.4.1, Gradle 9.7.1 (AGP built-in Kotlin), AndroidX appcompat 1.8.0, material 1.14.0, constraintlayout 2.2.2.
- The accessibility service now uses the app's own class name (`com.jev.probe.capture.ChatCaptureService`) instead of posing as a system component; **after upgrading from an older build, turn accessibility on again**.
- The privacy policy and in-app links now point to this fork.

### Removed
- WeChat, Feishu and QQ adapters, related code and documentation.
- Upstream's prebuilt APK, upstream's website source (`site/`), upstream's internal planning documents and the Simplified Chinese README.
