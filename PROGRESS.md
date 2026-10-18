# Selura — Development Progress
Last updated: 2026-10-18

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
- Post-merge Build #110 (run `39105542447`) started from the merge commit. Verify this run independently before claiming successful publication. Large-library memory improvement has not been measured on a real device.

## Unverified / blockers
- EPUB covers are merged and device-verified for displayed cover, offline persistence, and resume; unusual EPUB variants still need broader field testing.
- The package-ID correction means data stored by old `com.selura.selura_reader` debug installs does not automatically migrate to `com.selura.reader`.
- Release-signed builds use the permanent APK certificate; the user successfully upgraded Build #73 to #74 in place on Android. Legacy `selura-debug.apk` builds still have incompatible ephemeral signing identities.
- `shared_preferences_android` is intentionally pinned to **2.4.28** after the signed-release JNI regression on 2.5.0; reassess only with device-tested compatibility.
- `pdfx` has emitted a non-fatal Kotlin/Gradle compatibility warning that should be addressed before a future Flutter upgrade.

## Next steps
1. Verify post-merge signed Build #110 (run `39105542447`) and direct APK release.
2. Continue premium EPUB/PDF UI polish and measured large-library responsiveness while keeping import, progress, bookmarks and TTS stable.
3. Consider optional TTS sleep timer or other reading-comfort work as separate milestones, only after review and device testing. No highlights or annotations.
4. Maintain the tested `shared_preferences_android 2.4.28` pin. Keep backup ZIPs outside Selura for safe recovery.

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

## Future chat instructions
Read `PROJECT_CONTEXT.md` and `PROGRESS.md` from the GitHub main branch first, then inspect current source, open pull requests, and GitHub Actions before making development claims. Update this file with exact commits, build results, blockers, and next steps after each milestone. Never claim an APK or runtime feature works without verification.
