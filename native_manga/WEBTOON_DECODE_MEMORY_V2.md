# Seiryn Reader Performance 2.0 — Phase 2: safer large-webtoon decoding

## Root cause in the pinned native code

In `app/src/main/java/eu/kanade/tachiyomi/data/coil/ImageDecoder.kt`, the webtoon strip decoder previously called `decoder.decode(sampleSize)` to allocate a full intermediate bitmap, and **only afterward** shrank/cut the resulting bitmap into strips under `MAX_PAGE_BYTES = 128 MiB`. An unusually tall, high-resolution original page can therefore allocate hundreds of MiB or more before the existing strip budget acts, increasing peak memory pressure and risk of `OutOfMemoryError` during continuous scrolling.

## Scoped change

- Only the `decodeStrips()` path of the original `ImageDecoder.kt` is modified, adding `boundedWebtoonDecodeSampleSize`. The helper calculates a conservative temporary bitmap ceiling of **96 MiB at 4 bytes/pixel**, starting from the *existing* decoder-requested sample size and multiplying by 2 only for unusually large pages.
- Default regular pages keep the original decoding and resolution; large pages may be downsampled somewhat earlier to control peak allocation. The function never decreases the originally requested sample size.
- Preserve the existing strip allocation budget (128 MiB), 4 MiB strip targets, decoder semaphore concurrency 1, original disk cache and image URL behavior, animated-image path, paged reader sub-sampling and zoom controls, renderer, bitmap cleanup and chapter download behavior.
- Source-contract tests check that only the image decoder is patched, the baseline decoder stays unchanged for ordinary/paged images, the memory cap reacts to very tall high-resolution panels, and pinned source changes fail closed instead of silently modifying a new upstream version.
- This is an **estimated decoded bitmap pixel budget**, not a guaranteed process-level RAM maximum. Decoder implementations may have additional internal allocations; the app still needs real Android memory/performance tests before claiming improvement.

## Safety and verification

The patch is stacked on the **owner-tested Seiryn Build #123** from Reader Performance 2.0 Phase 1 ([PR #97](https://github.com/zexaldragneel/selura-reader/pull/97)); Seiryn branding PR #94 and its source chain stay intact. No change to Android package `com.selura.manga`, permanent signing SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`, user manga data, source IDs, extensions, downloads, bookmarks, progress, backup format, store URL or signed update installer.

GitHub Actions must pass all source tests, a real Kotlin release compile, exact package and certificate checks, and release publication before distribution. After that, verify on Android: very tall/high-resolution webtoon scrolling, return-to-previous-page sharpness, regular paged reader zoom quality, animated chapter pages (if available), online and airplane-mode downloaded manga, and preserved library/history. Do not claim FPS, latency, memory or battery measurements that were not collected.
