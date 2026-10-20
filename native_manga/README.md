# Selura Manga — Native Android Migration (Preview)

## Decision
**Selura is becoming a manga-only, Android-native reader.** The existing Flutter EPUB/PDF reader will no longer receive new feature development. We have not deleted the working legacy APK yet. The new build must pass Android installation, real Mihon backup restore, Keiyoushi-source installation and chapter-reading tests before final promotion.

## Why use Mihon as the engine?
Mihon already implements the workflows required by the owner:
- Original .tachibk backup parsing and restoration, including manga library, categories, chapters, progress/history, source metadata and supported extension store metadata
- Native Android extension management (including compatible Keiyoushi APKs), source search, manga chapter browsing, cookies/network handling and reader views (paged, webtoon, RTL and vertical)
- Image fetching, downloading, local reading, reading progress and database migrations

The previous Selura Flutter importer could restore metadata only, not execute Mihon extension APKs. Building with native Mihon source solves the compatibility mismatch.

## Source, provenance and license
- Upstream code: https://github.com/mihonapp/mihon
- Based on release v0.21.2, pinned to commit 9612d955db3165e1578fdf9ff19ca9b7762c4a46
- Upstream license: Apache-2.0, retained in the build checkout and published source.
- Original copyrights, contributor credits and unchanged source files remain part of the build. Changes are documented and marked in the modified source. Selura Manga is an independent customized build, not an official Mihon release.
- Native source is fetched from the pinned public Git commit in CI, then customized reproducibly by native_manga/apply_branding.py. Original backup, extension and manga runtime is retained: not a hyperlink or web viewer.
- First preview customizes app identity, app name, own launcher vector, version number and signing. Upstream automatic updater/telemetry disabled by build flags.
- The native Settings → Browse screen also offers a consent-gated **Add Keiyoushi extensions** action. It passes the documented official index directly to Mihon's `ExtensionStoresScreen` and retains native repository trust verification, extension installation, refresh and removal. No silent third-party APK installation and no external Mihon handoff.

## Android identity and data safety
- Legacy Flutter Selura: com.selura.reader
- Official Mihon: app.mihon
- Native Selura Manga preview: com.selura.manga
- The new package installs ALONGSIDE both other apps because Android package storage is isolated. Do not uninstall old apps until the new reader passes physical testing. Previous EPUB/PDF library does not transfer automatically and is not deleted by the new installation.
- Reuses Selura's established signing certificate without storing plaintext keystore/password in Git.
- Future native builds use incrementing Android version codes and pinned/reviewed upstream revisions.

## How to test an exported Mihon backup on your Android phone
1. In Mihon: Settings → Data and storage → Create backup. Include manga, categories, progress/history, tracking and extension stores as needed. Save the .tachibk outside app data.
2. Install the signed selura-manga.apk from Selura GitHub Actions as a NEW app, leaving existing Mihon and Flutter Selura installed.
3. Open Selura Manga, follow any storage-folder setup and grant Android access only as needed.
4. Open Settings → Data and storage → Restore backup. Select the original .tachibk, then check manga/categories/chapter history and reading positions.
5. Open **Settings → Browse → Add Keiyoushi extensions**. Selura opens Mihon's real extension-store confirmation screen **inside Selura**, using the official protobuf index `https://github.com/keiyoushi/extensions/raw/repo/index.pb`. Review the provider before confirming. This is not a companion-app link. If needed, use the standard Extension stores manager under the same Settings → Browse screen.
6. Review source signing and install only extensions you trust. Browse manga, read a real chapter, close/reopen, verify resume and history.
7. Missing providers may leave restored metadata without readable online pages. Backups do not include every downloaded manga image, and Selura will not bypass website access controls.

## Build verification
- Patch tests fail closed if the upstream source shape or native backup/extension modules change.
- CI pins Mihon upstream commit, preserves original license, builds the Android release using Java 21 and the native Gradle project.
- CI decrypts the existing Selura signer only in a trusted runner, verifies app ID, signer and version, and publishes an immutable signed preview APK.
- CI success alone does not prove live backup restore or Keiyoushi browsing: owner must test on phone.
- Automated source-level tests verify that the original repository manager remains accessible, the Keiyoushi entry uses the live in-app consent flow, and upstream source variations fail closed.
- If CI fails, inspect errors before releasing an APK.

## Promotion after testing
When native Selura Manga works on the owner's phone, make it the primary app, archive obsolete Flutter EPUB/PDF code with intact Git history and old downloadable APKs, then iterate premium manga-specific design. Do not remove working legacy versions or delete user data without a verified migration.
