"""Contract tests for read-only unfinished download review and opt-in queue resume."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

NATIVE = Path(__file__).resolve().parents[1]

def load(name, file):
    spec = importlib.util.spec_from_file_location(name, NATIVE / file)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value

base = load("selura_storage_base", "check_download_health.py")
review = load("selura_unfinished_review", "review_unfinished_transfers.py")

SETTINGS = """package eu.kanade.presentation.more.settings.screen
object SettingsDownloadScreen {
        val scope = rememberCoroutineScope()
        var checkingStorage by remember { mutableStateOf(false) }
        return listOf(
            getDeleteChaptersGroup(
                downloadPreferences = downloadPreferences,
            ),
        )
}
"""


class UnfinishedTransferReviewTests(unittest.TestCase):
    def test_temporary_folders_separate_from_corruption_and_bounded_details(self):
        result = review.patch_health(base.HEALTH_SOURCE)
        self.assertIn("private const val MAX_UNFINISHED_DETAILS = 20", result)
        self.assertIn("if (unfinishedDetails.size < MAX_UNFINISHED_DETAILS)", result)
        self.assertIn("val storedFiles = chapter.listFiles().orEmpty()", result)
        self.assertIn("it.isFile && imageName(it.name) && it.length() != 0L", result)
        self.assertIn('endsWith(".tmp", ignoreCase = true)', result)
        self.assertIn("val unfinishedDetails: List<String>", result)
        self.assertIn("fun describeUnfinished(context: Context, queuedCount: Int): String", result)
        self.assertIn("unfinished++", result)
        self.assertIn("continue", result)
        self.assertIn("MAX_CHAPTERS = 2500", result)
        self.assertNotIn("delete()", result)
        self.assertNotIn("renameTo(", result)

    def test_review_action_never_automatically_starts_queue(self):
        ui = review.patch_settings(SETTINGS)
        self.assertIn("SeluraDownloadHealth.scan(context, storagePreferences)", ui)
        self.assertIn("val queuedCount = downloadManager.queueState.value.size", ui)
        self.assertIn("report.describeUnfinished(context, queuedCount)", ui)
        self.assertIn("!report.storageMissing && report.unfinished > 0 && queuedCount > 0", ui)
        self.assertIn("dialog.setNegativeButton(android.R.string.cancel, null)", ui)
        self.assertIn("R.string.selura_recovery_resume_all", ui)
        self.assertIn("downloadManager.startDownloads()", ui)
        self.assertEqual(ui.count("downloadManager.startDownloads()"), 1)
        self.assertLess(ui.index("R.string.selura_recovery_resume_all"), ui.index("downloadManager.startDownloads()"))
        self.assertNotIn("downloadManager.clearQueue()", ui)
        self.assertNotIn("startDownloadNow(", ui)

    def test_orphaned_temporary_folders_not_auto_attached(self):
        labels = review.patch_strings(base.STRINGS_SOURCE)
        self.assertIn("The download queue is empty", labels)
        self.assertIn("cannot safely be reattached automatically", labels)
        self.assertIn("does not automatically reconnect orphaned folders", labels)
        self.assertIn("Resuming the existing queue", labels)
        self.assertIn("including Wi-Fi restrictions", labels)
        self.assertIn("No files were removed or repaired.", labels)

    def test_old_storage_health_ui_and_mihon_archive_reader_preserved(self):
        ui = review.patch_settings(SETTINGS)
        scanner = review.patch_health(base.HEALTH_SOURCE)
        self.assertIn("checkingStorage", ui)
        self.assertIn("getDeleteChaptersGroup(", ui)
        self.assertIn("chapter.archiveReader(context).use { reader ->", scanner)
        self.assertIn("CheckState.UNVERIFIED", scanner)
        self.assertIn("getDownloadsDirectory()", scanner)  # comment explicitly says not called
        self.assertIn('val root = base?.findFile("downloads")', scanner)
        self.assertNotIn("ZipInputStream(chapter.openInputStream())", scanner)

    def test_no_user_data_mutations_or_network_recovery_shortcuts(self):
        contents = review.patch_health(base.HEALTH_SOURCE) + review.patch_settings(SETTINGS)
        for forbidden in (".delete()", ".renameTo(", "openOutputStream(", "deleteChapters(",
                          "clearQueue(", "sourceId =", "manga.source =", "httpClient",
                          "downloadManager.startDownloadNow(", "createDirectory("):
            self.assertNotIn(forbidden, contents)
        self.assertIn("currentCoroutineContext().ensureActive()", contents)
        self.assertIn("withContext(Dispatchers.IO)", contents)

    def test_preflight_rejects_changed_inputs_without_writing_any_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for path, source in [
                (review.HEALTH, base.HEALTH_SOURCE),
                (review.SETTINGS, SETTINGS),
                (review.STRINGS, base.STRINGS_SOURCE),
            ]:
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source, encoding="utf-8")
            wrong = root / review.STRINGS
            wrong.write_text("<resources/>", encoding="utf-8")
            with self.assertRaises(review.ReviewTransfersPatchError):
                review.patch(root)
            self.assertEqual((root / review.HEALTH).read_text(encoding="utf-8"), base.HEALTH_SOURCE)
            wrong.write_text(base.STRINGS_SOURCE, encoding="utf-8")
            review.patch(root)
            self.assertIn("selura_recovery_title", wrong.read_text(encoding="utf-8"))
            self.assertIn("describeUnfinished", (root / review.HEALTH).read_text())
            with self.assertRaises(review.ReviewTransfersPatchError):
                review.patch(root)


if __name__ == "__main__":
    unittest.main()
