# Selura — Development Progress
Last updated: 2026-10-17

## Repository
https://github.com/john-selwyn/selura-reader

## Completed
- Created project context and progress docs on main.
- Added Flutter pubspec.yaml with EPUB, PDF, file picker, local storage dependencies.
- Added lib/main.dart with bookshelf, local EPUB/PDF import, EPUB reader with table of contents, and PDF reader.
- Added .github/workflows/android-apk.yml to generate Android scaffolding and build a debug APK.
- GitHub Actions Build #12 successfully compiled and uploaded the first Selura debug APK artifact.
- User confirmed the Build #12 APK installs and runs acceptably on an Android device.
- Pull Request #1 was squash-merged to main at e9c8d3a18f2fc5224ae41076dc7ebdebd69be752.

## Current milestone
- Feature branch: `feature/persisted-reading-progress`.
- EPUB reading position is now persisted as EPUB CFI and restored on reopen.
- PDF current page is now persisted and restored on reopen.
- Reader pages show a loading indicator while saved progress is restored.
- Bookshelf labels imported books as supporting auto-resume.

## Unverified / blockers
- Persisted EPUB/PDF progress changes require GitHub Actions verification and a fresh Android device test before merge.
- `pdfx` emits a non-fatal Kotlin Gradle Plugin compatibility warning that should be addressed before a future Flutter upgrade.
- Cover art, bookmarks, annotations, typography controls, and a more premium bookshelf UI are still pending.

## Next steps
1. Verify the persisted-reading-progress branch in GitHub Actions.
2. Install the resulting APK and confirm EPUB and PDF resume positions on Android.
3. Merge the reading-progress pull request after verification.
4. Upgrade or replace `pdfx` as needed to remove its future Kotlin compatibility warning.
5. Improve bookshelf UI, cover art, bookmarks, annotations, and reader theme/typography controls.

## Future chat instructions
Read PROJECT_CONTEXT.md and PROGRESS.md from the GitHub main branch. Verify code and CI status before making claims. Keep this file current.

## 2026-10-17 — Offline library hardening (feature branch)
- Commit: 6408e7c40dbfb7181be1ae306e031fafe1d28330
- Imported files now use generated safe filenames rather than user-supplied filenames.
- Missing local files are filtered when loading the bookshelf.
- Build status: not verified. Commit-specific workflow lookup returned no runs; the existing workflow only triggers on main or manual dispatch.
- Next: validate Android CI, add PR-triggered builds, implement EPUB/PDF resume positions and test on a device.

## 2026-10-17 — Build #3 failure diagnosed and patched
- Run #3 (39037710648) failed at `flutter analyze`; Android compilation was skipped.
- Root cause: `flutter create` generated a counter-app widget test referencing nonexistent `MyApp`, while `flutter_test` and `flutter_lints` were absent from pubspec.
- Fix commits: 10a137bc65a9cf791950ebfb0b4b6e732305481e (dev dependencies), e3595918d2f127e60c6890cb6dabe4df3acbf48a (remove generated template test before analysis).
- Verification: awaiting subsequent PR workflow. APK not yet confirmed.

## 2026-10-17 — Build #5 lint repair
- Run #5 (39037991308) failed at `flutter analyze` because of `unnecessary_brace_in_string_interps` at lib/main.dart:60; build/upload skipped.
- Fixed in commit 3534f5b94a348b310ecaf00f24355654cf9032fb.
- Awaiting next CI run. APK remains unverified.

## 2026-10-17 — Build #7 reached Android compilation
- Run #7 (39038184074) passed Flutter setup, dependency resolution, and `flutter analyze` with no issues.
- Android compilation then failed in transitive package `flutter_html` because `html` 0.15.7 removed the `matches` API used by `flutter_html` 3.0.0.
- Fix: pin direct dependency `html: 0.15.6` in commit 619b4088aca4deea062002324c361ee8f6137f4d.
- The `pdfx` Kotlin Gradle warning is non-fatal for this run and will be handled separately if needed.
- Verification: awaiting the next PR workflow. APK remains unverified.

## 2026-10-17 — Build #9 Android SDK compatibility blocker
- Run #9 (39038721621) passed dependency resolution and `flutter analyze`, then failed during Android compilation because file_picker 8.x compiled against Android API 34 while a lifecycle dependency required compileSdk 36.
- Fix: upgraded `file_picker` to 13.1.0 in commit 03f3c0676ede1d497978421eae7831e58dbb24d6.

## 2026-10-17 — Build #10 file_picker API migration
- Run #10 (39039469281) failed at `flutter analyze` because file_picker 13 removed the old `FilePicker.platform` API and the legacy `FilePickerResult` flow.
- Fix: migrated imports to `FilePicker.pickFiles(...)`, the new `List<PlatformFile>` return type, and removed the obsolete `allowMultiple` parameter in commit ba0b8bd81486d548f3c28f1dcd9d26a53e1b97e8.
- Verification: awaiting the next pull-request build. APK remains unverified.

## 2026-10-17 — First successful Android APK build
- Run #12 (39039815021) completed successfully.
- `flutter analyze` reported no issues.
- `flutter build apk --debug` completed successfully and produced `build/app/outputs/flutter-apk/app-debug.apk`.
- Artifact `selura-debug-apk` uploaded successfully (83,399,059 bytes, artifact ID 12103653028).
- Artifact SHA-256: `1736cbf2b57a90a320e4e5ae3a807a031ef932f02c9e7341d9908b8a760c1955`.
- User subsequently confirmed the APK installed and ran acceptably on Android.

## 2026-10-17 — Persisted reading progress implementation
- Branch: `feature/persisted-reading-progress`.
- Commit: 4620a4c939c9c821e5950dd2765763b780a8475b.
- EPUB: saves `EpubController.generateEpubCfi()` and restores it through `EpubController(epubCfi: ...)`.
- PDF: saves the current page via `onPageChanged` and restores it through `PdfControllerPinch(initialPage: ...)`.
- Status: implemented but not yet CI/device verified.
