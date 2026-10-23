#!/usr/bin/env python3
"""Guard user-requested single-chapter retry against stale completed chapters.

This file patches the pinned native Kotlin implementation after all existing
Selura downloader and UI patches. No scan, application startup or UI rendering
starts a download or changes user files. A retry requires an explicit tap.
"""
import argparse
from pathlib import Path

MAIN = "app/src/main/"
SCREEN = MAIN + "java/eu/kanade/tachiyomi/ui/manga/MangaScreen.kt"
MANAGER = MAIN + "java/eu/kanade/tachiyomi/data/download/DownloadManager.kt"
DOWNLOADER = MAIN + "java/eu/kanade/tachiyomi/data/download/Downloader.kt"
STRINGS = MAIN + "res/values/selura_single_chapter_recovery_strings.xml"


class RecoveryGuardPatchError(RuntimeError):
    pass


def once(s: str, old: str, new: str, label: str) -> str:
    count = s.count(old)
    if count != 1:
        raise RecoveryGuardPatchError(f"{label}: expected one audited anchor, found {count}")
    return s.replace(old, new, 1)


def patch_manager(s: str) -> str:
    s = once(
        s,
        "import android.content.Context\n",
        "import android.content.Context\nimport java.io.IOException\n",
        "download manager read-only IO import",
    )
    anchor = """    val isDownloaderRunning
        get() = DownloadWorker.isRunningFlow(context)

    /**"""
    inserted = """    val isDownloaderRunning
        get() = DownloadWorker.isRunningFlow(context)

    // Snapshot of one exact source/manga/chapter path. Does not create dirs,
    // load page URLs, queue downloads, delete temporary files or migrate data.
    data class SeluraUnfinishedChapter(
        val completedAlready: Boolean,
        val savedImages: Int,
        val pendingWrites: Int,
    )

    suspend fun inspectUnfinishedChapter(
        manga: Manga,
        chapter: Chapter,
    ): SeluraUnfinishedChapter? = withContext(Dispatchers.IO) {
        // The chapter is selected from this manga's own list, not guessed from
        // source or storage folder names. Never match a temporary folder by
        // fuzzy titles or the truncated names from the storage health report.
        if (chapter.mangaId != manga.id) {
            throw IllegalArgumentException("Chapter does not belong to the selected manga")
        }
        val source = sourceManager.get(manga.source) as? HttpSource ?: return@withContext null
        val mangaDir = provider.findMangaDir(manga.title, source) ?: return@withContext null
        val canonicalDir = provider.getChapterDirName(
            chapter.name,
            chapter.scanlator,
            chapter.url,
        )
        // Downloader.kt writes ONLY this exact canonical name with _tmp.
        // Legacy or ambiguous folder names are deliberately not auto-matched.
        val tmp = mangaDir.findFile(canonicalDir + Downloader.TMP_DIR_SUFFIX)
            ?: return@withContext null
        if (!tmp.isDirectory) throw IOException("Unfinished chapter location is not a directory")
        val files = tmp.listFiles() ?: throw IOException("Cannot inspect unfinished chapter files")
        val savedImages = files.count { file ->
            file.isFile && file.length() != 0L &&
                file.name.orEmpty().substringAfterLast('.', "").lowercase() in
                setOf("jpg", "jpeg", "png", "webp", "gif", "avif", "jxl", "heic")
        }
        val pendingWrites = files.count { file ->
            file.isFile && file.name.orEmpty().endsWith(".tmp", ignoreCase = true)
        }
        // Check the actual chapter's completed filename(s), including legacy
        // variants. An existing completed directory/CBZ takes precedence.
        // Do not touch _tmp; manual inspection is not evidence of corruption.
        val completedAlready = provider.findChapterDir(
            chapter.name,
            chapter.scanlator,
            chapter.url,
            manga.title,
            source,
        ) != null
        SeluraUnfinishedChapter(completedAlready, savedImages, pendingWrites)
    }

    /**"""
    return once(s, anchor, inserted, "exact-source inspection on existing DownloadManager")


def patch_downloader(s: str) -> str:
    return once(
        s,
        """            mangaDir.findFile(chapterDirname + TMP_DIR_SUFFIX)?.delete()
            cache.addChapter(chapterDirname, mangaDir, download.manga)""",
        """            // Preserve any old temporary pages even when a completed
            // chapter is already present. The user may be diagnosing them;
            // re-queueing must not silently erase orphaned folders.
            cache.addChapter(chapterDirname, mangaDir, download.manga)""",
        "preserve orphaned temp when finished file exists",
    )


def patch_screen(s: str) -> str:
    s = once(
        s,
        "import androidx.core.net.toUri\n",
        "import androidx.core.net.toUri\nimport com.google.android.material.dialog.MaterialAlertDialogBuilder\n",
        "Material confirmation dialog import",
    )
    s = once(
        s,
        "import eu.kanade.presentation.manga.components.DeleteChaptersDialog\n",
        "import eu.kanade.presentation.manga.components.ChapterDownloadAction\n"
        "import eu.kanade.presentation.manga.components.DeleteChaptersDialog\n",
        "download action enum import",
    )
    s = once(
        s,
        "import eu.kanade.tachiyomi.source.Source\n",
        "import eu.kanade.tachiyomi.source.Source\nimport eu.kanade.tachiyomi.R\n",
        "app resource import",
    )
    s = once(
        s,
        "import kotlinx.coroutines.Dispatchers\n",
        "import kotlinx.coroutines.CancellationException\nimport kotlinx.coroutines.Dispatchers\n",
        "coroutine cancellation import",
    )
    s = once(
        s,
        "import logcat.LogPriority\n",
        "import logcat.LogPriority\nimport mihon.app.di.appGraph\n",
        "app graph access",
    )
    return once(
        s,
        """            onDownloadChapter = viewModel::runChapterDownloadActions.takeIf { !successState.source.isLocalOrStub() },""",
        """            onDownloadChapter = ({ items: List<ChapterList.Item>, action: ChapterDownloadAction ->
                // All bulk/other actions retain the existing Mihon semantics.
                // Only manual single-chapter START and START_NOW inspect _tmp.
                if (
                    items.size == 1 &&
                    (action == ChapterDownloadAction.START || action == ChapterDownloadAction.START_NOW)
                ) {
                    val selected = items.single().chapter
                    scope.launch {
                        val manager = context.appGraph.downloadManager
                        try {
                            val inspection = manager.inspectUnfinishedChapter(successState.manga, selected)
                            when {
                                inspection == null -> viewModel.runChapterDownloadActions(items, action)
                                inspection.completedAlready -> {
                                    MaterialAlertDialogBuilder(context)
                                        .setTitle(R.string.selura_single_recovery_already_done_title)
                                        .setMessage(R.string.selura_single_recovery_already_done)
                                        .setPositiveButton(android.R.string.ok, null)
                                        .show()
                                }
                                else -> {
                                    MaterialAlertDialogBuilder(context)
                                        .setTitle(R.string.selura_single_recovery_title)
                                        .setMessage(
                                            context.getString(
                                                R.string.selura_single_recovery_message,
                                                inspection.savedImages,
                                                inspection.pendingWrites,
                                            ),
                                        )
                                        .setNegativeButton(android.R.string.cancel, null)
                                        .setPositiveButton(R.string.selura_single_recovery_retry) { _, _ ->
                                            scope.launch {
                                                try {
                                                    // Recheck to avoid blindly queueing if a
                                                    // background transfer finalized meanwhile.
                                                    val current = manager.inspectUnfinishedChapter(
                                                        successState.manga,
                                                        selected,
                                                    )
                                                    if (current == null || current.completedAlready) {
                                                        MaterialAlertDialogBuilder(context)
                                                            .setTitle(R.string.selura_single_recovery_changed_title)
                                                            .setMessage(R.string.selura_single_recovery_changed)
                                                            .setPositiveButton(android.R.string.ok, null)
                                                            .show()
                                                    } else {
                                                        viewModel.runChapterDownloadActions(items, action)
                                                    }
                                                } catch (e: CancellationException) {
                                                    throw e
                                                } catch (_: Exception) {
                                                    MaterialAlertDialogBuilder(context)
                                                        .setTitle(R.string.selura_single_recovery_changed_title)
                                                        .setMessage(R.string.selura_single_recovery_inspection_failed)
                                                        .setPositiveButton(android.R.string.ok, null)
                                                        .show()
                                                }
                                            }
                                        }
                                        .show()
                                }
                            }
                        } catch (e: CancellationException) {
                            throw e
                        } catch (_: Exception) {
                            // Fail closed on SAF error; do not enqueue by guessing.
                            MaterialAlertDialogBuilder(context)
                                .setTitle(R.string.selura_single_recovery_changed_title)
                                .setMessage(R.string.selura_single_recovery_inspection_failed)
                                .setPositiveButton(android.R.string.ok, null)
                                .show()
                        }
                    }
                } else {
                    viewModel.runChapterDownloadActions(items, action)
                }
                // The branches above return Job (scope.launch) or Unit.
                // Force a Unit-returning callback as the MangaScreen API requires.
                Unit
            }).takeIf { !successState.source.isLocalOrStub() },""",
        "single chapter manual retry gate",
    )


STRINGS_SOURCE = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="selura_single_recovery_title">Resume unfinished chapter?</string>
    <string name="selura_single_recovery_message">An unfinished folder for this exact chapter contains %1$d saved image-like files and %2$d pending writes. Selura may reuse valid pages, but retrying can use network data, overwrite invalid partial pages, and finalize or remove temporary pages after successful completion. No files have been modified by this inspection. Retry only this chapter?</string>
    <string name="selura_single_recovery_retry">Retry this chapter</string>
    <string name="selura_single_recovery_already_done_title">Completed chapter found</string>
    <string name="selura_single_recovery_already_done">A completed chapter already exists for this manga and chapter. Selura did not retry or remove the unfinished folder. Check whether the completed chapter opens offline before taking further action.</string>
    <string name="selura_single_recovery_changed_title">Recovery check</string>
    <string name="selura_single_recovery_changed">The unfinished folder changed or a completed download appeared while you were reviewing. No new download was requested. Check the chapter again.</string>
    <string name="selura_single_recovery_inspection_failed">Selura could not safely inspect the unfinished folder. Nothing was queued; check download storage permissions and try again.</string>
</resources>
"""


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file():
        raise RecoveryGuardPatchError("Upstream license not found")
    if (root / STRINGS).exists():
        raise RecoveryGuardPatchError("Single chapter recovery already patched")
    transforms = {MANAGER: patch_manager, DOWNLOADER: patch_downloader, SCREEN: patch_screen}
    pending = {}
    for name, fn in transforms.items():
        dest = root / name
        if not dest.is_file():
            raise RecoveryGuardPatchError(f"Pinned source missing: {name}")
        initial = dest.read_text(encoding="utf-8")
        changed = fn(initial)
        if changed == initial:
            raise RecoveryGuardPatchError(f"No native change for {name}")
        pending[dest] = changed
    # Preflight all three Kotlin files before writing a single modified byte.
    for path, value in pending.items():
        path.write_text(value, encoding="utf-8")
    dest = root / STRINGS
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(STRINGS_SOURCE, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
