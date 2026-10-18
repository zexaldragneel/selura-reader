# Keiyoushi compatibility — implementation boundary

This feature is being developed for the owner's personal Android Selura reader.

## Verified upstream format
- Official repository: https://github.com/keiyoushi/extensions
- Current repository index: https://github.com/keiyoushi/extensions/raw/repo/index.pb (protobuf, version 2).
- The legacy `index.min.json` on the `repo` branch contains only compatibility notices. It must not be used to advertise a complete extension catalog.
- Upstream extensions are Android APKs intended for Mihon, TachiyomiSY and certain compatible forks. An APK URL or package installation alone does not implement a source within Selura.
- Official setup: https://keiyoushi.github.io/add-repo; compatible reader: https://mihon.app/download/.

## What this milestone actually delivers
- A safe companion page in Selura that explains the limitation and offers one-tap official setup URLs and clipboard copy of the protobuf index URL.
- Improved **native Selura MangaDex** chapter discovery: selectable translation language, 100-row offset pagination, and explicit missing-chapter/external-host messaging.
- No downloading, installing, dynamically executing, loading, or silently trusting Keiyoushi Android extensions inside Selura. A guide is not equivalent to native plugin support.
- All current local EPUB/PDF/CBZ data stays private, offline and unchanged.

## Requirements for a *future* native Keiyoushi runtime
These are unresolved engineering milestones, NOT implemented in this PR:

1. Adopt or implement a licensed, version-compatible Android extension host API (Mihon source models, HTTP middleware, extension interfaces), including Gradle dependencies, exact ABI, and Kotlin/Flutter platform-channel methods.
2. Parse the `index.pb` v2 format and validate the repository signing fingerprint; cryptographically verify every selected APK's provenance and update identity before allowing user-authorized installation.
3. Account for package visibility, Android component isolation and the broad privileges of extension code. Treat every extension as executable third-party code with unrestricted app access and avoid silently loading it into the process.
4. Implement source search, manga detail, chapter feed, page URL and image request interception (Referer/cookies) without bypassing providers' authentication, anti-bot, age verification or terms.
5. Add per-extension sandbox testing, crash containment, opt-in privacy disclosures, network timeouts and update/rollback handling.
6. Supply an instrumented Android integration test and a signed APK; get the owner's explicit physical device verification before merging.

This architecture will be revisited only if the owner wants a **fully native plugin host inside Selura**, instead of using the official Mihon companion workflow. Do not claim this PR provides that native host.

## Sign-off
- Android app ID: `com.selura.reader`
- Keep permanent signing identity unchanged; keep `shared_preferences_android 2.4.28` pinned.
- User declined highlights/annotations. Do not add them as part of the manga integration.
