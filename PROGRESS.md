# Selura — Development Progress
Last updated: 2026-10-17

## Repository
https://github.com/john-selwyn/selura-reader

## Completed
- Created project context and progress docs on main.
- Added Flutter pubspec.yaml with EPUB, PDF, file picker, local storage dependencies.
- Added lib/main.dart with bookshelf, local EPUB/PDF import, EPUB reader with table of contents, and PDF reader.
- Added .github/workflows/android-apk.yml to generate Android scaffolding and build a debug APK.
- Latest workflow commit: 21d9aa889ce27fba07463e4425a80b7a258c951a

## Unverified / blockers
- GitHub Actions build result not yet verified. Do not claim APK exists or is working.
- EPUB/PDF plugin compatibility and Android device behavior need testing.
- Saved reading position, cover art, themes, and bookmarks are not implemented in this initial scaffold.

## Next steps
1. Check Actions tab: https://github.com/john-selwyn/selura-reader/actions
2. If build fails, read logs and repair.
3. Download selura-debug-apk artifact and install on Android; test EPUB/PDF.
4. Implement saved progress, bookmarks, theme controls, cover art.
5. Update this file after each meaningful milestone.

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
