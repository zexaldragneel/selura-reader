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

## Current milestone — Fix Android APK update installation (PR #12)
- User confirmed PR #11 feature APK works but repeatedly had to **uninstall current Selura** to install another APK. Android update requires the same app ID and signing certificate and a non-decreasing versionCode; uninstall can remove app-private books/bookmarks/progress.
- Previous Actions builds used `flutter build apk --debug` on fresh ephemeral runners with no persistent debug keystore and static version `0.1.0+1`. Changing debug certificates are a likely cause of the update failure; no exact Android installer error code or cross-APK certificate comparison has been collected yet.
- Infrastructure PR #12 (`fix/persistent-release-signing`) squash-merged into `main` at `b2ad074f745514363bf04c4984b4f914f2a0127a`. It adds permanent release signing with a GPG-AES256-encrypted keystore stored only in armored form in the repo, with decryption password in GitHub Actions secret `SELURA_SIGNING_PASSWORD`, plus monotonically increasing `versionCode` from `GITHUB_RUN_NUMBER`.
- Adds `.github/workflows/bootstrap-signing.yml` to generate/encrypt/commit the key once and dispatch the first signed build; `android/app/build.gradle.kts` is configured for the release key, and `.github/workflows/android-apk.yml` no longer publishes ephemeral debug builds. Signed release file name: `selura.apk`.
- Build validation includes Android package ID verification, source analysis/tests, a temporary non-published release signing smoke test before permanent setup, and `apksigner` + `aapt` validation for published builds. Fork PRs do not receive signing secrets.
- Local Java `keytool` + GPG AES256 encrypt/decrypt/keystore round-trip was verified successfully without exposing any persistent signing credentials.
- CI Build #62 (run `39083965699`) passed `flutter analyze` and `flutter test`, then intentionally failed at permanent-key setup because it has not yet been configured. No unsigned APK was published. Build #64 (run `39084137395`) passed source analysis, `flutter test`, **Android release APK compilation signed with a disposable test key, and APK signature verification**. It then intentionally failed at `Unlock persistent release signing key` because the GitHub repository signing secret and permanent encrypted keystore are not configured; the release publishing job was correctly skipped.
- **BLOCKER: no permanent signing key or signed Selura release APK has been generated/verified yet.** User must add a random >=24-character repository Actions secret named `SELURA_SIGNING_PASSWORD` via GitHub Settings from phone (never share the value in chat), then run `Actions → Bootstrap Selura Signing Key` on main **once**.
- The already-installed debug-signed Selura cannot be updated by an APK bearing a new signing certificate. Do **not** uninstall before considering loss of app-private imported books and reading data. There is no verified lossless migration path to the first permanent signer yet. Once that initial transition has been made, two consecutive new builds must be checked for identical certificate fingerprint and increasing version codes, and then an on-device in-place update must be tested without uninstall.
- Setup and security instructions: `android/signing/README.md`. **Do not claim the update installation problem is fully fixed until the signer is bootstrapped and an in-place Android update has been verified.**

## Unverified / blockers
- EPUB covers are merged and device-verified for displayed cover, offline persistence, and resume; unusual EPUB variants still need broader field testing.
- The package-ID correction means data stored by old `com.selura.selura_reader` debug installs does not automatically migrate to `com.selura.reader`.
- Release signing is not configured yet; current downloadable APKs are development/debug builds.
- `pdfx` has emitted a non-fatal Kotlin/Gradle compatibility warning that should be addressed before a future Flutter upgrade.

## Next steps
1. User securely adds `SELURA_SIGNING_PASSWORD` as a repository Actions secret (>=24 random characters, stored in password manager).
2. User runs `Bootstrap Selura Signing Key` once on main. Verify encrypted key commit, successful first release build, exact signing certificate and version code.
3. Verify the next signed APK has the same certificate and a higher versionCode; perform an Android update **without uninstalling** after the first-signature migration is safely addressed.
4. Do not erase current app-private book data without confirming a recovery/reimport plan. Add backup/export functionality once reliable upgrades are available.
5. Resume offline CBZ manga reader development after safe update installation is verified.

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

## Future chat instructions
Read `PROJECT_CONTEXT.md` and `PROGRESS.md` from the GitHub main branch first, then inspect current source, open pull requests, and GitHub Actions before making development claims. Update this file with exact commits, build results, blockers, and next steps after each milestone. Never claim an APK or runtime feature works without verification.
