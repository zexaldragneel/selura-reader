# Selura — Project Context
Last updated: 2026-10-20

## ACTIVE DIRECTION — Manga-only Android reader
- Owner explicitly ended EPUB/PDF development on 2026-10-20. The target is **Selura Manga**, a premium manga reader with fully functional manga source extensions and **native Mihon .tachibk backup restoration**, not a hyperlink to Mihon. Build and deliver actual Android APKs through GitHub Actions; owner has no computer.
- **Migration PR #24** (feature/selura-native-manga-migration) builds from the *actual native Mihon engine*, upstream v0.21.2 at commit 9612d955db3165e1578fdf9ff19ca9b7762c4a46, Apache-2.0, with reproducible Selura branding and package ID. Mihon's original native BackupRestorer, source/extension manager, and manga reader remain functional source modules. Native app must be tested on Android; **CI/real backup tests are pending** as of this entry.
- Preview Android package: **com.selura.manga** (separate from legacy Flutter com.selura.reader and official Mihon app.mihon). Deliberately install side by side to protect existing EPUB/PDF app data and source Mihon backup; **do not uninstall** either old application before successful restore test.
- Expected owner workflow: export .tachibk in Mihon; install new signed Selura Manga APK; restore through native Settings > Data and storage > Restore backup; verify manga library, categories, source extensions, chapter history and progress; configure trusted Keiyoushi repo; read chapters *in Selura Manga*.
- Current `main` contains working legacy Flutter EPUB/PDF reader, retained only as fallback. Old unmerged PRs #21 (CBZ/online sources), #22 (Keiyoushi hyperlink/MangaDex), #23 (metadata-only Mihon restore) are superseded by the native-manga migration; do not merge them into main by default.
- Native migration files are in `native_manga/` and `.github/workflows/native-manga-apk.yml`. A successful build and user on-device test are required before making the native build primary and archiving the Flutter code. Retain original Mihon license/attribution; do not present customized Selura as official Mihon.
- Respect website authentication, source licensing, age restrictions, and extension signing checks. Third-party APK extensions are executable code; only install from sources the user trusts and authorizes.
- Stable working old Selura APK history remains available on GitHub. No user data is to be deleted. Do not modify other repositories or the user's VPS.

## LEGACY FLUTTER CONTEXT — Archived requirements below

Last updated: 2026-10-18

Selura is an original Android eBook reader inspired by Moon+ Reader's feature set. Name inspired by Selwyn and Ruffa.

## Requirements
- Android APK, offline-first; no computer required for user.
- GitHub Actions builds APK in cloud.
- EPUB and PDF import/read, bookshelf, saved reading progress.
- Implemented and Android-tested milestones: EPUB/PDF library, resume, bookmarks, appearance/themes, offline EPUB TTS, ZIP backup/restore, and reading Focus Mode with quick typography.
- User explicitly declined highlights/annotations (2026-10-18). Do not propose or implement them without a new request.
- Future: continue premium UI and performance refinements, offline reading comfort, optional TTS features, and possibly manga/CBZ if requested.
- Flutter/Dart, private repo preferred, app ID com.selura.reader.
- Original UI and licensed open-source dependencies only.

## Continuity
At the start of each new chat, read PROJECT_CONTEXT.md and PROGRESS.md from this repository and inspect GitHub Actions runs. Update PROGRESS.md with real commits, results, and blockers. Never claim an APK works without a successful build and user testing.
