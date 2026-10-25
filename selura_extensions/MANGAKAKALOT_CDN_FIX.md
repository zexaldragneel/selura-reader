# Mangakakalot — repair exhausted CDN fallback error (Killer Peter, Chapter 75)

## Owner Android incident

2026-10-25 Seiryn Build #130 screenshot: failed download notification for **Killer Peter — Chapter 75** stating **"All CDN attempts failed."** The preceding notification showed download progress. Storage overview identifies an existing **Mangakakalot (EN) / Killer Peter** local manga folder. The screenshot alone does not reveal the exact page URL, failing CDN response codes or whether partial chapter files can be resumed.

## Exact pinned-source diagnosis

The literal error originates in **MangaBox.useAltCdnInterceptor()**, which Mangakakalot inherits from the pinned audited Keiyoushi Apache-2.0 source `ff521c17bb3e503c01e658e8fac00b60a95829f3`.

Identified defects in that code:

1. After an alternate CDN returns a successful HTTP response, the interceptor executes `return tryResponse` **inside** `chain.proceed(newRequest).use { ... }`. The `use` block closes that successful response and its body while returning it, leaving the reader/downloader unable to read the image.
2. It retries the original host again because it remains in the chapter-derived CDN set, making additional unsuccessful requests.
3. It creates alternate URLs with only the encoded path and fragment, dropping any query parameters that are needed for legitimate image URLs.
4. The shared live CDN set is mutated when a working host is moved to the front while it is being iterated.

The screenshot does not establish which of these triggered Chapter 75 or whether its public hosts were themselves inaccessible. Resolving source access restrictions is outside this work.

## Scoped fix

`selura_extensions/mangakakalot_cdn_fix.py` applies a **fail-closed, pinned-source** patch to the shared `MangaBox.kt` only in a checkout used to build **one** independently signed package: `eu.kanade.tachiyomi.extension.en.seluramangakakalot`. All other 42 published extension APKs remain byte-identical.

- Return successful fallback HTTP `Response` **open** so the downloader owns its body and may consume/close it.
- Close failed fallback responses, and take a synchronized snapshot of chapter-derived alternate CDN hosts before iterating.
- Avoid duplicate requests to the original hostname. Preserve original encoded path and query parameters when using alternate hosts already provided by the chapter.
- Do **not** switch hosts for **HTTP 401, 403 or 429** access/rate-limit restrictions; return the restriction rather than bypassing it.
- If the hosts genuinely fail, report an explicit Mangakakalot image-CDN error (including final HTTP status if available). No new hostnames, browser spoofing, Cloudflare workarounds, artificial retry loops, changes to allowed sources, or extra simultaneous network requests.
- Download worker, persistent chapter folder names, backup/source IDs, installed manga metadata, progress, categories, in-app update identity, offline chapter files and signatures are untouched.

## Release safeguards and tests

- Preserve original package `eu.kanade.tachiyomi.extension.en.seluramangakakalot`, source versionId **7301**, catalog source ID **5690172267177159639**, and original permanent extension signer SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`.
- Current public Mangakakalot extension baseline versionCode **109019**; require **strictly higher** Android versionCode for an in-place update, but never change source identity.
- Source-contract tests verify the old failure path is removed, successful response is returned open, HTTP 401/403/429 are not bypassed, queries retained, and no concurrent set iteration. Real pinned Kotlin Gradle `assembleRelease` and `lintRelease` must pass.
- Publish a signed **one-extension** immutable APK release, then via a separately audited store PR replace only Mangakakalot. Verify all other 42 APKs and existing 341 catalog source IDs and icons unchanged before publication.
- Phone acceptance: **Browse → Extensions → Mangakakalot → Update** without uninstalling; retry **Killer Peter Chapter 75**. Check whether the chapter loads and all downloaded pages open offline, and no other saved manga or bookmarks are lost. If the source continues returning access restrictions, report the real error; do not bypass it.

**Status:** code/test preparation under review. CI, store publishing and Android runtime checks must be recorded separately.
