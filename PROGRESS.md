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
- Pull Request #2 Build #19 completed successfully: source analysis, APK compilation, CI artifact upload, and direct APK prerelease publishing all passed.
- User confirmed the latest Android build works and EPUB/PDF automatic resume restores reading position correctly.
- Pull Request #2 was squash-merged to main at 0521e3bfeac5484c57d82c9362a1e727b73d4d0f.

## Current milestone
- EPUB reading position is persisted as EPUB CFI and restored on reopen.
- PDF current page is persisted and restored on reopen.
- Reader pages show a loading indicator while saved progress is restored.
- Bookshelf labels imported books as supporting auto-resume.
- Direct APK publishing is enabled for both main builds and same-repository pull-request test builds, so device testing does not require ZIP extraction.

## Unverified / blockers
- The post-merge main build/direct APK release still needs verification after Pull Request #2 merge.
- The generated Android application ID is still `com.selura.selura_reader`; project requirement is `com.selura.reader`. This should be fixed before release builds or long-term user data depends on the current package ID.
- The workflow regenerates Android scaffolding during CI; persisting the Android project with the correct package ID will make builds more stable and predictable.
- `pdfx` emits a non-fatal Kotlin Gradle Plugin compatibility warning that should be addressed before a future Flutter upgrade.
- Cover art, bookmarks, annotations, typography controls, premium bookshelf UI, and manga/CBZ support are still pending.

## Next steps
1. Verify the post-merge main build publishes a direct `selura-debug.apk` release asset.
2. Persist the Android scaffold and set the final application ID/namespace to `com.selura.reader`.
3. Rebuild and device-test installation/update behavior after the package-ID correction.
4. Improve bookshelf UI with covers, search/sort, favorites, and continue-reading presentation.
5. Add bookmarks and EPUB typography/theme controls.
6. Begin offline manga support with CBZ import and right-to-left/continuous reading modes.

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
- Build #19 (39042188909) passed analysis, APK compilation, artifact upload, and direct APK publishing.
- Device verification: user confirmed automatic resume works in the latest Android build.
- Pull Request #2 merged to main at 0521e3bfeac5484c57d82c9362a1e727b73d4d0f.

## 2026-10-17 — Direct-install APK publishing
- Initial commit: d28d1460b4245d43ebf938f69579b1472073d64f.
- GitHub Actions still keeps a CI artifact internally, because GitHub artifacts are downloaded as ZIP archives.
- Main-branch builds publish `selura-debug.apk` as a GitHub prerelease asset.
- Build #17 passed, but its `Publish direct APK` job was intentionally skipped because that first workflow revision only published on `main`.
- Follow-up commit: 2726b93c409cff8fada9cfc3a49c09106524a7c8 enables direct `.apk` prerelease publishing for same-repository pull-request builds as well.
- Build #19 verified that the pull-request direct APK release job succeeds.
- User-facing result: feature builds can be device-tested from a direct APK download without extracting a ZIP.
