#!/usr/bin/env python3
"""Non-destructive native Seiryn Storage Manager 2.0 — first milestone.

Run AFTER review_unfinished_transfers.py. The new opt-in settings action
inspects existing downloaded chapter folders and CBZ file sizes. It does not
delete or alter any files, database rows, cache metadata or manga progress.
"""
import argparse
from pathlib import Path
from textwrap import dedent

ROOT = "app/src/main/"
SCREEN = ROOT + "java/eu/kanade/presentation/more/settings/screen/SettingsDownloadScreen.kt"
DASHBOARD = ROOT + "java/eu/kanade/tachiyomi/data/download/SeirynStorageOverview.kt"
STRINGS = ROOT + "res/values/seiryn_storage_overview_strings.xml"

OLD_STATE = """        var checkingStorage by remember { mutableStateOf(false) }
        var reviewingTransfers by remember { mutableStateOf(false) }"""
NEW_STATE = """        var checkingStorage by remember { mutableStateOf(false) }
        var reviewingTransfers by remember { mutableStateOf(false) }
        var checkingStorageUsage by remember { mutableStateOf(false) }"""

OLD_PREFERENCE = """            getDeleteChaptersGroup(
                downloadPreferences = downloadPreferences,"""
NEW_PREFERENCE = """            Preference.PreferenceItem.TextPreference(
                title = context.getString(R.string.seiryn_storage_overview_title),
                subtitle = context.getString(
                    if (checkingStorageUsage) R.string.seiryn_storage_overview_scanning
                    else R.string.seiryn_storage_overview_subtitle,
                ),
                onClick = {
                    if (!checkingStorageUsage) {
                        checkingStorageUsage = true
                        scope.launch {
                            try {
                                val overview = SeirynStorageOverview.scan(context, storagePreferences)
                                MaterialAlertDialogBuilder(context)
                                    .setTitle(R.string.seiryn_storage_overview_title)
                                    .setMessage(overview.describe(context))
                                    .setPositiveButton(android.R.string.ok, null)
                                    .show()
                            } catch (e: CancellationException) {
                                throw e
                            } catch (_: Exception) {
                                MaterialAlertDialogBuilder(context)
                                    .setTitle(R.string.seiryn_storage_overview_title)
                                    .setMessage(R.string.seiryn_storage_overview_error)
                                    .setPositiveButton(android.R.string.ok, null)
                                    .show()
                            } finally {
                                checkingStorageUsage = false
                            }
                        }
                    }
                },
            ),
            getDeleteChaptersGroup(
                downloadPreferences = downloadPreferences,"""

KOTLIN = dedent(r'''\
package eu.kanade.tachiyomi.data.download

import android.content.Context
import android.net.Uri
import android.text.format.Formatter
import com.hippo.unifile.UniFile
import eu.kanade.tachiyomi.R
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import tachiyomi.domain.storage.service.StoragePreferences

/**
 * Read-only download-space overview for the configured SAF storage directory.
 *
 * Samples existing files; no database, chapter cache, rename, migration,
 * download scheduling, image decoding, archive opening or deletion.
 * Does not claim to know the free space of an arbitrary SAF provider.
 */
object SeirynStorageOverview {
    internal const val MAX_CHAPTERS = 5000
    internal const val MAX_FILE_ENTRIES = 20000
    internal const val MAX_SERIES = 3000
    private const val MAX_DISPLAY_SERIES = 10

    data class SeriesUsage(
        val name: String,
        val completedChapters: Int,
        val knownBytes: Long,
        val unfinishedChapters: Int,
    )

    data class Report(
        val completedChapters: Int,
        val unfinishedChapters: Int,
        val knownCompletedBytes: Long,
        val knownUnfinishedBytes: Long,
        val unknownFileSizes: Int,
        val inspectedFiles: Int,
        val inspectedSeries: Int,
        val capped: Boolean,
        val storageUnavailable: Boolean,
        val largestSeries: List<SeriesUsage>,
    ) {
        fun describe(context: Context): String {
            if (storageUnavailable) return context.getString(R.string.seiryn_storage_overview_missing)
            val summary = context.getString(
                R.string.seiryn_storage_overview_summary,
                Formatter.formatShortFileSize(context, knownCompletedBytes),
                Formatter.formatShortFileSize(context, knownUnfinishedBytes),
                completedChapters,
                unfinishedChapters,
                inspectedSeries,
                inspectedFiles,
            )
            val top = if (largestSeries.isEmpty()) "" else {
                "\n\n" + context.getString(R.string.seiryn_storage_overview_largest) +
                    "\n" + largestSeries.joinToString("\n") { entry ->
                        entry.name + " — " +
                            Formatter.formatShortFileSize(context, entry.knownBytes) +
                            " (" + entry.completedChapters + " chapters)"
                    }
            }
            val unknown = if (unknownFileSizes == 0) "" else {
                "\n\n" + context.getString(
                    R.string.seiryn_storage_overview_unknown,
                    unknownFileSizes,
                )
            }
            val limit = if (capped) {
                "\n\n" + context.getString(R.string.seiryn_storage_overview_limited)
            } else {
                ""
            }
            return summary + top + unknown + limit + "\n\n" +
                context.getString(R.string.seiryn_storage_overview_disclaimer)
        }
    }

    private data class CountedSeries(
        val label: String,
        var completed: Int = 0,
        var unfinished: Int = 0,
        var bytes: Long = 0L,
    )

    /**
     * SAF length() can return -1 for providers that cannot report file size.
     * Such files are NOT treated as 0-byte corruption or as proof of free space.
     */
    suspend fun scan(context: Context, storagePreferences: StoragePreferences): Report =
        withContext(Dispatchers.IO) {
            val base = UniFile.fromUri(
                context,
                Uri.parse(storagePreferences.baseStorageDirectory.get()),
            )
            // Only inspect the existing SAF downloads folder; do not create one.
            val root = base?.findFile("downloads")
            if (root == null || !root.isDirectory) {
                return@withContext Report(0, 0, 0L, 0L, 0, 0, 0, false, true, emptyList())
            }

            val series = mutableListOf<CountedSeries>()
            var completed = 0
            var unfinished = 0
            var knownCompletedBytes = 0L
            var knownUnfinishedBytes = 0L
            var unknownSizes = 0
            var visitedFiles = 0
            var capped = false

            scan@ for (source in root.listFiles().orEmpty()) {
                currentCoroutineContext().ensureActive()
                if (!source.isDirectory) continue
                for (manga in source.listFiles().orEmpty()) {
                    currentCoroutineContext().ensureActive()
                    if (!manga.isDirectory) continue
                    if (series.size >= MAX_SERIES) {
                        capped = true
                        break@scan
                    }
                    val label = source.name.orEmpty().take(30) +
                        " / " + manga.name.orEmpty().take(55)
                    val usage = CountedSeries(label)
                    series.add(usage)
                    for (chapter in manga.listFiles().orEmpty()) {
                        currentCoroutineContext().ensureActive()
                        val chapterName = chapter.name.orEmpty()
                        val isPending = chapter.isDirectory &&
                            chapterName.endsWith(Downloader.TMP_DIR_SUFFIX, ignoreCase = true)
                        val isCbz = chapter.isFile &&
                            chapterName.endsWith(".cbz", ignoreCase = true)
                        if (!isPending && !isCbz && !chapter.isDirectory) continue
                        if (completed + unfinished >= MAX_CHAPTERS) {
                            capped = true
                            break@scan
                        }
                        if (isPending) {
                            unfinished++
                            usage.unfinished++
                        } else {
                            completed++
                            usage.completed++
                        }
                        // Count actual saved bytes, not image dimensions or
                        // estimated compression ratios. Avoid opening streams.
                        val files = if (chapter.isDirectory) {
                            chapter.listFiles().orEmpty().filter { it.isFile }
                        } else {
                            listOf(chapter)
                        }
                        for (file in files) {
                            currentCoroutineContext().ensureActive()
                            if (visitedFiles >= MAX_FILE_ENTRIES) {
                                capped = true
                                break@scan
                            }
                            visitedFiles++
                            val length = file.length()
                            if (length < 0L) {
                                unknownSizes++
                            } else if (isPending) {
                                knownUnfinishedBytes += length
                            } else {
                                knownCompletedBytes += length
                                usage.bytes += length
                            }
                        }
                    }
                }
            }
            val top = series.asSequence()
                .filter { it.completed > 0 }
                .sortedByDescending { it.bytes }
                .take(MAX_DISPLAY_SERIES)
                .map { SeriesUsage(it.label, it.completed, it.bytes, it.unfinished) }
                .toList()
            Report(
                completed, unfinished, knownCompletedBytes, knownUnfinishedBytes,
                unknownSizes, visitedFiles, series.size, capped, false, top,
            )
        }
}
''').replace("\\\n", "\n").lstrip()

LABELS = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="seiryn_storage_overview_title">Storage overview</string>
    <string name="seiryn_storage_overview_subtitle">View download sizes and largest manga folders (read-only)</string>
    <string name="seiryn_storage_overview_scanning">Calculating storage usage…</string>
    <string name="seiryn_storage_overview_summary">Completed chapter files: %1$s\\nUnfinished transfers: %2$s\\n\\nCompleted chapters: %3$d\\nUnfinished folders: %4$d\\nManga folders inspected: %5$d\\nFiles inspected: %6$d</string>
    <string name="seiryn_storage_overview_largest">Largest manga folders (completed files only):</string>
    <string name="seiryn_storage_overview_unknown">%1$d files had unknown sizes; totals exclude those bytes.</string>
    <string name="seiryn_storage_overview_limited">The scan reached its safety limit. These are PARTIAL totals, not your entire downloaded library.</string>
    <string name="seiryn_storage_overview_disclaimer">Read-only measurement of existing downloaded files. SAF storage providers may not report every file size. This is not free-space information or proof that chapters are intact. No downloads, manga, progress, or backups were changed.</string>
    <string name="seiryn_storage_overview_missing">Download storage could not be accessed. Check the configured storage location and permissions. Nothing was changed.</string>
    <string name="seiryn_storage_overview_error">Storage usage could not be measured. Check storage access and try again. No files were changed.</string>
</resources>
'''


class StorageOverviewPatchError(RuntimeError):
    pass


def one(s: str, old: str, new: str, reason: str) -> str:
    n = s.count(old)
    if n != 1:
        raise StorageOverviewPatchError(f"{reason}: pinned source marker count {n}")
    return s.replace(old, new, 1)


def patch_settings(s: str) -> str:
    # Never attach a second copy of the overview to already-patched settings.
    if "SeirynStorageOverview" in s or "checkingStorageUsage" in s:
        raise StorageOverviewPatchError("Storage overview has already been inserted")
    for required in (
        "val downloadManager = remember { context.appGraph.downloadManager }",
        "val storagePreferences = remember { context.appGraph.storagePreferences }",
        "SeluraDownloadHealth.scan(context, storagePreferences)",
        "downloadManager.startDownloads()",
        "MaterialAlertDialogBuilder(context)",
        "var reviewingTransfers by remember { mutableStateOf(false) }",
    ):
        if required not in s:
            raise StorageOverviewPatchError(f"Current safety/download settings changed: {required}")
    s = one(s,
        "import eu.kanade.tachiyomi.data.download.SeluraDownloadHealth\n",
        "import eu.kanade.tachiyomi.data.download.SeluraDownloadHealth\n"
        "import eu.kanade.tachiyomi.data.download.SeirynStorageOverview\n",
        "existing health import")
    s = one(s, OLD_STATE, NEW_STATE, "settings overview state")
    s = one(s, OLD_PREFERENCE, NEW_PREFERENCE, "read-only storage action")
    return s


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file() or not (root / "gradlew").is_file():
        raise StorageOverviewPatchError("Pinned native source and license missing")
    files = [root / SCREEN, root / DASHBOARD, root / STRINGS]
    if not files[0].is_file() or files[1].exists() or files[2].exists():
        raise StorageOverviewPatchError("Existing settings missing or overview resources already exist")
    initial = files[0].read_text(encoding="utf-8")
    updated = patch_settings(initial)
    # All pinned source assertions succeed before any native file writes.
    files[0].write_text(updated, encoding="utf-8")
    files[1].parent.mkdir(parents=True, exist_ok=True)
    files[1].write_text(KOTLIN, encoding="utf-8")
    files[2].parent.mkdir(parents=True, exist_ok=True)
    files[2].write_text(LABELS, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
