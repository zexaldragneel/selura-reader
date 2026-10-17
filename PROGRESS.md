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
