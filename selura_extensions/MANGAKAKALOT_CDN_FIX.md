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


## October 26 follow-up — reduce source request bursts, not unlimited HTTP 429 retries

- **Confirmed phone behavior:** Owner uses signed Seiryn **Build #140**, installed versionCode 1140, which automatically resumes after HTTP 429 with 15 → 30 minute backoff; owner confirms auto-resume but Killer Peter **Chapter 68 (221 pages)** is still rate limited. Website/WebView loads. The difference from working Mihon is not yet proven; different extension versions, merge-image settings, source hosts, or server conditions can change outcomes.
- **Pinned Keiyoushi source inspection:** `src/en/mangakakalot/.../Mangakakalot.kt` configures `rateLimit(2, 1.seconds)`. The shared MangaBox `getPageList` contains an optional **Merge Split Images** preference (default **off**). When enabled, its chapter parser probes **every image URL** with a Range request to determine image dimensions *before* actual page image retrieval. On a 221-page chapter, this can add up to 221 extra requests; the existing client limiter applies to both probe and image traffic. The owner has **not confirmed** whether this preference is enabled; do not assume it is the reason for the current 429.
- **Isolated extension improvement:** The follow-up patch changes the Mangakakalot-only client setting to `rateLimit(1, 2.seconds)`, pacing all Mangakakalot traffic (including optional image-dimension probes) to about 30 requests per minute, rather than the earlier configured two per second. This trades a slower *successful* 221-page download for fewer request bursts and potentially much less time lost to source-side 429 blocks. **This is not a guarantee of success** and will not bypass a server restriction already in effect. The earlier CDN response-lifecycle fix remains intact. No new CDNs, user-agent/cookie tricks, rotating IPs, 429 auto-retry loops, or fabricated website permission.
- **Why no aggressive retry-on-429:** An HTTP 429 is a real response from the server telling the client to reduce request frequency. Infinite immediate retries make the same source restriction worse. Retry-After, if supplied, must be honored; no aggressive override should be added.
- **Compatibility:** Same package `eu.kanade.tachiyomi.extension.en.seluramangakakalot`, source versionId `7301`, original source ID `5690172267177159639`, original extension signing key, existing library/download entries, backup, progress and Seiryn app package remain unchanged. Only the isolated Mangakakalot APK is built.
- **Acceptance:** Source tests + Kotlin assembleRelease/lintRelease and signed identity verification before publication, then user test with **Merge Split Images off** and existing partial Killer Peter chapter still present. Do not clear/download anew unless explicitly safe and necessary.

## October 26 — Fix optional Merge Split Images HTTP response ownership

**Android evidence:** User confirmed Seiryn Build #140 + Mangakakalot v1.6.5519 successfully completed and opened Killer Peter Chapters 68 and 70 offline. Chapter 70.1 (9/176) subsequently received HTTP 429 and the source throttling remains unresolved. Do not confuse download success for two chapters with full source reliability.

**Pinned Kotlin defect:** MangaBox's optional Merge Split Images code reads each constituent image's `Response.body.byteStream()` and WebP dimension-probe response without closing the corresponding `Response`. For 100+ page webtoons, leaving those intermediate streams open can tie up HTTP connections and memory when Merge Split Images is enabled. This is a real resource ownership defect, **not evidence that the option is enabled for the owner** and not proof of the cause of source HTTP 429.

**Isolated repair:** Patch the existing Mangakakalot-only copy of MangaBox to wrap each constituent merged-image HTTP `Response` and size-probe HTTP `Response` in `use { }`; decoded Bitmap objects are recycled even when the canvas operation fails. The successful ordinary CDN fallback response is still returned **open** to Seiryn's reader, and the earlier response lifecycle fix is unchanged. This avoids enabling/disabling image merging, changing its image index mapping, or adding any network requests/retries.

**Boundary:** Respect HTTP 401/403/429 and user authentication; no IP/CDN rotation to evade website restrictions. Preserve source versionId 7301, source ID 5690172267177159639, package eu.kanade.tachiyomi.extension.en.seluramangakakalot, stable signing certificate, chapter queue, partial image files, bookmarks and offline manga. No unrelated APK is built.

**Verification required:** Python patch/identity tests, real pinned Kotlin `:assembleRelease` + `:lintRelease`, APK signature/package/source ID checks and a versionCode strictly newer than the public extension 111519. Only publish via audited store PR after full CI. On Android test Chapter 70.1 using existing partially downloaded files and confirm earlier Chapters 68/70 stay readable. Even after the repair, provider HTTP 429 may persist if Merge Split Images is disabled or the source is enforcing independent rate limits.

## October 26 — preserve genuine HTTP 503 when chapter CDN fallbacks exhaust

**Android evidence:** User installed the Seiryn Build #144 app and reports persistent `HTTP 503 during image transfer` at 12:56 PM; at 12:57 PM a new generic Downloader notification appears with no confirmed success. An additional `4 updates failed` notification is visible but is **not proven to be caused by the same source**. The one-minute WorkManager notification confirms only the scheduling code, not completion of the chapter. The earlier `Connection: close` experiment (PR #134) has not shown meaningful improvement.

**Audited source-side error-classification defect:** Current published Mangakakalot fallback creates a normal response from the image server. When `cdnSet` has alternate, chapter-provided CDNs, the fallback first closes the original response, tries the alternates, then if all fail it throws a generic `IOException`, **even if one or more CDNs returned actual HTTP 503 or another transient 5xx response**. The native downloader's `isTransientDownloadFailure(HttpException)` and server `Retry-After` support cannot reliably classify that synthetic error. This is a concrete *response preservation* bug, not proof that the host will start serving images.

**Scoped repair:** Keep only the latest real transient 5xx `Response` open while trying the same existing chapter-provided alternate CDNs. On a successful CDN return, close the held error and give the successful response body to the downloader. On 401/403/429, close held error and return that rejection untouched. On another 5xx, close the previous held error and hold the new response. On complete CDN exhaustion, **return the held genuine 5xx response open** (including Retry-After) instead of throwing `IOException`. Each superseded intermediate body is closed. A synthetic IOException remains only when there is no real transient HTTP status to pass along. Does not change CDN list/URLs, max requests, source access, rate limits, timeout policy, chapter pages, sources or signing identities.

**Test and publication gates:** Require fail-closed source contract tests, actual Kotlin compile/lint, signer and APK package/version validation. The signed test APK must use Android versionCode > 111810 (higher than public 111522, prior experimental image connection build 111609, and signed rollback build 111810). Public store stays unchanged until an actual Android test, and partially downloaded chapters are never deleted or migrated. No claim that server 503 can be bypassed; its restrictions must be respected.

## October 26 4:51 PM — confirmed failing image host and chapter-scoped fallback

**New direct evidence:** The user installed Seiryn Build #149 and sent an Android notification: `HTTP 503 from img-r2.2xstorage.com during image transfer. Retrying the saved chapter after 1 minute(s); download queue preserved.` This confirms the **hostname-only CDN diagnostic works on the actual device**. It does not prove the 503 is caused by the extension, or reveal the current chapter/page number. An HTTP 503 can be a legitimate remote host outage/overload. The reader does not control that server.

**Source defect confirmed by audited pinned MangaBox Kotlin:** `cdnSet` is a **source-wide mutable set**, and each `getPageList` appends every chapter's `cdns` and `backupImage` host values. The fallback interceptor then tries the entire accumulated set when any page fails. Consequently, a failed image for the current chapter can cause unrelated requests to stale hosts collected from completely different chapters; it can also expand attempts as more manga are read. This is an actual scope/request-amplification flaw, although it does not establish the initial `img-r2.2xstorage.com` 503 cause. Keiyoushi issue #7896 documented historical image-host differences, not that any particular host is working in October 2026.

**Scoped correction for isolated Mangakakalot APK:** After PR #138's existing 5xx response preservation, replace the global host set with a bounded, thread-safe 128-chapter LRU keyed to the exact parsed chapter URL. Record only HTTPS CDN hosts explicitly advertised in that chapter's own page data, and attach its immutable host snapshot to the already-tagged image request. The existing fallback may try only these current-chapter candidates, excluding the original requested host and duplicates. Optional WebP probes reuse the current chapter's parsed host list. Preserve existing Referer, source URLs and encoded image path/query, HTTP 401/403/429 rejection semantics, transfer of successful 200 and final genuine 503 open responses, preexisting request pacing, and server-provided Retry-After. This **can only reduce**, never increase, fallback requests; no proxies, new hosts, Cloudflare/authentication bypass, source migration or changes to offline chapter files.

**Data/installation:** Original package `eu.kanade.tachiyomi.extension.en.seluramangakakalot`, original source ID `5690172267177159639` and versionId `7301`, original V2 signing certificate, Seiryn app ID `com.selura.manga`, all read history/library/offline and queued/partially downloaded chapters remain intact. The user previously confirmed Mangakakalot v1.6.6126 installed; require a strictly higher Android versionCode (above 112126). CI Python contract tests, Kotlin compile/lint, original signature verification and immutable signed APK release must succeed before proposing Android installation. Do **not** merge to public extension store before owner testing, or claim the origin server's HTTP 503 has been fixed.
