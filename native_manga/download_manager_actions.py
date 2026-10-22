#!/usr/bin/env python3
"""Enhance Mihon's real Download Manager with visible failures and user-initiated retry.

Apply ONLY after verify_chapter_downloads.py against Mihon v0.21.2 pinned snapshot.
All changes fail closed. No queue migrations, deletion or source ID changes.
"""
import argparse
from pathlib import Path

ROOT = "app/src/main/"
HOLDER = ROOT + "java/eu/kanade/tachiyomi/ui/download/DownloadHolder.kt"
VIEWMODEL = ROOT + "java/eu/kanade/tachiyomi/ui/download/DownloadQueueViewModel.kt"
SCREEN = ROOT + "java/eu/kanade/tachiyomi/ui/download/DownloadQueueScreen.kt"
MENU = ROOT + "res/menu/download_single.xml"
LABELS = ROOT + "res/values/selura_download_retry_strings.xml"
DOWNLOADER = ROOT + "java/eu/kanade/tachiyomi/data/download/Downloader.kt"
FILES = (HOLDER, VIEWMODEL, SCREEN, MENU, DOWNLOADER)


class DownloadManagerPatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise DownloadManagerPatchError(f"{label}: expected one pinned marker, found {count}")
    return text.replace(old, new, 1)


def patch_holder(s: str) -> str:
    s = replace_once(s,
        "import androidx.recyclerview.widget.ItemTouchHelper\n",
        "import androidx.recyclerview.widget.ItemTouchHelper\n"
        "import com.google.android.material.color.MaterialColors\n",
        "holder MaterialColors import")
    s = replace_once(s,
        "    private val binding = DownloadItemBinding.bind(view)\n",
        "    private val binding = DownloadItemBinding.bind(view)\n"
        "    private val defaultProgressTextColors = binding.downloadProgressText.textColors\n",
        "holder text color setup")
    s = replace_once(s,
        """            binding.downloadProgressText.text = ""
        } else {
            binding.downloadProgress.max = pages.size * 100
            notifyProgress()
            notifyDownloadedPages()
        }
    }""",
        """        } else {
            binding.downloadProgress.max = pages.size * 100
            notifyProgress()
        }
        notifyDownloadedPages()
    }""",
        "holder bind status even without pages")
    s = replace_once(s,
        """        val pages = download.pages ?: return
        binding.downloadProgressText.text = "\${download.downloadedImages}/\${pages.size}"
    }""",
        """        notifyDownloadStatus()
    }

    // Show an error even if a source failed before any pages arrived.
    fun notifyDownloadStatus() {
        val pages = download.pages
        val count = pages?.let { "\${download.downloadedImages}/\${it.size}" }.orEmpty()
        if (download.status == Download.State.ERROR) {
            binding.downloadProgressText.setTextColor(
                MaterialColors.getColor(view, com.google.android.material.R.attr.colorError),
            )
            val failed = view.context.getString(R.string.selura_download_failed)
            binding.downloadProgressText.text = if (count.isEmpty()) failed else "$failed · $count"
        } else {
            binding.downloadProgressText.setTextColor(defaultProgressTextColors)
            binding.downloadProgressText.text = count
        }
    }""",
        "holder failed status label")
    s = replace_once(s,
        """            initMenu = {
                findItem(R.id.move_to_top).isVisible = bindingAdapterPosition > 1""",
        """            initMenu = {
                findItem(R.id.selura_retry_chapter).isVisible = download.status == Download.State.ERROR
                findItem(R.id.move_to_top).isVisible = bindingAdapterPosition > 1""",
        "holder retry menu visibility")
    return s


def patch_viewmodel(s: str) -> str:
    s = replace_once(s,
        "import kotlinx.coroutines.flow.filterNotNull\n",
        "import kotlinx.coroutines.flow.filterNotNull\n"
        "import kotlinx.coroutines.flow.flatMapLatest\n"
        "import kotlinx.coroutines.flow.flowOf\n",
        "viewmodel reactive imports")
    s = replace_once(s,
        """    lateinit var controllerBinding: DownloadListBinding""",
        """    // Observe status flows, not merely queue membership. Failed items
    // stay in the queue, so the retry-all action must update in real time.
    val failedCount: StateFlow<Int> = downloadManager.queueState
        .flatMapLatest { downloads ->
            if (downloads.isEmpty()) {
                flowOf(0)
            } else {
                combine(downloads.map { it.statusFlow }) { statuses ->
                    statuses.count { it == Download.State.ERROR }
                }
            }
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5.seconds), 0)

    lateinit var controllerBinding: DownloadListBinding""",
        "viewmodel failed count flow")
    s = replace_once(s,
        """                when (menuItem.itemId) {
                    R.id.move_to_top, R.id.move_to_bottom -> {""",
        """                when (menuItem.itemId) {
                    R.id.selura_retry_chapter -> retryChapter(item.download.chapter.id)
                    R.id.move_to_top, R.id.move_to_bottom -> {""",
        "viewmodel retry menu handler")
    s = replace_once(s,
        """    fun clearQueue() {
        viewModelScope.launch { downloadManager.clearQueue() }
    }""",
        """    fun clearQueue() {
        viewModelScope.launch { downloadManager.clearQueue() }
    }

    fun retryChapter(chapterId: Long) {
        viewModelScope.launch {
            val entry = downloadManager.getQueuedDownloadOrNull(chapterId)
            if (entry?.status == Download.State.ERROR) {
                downloadManager.startDownloadNow(chapterId)
            }
        }
    }

    fun retryFailedDownloads() {
        viewModelScope.launch {
            val failed = downloadManager.queueState.value.filter {
                it.status == Download.State.ERROR
            }
            if (failed.isNotEmpty()) {
                // Keep existing files and source identity. Use Mihon's
                // persisted queue and normal Wi-Fi/download policies.
                downloadManager.addDownloadsToStartOfQueue(failed)
            }
        }
    }""",
        "viewmodel retry callbacks")
    s = replace_once(s,
        """            Download.State.ERROR -> cancelProgressJob(download)
            else -> {
                /* unused */
            }
        }""",
        """            Download.State.ERROR -> {
                cancelProgressJob(download)
                getHolder(download)?.notifyDownloadStatus()
            }
            else -> getHolder(download)?.notifyDownloadStatus()
        }""",
        "viewmodel status updates")
    return s


def patch_screen(s: str) -> str:
    s = replace_once(s,
        "import androidx.compose.ui.platform.LocalLayoutDirection\n",
        "import androidx.compose.ui.platform.LocalLayoutDirection\n"
        "import androidx.compose.ui.res.stringResource as androidStringResource\n",
        "screen resource import")
    s = replace_once(s,
        "import eu.kanade.tachiyomi.databinding.DownloadListBinding\n",
        "import eu.kanade.tachiyomi.R\n"
        "import eu.kanade.tachiyomi.databinding.DownloadListBinding\n",
        "screen application resource")
    s = replace_once(s,
        """        val downloadList by viewModel.state.collectAsStateWithLifecycle()
        val downloadCount by remember {""",
        """        val downloadList by viewModel.state.collectAsStateWithLifecycle()
        val failedCount by viewModel.failedCount.collectAsStateWithLifecycle()
        val downloadCount by remember {""",
        "screen failed state")
    s = replace_once(s,
        """                            AppBarActions(
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
                            )""",
        """                            AppBarActions(
                                listOfNotNull(
                                    AppBar.Action(
                                        title = stringResource(MR.strings.action_sort),
                                        icon = MaterialSymbols.AutoMirroredRounded.Sort,
                                        onClick = { sortExpanded = true },
                                    ),
                                    if (failedCount > 0) {
                                        AppBar.OverflowAction(
                                            title = androidStringResource(R.string.selura_retry_failed_downloads),
                                            onClick = viewModel::retryFailedDownloads,
                                        )
                                    } else {
                                        null
                                    },
                                    AppBar.OverflowAction(
                                        title = stringResource(MR.strings.action_cancel_all),
                                        onClick = { viewModel.clearQueue() },
                                    ),
                                ),
                            )""",
        "screen retry failed action")
    return s


def patch_menu(s: str) -> str:
    return replace_once(s,
        """    <item
        android:id="@+id/cancel_download"
        android:title="@string/action_cancel" />""",
        """    <item
        android:id="@+id/selura_retry_chapter"
        android:title="@string/selura_retry_chapter" />

    <item
        android:id="@+id/cancel_download"
        android:title="@string/action_cancel" />""",
        "failed chapter retry context menu")


def patch_downloader(s: str) -> str:
    s = replace_once(s,
        "import java.util.concurrent.ConcurrentHashMap\n",
        "import java.util.concurrent.ConcurrentHashMap\n"
        "import java.util.zip.ZipInputStream\n",
        "ZIP readback import")
    s = replace_once(s,
        """        if (mangaDir.findFile("$chapterDirname.cbz") != null || mangaDir.findFile(chapterDirname) != null) {
            mangaDir.findFile(chapterDirname + TMP_DIR_SUFFIX)?.delete()
            cache.addChapter(chapterDirname, mangaDir, download.manga)
            download.status = Download.State.DOWNLOADED
            return
        }""",
        """        val existingArchive = mangaDir.findFile("$chapterDirname.cbz")
        val existingFolder = mangaDir.findFile(chapterDirname)
        if (existingArchive != null || existingFolder != null) {
            // Don't mark a zero-byte archive or an empty directory as done.
            // Keep historical files: no automatic deletion or replacement.
            val archiveReady = existingArchive?.let(::isReadableChapterArchive) == true
            val folderReady = existingFolder?.let(::hasReadableChapterImages) == true
            if (!archiveReady && !folderReady) {
                download.status = Download.State.ERROR
                notifier.onError(
                    "Existing chapter files are incomplete. Check storage before retrying.",
                    download.chapter.name,
                    download.manga.title,
                    download.manga.id,
                )
                return
            }
            mangaDir.findFile(chapterDirname + TMP_DIR_SUFFIX)?.delete()
            cache.addChapter(chapterDirname, mangaDir, download.manga)
            download.status = Download.State.DOWNLOADED
            return
        }""",
        "existing completed chapter readback")
    s = replace_once(s,
        """    private suspend fun downloadChapter(download: Download, slots: Semaphore, pagesStarted: CompletableDeferred<Unit>) {""",
        """    // Read-only integrity probes: do not migrate or delete old files.
    // The Build #85 page-by-page validation still covers new downloads.
    private fun hasReadableChapterImages(dir: UniFile): Boolean =
        dir.isDirectory && dir.listFiles().orEmpty().any { file ->
            file.isFile && file.length() > 0L &&
                ImageUtil.isImage(file.name) { file.openInputStream() }
        }

    private fun isReadableChapterArchive(file: UniFile): Boolean {
        if (!file.isFile || file.length() == 0L) return false
        return try {
            ZipInputStream(file.openInputStream()).use { it.nextEntry != null }
        } catch (_: java.io.IOException) {
            false
        }
    }

    private suspend fun downloadChapter(download: Download, slots: Semaphore, pagesStarted: CompletableDeferred<Unit>) {""",
        "non-destructive integrity probes")
    s = replace_once(s,
        """            // Index only AFTER a verified final rename.
            cache.addChapter(chapterDirname, mangaDir, download.manga)""",
        """            // Read back final SAF output before indexing it as downloaded.
            val finalReady = if (downloadPreferences.saveChaptersAsCBZ.get()) {
                mangaDir.findFile("$chapterDirname.cbz")?.let(::isReadableChapterArchive) == true
            } else {
                mangaDir.findFile(chapterDirname)?.let(::hasReadableChapterImages) == true
            }
            if (!finalReady) throw IOException("Finalized chapter is not readable in download storage")
            cache.addChapter(chapterDirname, mangaDir, download.manga)""",
        "finalized chapter storage check")
    return s


def patch(root: Path):
    root = root.resolve()
    paths = {p: root / p for p in FILES}
    if (root / LABELS).exists():
        raise DownloadManagerPatchError("Selura retry strings already present")
    originals = {}
    for relative, path in paths.items():
        if not path.is_file():
            raise DownloadManagerPatchError(f"Missing pinned source: {relative}")
        originals[relative] = path.read_text(encoding="utf-8")
    functions = {
        HOLDER: patch_holder,
        VIEWMODEL: patch_viewmodel,
        SCREEN: patch_screen,
        MENU: patch_menu,
        DOWNLOADER: patch_downloader,
    }
    updated = {p: fn(originals[p]) for p, fn in functions.items()}
    if any(originals[p] == updated[p] for p in FILES):
        raise DownloadManagerPatchError("An expected file was unchanged")
    # Preflight all five files before writing anything.
    for p in FILES:
        paths[p].write_text(updated[p], encoding="utf-8")
    (root / LABELS).parent.mkdir(parents=True, exist_ok=True)
    (root / LABELS).write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<resources>\n'
        '    <string name="selura_download_failed">Failed</string>\n'
        '    <string name="selura_retry_chapter">Retry download</string>\n'
        '    <string name="selura_retry_failed_downloads">Retry failed downloads</string>\n'
        '</resources>\n',
        encoding="utf-8",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)


if __name__ == "__main__":
    main()
