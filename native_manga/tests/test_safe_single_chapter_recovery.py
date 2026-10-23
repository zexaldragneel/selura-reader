"""Native single-chapter recovery guard: fail closed and never erase orphaned files."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "safe_single_chapter_recovery.py"
spec = importlib.util.spec_from_file_location("selura_safe_recovery", SCRIPT)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)

MANAGER = """package eu.kanade.tachiyomi.data.download
import android.content.Context
class DownloadManager {
    val isDownloaderRunning
        get() = DownloadWorker.isRunningFlow(context)

    /**
     * Starts downloads.
     */
}
"""

DOWNLOADER = """class Downloader {
    fun alreadyDownloaded() {
            mangaDir.findFile(chapterDirname + TMP_DIR_SUFFIX)?.delete()
            cache.addChapter(chapterDirname, mangaDir, download.manga)
    }
}
"""

SCREEN = """package eu.kanade.tachiyomi.ui.manga
import androidx.core.net.toUri
import eu.kanade.presentation.manga.components.DeleteChaptersDialog
import eu.kanade.tachiyomi.source.Source
import kotlinx.coroutines.Dispatchers
import logcat.LogPriority
fun Content() {
            onDownloadChapter = viewModel::runChapterDownloadActions.takeIf { !successState.source.isLocalOrStub() },
}
"""


class SafeRecoveryTests(unittest.TestCase):
    def test_exact_manga_chapter_identity_and_canonical_temp_path(self):
        result = recovery.patch_manager(MANAGER)
        self.assertIn("chapter.mangaId != manga.id", result)
        self.assertIn("sourceManager.get(manga.source)", result)
        self.assertIn("provider.getChapterDirName(", result)
        self.assertIn("canonicalDir + Downloader.TMP_DIR_SUFFIX", result)
        self.assertIn("provider.findChapterDir(", result)
        self.assertIn("withContext(Dispatchers.IO)", result)
        self.assertNotIn("createDirectory(", result)
        self.assertNotIn("startDownloadNow(", result)
        self.assertNotIn("downloadChapters(", result)
        self.assertNotIn(".delete()", result)

    def test_does_not_guess_folder_from_user_visible_truncated_names(self):
        result = recovery.patch_manager(MANAGER)
        self.assertNotIn("startsWith(chapter", result)
        self.assertNotIn("contains(chapter", result)
        self.assertNotIn("source.toString()", result)
        self.assertNotIn("createFile(", result)
        self.assertIn("tmp.listFiles() ?: throw IOException", result)

    def test_guard_completes_before_download_button_and_requires_user_tap(self):
        result = recovery.patch_screen(SCREEN)
        self.assertIn("items.size == 1", result)
        self.assertIn("ChapterDownloadAction.START_NOW", result)
        self.assertIn("ChapterDownloadAction.START", result)
        self.assertIn("inspectUnfinishedChapter(successState.manga, selected)", result)
        self.assertIn(".setNegativeButton(android.R.string.cancel, null)", result)
        self.assertIn(".setPositiveButton(R.string.selura_single_recovery_retry)", result)
        self.assertIn("val current = manager.inspectUnfinishedChapter(", result)
        self.assertIn("if (current == null || current.completedAlready)", result)
        self.assertIn("} catch (e: CancellationException)", result)
        self.assertIn("                Unit\n            }).takeIf", result)
        self.assertEqual(result.count("viewModel.runChapterDownloadActions(items, action)"), 3)

    def test_orphan_tmp_is_preserved_when_already_completed(self):
        result = recovery.patch_downloader(DOWNLOADER)
        self.assertIn("cache.addChapter(chapterDirname, mangaDir, download.manga)", result)
        self.assertNotIn("mangaDir.findFile(chapterDirname + TMP_DIR_SUFFIX)?.delete()", result)
        self.assertNotIn(".delete()", result)

    def test_messages_explain_download_writes_and_offline_verification(self):
        self.assertIn("overwrite invalid partial pages", recovery.STRINGS_SOURCE)
        self.assertIn("can use network data", recovery.STRINGS_SOURCE)
        self.assertIn("opens offline", recovery.STRINGS_SOURCE)
        self.assertIn("Nothing was queued", recovery.STRINGS_SOURCE)
        self.assertNotIn("automatic recovery", recovery.STRINGS_SOURCE)

    def test_atomic_preflight_prevents_partial_kotlin_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "LICENSE").write_text("Apache License 2.0\n")
            originals = {
                recovery.MANAGER: MANAGER,
                recovery.DOWNLOADER: DOWNLOADER,
                recovery.SCREEN: SCREEN,
            }
            for relative, text in originals.items():
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
            broken = root / recovery.SCREEN
            broken.write_text("wrong pinned file")
            with self.assertRaises(recovery.RecoveryGuardPatchError):
                recovery.patch(root)
            self.assertEqual((root / recovery.MANAGER).read_text(), MANAGER)
            self.assertEqual((root / recovery.DOWNLOADER).read_text(), DOWNLOADER)
            self.assertFalse((root / recovery.STRINGS).exists())
            broken.write_text(SCREEN)
            recovery.patch(root)
            self.assertTrue((root / recovery.STRINGS).exists())
            self.assertEqual((root / "LICENSE").read_text(), "Apache License 2.0\n")
            with self.assertRaises(recovery.RecoveryGuardPatchError):
                recovery.patch(root)

    def test_no_identity_or_migration_patch(self):
        self.assertNotIn("sourceId =", SCRIPT.read_text())
        for key in ("extension", "BackupRestorer.kt", "build.gradle", "deleteRecursively", "migrateManga"):
            self.assertNotIn(key, SCRIPT.read_text())
        self.assertEqual(len({recovery.MANAGER, recovery.SCREEN, recovery.DOWNLOADER}), 3)


if __name__ == "__main__":
    unittest.main()
