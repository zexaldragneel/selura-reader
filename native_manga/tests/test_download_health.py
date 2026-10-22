"""Non-destructive download-storage spot check patch contracts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "check_download_health.py"
spec = importlib.util.spec_from_file_location("selura_health", SCRIPT)
health = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health)

SETTINGS = '''package eu.kanade.presentation.more.settings.screen
import androidx.compose.runtime.remember
import eu.kanade.presentation.more.settings.widget.TriStateListDialog
import mihon.app.di.appGraph
object SettingsDownloadScreen {
        val downloadPreferences = remember { context.appGraph.downloadPreferences }
        return listOf(
            getDeleteChaptersGroup(
                downloadPreferences = downloadPreferences,
            ),
        )
}'''


class DownloadStorageHealthContracts(unittest.TestCase):
    def test_settings_action_is_visible_and_non_destructive(self):
        changed = health.patch_settings(SETTINGS)
        self.assertIn('title = context.getString(R.string.selura_health_title)', changed)
        self.assertIn("SeluraDownloadHealth.scan(context, storagePreferences)", changed)
        self.assertIn("if (!checkingStorage)", changed)
        self.assertIn("rememberCoroutineScope()", changed)
        self.assertIn("MaterialAlertDialogBuilder(context)", changed)
        self.assertIn("CancellationException", changed)
        self.assertNotIn("deleteChapters(", changed)
        self.assertNotIn("clearQueue(", changed)

    def test_finds_existing_downloads_without_creating_folders(self):
        source = health.HEALTH_SOURCE
        self.assertIn('val root = base?.findFile("downloads")', source)
        self.assertIn("UniFile.fromUri(", source)
        self.assertIn("storagePreferences.baseStorageDirectory.get()", source)
        self.assertNotIn("createDirectory(", source)
        self.assertNotIn("val root = storageManager.getDownloadsDirectory()", source)

    def test_scan_runs_on_io_and_checks_real_saved_directory_structure(self):
        source = health.HEALTH_SOURCE
        self.assertIn("withContext(Dispatchers.IO)", source)
        self.assertIn("currentCoroutineContext().ensureActive()", source)
        self.assertIn("for (source in root.listFiles().orEmpty())", source)
        self.assertIn("for (manga in source.listFiles().orEmpty())", source)
        self.assertIn("for (chapter in manga.listFiles().orEmpty())", source)
        self.assertIn("chapter.name.orEmpty()", source)
        self.assertIn("Downloader.TMP_DIR_SUFFIX", source)

    def test_uses_bounded_spot_checks_not_false_completeness_claims(self):
        source = health.HEALTH_SOURCE
        self.assertIn("private const val MAX_CHAPTERS = 2500", source)
        self.assertIn("private const val MAX_ZIP_ENTRIES = 4096", source)
        self.assertIn("ImageUtil.findImageType { file.openInputStream() } != null", source)
        self.assertIn("chapter.archiveReader(context).use { reader ->", source)
        self.assertIn("reader.useEntries { entries ->", source)
        self.assertIn("reader.getInputStream(entry.name)", source)
        self.assertIn("entries.take(MAX_ZIP_ENTRIES).firstOrNull", source)
        self.assertNotIn("ZipInputStream(", source)
        self.assertNotIn("chapter.length() <= 0L", source)
        self.assertIn("CheckState.UNVERIFIED", source)
        self.assertIn("unverified++", source)
        self.assertIn("catch (e: CancellationException)", source)
        self.assertIn("throw e", source)
        self.assertIn("catch (_: Exception)", source)
        self.assertNotIn("getOrDefault(false)", source)
        self.assertIn("could not be verified (not considered damaged)", health.STRINGS_SOURCE)
        self.assertIn("if (checked >= MAX_CHAPTERS)", source)
        self.assertIn("val storageMissing: Boolean", source)
        self.assertIn("read-only", source.lower())
        self.assertIn("not every page or crc", health.STRINGS_SOURCE.lower())

    def test_explicit_three_way_archive_outcome_never_conflates_errors_with_corruption(self):
        scanner = health.HEALTH_SOURCE
        self.assertIn("private enum class CheckState { READABLE, SUSPECT, UNVERIFIED }", scanner)
        self.assertIn("CheckState.UNVERIFIED -> {", scanner)
        self.assertIn('issues += "Could not verify: "', scanner)
        self.assertIn('issues += "Potentially unreadable: "', scanner)
        self.assertIn("if (images.isEmpty() || images.any { it.length() == 0L })", scanner)
        self.assertIn("return if (samples.all", scanner)
        self.assertIn("ImageUtil.findImageType", scanner)
        self.assertNotIn("getOrDefault(false)", scanner)

    def test_archive_reader_matches_existing_mihon_offline_reader(self):
        scanner = health.HEALTH_SOURCE
        self.assertIn("import mihon.core.archive.archiveReader", scanner)
        self.assertIn("reader.useEntries", scanner)
        self.assertIn("entry.name", scanner)
        self.assertIn("reader.getInputStream(entry.name)", scanner)
        self.assertNotIn("java.util.zip.ZipInputStream", scanner)
        self.assertNotIn("ZipInputStream(chapter.openInputStream())", scanner)
        self.assertIn("return@use CheckState.SUSPECT", scanner)

    def test_no_manga_source_or_user_file_mutations(self):
        content = health.HEALTH_SOURCE + health.STRINGS_SOURCE + health.patch_settings(SETTINGS)
        for dangerous in ("file.delete()", "chapter.delete()", ".renameTo(", "openOutputStream(", "deleteManga(", "removeChapter(", "clearQueue(", "sourceId =", "manga.source ="):
            self.assertNotIn(dangerous, content)
        self.assertNotIn("httpClient", content)
        self.assertNotIn("http://", content)
        self.assertNotIn("https://", content)

    def test_all_markers_verified_before_any_source_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name, content in ((health.SETTINGS, SETTINGS),):
                dest = root / name
                dest.parent.mkdir(parents=True)
                dest.write_text(content)
            target = root / health.SETTINGS
            target.write_text("unknown settings source")
            with self.assertRaises(health.DownloadHealthPatchError):
                health.patch(root)
            self.assertEqual((root / health.SETTINGS).read_text(), "unknown settings source")
            self.assertFalse((root / health.HEALTH).exists())
            target.write_text(SETTINGS)
            health.patch(root)
            self.assertTrue((root / health.HEALTH).exists())
            self.assertIn("selura_health_title", (root / health.STRINGS).read_text())
            with self.assertRaises(health.DownloadHealthPatchError):
                health.patch(root)


if __name__ == "__main__":
    unittest.main()
