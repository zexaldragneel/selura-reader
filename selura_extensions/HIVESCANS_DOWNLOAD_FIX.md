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

## Follow-up: public image HTTP cache efficiency — 2026-10-23

- **Current signed store baseline:** Hive Scans has Android package `eu.kanade.tachiyomi.extension.en.selurahivescans`, versionName `1.6.4028`, versionCode `110028` and immutable source versionId `7301`. Other 42 packages and the user's library remain unchanged.
- **Measured code bottleneck, not a measured device speedup:** The pinned Hive Scans adapter explicitly called `CacheControl.Builder().noCache().build()` on every image request. This forces revalidation rather than allowing OkHttp to reuse a still-fresh public image cache entry. We now generate `GET(page.imageUrl!!, headers)` and rely on the normal HTTP cache. **The server's no-store/no-cache, private, auth and expiration directives still apply.** We do not force cache storage, bypass auth, retry 403/429, change domains or increase image request concurrency.
- The existing chapter HTML `getPageList` parser, HTTPS and HiveToons-host checks and failure messages are unchanged. No manga/source ID, package name, signer, backup, download database or reading progress changes. The only functional extension change is to remove the forced image cache revalidation.
- The signed extension workflow uses a **monotonically higher** `versionCode` seed (4200 + workflow run number), checks current published versionCode `110028`, compiles and lints the real Kotlin extension, validates the original signed APK and publishes an immutable release. The catalog is not updated by the reader workflow.
- Next, publish only this verified new Hive Scans APK into `zexaldragneel/selura-extensions` while checking all 42 other APK digests and all 43 icons. User should then refresh the existing Selura Extensions store, update Hive Scans in place, and compare repeated public chapter loads; offline downloaded CBZ reading and library data must remain functional.
- **Performance and real-site behavior remain Android-unverified** until measured on the user's device. Network speed gains require a cacheable server response and an existing matching cache entry; some responses must still fetch over the network.
