# Seiryn Reader Performance 2.0 — phase 1: bounded online image prefetch

## Observed source bottleneck

In the pinned native Mihon HTTP reader `HttpPageLoader.kt`, the earlier `loadByRollingChunked` implementation used `items.indices` whenever read-ahead was allowed. It then built an ordered list across **the whole chapter**, filtering only when read-ahead was disabled. Opening page 1 of a 300-page chapter could therefore stage up to 300 page fetches and repeatedly plan large lists. The former growing chunk size could launch up to five background pages concurrently; reader-held foreground fetches were additional. This is a **code inspection**, not a measured device benchmark.

## Implemented optimization

- Limit opt-in online read-ahead to **8 pages ahead + 2 behind** (up to 11 incl. current). With read-ahead disabled, retain **4 ahead + 1 behind** (up to 6 incl. current).
- Preserve foreground/current page first, then previous and next, and only create ordered sublists within these bounded windows. This removes O(chapter length) page scheduling and avoids remote image requests for unrelated future pages.
- Lower subsequent image fetch chunk sizes from `3..5` to `2..3` for less background concurrency. Keep original `launchLoadOnce`, cancellation/retry state restoration, tracked job identity, disk-cache version and size, and the prior one-retry-only rule for transient socket errors.
- Apply **after** existing `optimize_reader.py` and before unrelated native UI patches. Only `HttpPageLoader.kt` is changed in the pinned Android checkout. No chapter ID, source ID, downloaded pages, cache format, user data, database schema, backup, extension, CDN host, request header, signing identity, or Cloudflare bypass is introduced.
- The 192 MiB original modified disk LRU is retained, as are offline/local chapter readers and Webtoon/Pager bitmap rendering. This change can reduce unnecessary cache traffic and potential resource contention on long **online** chapters, but **FPS gains, memory reductions and real-world load-time improvements remain unmeasured until Android testing**.

## Verification and rollout

- Contract tests verify exact pinned source anchors, cancellation/retries, unchanged storage paths, no duplicate page scheduling, and at most 11 or 6 staged pages (including for thousands of pages).
- GitHub Actions must pass full native patch tests; real Kotlin `:app:assembleRelease`; original APK signer fingerprint `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`; application ID `com.selura.manga`; strictly increasing versionCode; and immutable APK release.
- Device acceptance: install over **owner-tested Seiryn Build #121**. Open a long online chapter, scroll forward/backward with webtoon and paged readers, jump near chapter end, check pages are present without stale error states, reopen an already-read page, and verify at least one fully downloaded chapter with networking disabled. Do not uninstall, delete cache/library, migrate sources or modify extension APKs.
- This is the first **targeted** Reader Performance 2.0 milestone, not a promise of all future performance features at once.

**Status:** code and isolated test contracts prepared; CI and Android-device results recorded separately.
