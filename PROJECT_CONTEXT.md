# Selura — Project Context
Last updated: 2026-10-20

## ACTIVE DIRECTION — Manga-only Android reader
- **Actual NHentai.net first-party source (PR #25):** User screenshots confirm failing `NHentai` from **Cursed Yūzōnō 1.4.62** (not Keiyoushi's `nHentai.com (unoriginal)`). First-party separate signed `Selura NHentai` source, `selura_sources/nhentai/` and workflow `.github/workflows/selura-sources.yml`, based on Yuzono pinned Apache-2.0 `5dad5cf65dce98bb05ba8edf1f38770585e032b9`. Upstream randomly chooses CDN per page; Selura stabilizes per gallery and has bounded retries on declared nHentai.net CDNs. CI #8 `39390201876` passed build/signature/package and published separate source APK; **real on-phone source performance remains UNVERIFIED**. Distinct package/source IDs preserve existing installed extensions and library. Earlier `nhentai.to` experimental adapter does not ship.
- Owner explicitly ended EPUB/PDF development on 2026-10-20. The target is **Selura Manga**, a premium manga reader with fully functional manga source extensions and **native Mihon .tachibk backup restoration**, not a hyperlink to Mihon. Build and deliver actual Android APKs through GitHub Actions; owner has no computer.
- **Migration PR #24** (feature/selura-native-manga-migration) builds from the *actual native Mihon engine*, upstream v0.21.2 at commit 9612d955db3165e1578fdf9ff19ca9b7762c4a46, Apache-2.0, with reproducible Selura branding and package ID. Mihon's original native BackupRestorer, source/extension manager, and manga reader remain functional source modules. **Signed native Build #1 succeeded** in GitHub Actions run 39352273448, producing a validated direct APK; actual Mihon backup restoration and Keiyoushi chapter reading still require physical Android tests.
- Preview Android package: **com.selura.manga** (separate from legacy Flutter com.selura.reader and official Mihon app.mihon). Deliberately install side by side to protect existing EPUB/PDF app data and source Mihon backup; **do not uninstall** either old application before successful restore test.
- Expected owner workflow: export .tachibk in Mihon; install new signed Selura Manga APK; restore through native Settings > Data and storage > Restore backup; verify manga library, categories, source extensions, chapter history and progress; configure trusted Keiyoushi repo; read chapters *in Selura Manga*.
- Current `main` contains working legacy Flutter EPUB/PDF reader, retained only as fallback. Legacy PRs #21 (CBZ/online sources), #22 (Keiyoushi hyperlink/MangaDex), and #23 (metadata-only Mihon restore) have been closed unmerged as superseded by the native migration. Do not resurrect without a new request.
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
