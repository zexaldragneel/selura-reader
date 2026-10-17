# Selura — Development Progress
Last updated: 2026-10-17

## Confirmed
- GitHub repository: https://github.com/john-selwyn/selura-reader
- README.md on main confirmed accessible.
- Name: Selura; Android APK, offline-first Flutter app.

## Work in progress
- Add initial Flutter source, EPUB/PDF libraries and CI build workflow.
- CI builds must be checked; no successful APK has yet been verified.

## Next steps
1. Commit Flutter application and GitHub Actions.
2. Verify GitHub Actions run, repair dependency/Android build errors.
3. Download APK artifact and test EPUB/PDF import on Android.
4. Implement bookmarks, typography/themes, cover art and richer bookshelf.

## Notes
The workflow uses flutter create to generate missing Android platform scaffolding in CI. Production signing and Play Store distribution are not yet configured.
