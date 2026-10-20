#!/usr/bin/env python3
"""Apply auditable Selura branding to a pinned upstream Mihon source checkout.

Upstream: https://github.com/mihonapp/mihon v0.21.2
Commit: 9612d955db3165e1578fdf9ff19ca9b7762c4a46
License: Apache-2.0. Original license and source notices remain upstream.
This only applies branding and distinct app identity; all original manga,
extensions, and official Mihon backup/restore implementation stay native.
"""

import argparse
import os
import pathlib
import shutil
import xml.etree.ElementTree as ET

UPSTREAM_SHA = "9612d955db3165e1578fdf9ff19ca9b7762c4a46"
NATIVE_APPLICATION_ID = "com.selura.manga"
APP_LABEL = "Selura Manga"
LEGACY_FLUTTER_APPLICATION_ID = "com.selura.reader"
DEFAULT_VERSION_CODE = 1001


class IncompatibleUpstreamError(RuntimeError):
    """Fail closed if pinned upstream files have changed."""


def substitute_exact(root: pathlib.Path, relative: str, old: str, new: str):
    target = root / relative
    original = target.read_text(encoding="utf-8")
    if original.count(old) != 1:
        raise IncompatibleUpstreamError(
            f"Expected exactly one upstream marker in {relative}: {old!r}; "
            f"found {original.count(old)}"
        )
    target.write_text(original.replace(old, new), encoding="utf-8")


ICON_XML = """<?xml version="1.0" encoding="utf-8"?>
<!-- Selura customization: original vector launcher artwork, not Mihon trademarks. -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path android:fillColor="#181620"
        android:pathData="M0,0h108v108h-108z"/>
    <path android:fillColor="#B9A3E6"
        android:pathData="M15,25 Q35,18 54,31 L54,84 Q36,73 15,78 Z"/>
    <path android:fillColor="#E8DFFA"
        android:pathData="M93,25 Q73,18 54,31 L54,84 Q72,73 93,78 Z"/>
    <path android:strokeColor="#181620" android:strokeWidth="3"
        android:strokeLineCap="round"
        android:pathData="M54,31 L54,84"/>
</vector>
"""


def patch(root: pathlib.Path, version_code: int):
    if not 1 <= version_code <= 2_100_000_000:
        raise ValueError("Android version code outside supported range.")
    root = root.resolve()
    if not (root / "gradlew").is_file():
        raise IncompatibleUpstreamError("Expected a Mihon Gradle source checkout.")
    if not (root / "LICENSE").is_file():
        raise IncompatibleUpstreamError("Mihon Apache-2.0 license must be retained.")

    app_gradle = "app/build.gradle.kts"
    substitute_exact(root, app_gradle,
                     'applicationId = "app.mihon"',
                     f'applicationId = "{NATIVE_APPLICATION_ID}" // Selura customization')
    substitute_exact(root, app_gradle,
                     "versionCode = 38",
                     f"versionCode = {version_code} // Selura customization")
    substitute_exact(root, app_gradle,
                     'versionName = "0.21.2"',
                     'versionName = "0.1.0-native" // Selura customization')
    substitute_exact(root, "i18n/src/commonMain/moko-resources/base/strings.xml",
                     '<string name="app_name" translatable="false">Mihon</string>',
                     '<string name="app_name" translatable="false">Selura Manga</string>')
    substitute_exact(root, "app/src/main/AndroidManifest.xml",
                     'android:icon="@mipmap/ic_launcher"',
                     'android:icon="@drawable/selura_manga_icon"')
    substitute_exact(root, "app/src/main/AndroidManifest.xml",
                     'android:roundIcon="@mipmap/ic_launcher"',
                     'android:roundIcon="@drawable/selura_manga_icon"')
    substitute_exact(root, "settings.gradle.kts",
                     'rootProject.name = "Mihon"',
                     'rootProject.name = "SeluraManga" // Selura customization')

    # Add a genuine in-app Keiyoushi setup entry. The native Mihon
    # ExtensionStoresScreen fetches the actual protobuf index and requires
    # confirmation, preserving upstream extension-signature/trust checks.
    substitute_exact(
        root,
        "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsBrowseScreen.kt",
        """                    Preference.PreferenceItem.TextPreference(
                        title = stringResource(MR.strings.extensionStores),
                        subtitle = pluralStringResource(MR.plurals.num_repos, reposCount.toInt(), reposCount),
                        onClick = {
                            navigator.push(ExtensionStoresScreen())
                        },
                    ),""",
        """                    Preference.PreferenceItem.TextPreference(
                        title = stringResource(MR.strings.extensionStores),
                        subtitle = pluralStringResource(MR.plurals.num_repos, reposCount.toInt(), reposCount),
                        onClick = {
                            navigator.push(ExtensionStoresScreen())
                        },
                    ),
                    // Selura customization: consent-gated, in-app Keiyoushi store setup.
                    Preference.PreferenceItem.TextPreference(
                        title = "Add Keiyoushi extensions",
                        subtitle = "Review and add the official extension store",
                        onClick = {
                            navigator.push(
                                ExtensionStoresScreen(
                                    "https://github.com/keiyoushi/extensions/raw/repo/index.pb",
                                ),
                            )
                        },
                    ),""",
    )

    # Selura customization: show what is actually in the selected Mihon backup
    # before restoring. Category/settings-only backups must not appear to have
    # successfully restored a manga library.
    substitute_exact(
        root,
        "app/src/main/java/eu/kanade/tachiyomi/data/backup/BackupFileValidator.kt",
        "return Results(missingSources, missingTrackers)",
        """return Results(
            missingSources,
            missingTrackers,
            mangaCount = backup.backupManga.size,
            favoriteCount = backup.backupManga.count { it.favorite },
        )""",
    )
    substitute_exact(
        root,
        "app/src/main/java/eu/kanade/tachiyomi/data/backup/BackupFileValidator.kt",
        """        val missingTrackers: List<String>,
    )""",
        """        val missingTrackers: List<String>,
        val mangaCount: Int,
        val favoriteCount: Int,
    )""",
    )

    restore_screen = "app/src/main/java/eu/kanade/presentation/more/settings/screen/data/RestoreBackupScreen.kt"
    substitute_exact(
        root,
        restore_screen,
        """                if (state.canRestore) {
                    item {
                        SectionCard {
                            RestoreOptions.options.forEach""",
        """                if (state.canRestore) {
                    item {
                        SectionCard {
                            Column(
                                modifier = Modifier.padding(MaterialTheme.padding.medium),
                                verticalArrangement = Arrangement.spacedBy(MaterialTheme.padding.small),
                            ) {
                                Text(
                                    text = "Selected backup: ${state.mangaCount} manga; " +
                                        "${state.favoriteCount} marked as library entries.",
                                )
                                if (state.mangaCount == 0) {
                                    Text(
                                        text = "No manga entries were found in this backup. " +
                                            "Create a new backup in Mihon with Manga selected.",
                                    )
                                } else if (state.favoriteCount == 0) {
                                    Text(
                                        text = "No titles are marked as library favorites in " +
                                            "this backup; they may not appear in your Library.",
                                    )
                                }
                                if (!state.options.libraryEntries) {
                                    Text(text = "Enable Library below to restore manga titles.")
                                }
                            }
                        }
                    }
                    item {
                        SectionCard {
                            RestoreOptions.options.forEach""",
    )
    substitute_exact(
        root,
        restore_screen,
        """                canRestore = true,
            )
            return
        }

        setError(error = null, canRestore = true)""",
        """                canRestore = true,
                mangaCount = results.mangaCount,
                favoriteCount = results.favoriteCount,
            )
            return
        }

        setError(
            error = null,
            canRestore = true,
            mangaCount = results.mangaCount,
            favoriteCount = results.favoriteCount,
        )""",
    )
    substitute_exact(
        root,
        restore_screen,
        """    private fun setError(error: Any?, canRestore: Boolean) {
        state.update {
            it.copy(
                error = error,
                canRestore = canRestore,
            )
        }
    }""",
        """    private fun setError(
        error: Any?,
        canRestore: Boolean,
        mangaCount: Int = 0,
        favoriteCount: Int = 0,
    ) {
        state.update {
            it.copy(
                error = error,
                canRestore = canRestore,
                mangaCount = mangaCount,
                favoriteCount = favoriteCount,
            )
        }
    }""",
    )
    substitute_exact(
        root,
        restore_screen,
        """        val options: RestoreOptions = RestoreOptions(),
    )""",
        """        val options: RestoreOptions = RestoreOptions(),
        val mangaCount: Int = 0,
        val favoriteCount: Int = 0,
    )""",
    )

    # Selura: add a real one-tap Select All / Deselect All action to the
    # original source migration screen, which already supports bulk Copy/Migrate.
    # Selecting everything NEVER runs a migration automatically.
    manga_list_vm = "app/src/main/java/eu/kanade/tachiyomi/ui/browse/migration/manga/MigrateMangaViewModel.kt"
    substitute_exact(
        root,
        manga_list_vm,
        """    fun clearSelection() {
        selection.update { emptySet() }
    }""",
        """    fun clearSelection() {
        selection.update { emptySet() }
    }

    // Selura: operate only on this source's displayed favorites.
    fun toggleSelectAll() {
        val mangaIds = state.value.titles.mapTo(mutableSetOf()) { it.id }
        if (mangaIds.isEmpty()) return
        selection.update { selected ->
            if (mangaIds.all { it in selected }) emptySet() else mangaIds
        }
    }""",
    )
    substitute_exact(
        root,
        manga_list_vm,
        """        val selectionMode = selection.isNotEmpty()
    }""",
        """        val selectionMode = selection.isNotEmpty()

        val allSelected: Boolean
            get() = titles.isNotEmpty() && titles.all { it.id in selection }
    }""",
    )
    manga_list_screen = "app/src/main/java/eu/kanade/tachiyomi/ui/browse/migration/manga/MigrateMangaScreen.kt"
    substitute_exact(
        root,
        manga_list_screen,
        "import eu.kanade.presentation.components.AppBar\n",
        "import eu.kanade.presentation.components.AppBar\nimport eu.kanade.presentation.components.AppBarActions\n",
    )
    substitute_exact(
        root,
        manga_list_screen,
        "import mihon.icons.materialsymbols.automirroredrounded.ArrowForward\n",
        """import mihon.icons.materialsymbols.automirroredrounded.ArrowForward
import mihon.icons.materialsymbols.rounded.Deselect
import mihon.icons.materialsymbols.rounded.SelectAll
""",
    )
    substitute_exact(
        root,
        manga_list_screen,
        """                    scrollBehavior = scrollBehavior,
                )
            },
            floatingActionButton = {""",
        """                    actions = {
                        AppBarActions(
                            listOf(
                                AppBar.Action(
                                    title = if (state.allSelected) "Deselect all" else "Select all",
                                    icon = if (state.allSelected) {
                                        MaterialSymbols.Rounded.Deselect
                                    } else {
                                        MaterialSymbols.Rounded.SelectAll
                                    },
                                    onClick = viewModel::toggleSelectAll,
                                    enabled = !state.isEmpty,
                                ),
                            ),
                        )
                    },
                    scrollBehavior = scrollBehavior,
                )
            },
            floatingActionButton = {""",
    )

    # Selura: NHentai gallery IDs are stable between Yuzono and our own
    # source. Exact-ID lookup avoids unreliable long adult-gallery title matches.
    # Validate the returned URL: never auto-select a wrong title.
    migration_list_vm = "app/src/main/java/mihon/feature/migration/list/MigrationListViewModel.kt"
    substitute_exact(
        root,
        migration_list_vm,
        "import mihon.domain.migration.usecases.MigrateMangaUseCase\n",
        """import mihon.domain.migration.usecases.MigrateMangaUseCase
import mihon.domain.manga.model.toDomainManga
""",
    )
    substitute_exact(
        root,
        migration_list_vm,
        """            val searchResult = if (deepSearchMode) {
                smartSearchEngine.deepSearch(source, manga.title)
            } else {
                smartSearchEngine.regularSearch(source, manga.title)
            }""",
        """            val galleryId = manga.url.takeIf {
                source.name == "Selura NHentai" && it.matches(Regex("^/g/[0-9]+/?$"))
            }?.removePrefix("/g/")?.trimEnd('/')
            val searchResult = if (galleryId != null) {
                // The new extension resolves numeric IDs through its original API.
                // Do not fall back to fuzzy title matches for this exact gallery.
                source.getSearchManga(1, galleryId, source.getFilterList())
                    .mangas.firstOrNull {
                        it.url.trimEnd('/') == manga.url.trimEnd('/')
                    }?.toDomainManga(source.id)
            } else if (deepSearchMode) {
                smartSearchEngine.deepSearch(source, manga.title)
            } else {
                smartSearchEngine.regularSearch(source, manga.title)
            }""",
    )

    # Selura: when old/new sources refer to the identical NHentai gallery and
    # both have exactly one chapter, preserve bookmark, read status and exact
    # page position even though both native chapters have unknown numbers.
    # The generic Mihon migration semantics remain unchanged for every other
    # source and for any ambiguous/non-identical gallery.
    migration_usecase = "app/src/main/java/mihon/domain/migration/usecases/MigrateMangaUseCase.kt"
    substitute_exact(
        root,
        migration_usecase,
        """                val maxChapterRead = prevMangaChapters
                    .filter { it.read }
                    .maxOfOrNull { it.chapterNumber }

                val chapterUpdates = mangaChapters
                    .filter { it.isRecognizedNumber }
                    .map { mangaChapter ->
                        val prevChapter = prevMangaChapters
                            .find { it.isRecognizedNumber && it.chapterNumber == mangaChapter.chapterNumber }

                        ChapterUpdate(mangaChapter.id) {
                            if (prevChapter != null) {
                                dateFetch = prevChapter.dateFetch
                                bookmark = prevChapter.bookmark
                            }

                            if (maxChapterRead != null && mangaChapter.chapterNumber <= maxChapterRead) {
                                read = true
                            }
                        }
                    }
                updateChapter.awaitAll(chapterUpdates)""",
        """                val maxChapterRead = prevMangaChapters
                    .filter { it.read }
                    .maxOfOrNull { it.chapterNumber }

                val sameSeluraGallery = targetSource.name == "Selura NHentai" &&
                    current.url.matches(Regex("^/g/[0-9]+/?$")) &&
                    current.url.trimEnd('/') == target.url.trimEnd('/') &&
                    prevMangaChapters.size == 1 && mangaChapters.size == 1 &&
                    prevMangaChapters.single().url.trimEnd('/') ==
                        mangaChapters.single().url.trimEnd('/')

                val chapterUpdates = mangaChapters
                    .filter { it.isRecognizedNumber || sameSeluraGallery }
                    .map { mangaChapter ->
                        val prevChapter = prevMangaChapters.find {
                            (it.isRecognizedNumber && mangaChapter.isRecognizedNumber &&
                                it.chapterNumber == mangaChapter.chapterNumber) ||
                                (sameSeluraGallery && it.url.trimEnd('/') ==
                                    mangaChapter.url.trimEnd('/'))
                        }

                        ChapterUpdate(mangaChapter.id) {
                            if (prevChapter != null) {
                                dateFetch = prevChapter.dateFetch
                                bookmark = prevChapter.bookmark
                                if (sameSeluraGallery) {
                                    lastPageRead = prevChapter.lastPageRead
                                    read = prevChapter.read
                                }
                            }

                            if (!sameSeluraGallery && maxChapterRead != null &&
                                mangaChapter.chapterNumber <= maxChapterRead
                            ) {
                                read = true
                            }
                        }
                    }
                updateChapter.awaitAll(chapterUpdates)""",
    )

    # Selura NHentai: one-tap foreground-service-backed WorkManager copy.
    # Work is owned by Android rather than the migration screen's ViewModel,
    # so the reader remains usable throughout very large library copies.
    substitute_exact(
        root,
        manga_list_screen,
        "import androidx.compose.material3.Text\n",
        """import androidx.compose.material3.Text
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.TextButton
""",
    )
    substitute_exact(
        root,
        manga_list_screen,
        "import androidx.compose.runtime.LaunchedEffect\n",
        """import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
""",
    )
    substitute_exact(
        root,
        manga_list_screen,
        "import androidx.compose.runtime.getValue\n",
        """import androidx.compose.runtime.getValue
import mihon.feature.migration.background.SeluraNhentaiBackgroundCopyWorker
""",
    )
    substitute_exact(
        root,
        manga_list_screen,
        "        val navigator = LocalNavigator.currentOrThrow\n",
        """        val navigator = LocalNavigator.currentOrThrow
        var backgroundCopyConfirm by remember { mutableStateOf(false) }
""",
    )
    substitute_exact(
        root,
        manga_list_screen,
        """                                    enabled = !state.isEmpty,
                                ),
                            ),""",
        """                                    enabled = !state.isEmpty,
                                ),
                                AppBar.OverflowAction(
                                    title = "Copy NHentai in background",
                                    enabled = !state.isEmpty &&
                                        state.source?.name?.contains("nhentai", ignoreCase = true) == true,
                                    onClick = { backgroundCopyConfirm = true },
                                ),
                            ),""",
    )
    substitute_exact(
        root,
        manga_list_screen,
        "        LaunchedEffect(Unit) {\n",
        """        if (backgroundCopyConfirm) {
            AlertDialog(
                onDismissRequest = { backgroundCopyConfirm = false },
                title = { Text("Copy NHentai while you read") },
                text = {
                    Text(
                        "Copy numeric galleries to your installed Selura NHentai ALL source " +
                            "one at a time in the background. Originals, downloads and " +
                            "reading progress stay intact. Check the notification for " +
                            "progress, Stop, and retry.",
                    )
                },
                confirmButton = {
                    TextButton(
                        onClick = {
                            backgroundCopyConfirm = false
                            SeluraNhentaiBackgroundCopyWorker.start(
                                context.applicationContext,
                                sourceId,
                            )
                            context.toast("Background copy queued; you can continue reading")
                        },
                    ) { Text("Start background copy") }
                },
                dismissButton = {
                    TextButton(onClick = { backgroundCopyConfirm = false }) {
                        Text("Cancel")
                    }
                },
            )
        }

        LaunchedEffect(Unit) {
""",
    )

    # AppGraph performs Metro injection for WorkManager workers in Mihon.
    # Keep the existing dependency graph and its providers untouched.
    app_graph = "app/src/main/java/mihon/app/di/AppGraph.kt"
    substitute_exact(
        root,
        app_graph,
        "import eu.kanade.tachiyomi.data.backup.restore.BackupRestoreWorker\n",
        """import eu.kanade.tachiyomi.data.backup.restore.BackupRestoreWorker
import mihon.feature.migration.background.SeluraNhentaiBackgroundCopyWorker
""",
    )
    substitute_exact(
        root,
        app_graph,
        "    fun inject(backupRestoreWorker: BackupRestoreWorker)\n",
        """    fun inject(backupRestoreWorker: BackupRestoreWorker)
    fun inject(seluraNhentaiBackgroundCopyWorker: SeluraNhentaiBackgroundCopyWorker)
""",
    )
    background_source = (
        pathlib.Path(__file__).resolve().parent /
        "background_migration/SeluraNhentaiBackgroundCopyWorker.kt"
    )
    background_destination = (
        root /
        "app/src/main/java/mihon/feature/migration/background/SeluraNhentaiBackgroundCopyWorker.kt"
    )
    if not background_source.is_file() or background_destination.exists():
        raise IncompatibleUpstreamError("Invalid Selura background migration worker source.")
    background_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(background_source, background_destination)

    # Never delete the original downloaded galleries when users choose Copy,
    # even if they previously selected the generic Remove Downloads option.
    substitute_exact(
        root,
        migration_usecase,
        "if (MigrationFlag.REMOVE_DOWNLOAD in flags && currentSource != null) {",
        "if (replace && MigrationFlag.REMOVE_DOWNLOAD in flags && currentSource != null) {",
    )

    # Selura startup update prompt. Mihon's update checker stays disabled
    # because it points to Mihon's releases; the first-party read-only manifest
    # is intended to be published independently with explicit owner consent.
    substitute_exact(
        root,
        "app/src/main/java/eu/kanade/tachiyomi/ui/main/MainActivity.kt",
        """                if (!isBenchmarkBuildType) {
                    if (isLaunch) CheckForUpdates()
                    ShowOnboarding()
                    ShowDonationCampaign()
                }""",
        """                if (!isBenchmarkBuildType) {
                    if (isLaunch) {
                        CheckForUpdates()
                        SeluraStartupUpdateCheck()
                    }
                    ShowOnboarding()
                    ShowDonationCampaign()
                }""",
    )
    update_source = (
        pathlib.Path(__file__).resolve().parent /
        "selura_updater/SeluraStartupUpdateCheck.kt"
    )
    update_dest = (
        root /
        "app/src/main/java/eu/kanade/tachiyomi/ui/main/SeluraStartupUpdateCheck.kt"
    )
    if update_dest.exists():
        raise IncompatibleUpstreamError("Native Selura updater already exists.")
    if not update_source.is_file():
        raise IncompatibleUpstreamError("Missing first-party Selura updater source.")
    shutil.copyfile(update_source, update_dest)

    icon = root / "app/src/main/res/drawable/selura_manga_icon.xml"
    icon.parent.mkdir(parents=True, exist_ok=True)
    icon.write_text(ICON_XML, encoding="utf-8")
    ET.parse(icon)

    gradle = (root / app_gradle).read_text(encoding="utf-8")
    assert f'applicationId = "{NATIVE_APPLICATION_ID}"' in gradle
    assert f"versionCode = {version_code}" in gradle
    assert 'namespace = "eu.kanade.tachiyomi"' in gradle
    assert "signingConfig = debug.signingConfig" in gradle, (
        "Upstream signing contract changed; do not produce unsigned APK."
    )
    assert LEGACY_FLUTTER_APPLICATION_ID != NATIVE_APPLICATION_ID
    manifest = (root / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    assert '@drawable/selura_manga_icon' in manifest
    assert 'android:label="@string/app_name"' in manifest
    for native_feature in (
        "app/src/main/java/eu/kanade/tachiyomi/data/backup/restore/BackupRestorer.kt",
        "app/src/main/java/eu/kanade/tachiyomi/extension/ExtensionManager.kt",
        "app/src/main/java/eu/kanade/tachiyomi/ui/reader/viewer/webtoon/WebtoonConfig.kt",
    ):
        if not (root / native_feature).is_file():
            raise IncompatibleUpstreamError(
                f"Missing native Mihon feature: {native_feature}"
            )
    print(f"Prepared {APP_LABEL} ({NATIVE_APPLICATION_ID}); versionCode {version_code}")
    print("Original native Mihon backup/restore and extension code remain intact.")
    print("Apache-2.0 license and contributor notices remain in upstream checkout.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=pathlib.Path,
                        help="Existing checkout of pinned Mihon upstream commit")
    parser.add_argument("--version-code", type=int,
                        default=int(os.getenv("SELURA_NATIVE_VERSION_CODE",
                                            str(DEFAULT_VERSION_CODE))))
    args = parser.parse_args()
    patch(args.upstream, args.version_code)


if __name__ == "__main__":
    main()
