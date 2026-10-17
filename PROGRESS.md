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

## Current milestone — Embedded EPUB cover thumbnails (Pull Request #8)
- Branch: `feature/epub-cover-thumbnails`; PR: https://github.com/john-selwyn/selura-reader/pull/8. Not merged; device testing is still required.
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
- Runtime result: NOT YET DEVICE-VERIFIED. Test imported EPUBs with and without embedded covers, offline restart, existing library covers, and EPUB/PDF auto-resume before merging PR #8.

## Unverified / blockers
- The EPUB cover feature in PR #8 passes CI but remains unmerged and unverified on an Android device.
- The package-ID correction means data stored by old `com.selura.selura_reader` debug installs does not automatically migrate to `com.selura.reader`.
- Release signing is not configured yet; current downloadable APKs are development/debug builds.
- `pdfx` has emitted a non-fatal Kotlin/Gradle compatibility warning that should be addressed before a future Flutter upgrade.

## Next steps
1. Install PR #8 test APK on Android and confirm covers for existing/new EPUBs, missing-cover fallback, offline display, and unaffected EPUB/PDF reading/resume.
2. Once device verification succeeds, merge PR #8 and confirm the post-merge main APK release.
3. Add per-book EPUB CFI/PDF-page bookmarks and local bookmark navigation.
4. Add EPUB typography and reading-theme controls.
5. Begin offline manga/CBZ support after core reader milestones.

## Key milestone history
- Pull Request #1: offline library hardening, squash-merged to main at `e9c8d3a18f2fc5224ae41076dc7ebdebd69be752`.
- Build #12 (run `39039815021`): first successful Android debug APK; user confirmed installation/runtime.
- Pull Request #2: persisted EPUB/PDF reading progress, squash-merged to main at `0521e3bfeac5484c57d82c9362a1e727b73d4d0f`.
- Build #19 (run `39042188909`): analysis, APK compilation, artifact upload, and direct APK publishing passed; user verified automatic resume on device.
- Build #23 (run `39043338015`): post-merge main build and direct APK publishing passed.
- Pull Request #5: final Android identity and committed scaffold; merged at `c0fcd6f46fd514cff182c10606a38bced2a581b1` after successful device testing.
- Pull Request #7: premium bookshelf, Build #34 (run `39048049148`) fully passed, direct APK `test-pr-7` published, user confirmed it works on Android, squash-merged at `073c0b0ca9a7816f6c8aaf3209fe7863f88f5fee`.

## Future chat instructions
Read `PROJECT_CONTEXT.md` and `PROGRESS.md` from the GitHub main branch first, then inspect current source, open pull requests, and GitHub Actions before making development claims. Update this file with exact commits, build results, blockers, and next steps after each milestone. Never claim an APK or runtime feature works without verification.
