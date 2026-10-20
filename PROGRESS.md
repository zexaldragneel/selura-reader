# Selura — Development Progress
Last updated: 2026-10-20

## Slow NHentai pages — follow-up iteration 2 (2026-10-20)
- Owner reports first Selura NHentai extension still slow. Possible cause in our own initial fix: up to 10 sequential CDN image attempts with default timeouts; no packet capture or precise page data yet.
- New versionCode 2: at most 3 provider-declared CDN hosts, 1 attempt per host, 4s connect/9s read timeouts, stop scheduling more attempts once ~18s elapsed, remember a successful CDN, retry only CDN 404/408/410/5xx/HTML-instead-of-image. Never retry 401/403/429. Log only host/status; do not log sensitive gallery URL/header data.
- IMPORTANT: existing Library manga remain bound to original Cursed Yuzono NHentai source IDs. User needs to test via **Browse → Sources → Selura NHentai** or the old extension will still be used.
- **Verified CI for version 2:** GitHub Actions source build **#12** run `39392347725` (head commit `1c7c611cd242d90659f952f998eff883071bccf8`) completed SUCCESS after repairing an outdated contract test assertion (commit `66f65d6`) and Kotlin import-order formatting (commit `1c7c611`). Passed source contract tests, Java 25 Gradle Android assembly, independently signed Android package/fingerprint verification, artifact upload, and prerelease publication.
- **Version 2 direct download:** https://github.com/john-selwyn/selura-reader/releases/download/test-selura-source-pr-25-run-12/selura-nhentai.apk (51,543 bytes; SHA-256 `827aa8a8f3ae2745ca9e810a89427bf08ee753ed90e8b8ebe8a0930b8dd276c6`). Package `eu.kanade.tachiyomi.extension.all.seluranhentai` uses the same Selura signing certificate as pilot v1, bumped extension versionCode to 2 for Android upgrade.
- **Still unverified:** actual gallery image-loading speed and completeness in v2 on Android. User must open a title directly from **Browse → Sources → Selura NHentai** rather than pre-existing Library entries bound to Cursed Yuzono. Keep original extension and library intact; record first-page load time, problematic page/error and Wi-Fi-vs-mobile-data if still slow.

## Cursed Yuzono NHentai.net repair pilot — PR #25 (2026-10-20)
- **Exact source identified by Android screenshots:** installed failing provider **NHentai — Cursed Yūzōnō 1.4.62**, targeting `https://nhentai.net`; separately installed `nHentai.com (unoriginal) — Keiyoushi 1.6.1` is NOT the same source. The former `nhentai.to` pilot targeted the wrong site and is retained only as unused experimental code; do not install it for this issue.
- **Verified upstream source:** `yuzono/cursed-manga-extensions@5dad5cf65dce98bb05ba8edf1f38770585e032b9`, `src/all/nhentai/NHentai.kt`, with original Apache-2.0 license. Upstream `pageListParse()` constructs image URLs with `$imageServer`; original getter returns `nhConfig.imageServers.random()`, which chooses a possibly different CDN for each gallery page. This is a testable candidate cause, not confirmed by packet capture.
- **Selura implementation:** First-party Kotlin source files in `selura_sources/nhentai/`, Yuzono-pinned fail-closed copier in `selura_sources/apply_source.py`, own build workflow `.github/workflows/selura-sources.yml`. Different signed package `eu.kanade.tachiyomi.extension.all.seluranhentai`, name **Selura NHentai**, with *different source IDs* from original so the existing library and extensions are not overwritten. Copies original manifest-resources/proguard into build checkout, retains Yuzono original.
- **Reliability changes:** choose a consistent image CDN host once per gallery; bound image retries to 2 attempts per candidate and up to 5 distinct hosts from the source's own nHentai API config, all HTTPS and restricted to nHentai image domains; do not retry or circumvent HTTP 401/403/429. Fail with a clear incomplete-gallery error when API returns fewer page records than advertised.
- **Verified GitHub Actions:** Build #8, run `39390201876`, completed **success** on `45ec93f7df98f6d10686c1a383d39484389b89b3`; source contracts, Java 25 Gradle `:src:all:seluranhentai:assembleRelease`, SHA256 signing-certificate check, Android package verification and GitHub release publication all succeeded. Direct separate source APK: https://github.com/john-selwyn/selura-reader/releases/download/test-selura-source-pr-25-run-8/selura-nhentai.apk (51,095 bytes; SHA-256 `25fb6b2ba8e6331b8d8059059287af256a0ffd26dac85f8673c5f350f532016a`).
- **Next acceptance:** owner installs and authorizes the distinct Selura NHentai APK, browses source from Browse, opens same gallery in Selura vs website, checks every page and time to load, and reports any HTTP/error state. Actual on-device behavior of the **new** source remains UNVERIFIED. Do not delete old Yuzono NHentai, install over its APK, silently migrate source IDs, or claim that the source works until user tests.
- **Owner-verified Selura baseline:** Mihon .tachibk library restored after clearing downloaded-only filter, chapter images load, reading progress and resume work, downloaded manga reads offline. Native Selura APK build #12 `39386818560` also succeeded and published a signed APK. Keep original manga library, history and package IDs intact.



## Repository
https://github.com/john-selwyn/selura-reader

## Verified baseline
- Flutter/Dart offline-first Android reader with local EPUB/PDF import.
- EPUB reading with table of contents through `epub_view`.
- PDF reading through `pdfx`.
- Imported books are copied into app-private storage.
- Missing local files are filtered from the library.
- EPUB reading position is persisted as EPUB CFI and restored on reopen.
- PDF current page is persisted and restored on reopen.
- Direct `.apk` prerelease publishing is enabled for main and same-repository pull-request builds.
- User has device-tested EPUB/PDF import, reading, and automatic resume successfully.

## Android application identity milestone
- Pull Request #5 (`fix/android-app-identity`) was squash-merged to `main` at `c0fcd6f46fd514cff182c10606a38bced2a581b1`.
- Final Android namespace/application ID is `com.selura.reader`.
- Launcher label is `Selura`.
- Android project scaffold is committed to the repository instead of being regenerated during every normal CI build.
- CI verifies the committed application ID, MainActivity package, and launcher label before Android compilation.
- Build #28 (run `39045696185`) passed identity checks, dependency resolution, `flutter analyze`, debug APK compilation, artifact upload, and direct APK prerelease publishing.
- Build #30 also passed for the finalized PR #5 branch.
- User installed and tested the corrected-package APK successfully before merge.
- Post-merge main Build #31 (run `39047362727`) has passed identity checks, dependency resolution, and source analysis; Android APK compilation was still running at the last check.

## Completed milestone — Premium bookshelf
Pull Request #7 (`feature/premium-bookshelf`) was squash-merged to `main` at `073c0b0ca9a7816f6c8aaf3209fe7863f88f5fee` after the user confirmed the test APK works on Android.

Implemented and device-tested:
- Premium responsive bookshelf UI with grid and list layouts.
- Grid/list preference persists locally.
- Search by book title or format.
- Sorting by recent, title, favorites, or format.
- Persistent favorites.
- Continue Reading carousel driven by per-book last-opened metadata.
- Library surfaces saved PDF page state and EPUB resume availability.
- Improved empty-state/import experience and extended import action.
- Format-aware cover cards for EPUB/PDF while real embedded-cover extraction remains a follow-up.
- Existing EPUB/PDF readers and auto-resume behavior remain intact.

Commits:
- `b8869df73bd20d8f472031bb1e202cde2c494729` — initial premium bookshelf implementation.
- `8c1ab3afe18e182c2a3afadfb24b2f9a8e9869cd` — corrected sort-index syntax/state handling, added explicit switch exits, and fixed search clearing with a controller.

CI status:
- Build #32 (run `39047510035`) failed at `flutter analyze` with `Expected to find ']'` in the first bookshelf revision. Android compilation was skipped.
- The syntax issue was fixed in `8c1ab3afe18e182c2a3afadfb24b2f9a8e9869cd`.
- Build #33 (run `39047653966`) completed successfully.
- Build #34 (run `39048049148`) completed successfully for the final PR #7 head, including `flutter analyze`, Android APK compilation, artifact upload, and direct APK prerelease publishing (`test-pr-7`).
- User confirmed PR #7 test APK works on Android; merged with squash commit `073c0b0ca9a7816f6c8aaf3209fe7863f88f5fee`.
- Post-merge main APK build: pending verification.

## Completed milestone — Embedded EPUB cover thumbnails (Pull Request #8)
- PR #8 (`feature/epub-cover-thumbnails`) squash-merged to main as `c9d29173690f259af4f67e3ac3f374953143ff2f` after successful user device testing.
- `lib/cover_cache.dart` reads the EPUB container/package manifest and extracts only the declared cover image from EPUB 2 (`meta name="cover"`) or EPUB 3 (`properties="cover-image"`).
- Cover extraction, image decode and resizing run in a Flutter background isolate. Thumbnails are JPEG-compressed with a maximum 720px longest side.
- The app caches thumbnails locally under application support storage keyed to the book path, size and modification time; missing/unsupported covers use the existing book artwork without crashing.
- Existing EPUB imports are warmed lazily; newly imported EPUBs generate covers after the bookshelf appears. Covers display in Continue Reading, grid, and list views.
- EPUB files above 128 MiB and embedded cover files above 16 MiB are skipped for memory safety.
- Added tests for EPUB 2 and EPUB 3 declared covers, aspect-preserving downsampling, non-upscaling, and corrupt-file fallback; `flutter test` now runs in CI.
- Main commits: `5910d44562596592c3b4420fb175e819f22e6f82` (cache implementation), `92507a53f4895d5d58d04873d5918bd0870d9fab` (EPUB 2/3 package parsing), `4537d6fc308445102b83fbc1c61a4148de097148` (dual-format regression tests).
- Builds #37 and #38 caught missing async and Image import conflicts; fixed in `d7dc6e7e2a8567f71752b9fe9bb09183ac2aa7c9`.
- Build #39 surfaced an EPUB fixture failing in the older EPUB 2-only reader; replaced extraction with manifest-based ZIP parsing.
- **Build #43** (GitHub Actions run `39078336724`) passed source analysis, EPUB cover regression tests, Android debug APK compilation, CI artifact upload, and direct APK prerelease publishing.
- Test APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-8/selura-debug.apk
- APK SHA-256 from release: `385e818184f70792a76001b2e22ca452c5ec040fc51e318117fbc06646b439ed`.
- Runtime result: user confirmed on-device real EPUB cover display (screenshot), cover persistence after offline restart, and correct reading-position auto-resume. Missing-cover fallback and every EPUB variation have automated tests but not all were individually device-tested.

## Completed milestone — Offline EPUB/PDF bookmarks (PR #9)
- Pull Request #9 (`feature/local-reader-bookmarks`) squash-merged into `main` at `e9bcc5a365f53e01f26a9f23cceb33e38f83a2ad` after successful user device testing.
- Added `lib/bookmarks.dart`: per-book SharedPreferences bookmark storage, duplicate-location handling, malformed-record isolation, deletion and bookmark list UI.
- EPUB reader: save current EPUB CFI, show saved positions and jump to a CFI with `gotoEpubCfi`.
- PDF reader: save current page, show saved pages and jump using `PdfControllerPinch.jumpToPage`.
- Existing EPUB/PDF auto-resume and bookshelf are unchanged; bookmarks have independent local storage.
- Regression tests in `test/bookmarks_test.dart`: persistence across reads, isolation per book, deduplication, delete and corrupt stored rows.
- Commits: `b3a0e466ee575785aa540e710799d28150723adc` (bookmark persistence/UI), `a4d81a0ae7778733bdc1d77b7fd919d0d648e20c` (reader controls), `b105f35fe775dcced30341f7ac0d993feb85739f` (tests).
- Build #47 (run `39079345156`) completed successfully.
- Build #48 (run `39079512964`) passed source analysis, `flutter test`, Android debug APK compilation, CI artifact upload, and direct APK publishing; test APK: `https://github.com/john-selwyn/selura-reader/releases/download/test-pr-9/selura-debug.apk`.
- Device verification: user reported that the installed PR #9 test APK and bookmarks work on Android. Comprehensive separate checks for every edge case were not individually reported.
- Post-merge `main` Builds #49 (run `39080726373`) and #50 (run `39080742987`) both completed successfully, including direct APK publishing.

## Completed milestone — EPUB reading appearance (PR #10)
- Pull Request #10 (`feature/epub-reading-customization`) squash-merged into `main` at `1396846c795a3cf25f89fda6fb48eda893f7873f` after the user confirmed the feature APK works on Android.
- Uses existing `epub_view` renderer builder options rather than replacing the EPUB reader/controller, so CFI auto-resume and EPUB bookmarks remain integrated.
- Added offline global EPUB appearance settings in `lib/reader_settings.dart`: Light/Dark/Sepia themes, System/Serif/Sans/Mono fonts, size 12–32, line height 1.1–2.0, side margins 8–40, and Reset.
- The EPUB reader has a Reading appearance button and a live-preview modal; preferences save via SharedPreferences, with serialized writes and safe fallback for corrupted entries.
- The EPUB page background, foreground text, app bar, and chapter dividers update with the reading theme. PDF pages retain their original fixed layout.
- Added `test/reader_settings_test.dart`: defaults, JSON persistence, range clamping, corrupt settings fallback, dark/mono restoration, and live settings UI interactions.
- Commits: `7d057958390847449cecc71975b3a3527ea52e6a` (settings model and UI), `58185c9d7ca85d42f55d8c7ab2cd64357328d712` (existing EPUB reader integration), `0f4698cfee71f7a0f476e427b5c81b40a8062438` (settings tests), `2cd4465a1c1eec4b19c3b94f8193797d54789948` (resolve EPUB/PDF renderer class-name collision).
- Build #51 (run `39081031700`) failed `flutter analyze` due conflicting `DefaultBuilderOptions` symbols from `epub_view` and `pdfx`; resolved by hiding the unused PDF export.
- **Build #52 (run `39081145276`) passed Android identity verification, dependency resolution, `flutter analyze`, all `flutter test` suites, debug APK compilation, CI artifact upload, and the direct prerelease APK job.**
- Verified test APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-10/selura-debug.apk ; GitHub release SHA-256 `4c9b8e3d061ee86df7aa05001c2886e25f8512396f537c7d3fe859c4899628db`.
- Device verification: user confirmed PR #10 APK works on Android. The user did not separately report individual test results for every theme, margin, bookmark and persistence edge case; those remain useful regression checks.
- Post-merge `main` Builds #54 (run `39082036348`) and #55 (run `39082054291`) both passed full Android APK build and direct APK publishing.

## Completed milestone — Accurate reading position (PR #11)
- PR #11 (`feature/reading-progress-details`) squash-merged into `main` at `2c3f71cbbf7e0c4c3966689ea3be95c6398031a0` after user confirmed reading-progress APK works on Android.
- Existing EPUB CFI (`reading_epub_cfi:`) and PDF page (`reading_pdf_page:`) keys are retained unchanged to preserve auto-resume for previously imported books.
- Added `lib/reading_progress.dart` with optional EPUB chapter number/title and actual PDF total-page metadata, plus backward-compatible, per-book summary formatting.
- PDF: `PdfViewPinch.onDocumentLoaded` persists the document's real `pagesCount`. Reader and bookshelf/Continue Reading show `Page X of Y` with a page-position bar when totals are available. Older PDFs show `Page X` until reopened; no invented totals or reading percentages.
- EPUB: chapter number/title come from `EpubView.onChapterChanged` and appear in the reader and bookshelf/Continue Reading. CFI remains the exact resume location; no EPUB percentage is inferred.
- UI updates from the chapter/page callbacks are deferred until after layout frames to avoid `setState` during the renderer's build/layout phase. Existing bookmarks, covers, appearance controls and offline storage remain intact.
- Tests: `test/reading_progress_test.dart` covers true PDF fractions, unknown or changed totals, backwards compatibility with legacy positions, EPUB chapter and CFI handling, invalid metadata, and chapter-title normalization.
- Implementation commits: `05d226048099f185c47e1a0b57ae1f81c741cd1b`, `2994c201aa2f8d6c7d60c1153899d9abcbbe7d3d`, `d45f8c68f82107857c980463d2c288bd7261c8b1`, `7b4b39fa6431748be152fbda3efdc35fdf27344b`, `ff65d6cb8149868186cfdceca1759058f0b84bfa`, `623444753f7596b9e6d08d21447372e0f02c32e8`, `1e9e60c0e8776f0a466d62e265fc79e0c505c93f`, and `c6275c9399df8115972c22d84c94ab2de9f10032`.
- Build #58 (GitHub Actions run `39082566356`) passed Android project verification, dependencies, `flutter analyze`, `flutter test`, APK compilation, artifact upload and direct APK prerelease publishing.
- Direct APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-11/selura-debug.apk (GitHub asset SHA-256 `121e5adb556c9c6472d269ba3dfa0cc0ccdf0d271caa8275821476fa1b07a967`).
- Device/runtime verification: user confirmed the reading-progress test APK works on Android; comprehensive checks for every EPUB/PDF edge case were not individually reported.
- New reported blocker: successive APKs cannot be installed over existing Selura; user has had to uninstall before installing updates. This risks deleting app-private EPUB/PDF imports, bookmarks, and preferences.
- Root-cause assessment: GitHub Actions builds with `flutter build apk --debug` on fresh ephemeral runners, with no persistent signing keystore; signing certificate changes can cause update rejection. Every build also uses `version: 0.1.0+1` with no monotonic build number.
- Corrective work: configure persistent signing and monotonic versionCode before further installable APK releases; first signing-key transition cannot replace an incompatible preexisting signing certificate without uninstall, so plan data preservation carefully.

## Runtime confirmation and EPUB import report — 2026-10-18
- User confirmed the permanently signed Selura **Build #74 installed over Build #73 without uninstalling**, validating the actual Android in-place upgrade after first signer transition.
- The new `com.selura.reader` release signing certificate is stable across #73 and #74, Android versionCode increases (73 -> 74), and Android device installation was reported successful.
- **New unresolved issue:** after the signed-release installation, attempting to import an EPUB shows an error on the phone. Exact error text, whether failure occurs in the file picker/copy or when opening the EPUB, and whether a PDF imports successfully are not yet established. Do not assume root cause or claim the EPUB reader is working in signed release.
- Reviewed current `lib/main.dart`: `_import` uses `FilePicker.pickFiles(type: FileType.custom, allowedExtensions: ['epub', 'pdf'])`, copies the selected platform file into app documents, persists library JSON, and shows caught exceptions as `Import failed: $e`. `_warmCovers` happens asynchronously after import and uses an isolated cover decoder. Await a screenshot/exact error before targeted source changes; no reinstall is needed to diagnose.
- Next: reproduce from the on-device error message, implement targeted fix on a feature branch, verify signed-release CI, ask user to test import again. Preserve install signing/version continuity.

## Current milestone — Signed APK upgrade verification (PRs #12 and #13)
- User confirmed PR #11 feature APK works but repeatedly had to **uninstall current Selura** to install another APK. Android update requires the same app ID and signing certificate and a non-decreasing versionCode; uninstall can remove app-private books/bookmarks/progress.
- Previous Actions builds used `flutter build apk --debug` on fresh ephemeral runners with no persistent debug keystore and static version `0.1.0+1`. Changing debug certificates are a likely cause of the update failure; no exact Android installer error code or cross-APK certificate comparison has been collected yet.
- Infrastructure PR #12 (`fix/persistent-release-signing`) squash-merged into `main` at `b2ad074f745514363bf04c4984b4f914f2a0127a`. It adds permanent release signing with a GPG-AES256-encrypted keystore stored only in armored form in the repo, with decryption password in GitHub Actions secret `SELURA_SIGNING_PASSWORD`, plus monotonically increasing `versionCode` from `GITHUB_RUN_NUMBER`.
- Adds `.github/workflows/bootstrap-signing.yml` to generate/encrypt/commit the key once and dispatch the first signed build; `android/app/build.gradle.kts` is configured for the release key, and `.github/workflows/android-apk.yml` no longer publishes ephemeral debug builds. Signed release file name: `selura.apk`.
- Build validation includes Android package ID verification, source analysis/tests, a temporary non-published release signing smoke test before permanent setup, and `apksigner` + `aapt` validation for published builds. Fork PRs do not receive signing secrets.
- Local Java `keytool` + GPG AES256 encrypt/decrypt/keystore round-trip was verified successfully without exposing any persistent signing credentials.
- CI Build #62 (run `39083965699`) passed `flutter analyze` and `flutter test`, then intentionally failed at permanent-key setup because it has not yet been configured. No unsigned APK was published. Build #64 (run `39084137395`) passed source analysis, `flutter test`, **Android release APK compilation signed with a disposable test key, and APK signature verification**. It then intentionally failed at `Unlock persistent release signing key` because the GitHub repository signing secret and permanent encrypted keystore are not configured; the release publishing job was correctly skipped.
- **Permanent-key build setup complete and verified:** Bootstrap #1 generated the encrypted key, and signed APK Builds #73 and #74 passed Android compilation, signature/package/version-code checks, artifact upload and GitHub Releases publishing. Android in-place update behavior still requires a device test.
- The already-installed debug-signed Selura cannot be updated by an APK bearing a new signing certificate. Do **not** uninstall before considering loss of app-private imported books and reading data. There is no verified lossless migration path to the first permanent signer yet. Once that initial transition has been made, two consecutive new builds must be checked for identical certificate fingerprint and increasing version codes, and then an on-device in-place update must be tested without uninstall.
- Setup and security instructions: `android/signing/README.md`. **Do not claim the update installation problem is fully fixed until the signer is bootstrapped and an in-place Android update has been verified.**

## Signing bootstrap activation — 2026-10-18
- User confirmed `SELURA_SIGNING_PASSWORD` was added as a GitHub Actions repository secret (secret value is not stored in this file).
- To avoid another manual GitHub screen, the one-time bootstrap workflow was augmented with an exact-path push trigger in commit `4ff98fda8234be09dc128f6b97d59e8ee317966d`; trigger file `android/signing/START_SIGNING_SETUP` added in `2c67b074cd9bab72bef824cb05e0a052cf553435`.
- **Bootstrap Selura Signing Key** run #1 (`39087102850`) completed **successfully**. The encrypted permanent Android signing key now exists at `android/signing/selura-release.jks.asc` on `main` (ASCII-armored PGP symmetric ciphertext, not a raw keystore).
- The bootstrap created a key commit `2b6a5018905aa77c6dffa9aa5b1dd0f9df4b2159` and dispatched **Build Android APK #70** (`39087117047`). At documentation time the first permanent-signer release APK was not yet verified.
- Next: confirm Build #70 analysis/tests/release-signing, inspect `apksigner` SHA-256 fingerprint and APK versionCode, then compare against a second signed build. Do not claim in-place upgrade works until Android device testing.
- Old debug-signed APKs remain incompatible with the new permanent key; DO NOT uninstall old Selura until the owner understands app-private data loss and verifies copies of imported files.

## Signed APK CI verification — Builds #73 and #74
- PR #13 (`fix/apk-verification-sdk-tools`) merged to main at `19aba6db11f50f18521468791908c88ba112d813`, updating verifier to recognize `V2 Signer: certificate SHA-256 digest` from current Android Build Tools.
- Build #72 compiled the signed APK but failed its certificate-label grep. Build #73 (`39088658937`) and main Build #74 (`39088677579`) **fully succeeded**, including all source tests, Android release APK build, APK signature verification, package/version checks, artifact upload, and GitHub release publishing.
- **Same permanent certificate:** Build #73 and Build #74 both logged `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` as signer certificate SHA-256; `apksigner` verified APK Signature Scheme v2 on both builds.
- **Monotonic Android versionCode:** `com.selura.reader` `0.2.0`, versionCode `73` for Build #73 and versionCode `74` for Build #74.
- Verified GitHub release artifacts: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-13/selura.apk and https://github.com/john-selwyn/selura-reader/releases/download/dev-74/selura.apk (the latter SHA-256 asset digest `bf11d331c7d0fc67cd932013b6b69fcbc8e8a5a8e0514e3b29d32988b9a3329e`).
- **Outstanding device verification:** test that Build #74 installs over already-installed Build #73 without uninstalling (or a later signed APK installs over #74). This does **not** remove the one-time old debug-signature incompatibility or automatically save app-private library data.

## Completed milestone — Signed Android EPUB import repair (PR #14)
- On-device failure in signed Builds #73/#74: importing an EPUB triggered a Java `NoSuchMethodError` for `io.flutter.plugins.sharedpreferences.SharedPreferencesApiRegistrar.getAll(String,List,Continuation)`. This was a SharedPreferences native plugin ABI issue rather than an EPUB format problem.
- Build #74 dependencies resolved `shared_preferences_android 2.5.0`, whose new JNI implementation triggered the runtime failure. PR #14 on branch `fix/shared-preferences-release-import` applied an explicit `dependency_overrides` pin to **`shared_preferences_android 2.4.28`** and added an Android CI guard requiring the exact resolved version.
- CI Build #77 (run `39090015554`) passed dependency verification, `flutter analyze`, `flutter test`, signed release APK compilation, APK signature/Android package/version-code verification, artifact upload, and direct release publishing (`test-pr-14/selura.apk`). Package `com.selura.reader`, versionCode `77`, same permanent signing certificate SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`.
- **Device verification:** user installed the fix and confirmed that EPUB importing/reading works again. The signed APK update process was previously tested successfully from Build #73 to #74 without uninstalling.
- PR #14 squash-merged into `main` as `b94153c8491389551d53c43791c047af441272ab` after device confirmation.
- **Next:** verify a successful post-merge `main` signed APK build; retain the 2.4.28 pin until a tested upstream plugin release is available. Do not upgrade the native plugin blindly.

## Completed milestone — Premium Selura UI and offline EPUB narration (PR #15)
- Feature branch: `feature/premium-loading-and-epub-tts`; PR https://github.com/john-selwyn/selura-reader/pull/15 squash-merged to `main` as `05732ee33897550fd3d26543479f0ef08411dd63` after the user confirmed the APK works on Android.
- Premium UI: coordinated light/dark Material 3 palettes, editorial bookshelf banner, adaptive Selura launcher icon and branded Android splash screen, subtle reader navigation animation.
- Loading/error optimization: proper initial library loading state instead of a false empty-library flash, import loading overlay, EPUB/PDF branded loading views and recoverable error screens; library rows with invalid metadata no longer prevent healthy books from appearing.
- Offline EPUB read-aloud: `flutter_tts` Android on-device TTS for the **current chapter**; pause/resume/stop, selected installed Android voice, persisted narration speed/voice preferences, bounded text chunks, background-isolate XHTML-to-speech extraction. Active chapter switches stop narration, and leaving the reader releases TTS.
- EPUB toolbar keeps Listen and Reading appearance visible; bookmarks and chapter navigation remain available in the overflow menu.
- Cover thumbnails now warm with bounded concurrency. EPUB/PDF reading, resume, bookmarks, real covers, typography settings and the Android signing identity are preserved.
- Regression tests for narration HTML extraction, chunk sizes, pause/resume/stop, saved speed/voice preferences and empty-chapter handling run alongside existing reader tests.
- **Build #95** (Actions run `39092988929`) passed source analysis, Flutter tests, release APK build, signature/package/version-code verification, CI upload, and GitHub release publishing. Exact test APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-15-run-95/selura.apk (60,117,425 bytes, asset SHA-256 `ae197127ff697e24fdd65a44c49d10c9b3980054b8051ac5b9582475204ffc5a`).
- **Device verification:** user reports Build #95 works on Android after testing the new design and EPUB TTS. Individual edge cases, Android offline voice data availability on other phones, and all combinations of controls have not been exhaustively tested.
- Limitations: EPUB narration starts at the beginning of the visible **chapter**, not the exact visible paragraph; PDF text-to-speech and continuing narration after closing the reader are not implemented.
- Post-merge `main` build and publication: pending verification.

## Completed milestone — Paragraph narration and scalable library (PR #16)
- PR #16 (`feature/paragraph-tts-library-performance`) was squash-merged into `main` at `02e125515d16f63ecb14cd9612b014735d638287` **after** user installed and tested Build #102 on Android and confirmed the navigation overlap was fixed.
- The EPUB TTS panel now supports selecting the narration start paragraph and skipping to previous/next paragraphs. The selected chapter XHTML is parsed to a cached, per-paragraph speech plan in an isolate. Playback interruption and pause/resume preserve the segment index, repeating only the short interrupted utterance (native Android TTS does not provide reliable exact pause within a segment).
- Bookshelf now uses lazily built `CustomScrollView` sliver grid/list items rather than shrink-wrapped nested lists, retaining search, sorting, favorites, Continue Reading, covers and reading-progress summaries.
- Regression tests cover paragraph bounds, seek/skip, long speech segments, playback continuity, panel reopening, and route opacity.
- **Build #101** (run `39094466298`) passed Flutter analysis/tests, persistent release signing and direct GitHub APK publishing. User tested APK features and reported a reader/bookshelf overlay during slow EPUB opening.
- **Transition fix:** commit `5f39db25c32674be1dcae5f4d5077bb1744ce2a3` replaces the fade-and-slide book route with an immediately opaque reader route and adds a navigation regression test. No EPUB/PDF content or user data format changes.
- **Build #102** (run `39096407925`) passed dependency pin verification, `flutter analyze`, `flutter test`, signed APK compilation, cert/package/version checks, CI artifact upload, and published the direct APK at https://github.com/john-selwyn/selura-reader/releases/download/test-pr-16-run-102/selura.apk.
- Build #102 APK: `com.selura.reader` version `0.2.0`, versionCode `102`; certificate SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` (unchanged); APK SHA-256 `352bdc48c929592866793fe63df25cb4b6024766b93f4bb3de1a568d1cfe1b4b`.
- **Device result:** user installed Build #102 and explicitly confirmed Selura and the corrected reader opening now work; broad device testing of huge libraries and unusually structured EPUBs remains outstanding.
- **Post-merge main Build #103** (run `39097231670`) completed successfully for squash commit `02e125515d16f63ecb14cd9612b014735d638287`: Flutter analysis/tests, pinned Android preferences dependency, signed Android release APK, certificate/identity/version checks, artifact upload, and direct GitHub Release publication all passed. Published APK: https://github.com/john-selwyn/selura-reader/releases/download/dev-103/selura.apk (`60,281,649` bytes; asset SHA-256 `d10d3ad5a0426c85349d1251732df904b5bc29a86c6d227d706c43aade568a6c`). Verified `com.selura.reader`, versionCode `103`, versionName `0.2.0`; permanent signer SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` unchanged. User tested prior signed Build #102 successfully; Build #103 has not separately been device-tested.

## Completed milestone — Offline library ZIP backup and restore (PR #17)
- PR #17 (`feature/offline-library-backup-restore`) was squash-merged into `main` as `9a9f9d06678e8aa72bcacb6d961a18b735389ae9` after user confirmed Build #104 works on their Android phone.
- Implemented offline ZIP export containing EPUB/PDF originals, versioned portable manifest, favorites and last-opened times, EPUB CFI/chapter data, PDF progress, per-book bookmarks, and appearance/TTS/shelf preferences. Android native Save File dialog allows storing the backup outside app-private storage.
- Restore validates manifest/schema, archive filenames, sizes, SHA-256 checksums and metadata, stages files, assigns new paths, remaps reading/bookmark keys and preserves existing books and preferences. Identical book files are skipped. Restore does not require internet/cloud.
- Backup ZIP files are **not encrypted**. The user must save a copy outside the app; backups in app-private storage are lost on uninstall. Large file and archive limits apply.
- Added regression tests for ZIP round trip, path remapping, stored preferences and bookmarks, duplicate restore, unsafe ZIP paths, wrong checksums, and missing source files.
- Signed PR test **Build #104** (run `39098475269`) passed dependency regression pin, `flutter analyze`, all `flutter test`, release APK build, certificate/application ID/version checks, artifact upload and GitHub release publishing.
- Direct test APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-17-run-104/selura.apk (60,675,277 bytes; SHA-256 `a28ecae57ede41e20ade4f3ce404629bc933b7d63cf85390ab1e46ceac68a423`). Application ID `com.selura.reader`, versionCode `104`, same permanent signer certificate `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`.
- **Device testing:** user reports Build #104 works on Android; individual edge cases including fresh-device recovery, very large ZIP files, checksum tampering, and recovery after accidental uninstall have not all been independently device-tested.
- **Post-merge main Build #105** (run `39099324058`) completed successfully for PR #17 merge commit `9a9f9d06678e8aa72bcacb6d961a18b735389ae9`, with signed APK and direct GitHub publication at https://github.com/john-selwyn/selura-reader/releases/download/dev-105/selura.apk (60,675,277 bytes; SHA-256 `5b8a4845969e56c458645e16c6d09780aaad6ce8f4bce339773c92579bd46d93`). Separate phone testing of Build #105 was not reported; PR test Build #104 was confirmed working.

## Completed milestone — Premium reading chrome and Focus Mode (PR #18)
- PR #18 (`feature/immersive-reading-chrome`) was squash-merged to `main` as `c767af6c013c53345cea25e745c337f39f27979d` **after** the user installed Build #107 and confirmed it works on their Android phone.
- EPUB/PDF Focus Mode hides the reader top and bottom chrome without remounting the loaded document; a small visible `Show controls` pill restores normal mode. This is an in-app focus layout, not forced Android system-bar immersive mode.
- EPUB quick A−/A+ buttons adjust reading font from 12–32sp using the existing serialized appearance-settings persistence. Theme-aware bottom bars show EPUB chapter labels and actual PDF page/progress metadata.
- Preserved EPUB/PDF rendering packages, reader navigation, progress/bookmarks, offline TTS, books, app package ID and permanent signing certificate. No highlights or annotations: the owner explicitly declined that feature.
- Added widget regressions for preserving mounted reader state during Focus Mode, entering/exiting chrome, font-size bounds/increments, and PDF progress. Initial Build #106 failed Flutter syntax analysis; commit `bbaf28d85bd4061fd354a00c54ccc068eba7ef9b` corrected the unmatched class closure.
- **Signed PR Build #107** (run `39100988481`) passed the pinned preferences-dependency guard, `flutter analyze`, all `flutter test`, release APK compilation, signing certificate/package/version verification, artifact upload and GitHub direct release. User confirmed on-phone functionality.
- Published PR APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-18-run-107/selura.apk (60,757,489 bytes; SHA-256 `a4b429998537073761b13b8dd94a7a957a35b33b07251150650eb85d1590931e`). Application ID `com.selura.reader`, version `0.2.0` (code 107), permanent signer SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` unchanged.
- **Post-merge Build #108** (run `39102269836`) completed successfully for merge commit `c767af6c013c53345cea25e745c337f39f27979d`, including Flutter checks, signed APK and direct release publishing: https://github.com/john-selwyn/selura-reader/releases/download/dev-108/selura.apk (60,757,489 bytes; SHA-256 `3e6c46a628e994836675a0cc90337cc905b6e7c3a67946f282887d55918f0716`). The user tested PR Build #107, not necessarily this post-merge APK.

## Completed milestone — EPUB comfort presets and efficient covers (PR #19)
- PR #19 was squash-merged to main as `af7f8ddc2520db69b463c5e0e887201bb9404f2a` after the user confirmed signed test Build #109 works on Android.
- Added Compact (15sp / 1.15 line spacing / 10px margins), Balanced (16sp / 1.25 / 16px), and Relaxed (19sp / 1.6 / 24px) EPUB reading layouts. Existing selected theme and font family remain unchanged, and manual adjustments still work.
- Bookshelf covers now request bounded decoded image dimensions based on actual card size and device pixel ratio. This reduces potential cached image memory use while preserving existing book covers, readers and offline files.
- Added regression tests covering reading presets and saved preferences, live choice controls, cover sizing, invalid constraints and memory bounds.
- **Build #109**, run `39104469074`: Flutter analysis and tests passed, permanently signed APK compiled, signer/package/version verified, and direct download published. User confirmed this build works on their phone.
- Published APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-19-run-109/selura.apk, 60,823,025 bytes, SHA-256 `7022cdfcf973912458325d714a33f798efb30b6483db825bd7528cd0298b11b6`. Android application ID `com.selura.reader`, versionCode 109, signing certificate unchanged.
- Post-merge Build #110 (run `39105542447`) passed CI and published signed Android APK at https://github.com/john-selwyn/selura-reader/releases/download/dev-110/selura.apk (60,823,025 bytes; SHA-256 `091795ec721830e4a4041172f200acf9599dd5122565e443f83073adbd24ca7e`). The user confirmed PR Build #109; Build #110 itself was not separately device-tested. Large-library memory improvement has not been measured on a real device.

## Completed milestone — Quiet Luxury bookshelf redesign (PR #20)
- PR #20 (`feature/premium-bookshelf-quiet-luxury`) was squash-merged into `main` as `f9414f3ca7326ba0a36ea1e49289670f514f76fd` **after** the user installed signed test Build #113 and confirmed it works on Android.
- Added refined editorial ivory/lavender and midnight charcoal design, responsive real library book/favorite counts and an existing-working import action, upgraded Continue Reading hero, book grid and list cards, search presentation, and useful empty/results reset states.
- Added real, scrollable All books / EPUB / PDF / Favorites filtering driven by existing local book attributes. Existing search, sorting, favorites, grid/list toggle and persistent EPUB/PDF storage remain functional by design; no renderer or native Android changes.
- Tests cover actual filter behavior, 320px narrow-device responsive dark banner, counts, empty search reset and layout states. Initial PR Builds #111 and #112 failed with narrow dark-mode banner overflow; corrected in passing commit `9b7f460f0a08cde67ab50e89bf2339402576f6d7`.
- **Signed PR Build #113** (run `39126079596`) passed `flutter analyze`, 53 widget/unit tests, native plugin version guard, release APK compilation and signing, package/version/certificate checks and GitHub direct APK publishing.
- Published Android test APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-20-run-113/selura.apk (60,921,317 bytes, SHA-256 `78dcd5a42099156c6e360504b50020af1e693551c1add6b53abb9b7927aa2ffb`), application ID `com.selura.reader`, versionCode 113, permanent signer SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` unchanged.
- **Device testing:** user confirmed Build #113 works. This does not independently establish every edge case of backup restoration, rare EPUB/PDF formats, or performance on very large libraries.
- **Post-merge main Build #114** (run `39127248456`) **succeeded** for merge commit `f9414f3ca7326ba0a36ea1e49289670f514f76fd`, including CI, signing and direct APK publishing at https://github.com/john-selwyn/selura-reader/releases/download/dev-114/selura.apk (60,921,317 bytes, SHA-256 `0aecd540dc166c474f520c8d99031fca92009a0f018046e2c559bc27db001919`). User confirmed PR test Build #113; post-merge Build #114 not independently phone-tested.

## Pending milestone — Offline CBZ manga reader (PR #21)
- Open PR #21 (`feature/offline-cbz-manga-reader`, implementation commit `91f39b7ec417f86e9a81e1268cb69ba9fa065265`) introduces **offline CBZ** import into the existing bookshelf, a real Manga filter, bounded cover thumbnails, vertical or horizontal one-page-at-a-time navigation, pinch-to-zoom, local page resume and per-book bookmarks. **CBR/RAR and continuous webtoon scrolling are not implemented.**
- Imports keep original CBZ files inside app-private storage; ZIP image entries are scanned using streaming archive inputs on worker isolates, naturally sorted by numeric filename, validated for unsafe paths/size limits, and individual page extraction is bounded to a nearby temporary cache. CBZ limit 512 MiB, 2000 image pages, individual images 32 MiB. Existing EPUB/PDF readers and all local data are kept independent.
- Existing Selura ZIP backup/export and restore can include CBZ originals, page progress, total page count and bookmarks. Unit tests cover file order, extraction, malicious/invalid ZIP rejection, reading state, Manga filter, CBZ backup round trip and idempotent restore.
- **Signed PR Build #120** (run `39128684570`) passed `flutter analyze`, all **60 Flutter tests**, unchanged `shared_preferences_android 2.4.28` pin, signed release APK compilation, certificate/package/version checks, artifact upload and direct release publishing.
- Direct APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-21-run-120/selura.apk (61,151,057 bytes, SHA-256 `559adf293738269b43238cea58d32b9a67f1d1706ec3827207aaef559315d687`, package `com.selura.reader`, versionCode 120, original cert SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` unchanged).
- **NOT YET MERGED OR DEVICE-VERIFIED.** User must install over existing release, test import and rendering of a real CBZ, image order/zoom/scroll, resume/bookmarks, Manga filter/cover, and CBZ backup/restore before merge. Earlier CI Builds #115/#118/#119 found syntax, analyzer and test issues; corrected before #120.

## Pending milestone — Installable online manga source (PR #21)
- User requested manga extensions because they have no local manga to import. Existing open PR #21 (`feature/offline-cbz-manga-reader`) was extended to include a **reviewed, installable MangaDex source adapter** and functional online manga browser. This is **not** compatible with third-party Mihon/Tachiyomi extension APKs; no remote executable code is installed.
- A Manga extensions button is accessible from the Selura bookshelf even if there are zero local books. Users can Install/Remove the MangaDex adapter (saved in SharedPreferences) and Browse manga, search titles, select English chapters, and read image pages with vertical swipes, pinch-zoom, focus mode and locally saved online chapter/page position. Explicit source and scanlation group credits are displayed; content and guest limits are controlled by MangaDex.
- Added restricted HTTPS MangaDex JSON API access, safe-rated English listings, bounded JSON decoding and timeout handling, protected MangaDex CDN hosts, responsive online catalogue/detail/reader screens and release INTERNET permission. All offline EPUB/PDF/CBZ readers remain independent. MangaDex terms prohibit paid services or advertising based on their API; the adapter is intended for the owner's personal app.
- **PR online-source Build #126** (run `39130225014`, commit `3683e1786964b8e6648b3095c2ea9fb0bcd09609`) passed Flutter analysis, **66 automated tests**, Android storage plugin compatibility, signed APK compilation, permanent signer/package/version checks, and direct GitHub Release publication.
- Direct test APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-21-run-126/selura.apk (61,430,049 bytes; SHA-256 `96c6e167a8ffd604af7a656661765a99b6a7866b1acebaa68d1699ac259b8473`; Android `com.selura.reader` versionCode 126; signer SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` unchanged). Testing of source API uses local JSON fixtures, not a real MangaDex connection.
- **Still open and NOT phone-verified.** User should install Build #126 over existing Selura without uninstalling, then test **Manga extensions -> Install MangaDex -> Browse manga -> search a title -> English chapter -> images/zoom/swipes -> resume**. Test existing EPUB/PDF import/resume. Real MangaDex reachability, provider guest restrictions and image CDN availability remain unverified; do not merge before user's test.

## Pending milestone — Optional nHentai gallery source (PR #21)
- User tested the MangaDex browser and observed chapters on some titles but not others. Current MangaDex implementation lists safe-rated English titles, fetches only the first 100 English chapters and excludes external-link chapters, so an empty list can reflect missing English or externally hosted chapters. This remains a usability improvement to address separately.
- User explicitly requested an additional nHentai source. The still-open `feature/offline-cbz-manga-reader` PR #21 was extended with a **separate, optional 18+ nHentai gallery source adapter**, installation consent dialog, a text-only gallery list/search, page-by-page reader with zoom/focus mode and persistent per-gallery page position. nHentai galleries are standalone image volumes, not traditional MangaDex chapter feeds. No third-party plugin APK execution or remote script loading.
- The reviewed adapter uses the nHentai public v2 API for listing, search, gallery detail and official CDN discovery. Requests are TLS/host constrained, return bounded JSON, respect HTTP 429/401/403 and site access controls, and do not bypass authentication, challenges or rate limits. Search results have no remote thumbnails before gallery selection, and restricted gallery metadata is excluded. Adult source remains disabled by default, with an explicit age/legality confirmation required at installation.
- **Signed PR Build #133** (GitHub Actions run `39132269635`, commit `3156eb5d3f1cdf62cd8c75aebc36729927504eb4`) **succeeded**: `flutter analyze` clean, all **72 automated tests** passed (nHentai parser, host validation, restricted metadata and 18+ UI; prior CBZ/EPUB/PDF/MangaDex regression coverage). The permanently signed APK compiled, certificate/package/version verified, and direct release published.
- Direct APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-21-run-133/selura.apk (61,528,429 bytes; SHA-256 `c64aaba73f1508f8055f6779fc75855235f3b63175594eb58b2443668a6f21f2`; package `com.selura.reader`, versionName `0.2.0`, versionCode `133`, existing signer SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` unchanged).
- **Not yet device-verified**: local test fixtures do not confirm public API responses or CDN image access on a real phone. Owner must install over their existing app (without uninstalling), open Manga extensions, explicitly enable nHentai if 18+, browse/search, select a permitted gallery and verify pages, zoom and resume; retest MangaDex/EPUB/PDF. PR #21 must stay open until owner confirms Android operation or requests fixes.

## Pending milestone — Keiyoushi compatible reader handoff and MangaDex chapter discovery (PR #22)
- User reported MangaDex chapters missing on some titles and experimental nHentai results still not working, then requested https://github.com/keiyoushi/extensions to act as an extension repository.
- Verified Keiyoushi's actual new-format source index is the **protobuf** URL `https://github.com/keiyoushi/extensions/raw/repo/index.pb`; the old `index.min.json` currently contains only two obsolete-version notices. Its Android extensions run in **Mihon or compatible hosts**, not in Flutter itself.
- Open PR #22 (`feature/keiyoushi-compatibility-guide-and-chapters`, head `69fa774c753ce160ac04515f7100b600efc2b2c8`), based on the existing open PR #21, adds a **functional Keiyoushi companion setup screen** under Manga extensions, official allowlisted HTTPS Mihon/Keiyoushi buttons and clipboard copy for the new protobuf repo URL. It does **not** claim to install/execute Keiyoushi APKs inside Selura. Full native host API, signing verification, platform-channel reader integration and extension isolation would require a separate engineering milestone. Documented in `docs/KEIYOUSHI_COMPATIBILITY.md`.
- Improves the **native Selura MangaDex chapter reader** with language selection (English, all languages and named translations), 100-row offset pagination and Load more, correct accounting of skipped external-hosted chapters and honest missing-chapter explanations. No bypassing providers' site restrictions.
- UI/parser tests cover the official repo URL and safe links, Keiyoushi companion, language fallback, 101-chapter pagination, external-feed skipping and prior EPUB/PDF/CBZ/MangaDex/nHentai behavior. Previous Build #134 found an off-screen MangaDex Install button in widget tests after adding the companion card; test corrected without changing production behavior.
- **Signed PR #22 Build #135** (run `39134544254`) passed `flutter analyze`, all **75 Flutter tests**, pinned `shared_preferences_android 2.4.28`, permanent Android signing, APK package/version/certificate checks and direct GitHub publishing. Android identity `com.selura.reader`, versionName `0.2.0`, versionCode 135, original signer SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` unchanged.
- Verified downloadable signed APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-22-run-135/selura.apk (62,055,320 bytes; SHA-256 `6bdd72f10cc54413b1c6228fc6d6f420394aa62f83ccbbf680b97a906e1d7c42`).
- **Owner phone test is pending.** User should install Build #135 over the existing signed APK without uninstalling; test EPUB/PDF library/resume, MangaDex → chapter language All → Load more for missing titles, and Manga extensions → Keiyoushi setup → official Mihon companion. Keiyoushi extensions run in Mihon, not in Selura. Do not merge PR #22 or superseded PR #21 before owner confirmation.

## Pending milestone — Mihon .tachibk library restoration (PR #23)
- User requested restoring a real Mihon backup directly inside Selura instead of Mihon hyperlinks; user approved platform changes if needed. Confirmed official Mihon backup files are potentially gzip-compressed **protobuf** streams with `BackupManga`, `BackupChapter`, `BackupCategory`, `BackupHistory`, and `BackupSource` records. The backup **does not contain downloaded manga images or the extension APK code**. Flutter is sufficient to import metadata; a Kotlin extension host would be separately needed to read non-supported Keiyoushi sources.
- Open PR #23 (`feature/mihon-backup-restore`, head commit `8e4797b95edbe6069d6a39a2321cea7a045f6037`) adds a bounded raw/gzip protobuf decoder operating off the UI isolate (32 MiB compressed/128 MiB expanded; 20k manga/200k chapters), safely handling unknown tags. Imports manga titles, favorite state, author/artist/description, source ID/name/URL, category membership by **category order**, chapter read/bookmark flags, page positions and per-chapter read history. No data was copied from Mihon's private storage and no external APKs are executed.
- A new **Mihon library & backup** entry under Selura's existing library overflow menu opens a searchable, category-filterable library. The empty bookshelf also offers **Restore or browse Mihon manga**. The Android file picker accepts Mihon backup files; a preview confirms manga/chapter/read/category counts before non-destructive atomic import. Duplicate source-ID + URL records are updated rather than re-added. EPUB/PDF/CBZ storage/reader state stays independent.
- Imported manga details display chapter history and source. Only recognized MangaDex titles offer an in-Selura **Read with MangaDex** action using the existing supported online reader and careful mapping of old chapter location when possible. Other source chapters remain displayed as imported metadata until a compatible runtime/source adapter is implemented.
- CI Build #140 caught an incorrect exception identifier in the gzip error handler; fixed before release. **Signed PR Build #141** (run `39136935531`) passed Flutter analysis, all **80 automated tests**, pinned `shared_preferences_android 2.4.28`, Android signed-release compilation, package/certificate/version verification and GitHub direct APK publishing. Tests include upstream-schema-compatible protobuf fixtures (gzip and raw), categories, history, saved chapter states, safe malformed input, idempotent restore and UI.
- Verified signed test APK: https://github.com/john-selwyn/selura-reader/releases/download/test-pr-23-run-141/selura.apk (62,170,524 bytes, SHA-256 `7609ff00dd1d7d899cd4f4527b693926ed29890332e9c0201cd46253d23049ed`). App ID `com.selura.reader`, versionName `0.2.0`, versionCode 141, original signer SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42` unchanged.
- **BLOCKER: No real user-created Mihon backup or physical Android test yet.** Test fixtures validate known schema fields, not all real source variations. Keep PR #23 open until user installs signed Build #141 over their current Selura (without uninstalling), selects their exported `.tachibk`, confirms preview/import, validates titles/categories/read/bookmark/page history and EPUB/PDF regression. For non-MangaDex titles, do not claim restored page images can be read from the backup.

## Pending manga-only migration (PR #24)
- **2026-10-20 OWNER DECISION:** stop further EPUB/PDF and Flutter reader feature development. Selura will be rebuilt as a **native Android manga reader** supporting Mihon `.tachibk` restoration and Keiyoushi-compatible Android extension APKs directly inside the app, not a URL-only handoff.
- Researched [Mihon native source](https://github.com/mihonapp/mihon) version **v0.21.2**, commit `9612d955db3165e1578fdf9ff19ca9b7762c4a46` (Apache-2.0). It already implements `BackupRestorer.kt`, `ExtensionManager.kt`, and manga/webtoon reader modules. Previous Flutter PR #23 imported **metadata only** and cannot execute native extensions, so using real Mihon source is the engineering path to direct functionality.
- Created isolated `feature/selura-native-manga-migration` [PR #24](https://github.com/john-selwyn/selura-reader/pull/24) with reproducible `native_manga/apply_branding.py`, patch compatibility tests, `native_manga/README.md` including upstream license/provenance and Android owner instructions, plus separate `.github/workflows/native-manga-apk.yml` for actual Java 21/Gradle native release compilation, Selura permanent signing and direct APK publishing.
- Preview app ID is `com.selura.manga`; distinct from old Flutter `com.selura.reader` and upstream Mihon `app.mihon`. This **protects existing installed app data** by enabling side-by-side Android installation while owner checks native backups/extensions. Own launcher art and label `Selura Manga`, upstream telemetry/updater disabled.
- **Native Build #1** (GitHub Actions run `39352273448`) **completed successfully**, including 5 migration patch tests, exact Mihon source pin/Apache license checks, Java 21 native Gradle `:app:assembleRelease` (BUILD SUCCESSFUL in 16m 8s), reuse of the established signing certificate, package/version checks, artifact upload and immutable direct GitHub release publishing. Android ID `com.selura.manga`, versionCode 1001 and versionName `0.1.0-native`. Original signing SHA-256 `da9cfd25f9b1c694b585d427e5faa8c9a1d052b8d846051fbe1569d65c851d42`. Signed APK: https://github.com/john-selwyn/selura-reader/releases/download/test-native-pr-24-run-1/selura-manga.apk (67,154,260 bytes, SHA-256 `95a8cfe3a034e9e1dd53b8b468a025828365dfd42c6f02e2c31863690c4c0320`). **Real device install/restore and live extension/chapter reading NOT YET verified.**
- **Acceptance gate:** native signed APK success (package/signature/version and publication); user installs new package alongside originals, restores real exported Mihon .tachibk, checks manga categories/history/read progress, configures Keiyoushi repo, installs trusted extension and reads/reopens online chapter. Do not delete or archive old Flutter code until physically verified.

## Unverified / blockers
- EPUB covers are merged and device-verified for displayed cover, offline persistence, and resume; unusual EPUB variants still need broader field testing.
- The package-ID correction means data stored by old `com.selura.selura_reader` debug installs does not automatically migrate to `com.selura.reader`.
- Release-signed builds use the permanent APK certificate; the user successfully upgraded Build #73 to #74 in place on Android. Legacy `selura-debug.apk` builds still have incompatible ephemeral signing identities.
- `shared_preferences_android` is intentionally pinned to **2.4.28** after the signed-release JNI regression on 2.5.0; reassess only with device-tested compatibility.
- `pdfx` has emitted a non-fatal Kotlin/Gradle compatibility warning that should be addressed before a future Flutter upgrade.

## Next steps
1. Owner: export Mihon `.tachibk` with manga/categories/reading history enabled, and preserve the original backup file. Install **native Selura Manga PR #24 Build #1**, https://github.com/john-selwyn/selura-reader/releases/download/test-native-pr-24-run-1/selura-manga.apk, as a **separate app**, without uninstalling Mihon or legacy Flutter Selura. Check the actual Android app opens and backup restore works on the original file.
2. On the native app test categories, favorite mangas, chapter read state/history, and current page. Native Mihon backup restore should handle the same backup format, but this is not a physical verification; report any crash or missing field and correct PR #24.
3. Configure the Keiyoushi repository in the new native extension manager; review trusted sources and install only authorized packages; browse and read a real manga chapter, then verify downloaded reading, navigation and resume. Provider availability and legal restrictions apply.
4. Keep PR #24 **open and unmerged** until owner phone-tests the signed native APK. Legacy Flutter PRs #21/#22/#23 were closed unmerged as superseded; legacy main app/data and old APKs remain preserved. After user validation, decide native manga-only primary release and archive old EPUB/PDF source safely.

## Key milestone history
- Pull Request #1: offline library hardening, squash-merged to main at `e9c8d3a18f2fc5224ae41076dc7ebdebd69be752`.
- Build #12 (run `39039815021`): first successful Android debug APK; user confirmed installation/runtime.
- Pull Request #2: persisted EPUB/PDF reading progress, squash-merged to main at `0521e3bfeac5484c57d82c9362a1e727b73d4d0f`.
- Build #19 (run `39042188909`): analysis, APK compilation, artifact upload, and direct APK publishing passed; user verified automatic resume on device.
- Build #23 (run `39043338015`): post-merge main build and direct APK publishing passed.
- Pull Request #5: final Android identity and committed scaffold; merged at `c0fcd6f46fd514cff182c10606a38bced2a581b1` after successful device testing.
- Pull Request #7: premium bookshelf, Build #34 (run `39048049148`) fully passed, direct APK `test-pr-7` published, user confirmed it works on Android, squash-merged at `073c0b0ca9a7816f6c8aaf3209fe7863f88f5fee`.
- Pull Request #8: real EPUB covers, Build #43 passed, offline on-device cover display/resume verified, squash-merged at `c9d29173690f259af4f67e3ac3f374953143ff2f`.
- Pull Request #9: local EPUB/PDF bookmarks, Build #48 (run `39079512964`) passed analysis/tests/APK/release; user confirmed runtime works, squash-merged at `e9bcc5a365f53e01f26a9f23cceb33e38f83a2ad`.
- Pull Request #10: EPUB appearance and typography, Build #52 (run `39081145276`) passed analysis/tests/APK/release; user confirmed Android runtime works, squash-merged at `1396846c795a3cf25f89fda6fb48eda893f7873f`.
- Pull Request #11: accurate PDF pages and EPUB chapters, Build #58 (run `39082566356`) passed analysis/tests/APK/release; user confirmed feature works but reports update installation failures with debug APKs; squash-merged at `2c3f71cbbf7e0c4c3966689ea3be95c6398031a0`.
- Pull Request #14: signed-release EPUB import plugin compatibility fix, Build #77 (run `39090015554`) passed source/tests/release APK/signing/release publishing; user confirmed Android EPUB import works, squash-merged at `b94153c8491389551d53c43791c047af441272ab`.
- Pull Request #15: premium Selura UI, native loading states and offline EPUB chapter narration, signed Build #95 (run `39092988929`) fully passed, user confirmed Android runtime works, squash-merged at `05732ee33897550fd3d26543479f0ef08411dd63`.

- Pull Request #16: paragraph seeking/skip offline TTS, sliver bookshelf performance and instant opaque reader navigation; Build #102 (run `39096407925`) passed analysis/tests/signing/APK/release; user confirmed Android fix works; squash-merged at `02e125515d16f63ecb14cd9612b014735d638287`.

- Pull Request #17: offline library backup/export and non-destructive ZIP restore, CI Build #104 passed signing/APK/release, user confirmed Android functionality, squash-merged into main at `9a9f9d06678e8aa72bcacb6d961a18b735389ae9`; post-merge Build #105 pending verification.

- Pull Request #18: premium EPUB/PDF Focus Mode, quick EPUB typography and refined status footers; signed Build #107 (run `39100988481`) passed CI and user confirmed Android runtime; squash-merged as `c767af6c013c53345cea25e745c337f39f27979d`. Main Build #108 awaiting verification. Highlights and annotations intentionally excluded by user choice.

- PR #19: EPUB comfort presets and bounded bookshelf cover decoding; signed Build #109 passed CI and worked on Android; merged at `af7f8ddc2520db69b463c5e0e887201bb9404f2a`. Post-merge Build #110 must be independently verified.

- PR #20: Quiet Luxury premium bookshelf with real filters, Continue Reading hero, editorial themes, responsive layout and regression tests; signed Build #113 CI succeeded, user confirmed device functionality, squash-merged as `f9414f3ca7326ba0a36ea1e49289670f514f76fd`. Main Build #114 pending final release verification.

## Future chat instructions
Read `PROJECT_CONTEXT.md` and `PROGRESS.md` from the GitHub main branch first, then inspect current source, open pull requests, and GitHub Actions before making development claims. Update this file with exact commits, build results, blockers, and next steps after each milestone. Never claim an APK or runtime feature works without verification.
