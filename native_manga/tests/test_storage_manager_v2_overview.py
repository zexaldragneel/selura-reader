"""Storage Manager 2.0: safe, bounded, read-only filesystem usage screen."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

MODULE_FILE = Path(__file__).resolve().parents[1] / "storage_manager_v2_overview.py"
spec = importlib.util.spec_from_file_location("storage_overview", MODULE_FILE)
overview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(overview)

SETTINGS = """package eu.kanade.presentation.more.settings.screen
import eu.kanade.tachiyomi.data.download.SeluraDownloadHealth
fun getPreferences() {
    val downloadManager = remember { context.appGraph.downloadManager }
    val storagePreferences = remember { context.appGraph.storagePreferences }
    var checkingStorage by remember { mutableStateOf(false) }
    var reviewingTransfers by remember { mutableStateOf(false) }
    val result = SeluraDownloadHealth.scan(context, storagePreferences)
    downloadManager.startDownloads()
    MaterialAlertDialogBuilder(context)
    getDeleteChaptersGroup(
                downloadPreferences = downloadPreferences,
}


class StorageOverviewTests(unittest.TestCase):
    def test_real_settings_action_visible_next_to_existing_health_and_review(self):
        patched = overview.patch_settings(SETTINGS)
        self.assertIn("title = context.getString(R.string.seiryn_storage_overview_title)", patched)
        self.assertIn("SeirynStorageOverview.scan(context, storagePreferences)", patched)
        self.assertIn("MaterialAlertDialogBuilder(context)", patched)
        self.assertIn("var checkingStorageUsage by remember { mutableStateOf(false) }", patched)
        self.assertIn("checkingStorageUsage = false", patched)
        self.assertIn("catch (e: CancellationException)", patched)
        self.assertEqual(patched.count("getDeleteChaptersGroup("), 1)
        self.assertIn("SeluraDownloadHealth.scan(context, storagePreferences)", patched)
        self.assertIn("downloadManager.startDownloads()", patched)

    def test_saf_scanner_uses_only_existing_downloads_and_never_modifies(self):
        source = overview.KOTLIN
        self.assertIn('val root = base?.findFile("downloads")', source)
        self.assertIn("Uri.parse(storagePreferences.baseStorageDirectory.get())", source)
        self.assertIn("withContext(Dispatchers.IO)", source)
        self.assertIn("currentCoroutineContext().ensureActive()", source)
        self.assertIn("MAX_CHAPTERS = 5000", source)
        self.assertIn("MAX_FILE_ENTRIES = 20000", source)
        self.assertIn("MAX_SERIES = 3000", source)
        self.assertIn("val length = file.length()", source)
        self.assertIn("if (length < 0L)", source)
        self.assertIn("unknownSizes++", source)
        self.assertIn('chapterName.endsWith(Downloader.TMP_DIR_SUFFIX, ignoreCase = true)', source)
        self.assertIn('chapterName.endsWith(".cbz", ignoreCase = true)', source)
        self.assertIn(".sortedByDescending { it.bytes }", source)
        self.assertIn("MAX_DISPLAY_SERIES = 10", source)
        forbidden = [
            ".delete(", ".delete()", ".rename(", ".createFile(", "createDirectory(",
            "getDownloadsDirectory(", "archiveReader(", "getOutputStream(",
            "downloadManager.", "chapterCache.", "mangaRepository.", "source.get",
            "HttpClient", "POST(", "newDownload(", "removeChapter(",
        ]
        for action in forbidden:
            with self.subTest(action=action):
                self.assertNotIn(action, source)

    def test_partial_scan_does_not_misrepresent_complete_totals(self):
        k = overview.KOTLIN
        self.assertIn("capped = true", k)
        self.assertIn("R.string.seiryn_storage_overview_limited", k)
        self.assertIn("R.string.seiryn_storage_overview_unknown", k)
        self.assertIn("R.string.seiryn_storage_overview_disclaimer", k)
        self.assertIn("if (storageUnavailable)", k)
        self.assertIn("if (length < 0L)", k)
        self.assertIn("knownUnfinishedBytes += length", k)
        self.assertIn("knownCompletedBytes += length", k)
        self.assertNotIn("StatFs(", k)
        self.assertNotIn("freeBytes", k)
        self.assertIn("No files were changed", overview.LABELS)

    def test_resource_strings_valid_and_no_duplicate_ids(self):
        root = ET.fromstring(overview.LABELS)
        ids = [x.attrib["name"] for x in root.findall("string")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn("seiryn_storage_overview_title", ids)
        self.assertIn("seiryn_storage_overview_summary", ids)
        self.assertIn("seiryn_storage_overview_disclaimer", ids)
        self.assertIn("seiryn_storage_overview_limited", ids)
        self.assertIn("seiryn_storage_overview_missing", ids)

    def test_original_feature_contract_changes_fail_closed_without_writing(self):
        bad = [
            SETTINGS.replace("SeluraDownloadHealth.scan", "DifferentScanner.scan"),
            SETTINGS.replace("downloadManager.startDownloads()", "downloadManager.stopDownloads()"),
            SETTINGS.replace("var reviewingTransfers", "var newReviewOption"),
            overview.patch_settings(SETTINGS),
        ]
        for s in bad:
            with self.subTest(value=s[-30:]), self.assertRaises(overview.StorageOverviewPatchError):
                overview.patch_settings(s)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LICENSE").write_text("Apache License 2.0")
            (root / "gradlew").write_text("gradle")
            screen = root / overview.SCREEN
            screen.parent.mkdir(parents=True, exist_ok=True)
            screen.write_text("unexpected settings change")
            with self.assertRaises(overview.StorageOverviewPatchError):
                overview.patch(root)
            self.assertEqual(screen.read_text(), "unexpected settings change")
            self.assertFalse((root / overview.DASHBOARD).exists())
            self.assertFalse((root / overview.STRINGS).exists())
            screen.write_text(SETTINGS)
            overview.patch(root)
            self.assertIn("SeirynStorageOverview.scan", screen.read_text())
            self.assertIn("object SeirynStorageOverview", (root / overview.DASHBOARD).read_text())
            with self.assertRaises(overview.StorageOverviewPatchError):
                overview.patch(root)


if __name__ == "__main__":
    unittest.main()
