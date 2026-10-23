# Hive Scans (HiveToons) chapter download repair

Reported 2026-10-22: Selura Manga user says Hive Scans chapter downloads do not work.

## Investigation
- Public HiveToons 2.0 reader at `https://hivetoons.org/series/the-constellations-are-my-disciples/chapter-161` currently exposes 32 page images via `img` elements whose accessible page descriptions contain "Page N"; the image URLs use `storage.hivetoon.com`.
- Pinned Keiyoushi `src/en/hivescans` inherits Iken's old `/api/chapter?chapterId=...` page-list implementation. The site's currently presented reader uses HTML page elements; old API reliability for this exact user error is not independently confirmed.
- Earlier Keiyoushi issue #13548 describes blank chapter image URLs and failed downloads, fixed upstream in early 2026. That historic bug does not establish this failure's precise HTTP exception.

## Implementation
- `hivescans_download_fix.py` reuses the existing pinned and licensed `orphaned_sources.py` module transformer. It only modifies copied, isolated `selurahivescans` Kotlin source and fails closed if the approved upstream class changes.
- Uses original persisted `chapter.url` before the legacy `#id` suffix to retrieve the user's public HTML reader page with `client.get`. Extracts sequential pages with an explicit `Page N` alt-label filter, supports lazy `data-src` and `src`, accepts only HTTPS URLs on observed HiveToons-owned hosts, rejects empty lists, and never silently fabricates blank pages.
- Does not log in, solve captchas, bypass 403s, or scrape private/locked chapters. Existing image-request behavior is retained.
- APK Android package `eu.kanade.tachiyomi.extension.en.selurahivescans`, source-name, source ID and version-ID family `7301` remain unchanged. A higher versionCode permits a normal APK upgrade.
- No native Selura application rebuild is required; this is one extension APK.
- Tests check the pinned source transform, fail-closed behavior, unchanged original files and package/source ID invariants. Single-extension CI compiles Kotlin and lint, checks package/signing fingerprint `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`, and publishes one signed APK.

## Acceptance gates
1. GitHub Python contract tests and Kotlin Gradle build/lint succeed.
2. APK signer, package and increasing versionCode verified.
3. A separate extension-store publishing PR changes **only** Hive Scans version metadata and APK bytes, leaving 42 other APKs, all icons, source IDs and original store URL unchanged.
4. On Android, refresh extension list and upgrade Hive Scans in place. Download a complete public chapter, open all downloaded pages offline, and confirm progress/bookmarks and library entries remain.
5. If the site blocks the public chapter request, do not bypass it; capture the HTTP status/error and report that the website may restrict access.

Do not claim device functionality before step 4.

## Emergency rollback following Cloudflare error report — 2026-10-23

- After the owner installed the cache-optimized Hive Scans v1.6.4229, the owner reported **"failed to bypass cloudflare"**. The exact failing URL and request type have **not** been captured. There is no proof the `noCache()` removal caused the challenge; site-side access policy and device connectivity remain alternative causes.
- Live public `https://hivetoons.org/` and a public chapter URL were readable through a separate web client in the investigation, but accessibility from this environment does **not** establish Android/IP-specific accessibility, nor does it authorize bypassing access controls.
- This rollback builds the **same pinned Hive Scans implementation used before optimization** (original public HTML `getPageList`, canonical folder/source IDs and `CacheControl.Builder().noCache()` for images). The code from `feature/selura-hivescans-html-downloads` is reused without changing the manga reader or third-party source authentication. It does not attempt to defeat Cloudflare, rotate user agents, scrape protected routes, solve CAPTCHAs or alter HTTP client identities.
- The new independently signed Hive Scans APK must have **higher Android versionCode than 110229**, preserve package `eu.kanade.tachiyomi.extension.en.selurahivescans`, source versionId 7301, signer, and immutable source ID. This avoids uninstalling and resetting stored entries.
- Only after passing source tests, full Kotlin build/lint, APK signature/identity checks, and existing store's invariants may the single Hive Scans APK be published. The other **42 extension APKs, 43 icons and all 341 source identities** must remain unchanged.
- The user must refresh Hive Scans only and retry one publicly accessible chapter. If Cloudflare still blocks loading, classify the problem as an unresolved challenge; open the source website in the normal browser/WebView to see whether the site allows legitimate access and do **not** automatically retry, delete downloads or claim success.

