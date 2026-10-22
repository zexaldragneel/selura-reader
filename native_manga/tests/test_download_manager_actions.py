"""Selura Download Manager retry/status and storage integrity contracts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("selura_download_manager", ROOT / "download_manager_actions.py")
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)

HOLDER = '''package eu.kanade.tachiyomi.ui.download
import androidx.recyclerview.widget.ItemTouchHelper
class DownloadHolder {
    private val binding = DownloadItemBinding.bind(view)
    fun bind(download: Download) {
        if (pages == null) {
            binding.downloadProgress.progress = 0
            binding.downloadProgress.max = 1
            binding.downloadProgressText.text = ""
        } else {
            binding.downloadProgress.max = pages.size * 100
            notifyProgress()
            notifyDownloadedPages()
        }
    }
    fun notifyDownloadedPages() {
        val pages = download.pages ?: return
        binding.downloadProgressText.text = "\${download.downloadedImages}/\${pages.size}"
    }
    fun showPopupMenu(view: View) {
        view.popupMenu(
            menuRes = R.menu.download_single,
            initMenu = {
                findItem(R.id.move_to_top).isVisible = bindingAdapterPosition > 1
            },
        )
    }
}'''

VIEWMODEL = '''package eu.kanade.tachiyomi.ui.download
import kotlinx.coroutines.flow.filterNotNull
class DownloadQueueViewModel {
    lateinit var controllerBinding: DownloadListBinding
    fun onMenuItemClick(position: Int, menuItem: MenuItem) {
                when (menuItem.itemId) {
                    R.id.move_to_top, R.id.move_to_bottom -> {
                    }
                }
    }
    fun clearQueue() {
        viewModelScope.launch { downloadManager.clearQueue() }
    }
    fun onStatusChange(download: Download) {
        when (download.status) {
            Download.State.ERROR -> cancelProgressJob(download)
            else -> {
                /* unused */
            }
        }
    }
}'''

SCREEN = '''package eu.kanade.tachiyomi.ui.download
import androidx.compose.ui.platform.LocalLayoutDirection
import eu.kanade.tachiyomi.databinding.DownloadListBinding
class DownloadQueueScreen {
        val downloadList by viewModel.state.collectAsStateWithLifecycle()
        val downloadCount by remember {
        }
                            AppBarActions(
                                listOf(
                                    AppBar.Action(
                                        title = stringResource(MR.strings.action_sort),
                                        icon = MaterialSymbols.AutoMirroredRounded.Sort,
                                        onClick = { sortExpanded = true },
                                    ),
                                    AppBar.OverflowAction(
                                        title = stringResource(MR.strings.action_cancel_all),
                                        onClick = { viewModel.clearQueue() },
                                    ),
                                ),
                            )
}'''

MENU = '''<?xml version="1.0" encoding="utf-8"?>
<menu>
    <item
        android:id="@+id/cancel_download"
        android:title="@string/action_cancel" />
</menu>'''

DOWNLOADER = '''package eu.kanade.tachiyomi.data.download
import java.util.concurrent.ConcurrentHashMap
class Downloader {
        if (mangaDir.findFile("$chapterDirname.cbz") != null || mangaDir.findFile(chapterDirname) != null) {
            mangaDir.findFile(chapterDirname + TMP_DIR_SUFFIX)?.delete()
            cache.addChapter(chapterDirname, mangaDir, download.manga)
            download.status = Download.State.DOWNLOADED
            return
        }
    private suspend fun downloadChapter(download: Download, slots: Semaphore, pagesStarted: CompletableDeferred<Unit>) {
    }
            // Index only AFTER a verified final rename.
            cache.addChapter(chapterDirname, mangaDir, download.manga)
}'''

SOURCES = {
    fix.HOLDER: HOLDER, fix.VIEWMODEL: VIEWMODEL,
    fix.SCREEN: SCREEN, fix.MENU: MENU, fix.DOWNLOADER: DOWNLOADER,
}


class DownloadManagerTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        for path, contents in SOURCES.items():
            dest = self.root / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(contents, encoding="utf-8")

    def get(self, path):
        return (self.root / path).read_text(encoding="utf-8")

    def test_download_row_shows_failure_even_without_pages(self):
        source = fix.patch_holder(HOLDER)
        self.assertIn("fun notifyDownloadStatus()", source)
        self.assertIn("binding.downloadProgressText.text = if (count.isEmpty()) failed", source)
        self.assertIn("download.status == Download.State.ERROR", source)
        self.assertIn("MaterialColors.getColor", source)
        self.assertIn("setTextColor(defaultProgressTextColors)", source)
        self.assertIn("notifyDownloadedPages()\n    }", source)
        self.assertIn("findItem(R.id.selura_retry_chapter).isVisible", source)

    def test_retry_only_failed_items_and_uses_existing_queue(self):
        source = fix.patch_viewmodel(VIEWMODEL)
        self.assertIn("fun retryChapter(chapterId: Long)", source)
        self.assertIn("entry?.status == Download.State.ERROR", source)
        self.assertIn("downloadManager.startDownloadNow(chapterId)", source)
        self.assertIn("fun retryFailedDownloads()", source)
        self.assertIn("it.status == Download.State.ERROR", source)
        self.assertIn("downloadManager.addDownloadsToStartOfQueue(failed)", source)
        self.assertIn("flatMapLatest { downloads ->", source)
        self.assertIn("statuses.count { it == Download.State.ERROR }", source)
        self.assertIn("getHolder(download)?.notifyDownloadStatus()", source)
        self.assertNotIn("deleteChapters", source)

    def test_retry_controls_are_conditional_and_visible(self):
        source = fix.patch_screen(SCREEN)
        self.assertIn("failedCount by viewModel.failedCount.collectAsStateWithLifecycle()", source)
        self.assertIn("if (failedCount > 0)", source)
        self.assertIn("onClick = viewModel::retryFailedDownloads", source)
        menu = fix.patch_menu(MENU)
        self.assertEqual(menu.count("selura_retry_chapter"), 2)
        self.assertIn("@string/action_cancel", menu)

    def test_existing_archives_check_for_readability_without_deleting(self):
        source = fix.patch_downloader(DOWNLOADER)
        self.assertIn("private fun hasReadableChapterImages(dir: UniFile)", source)
        self.assertIn("private fun isReadableChapterArchive(file: UniFile)", source)
        self.assertIn("ZipInputStream(file.openInputStream())", source)
        self.assertIn("if (!archiveReady && !folderReady)", source)
        self.assertIn('notifier.onError(', source)
        self.assertIn("if (!finalReady) throw IOException(", source)
        self.assertIn("cache.addChapter(chapterDirname, mangaDir, download.manga)", source)
        self.assertIn('mangaDir.findFile(chapterDirname + TMP_DIR_SUFFIX)?.delete()', source)
        self.assertNotIn("existingArchive?.delete()", source)
        self.assertNotIn("existingFolder?.delete()", source)

    def test_fails_closed_without_partial_writes(self):
        wrong = self.root / fix.SCREEN
        wrong.write_text("unknown source shape", encoding="utf-8")
        with self.assertRaises(fix.DownloadManagerPatchError):
            fix.patch(self.root)
        self.assertEqual(self.get(fix.HOLDER), HOLDER)
        self.assertFalse((self.root / fix.LABELS).exists())
        wrong.write_text(SCREEN, encoding="utf-8")
        fix.patch(self.root)
        self.assertIn("selura_retry_chapter", self.get(fix.MENU))
        self.assertIn("Retry failed downloads", self.get(fix.LABELS))
        with self.assertRaises(fix.DownloadManagerPatchError):
            fix.patch(self.root)

    def test_preserves_user_data_scope(self):
        self.assertEqual(set(fix.FILES), {fix.HOLDER, fix.VIEWMODEL, fix.SCREEN, fix.MENU, fix.DOWNLOADER})
        self.assertNotIn("database", " ".join(fix.FILES).lower())
        self.assertNotIn("backups", " ".join(fix.FILES).lower())
        self.assertTrue(fix.DOWNLOADER.endswith("/data/download/Downloader.kt"))
        for text in [fix.patch_holder(HOLDER), fix.patch_downloader(DOWNLOADER)]:
            self.assertNotIn("sourceId =", text)
            self.assertNotIn("manga.source =", text)
            self.assertNotIn("library.remove", text)


if __name__ == "__main__":
    unittest.main()
