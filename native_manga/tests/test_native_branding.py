"""Contract tests for the pinned Mihon -> Selura Native customization.

These run before the Android build and use an isolated upstream fixture.
They ensure app identity, backup/extension retention and fail-closed patches.
"""

import pathlib
import tempfile
import unittest

from native_manga.apply_branding import (
    APP_LABEL,
    LEGACY_FLUTTER_APPLICATION_ID,
    NATIVE_APPLICATION_ID,
    IncompatibleUpstreamError,
    patch,
)


class NativeMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)

        def write(name: str, text: str):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

        write("gradlew", "#!/bin/sh\n")
        write("LICENSE", "Apache-2.0 test fixture; real license stays intact.\n")
        write(
            "app/build.gradle.kts",
            'android {\n'
            '  namespace = "eu.kanade.tachiyomi"\n'
            '  defaultConfig {\n'
            '    applicationId = "app.mihon"\n'
            '    versionCode = 38\n'
            '    versionName = "0.21.2"\n'
            '  }\n'
            '  buildTypes {\n'
            '    getByName("release") {\n'
            '      signingConfig = debug.signingConfig\n'
            '    }\n'
            '  }\n'
            '}\n',
        )
        write(
            "i18n/src/commonMain/moko-resources/base/strings.xml",
            '<resources><string name="app_name" translatable="false">'
            'Mihon</string></resources>',
        )
        write(
            "app/src/main/AndroidManifest.xml",
            '<manifest><application android:icon="@mipmap/ic_launcher" '
            'android:roundIcon="@mipmap/ic_launcher" '
            'android:label="@string/app_name">'
            '<provider android:authorities="${applicationId}.provider" />'
            '</application></manifest>\n',
        )
        write("settings.gradle.kts", 'rootProject.name = "Mihon"\n')
        write(
            "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsBrowseScreen.kt",
            """object SettingsBrowseScreen {
                    Preference.PreferenceItem.TextPreference(
                        title = stringResource(MR.strings.extensionStores),
                        subtitle = pluralStringResource(MR.plurals.num_repos, reposCount.toInt(), reposCount),
                        onClick = {
                            navigator.push(ExtensionStoresScreen())
                        },
                    ),
            }""",
        )
        write(
            "app/src/main/java/eu/kanade/tachiyomi/data/backup/BackupFileValidator.kt",
            """class BackupFileValidator {
        fun validate(backup: Backup): Results {
            return Results(missingSources, missingTrackers)
        }
    data class Results(
        val missingSources: List<String>,
        val missingTrackers: List<String>,
    )
}""",
        )
        write(
            "app/src/main/java/eu/kanade/presentation/more/settings/screen/data/RestoreBackupScreen.kt",
            """class RestoreBackupScreen {
                if (state.canRestore) {
                    item {
                        SectionCard {
                            RestoreOptions.options.forEach { option ->
                                LabeledCheckbox(label = stringResource(option.label))
                            }
                        }
                    }
                }
                canRestore = true,
            )
            return
        }

        setError(error = null, canRestore = true)

    private fun setError(error: Any?, canRestore: Boolean) {
        state.update {
            it.copy(
                error = error,
                canRestore = canRestore,
            )
        }
    }

        val options: RestoreOptions = RestoreOptions(),
    )
            }""",
        )
        # Native batch migration fixtures. Each uses the exact audited Mihon
        # v0.21.2 anchor; the test deliberately fails on upstream changes.
        write(
            "app/src/main/java/eu/kanade/tachiyomi/ui/browse/migration/manga/MigrateMangaViewModel.kt",
            """class MigrateMangaViewModel {
    fun clearSelection() {
        selection.update { emptySet() }
    }

    data class State(
        val titles: List<Manga>,
    ) {
        val selectionMode = selection.isNotEmpty()
    }
}""",
        )
        write(
            "app/src/main/java/eu/kanade/tachiyomi/ui/browse/migration/manga/MigrateMangaScreen.kt",
            """import androidx.compose.material3.Text
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import eu.kanade.presentation.components.AppBar
import mihon.icons.materialsymbols.automirroredrounded.ArrowForward

class MigrateMangaScreen {
        val navigator = LocalNavigator.currentOrThrow
        Scaffold(
            topBar = { scrollBehavior ->
                AppBar(
                    title = state.source!!.name,
                    navigateUp = {
                        if (state.selectionMode) {
                            viewModel.clearSelection()
                        } else {
                            navigator.pop()
                        }
                    },
                    scrollBehavior = scrollBehavior,
                )
            },
            floatingActionButton = {
            }
        )
        LaunchedEffect(Unit) {
        }
}""",
        )
        write(
            "app/src/main/java/mihon/feature/migration/list/MigrationListViewModel.kt",
            """import mihon.domain.migration.usecases.MigrateMangaUseCase

class MigrationListViewModel {
        fun search() {
            val searchResult = if (deepSearchMode) {
                smartSearchEngine.deepSearch(source, manga.title)
            } else {
                smartSearchEngine.regularSearch(source, manga.title)
            }
        }
}""",
        )
        write(
            "app/src/main/java/mihon/domain/migration/usecases/MigrateMangaUseCase.kt",
            """class MigrateMangaUseCase {
    suspend operator fun invoke(current: Manga, target: Manga, replace: Boolean) {
        val flags = sourcePreferences.migrationFlags.get()
        try {
            // Update chapters read, bookmark and dateFetch
            if (MigrationFlag.CHAPTER in flags) {
                val prevMangaChapters = getChaptersByMangaId.await(current.id)
                val mangaChapters = getChaptersByMangaId.await(target.id)

                val maxChapterRead = prevMangaChapters
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
                updateChapter.awaitAll(chapterUpdates)
            }
            if (MigrationFlag.CATEGORY in flags) {
                val categoryIds = getCategories.await(current.id).map { it.id }
                setMangaCategories.await(target.id, categoryIds)
            }
            if (MigrationFlag.REMOVE_DOWNLOAD in flags && currentSource != null) {
                scope.launch { downloadManager.deleteManga(current, currentSource) }
            }
        } catch (e: Throwable) {
            if (e is CancellationException) {
                throw e
            }
        }
    }
}""",
        )
        write(
            "app/src/main/java/eu/kanade/tachiyomi/ui/main/MainActivity.kt",
            """class MainActivity : BaseActivity() {
                if (!isBenchmarkBuildType) {
                    if (isLaunch) CheckForUpdates()
                    ShowOnboarding()
                    ShowDonationCampaign()
                }
            }""",
        )
        write(
            "app/src/main/java/mihon/app/di/AppGraph.kt",
            """import eu.kanade.tachiyomi.data.backup.restore.BackupRestoreWorker
interface AppGraph {
    fun inject(backupRestoreWorker: BackupRestoreWorker)
}
""",
        )
        for native in (
            "app/src/main/java/eu/kanade/tachiyomi/data/backup/restore/BackupRestorer.kt",
            "app/src/main/java/eu/kanade/tachiyomi/extension/ExtensionManager.kt",
            "app/src/main/java/eu/kanade/tachiyomi/ui/reader/viewer/webtoon/WebtoonConfig.kt",
        ):
            write(native, "package eu.kanade.tachiyomi\n")

    def test_native_branding_keeps_upstream_restore_and_extensions(self):
        patch(self.root, 2001)
        gradle = (self.root / "app/build.gradle.kts").read_text()
        self.assertIn('applicationId = "com.selura.manga"', gradle)
        self.assertIn("versionCode = 2001", gradle)
        self.assertIn("namespace = \"eu.kanade.tachiyomi\"", gradle)
        self.assertNotIn('applicationId = "app.mihon"', gradle)
        i18n = (self.root /
                "i18n/src/commonMain/moko-resources/base/strings.xml").read_text()
        self.assertIn(">Selura Manga</string>", i18n)
        manifest = (self.root / "app/src/main/AndroidManifest.xml").read_text()
        self.assertIn("@drawable/selura_manga_icon", manifest)
        self.assertIn("android:label", manifest)
        self.assertTrue((self.root / "LICENSE").exists())
        self.assertNotEqual(NATIVE_APPLICATION_ID, LEGACY_FLUTTER_APPLICATION_ID)
        self.assertEqual(APP_LABEL, "Selura Manga")
        settings = (
            self.root /
            "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsBrowseScreen.kt"
        ).read_text(encoding="utf-8")
        self.assertIn("Add Keiyoushi extensions", settings)
        self.assertIn(
            "https://github.com/keiyoushi/extensions/raw/repo/index.pb", settings
        )
        self.assertIn("navigator.push(ExtensionStoresScreen())", settings)
        self.assertIn("ExtensionStoresScreen(\n", settings)
        self.assertNotIn("Intent.ACTION_VIEW", settings)
        self.assertNotIn("startActivity", settings)
        self.assertNotIn("installPackage", settings)

    def test_selura_update_prompt_preserves_native_updater_separation(self):
        patch(self.root, 2025)
        main = (self.root /
            "app/src/main/java/eu/kanade/tachiyomi/ui/main/MainActivity.kt").read_text()
        updater = (self.root /
            "app/src/main/java/eu/kanade/tachiyomi/ui/main/SeluraStartupUpdateCheck.kt").read_text()
        self.assertIn("if (isLaunch) {", main)
        self.assertIn("SeluraStartupUpdateCheck()", main)
        self.assertIn("CheckForUpdates()", main)
        self.assertIn("BuildConfig.VERSION_CODE", updater)
        self.assertIn("Selura Manga update available", updater)
        self.assertIn('Text("Later")', updater)
        self.assertIn("raw.githubusercontent.com/zexaldragneel/selura-reader/gh-pages/updates/latest.json", updater)
        self.assertIn('segments[1] != "selura-reader"', updater)
        self.assertNotIn("github_pat_", updater)
        installer = (self.root /
            "app/src/main/java/eu/kanade/tachiyomi/ui/main/SeluraApkInstaller.kt").read_text()
        self.assertIn("SeluraApkInstaller.download(", updater)
        self.assertIn("LinearProgressIndicator(", updater)
        self.assertIn('Text("Download update")', updater)
        self.assertIn('Text("Install")', updater)
        self.assertIn("sha256 = digest.lowercase()", updater)
        self.assertIn("MessageDigest.getInstance(\"SHA-256\")", installer)
        self.assertIn("archiveIsSafe(context, partial, offer)", installer)
        self.assertIn("PackageManager.GET_SIGNING_CERTIFICATES", installer)
        self.assertIn("FileProvider.getUriForFile(", installer)
        self.assertIn("Intent.ACTION_VIEW", installer)
        self.assertIn("Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES", installer)
        self.assertIn("currentCoroutineContext().ensureActive()", installer)
        self.assertNotIn("openUri(update.releaseUrl)", updater)

    def test_refuse_modified_main_activity_update_entry(self):
        main = (self.root /
            "app/src/main/java/eu/kanade/tachiyomi/ui/main/MainActivity.kt")
        main.write_text(main.read_text().replace(
            "if (isLaunch) CheckForUpdates()",
            "if (isLaunch) Unit",
        ))
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2026)

    def test_mihon_backup_preview_reports_library_counts(self):
        patch(self.root, 2011)
        validator = (
            self.root /
            "app/src/main/java/eu/kanade/tachiyomi/data/backup/BackupFileValidator.kt"
        ).read_text()
        screen = (
            self.root /
            "app/src/main/java/eu/kanade/presentation/more/settings/screen/data/RestoreBackupScreen.kt"
        ).read_text()
        self.assertIn("mangaCount = backup.backupManga.size", validator)
        self.assertIn("favoriteCount = backup.backupManga.count { it.favorite }", validator)
        self.assertIn("Selected backup:", screen)
        self.assertIn("mangaCount = results.mangaCount", screen)
        self.assertIn("favoriteCount = results.favoriteCount", screen)
        self.assertIn("Enable Library below", screen)
        self.assertIn("No manga entries were found", screen)

    def test_batch_migration_select_all_and_exact_nhentai_gallery(self):
        patch(self.root, 2022)
        vm = (self.root /
              "app/src/main/java/eu/kanade/tachiyomi/ui/browse/migration/manga/MigrateMangaViewModel.kt").read_text()
        screen = (self.root /
                  "app/src/main/java/eu/kanade/tachiyomi/ui/browse/migration/manga/MigrateMangaScreen.kt").read_text()
        migration = (self.root /
                     "app/src/main/java/mihon/feature/migration/list/MigrationListViewModel.kt").read_text()
        usecase = (self.root /
                   "app/src/main/java/mihon/domain/migration/usecases/MigrateMangaUseCase.kt").read_text()
        self.assertIn("fun toggleSelectAll()", vm)
        self.assertIn("mangaIds.all { it in selected }", vm)
        self.assertIn("val allSelected: Boolean", vm)
        self.assertIn('title = if (state.allSelected) "Deselect all" else "Select all"', screen)
        self.assertIn("viewModel::toggleSelectAll", screen)
        self.assertIn('source.name == "Selura NHentai"', migration)
        self.assertIn('it.matches(Regex("^/g/[0-9]+/?$"))', migration)
        self.assertIn("it.url.trimEnd('/') == manga.url.trimEnd('/')", migration)
        self.assertIn("toDomainManga(source.id)", migration)
        self.assertIn("val sameSeluraGallery", usecase)
        self.assertIn("prevMangaChapters.size == 1 && mangaChapters.size == 1", usecase)
        self.assertIn("lastPageRead = maxOf(mangaChapter.lastPageRead, prevChapter.lastPageRead)", usecase)
        self.assertIn("read = mangaChapter.read || prevChapter.read", usecase)
        self.assertIn("bookmark = mangaChapter.bookmark || prevChapter.bookmark", usecase)
        self.assertIn("if (!sameSeluraGallery && maxChapterRead != null", usecase)

    def test_background_nhentai_move_verifies_target_before_unfavoriting_source(self):
        patch(self.root, 2024)
        worker = (self.root /
                  "app/src/main/java/mihon/feature/migration/background/SeluraNhentaiBackgroundCopyWorker.kt").read_text()
        screen = (self.root /
                  "app/src/main/java/eu/kanade/tachiyomi/ui/browse/migration/manga/MigrateMangaScreen.kt").read_text()
        graph = (self.root /
                 "app/src/main/java/mihon/app/di/AppGraph.kt").read_text()
        usecase = (self.root /
                   "app/src/main/java/mihon/domain/migration/usecases/MigrateMangaUseCase.kt").read_text()
        self.assertIn("Migrate NHentai in background", screen)
        self.assertIn("SeluraNhentaiBackgroundCopyWorker.start(", screen)
        self.assertIn("fun inject(seluraNhentaiBackgroundCopyWorker:", graph)
        self.assertIn("class SeluraNhentaiBackgroundCopyWorker", worker)
        self.assertIn("ExistingWorkPolicy.KEEP", worker)
        self.assertIn("setForegroundSafely()", worker)
        self.assertIn("last_moved_manga_", worker)
        self.assertIn("replace = false", worker)
        self.assertIn("matching.toDomainManga(target.id)", worker)
        self.assertIn('Regex("^/g/[0-9]+/?$")', worker)
        self.assertIn("sourceManager.getOnlineSources()", worker)
        self.assertIn("createCancelPendingIntent(id)", worker)
        self.assertIn("if (replace && MigrationFlag.REMOVE_DOWNLOAD in flags", usecase)
        self.assertNotIn("replace = true", worker)
        # Failure IDs and the cursor must survive cancellation together;
        # re-entry skips successful entries, not failed entries.
        self.assertIn('val failuresKey = "failed_move_manga_"', worker)
        self.assertIn("getFavorites.subscribe(sourceId).first()", worker)
        self.assertIn("putStringSet(failuresKey", worker)
        self.assertIn(".putLong(cursorKey, manga.id)", worker)
        self.assertIn("failedIds.add(manga.id)", worker)
        self.assertIn("failedIds.remove(manga.id)", worker)
        self.assertNotIn("remove(cursorKey)", worker)
        self.assertIn("getFavorites.subscribe(target.id).first()", worker)
        self.assertIn("val existing = existingTargets[canonicalUrl]", worker)
        self.assertIn("setRequiredNetworkType(NetworkType.CONNECTED)", worker)
        self.assertIn("setupFailure(", worker)
        self.assertIn("updateManga.awaitAll(listOf(MangaUpdate(manga.id) { favoriteAt = null }))", worker)
        self.assertIn("strict = true", worker)
        self.assertIn("getChaptersByMangaId.await(targetManga.id)", worker)
        self.assertIn("targetCategories.containsAll(originalCategories)", worker)
        self.assertIn("inputData.getString(MODE) != MOVE_MODE", worker)
        self.assertIn("cancelUniqueWork(LEGACY_COPY_WORK)", worker)
        self.assertIn("selected + setOf(", usecase)
        self.assertIn("MigrationFlag.CHAPTER,", usecase)
        self.assertIn("MigrationFlag.CATEGORY,", usecase)
        self.assertIn("if (e is CancellationException || strict)", usecase)
        self.assertIn("getCategories.await(target.id)", usecase)

    def test_refuse_unexpected_upstream_batch_migration_marker(self):
        vm = (self.root /
              "app/src/main/java/eu/kanade/tachiyomi/ui/browse/migration/manga/MigrateMangaViewModel.kt")
        vm.write_text(vm.read_text().replace(
            "selection.update { emptySet() }",
            "selection.update { selected -> selected }",
        ))
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2023)

    def test_refuse_modified_backup_validator_contract(self):
        validator = (
            self.root /
            "app/src/main/java/eu/kanade/tachiyomi/data/backup/BackupFileValidator.kt"
        )
        validator.write_text(validator.read_text().replace(
            "return Results(missingSources, missingTrackers)",
            "return Results(emptyList(), emptyList())",
        ))
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2009)

    def test_refuse_modified_extension_store_entry(self):
        settings = (
            self.root /
            "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsBrowseScreen.kt"
        )
        settings.write_text(
            settings.read_text().replace(
                "navigator.push(ExtensionStoresScreen())",
                "navigator.pop()",
            ),
            encoding="utf-8",
        )
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2002)

    def test_refuse_unexpected_upstream_variant(self):
        path = self.root / "app/build.gradle.kts"
        path.write_text(path.read_text().replace("app.mihon", "modified.other"))
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2002)

    def test_refuse_missing_native_extension_host(self):
        (self.root /
         "app/src/main/java/eu/kanade/tachiyomi/extension/ExtensionManager.kt").unlink()
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2002)

    def test_refuse_invalid_version_code(self):
        for invalid in (0, -1, 2_200_000_000):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    patch(self.root, invalid)

    def test_refuse_double_patching(self):
        patch(self.root, 2010)
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2010)


if __name__ == "__main__":
    unittest.main()
