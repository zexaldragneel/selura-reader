# Doujins gallery and chapter reliability (one-extension update)

## Verified source bottlenecks in pinned Kotlin

The existing Doujins gallery assigns an entire HTML `srcset` string directly to `SManga.thumbnail_url`, even though valid `srcset` values may have multiple candidate URLs separated by commas and density/width suffixes. Passing that HTML expression to the image loader can cause failed covers, repeated attempts and unnecessary requests. The listing parser also dereferences optional artist markup with `!!`, so a slightly different listing card can throw an exception even when valid manga covers and titles exist.

Chapter parsing currently returns an empty list when its `.doujin` selector matches nothing, which can misrepresent an inaccessible/changed reader as an empty successful chapter.

## Focused implementation

- Resolve **one genuine HTTPS cover image URL** from the first `srcset` candidate, then fall back to `data-src` and `src`. Relative URLs resolve against existing `baseUrl`. No additional HTTP calls, request concurrency, cache policy, user-agent or CDN host changes. Invalid/blank candidates do not get passed directly to the image loader.
- Use null-safe access for optional gallery artist markup so listings survive layout variations.
- Report a clear `IOException` if the original public chapter page contains no matching image elements, rather than silently returning zero pages. Existing chapter image URL construction and page order are preserved **byte for byte**.
- No Cloudflare or Play Protect bypass, site authentication changes or new access workarounds. Google Play Protect may still recommend an APK scan.
- Based on audited Apache-2.0 Keiyoushi source at `ff521c17bb3e503c01e658e8fac00b60a95829f3`. Keep upstream attribution intact.

## Compatibility

Build **only** `en/seluradoujins`, keeping original package `eu.kanade.tachiyomi.extension.en.seluradoujins`, original source family `versionId 7301`, natural displayed name Doujins, and the original permanent signing certificate SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`. The published baseline is versionName `1.6.3004` / Android versionCode `109004`. Any new APK versionCode must exceed `109004`, and must install over the existing extension. The other **42** store APKs, all icons, the **341** source identities, Seiryn Build #125, library, bookmarks, backups, progress, downloaded chapters and NHentai migration remain unchanged.

## Release gates

1. Fail-closed original source pattern tests, original ID/source-family contracts, unchanged upstream source, one-module Gradle `assembleRelease` and `lintRelease`.
2. Original signer/package verification and positive Android versionCode increment. Publish only an immutable signed Doujins APK release.
3. Use separate audited store PR, compare original catalog fields, all other 42 APK SHA-256s, every icon and all 341 source IDs before publishing to the live store.
4. On phone: **Browse → Extensions → refresh → update Doujins in place**, open series with multiple covers, search and browse a chapter, check existing bookmarked manga opens and at least one downloaded chapter works offline. If Play Protect suggests a scan, choose **Scan app**; this release does not disable those prompts.
5. Do not claim improved loading speed, successful site access, or device acceptance until Android testing or actual benchmarks.

**Status:** code prepared; full CI/release and device acceptance tracked separately.
