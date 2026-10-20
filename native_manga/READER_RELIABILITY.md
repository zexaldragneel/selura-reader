# Native Selura reader reliability and extension update checks

## Objective

Make **real online chapter reading** more resilient without touching the library database, source identities, downloaded chapters, user-authentication flow, extension certificates, or the established Android package/signing certificate.

## Applied to pinned native Mihon engine

The dedicated `native_manga/optimize_reader.py` transformer runs **after** `native_manga/apply_branding.py` against the pinned Mihon 0.21.2 source mirror. It is fail-closed: refuses unexpected source shapes and validates all three source edits before writing.

1. **Online page transport failures:** In Mihon's existing `HttpPageLoader`, wrap page-list lookup, image URL resolution and `getImage`/disk-cache writes in a helper with **one delayed retry (450 ms)** strictly for `SocketTimeoutException`, `ConnectException`, or `EOFException`. A second failure surfaces normally. Do not retry HTTP 403/404/429, Cloudflare/interstitial responses, provider-specific errors or cancellation; preserve upstream per-provider rate limits and existing chunk concurrency.
2. **Chapter image cache capacity:** increase `ChapterCache`'s existing disk LRU from **100 MiB to 192 MiB**. Keep cache directory, key algorithm, cache format/version and LRU eviction unchanged. This is an upper disk usage bound, not offline downloads and not a guarantee that a provider has stable CDN links. No cache wipe occurs.
3. **Extension update notices:** Mihon's built-in `ExtensionManager.checkForUpdates()` already refreshes extension-store trust/listings and notifies when an installed extension has a newer signed version; Mihon already provides the extension **Update all** action. Trigger that existing check at launch and **at most once each 12 hours while the Activity is STARTED**, using `SystemClock.elapsedRealtime()` for process-lifetime throttling and lifecycle cancellation when backgrounded. Do not auto-download or silently install third-party extension APKs; installation continues through the trusted Mihon/Android user-approval flow.

The upstream reader's existing preloading strategy (small rolling download chunks and cancellation) remains untouched to avoid excessive requests. Changes do not use alternate CDNs, bypass access restrictions, or increase source concurrency.

## Validation gates

- Python patch contract tests and existing native tests must pass.
- Gradle `:app:assembleRelease` must compile actual Kotlin from the patched Mihon engine in GitHub Actions.
- `apksigner` must confirm the existing Selura SHA-256 certificate and AAPT must confirm `com.selura.manga` with monotonically increasing `versionCode`.
- GitHub must publish the signed immutable APK asset and only then is it a **build-verified preview**.
- **Owner Android device acceptance pending:** install over the existing Selura Manga (without uninstall); check online chapters on one reliable and one problematic source, fast swipe/scroll through multiple pages, reopened cache behavior, offline downloaded chapters, extension update badges and the manual update action. Periodic 12-hour checks require leaving the app foregrounded for that long; one startup check can be tested immediately.
- Preserve categories, bookmarks, history, reading positions, backups, existing 38 extension/source IDs and downloaded manga. Never state these are Android-verified without user confirmation.

## Limitations

An error caused by removed manga, expired domains, blocked sites, authentication or rate limiting is **not** automatically fixed by retries or caching. Network speed and online uptime are provider-dependent. This milestone improves specific normal transport/eviction cases and update notices; it does not claim to solve every extension failure.
