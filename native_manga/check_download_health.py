#!/usr/bin/env python3
"""Add a non-destructive Download Storage Health action to native Mihon settings.

Apply after the existing Selura native patches to pinned Mihon v0.21.2.
This ONLY creates source and string resources and adjusts AppGraph and
SettingsDownloadScreen. It never deletes, renames or rewrites manga files.
"""
import argparse
from pathlib import Path
from textwrap import dedent

PREFIX = "app/src/main/"
SETTINGS = PREFIX + "java/eu/kanade/presentation/more/settings/screen/SettingsDownloadScreen.kt"
HEALTH = PREFIX + "java/eu/kanade/tachiyomi/data/download/SeluraDownloadHealth.kt"
STRINGS = PREFIX + "res/values/selura_download_health_strings.xml"


class DownloadHealthPatchError(RuntimeError):
    pass


def replace_one(s: str, old: str, new: str, label: str) -> str:
    found = s.count(old)
    if found != 1:
        raise DownloadHealthPatchError(f"{label}: expected exactly 1 marker, found {found}")
    return s.replace(old, new, 1)


def patch_settings(s: str) -> str:
    s = replace_one(
        s, "import androidx.compose.runtime.remember\n",
        "import androidx.compose.runtime.remember\n"
        "import androidx.compose.runtime.rememberCoroutineScope\n",
        "settings Compose coroutine scope",
    )
    s = replace_one(
        s, "import eu.kanade.presentation.more.settings.widget.TriStateListDialog\n",
        "import eu.kanade.presentation.more.settings.widget.TriStateListDialog\n"
        "import eu.kanade.tachiyomi.R\n"
        "import eu.kanade.tachiyomi.data.download.SeluraDownloadHealth\n",
        "settings health imports",
    )
    s = replace_one(
        s, "import mihon.app.di.appGraph\n",
        "import kotlinx.coroutines.CancellationException\n"
        "import kotlinx.coroutines.launch\n"
        "import mihon.app.di.appGraph\n"
        "import com.google.android.material.dialog.MaterialAlertDialogBuilder\n",
        "settings launch/dialog imports",
    )
    s = replace_one(
        s,
        """        val downloadPreferences = remember { context.appGraph.downloadPreferences }
        return listOf(""",
        """        val downloadPreferences = remember { context.appGraph.downloadPreferences }
        val storagePreferences = remember { context.appGraph.storagePreferences }
        val scope = rememberCoroutineScope()
        var checkingStorage by remember { mutableStateOf(false) }
        return listOf(""",
        "settings health state",
    )
    s = replace_one(
        s,
        """            getDeleteChaptersGroup(
                downloadPreferences = downloadPreferences,""",
        """            Preference.PreferenceItem.TextPreference(
                title = context.getString(R.string.selura_health_title),
                subtitle = context.getString(
                    if (checkingStorage) R.string.selura_health_scanning
                    else R.string.selura_health_subtitle,
                ),
                onClick = {
                    if (!checkingStorage) {
                        checkingStorage = true
                        scope.launch {
                            try {
                                val result = SeluraDownloadHealth.scan(context, storagePreferences)
                                MaterialAlertDialogBuilder(context)
                                    .setTitle(R.string.selura_health_title)
                                    .setMessage(result.describe(context))
                                    .setPositiveButton(android.R.string.ok, null)
                                    .show()
                            } catch (e: CancellationException) {
                                throw e
                            } catch (_: Exception) {
                                MaterialAlertDialogBuilder(context)
                                    .setTitle(R.string.selura_health_title)
                                    .setMessage(R.string.selura_health_scan_error)
                                    .setPositiveButton(android.R.string.ok, null)
                                    .show()
                            } finally {
                                checkingStorage = false
                            }
                        }
                    }
                },
            ),
            getDeleteChaptersGroup(
                downloadPreferences = downloadPreferences,""",
        "settings visible Check Download Storage button",
    )
    return s


HEALTH_SOURCE = dedent(r'''\
package eu.kanade.tachiyomi.data.download

import android.content.Context
import com.hippo.unifile.UniFile
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import tachiyomi.core.common.util.system.ImageUtil
import tachiyomi.domain.storage.service.StoragePreferences
import android.net.Uri
import eu.kanade.tachiyomi.R
import java.io.IOException
import mihon.core.archive.archiveReader

/**
 * Read-only, bounded spot check of saved chapter files.
 *
 * Does NOT inspect database/library status, alter the download cache,
 * delete temporary pages, rewrite CBZ files or make network requests.
 * The result is not a full page-by-page checksum/CRC audit.
 */
object SeluraDownloadHealth {
    private const val MAX_CHAPTERS = 2500
    private const val MAX_ZIP_ENTRIES = 4096
    private const val MAX_SAMPLE_ISSUES = 6

    data class Result(
        val checked: Int,
        val suspect: Int,
        val unverified: Int,
        val unfinished: Int,
        val capped: Boolean,
        val storageMissing: Boolean,
        val issueExamples: List<String>,
    ) {
        fun describe(context: Context): String {
            if (storageMissing) return context.getString(R.string.selura_health_storage_missing)
            val summary = context.getString(
                R.string.selura_health_report,
                checked,
                suspect,
                unverified,
                unfinished,
            )
            val examples = if (issueExamples.isEmpty()) "" else {
                "\n\n" + context.getString(R.string.selura_health_issues) +
                    "\n" + issueExamples.joinToString("\n")
            }
            val limit = if (capped) {
                "\n\n" + context.getString(R.string.selura_health_limited)
            } else {
                ""
            }
            return summary + examples + limit + "\n\n" +
                context.getString(R.string.selura_health_disclaimer)
        }
    }

    suspend fun scan(context: Context, storagePreferences: StoragePreferences): Result =
        withContext(Dispatchers.IO) {
        // Find the existing download directory rather than calling
        // StorageManager.getDownloadsDirectory(), which may CREATE it.
        val base = UniFile.fromUri(
            context,
            Uri.parse(storagePreferences.baseStorageDirectory.get()),
        )
        val root = base?.findFile("downloads")
        if (root == null || !root.isDirectory) {
            return@withContext Result(0, 0, 0, 0, false, true, emptyList())
        }
        var checked = 0
        var suspect = 0
        var unverified = 0
        var unfinished = 0
        var capped = false
        val issues = mutableListOf<String>()

        chapterScan@ for (source in root.listFiles().orEmpty()) {
            currentCoroutineContext().ensureActive()
            if (!source.isDirectory) continue
            for (manga in source.listFiles().orEmpty()) {
                currentCoroutineContext().ensureActive()
                if (!manga.isDirectory) continue
                for (chapter in manga.listFiles().orEmpty()) {
                    currentCoroutineContext().ensureActive()
                    val name = chapter.name.orEmpty()
                    if (name.endsWith(Downloader.TMP_DIR_SUFFIX, ignoreCase = true)) {
                        unfinished++
                        continue
                    }
                    if (!chapter.isDirectory && !(chapter.isFile && name.endsWith(".cbz", ignoreCase = true))) {
                        continue
                    }
                    if (checked >= MAX_CHAPTERS) {
                        capped = true
                        break@chapterScan
                    }
                    checked++
                    // Exceptions mean this SAF/provider or archive could
                    // not be inspected; they DO NOT prove corruption.
                    val state = try {
                        if (chapter.isDirectory) inspectImages(chapter)
                        else inspectArchive(context, chapter)
                    } catch (e: CancellationException) {
                        throw e
                    } catch (_: Exception) {
                        CheckState.UNVERIFIED
                    }
                    when (state) {
                        CheckState.READABLE -> Unit
                        CheckState.SUSPECT -> {
                            suspect++
                            if (issues.size < MAX_SAMPLE_ISSUES) {
                                issues += "Potentially unreadable: " +
                                    manga.name.orEmpty().take(50) + " / " + name.take(70)
                            }
                        }
                        CheckState.UNVERIFIED -> {
                            unverified++
                            if (issues.size < MAX_SAMPLE_ISSUES) {
                                issues += "Could not verify: " +
                                    manga.name.orEmpty().take(50) + " / " + name.take(70)
                            }
                        }
                    }
                }
            }
        }
        Result(checked, suspect, unverified, unfinished, capped, false, issues)
    }

    private fun imageName(name: String?): Boolean {
        val n = name.orEmpty().lowercase(java.util.Locale.ROOT)
        return n.endsWith(".jpg") || n.endsWith(".jpeg") || n.endsWith(".png") ||
            n.endsWith(".webp") || n.endsWith(".gif") || n.endsWith(".avif") ||
            n.endsWith(".heic") || n.endsWith(".jxl")
    }

    private enum class CheckState { READABLE, SUSPECT, UNVERIFIED }

    // Confirm nonempty image files. SAF may return unknown file sizes,
    // so never treat -1 as corruption. Failed image header sampling is
    // inconclusive, not evidence that previously readable images are bad.
    private fun inspectImages(chapter: UniFile): CheckState {
        val images = chapter.listFiles().orEmpty().filter { it.isFile && imageName(it.name) }
        if (images.isEmpty() || images.any { it.length() == 0L }) return CheckState.SUSPECT
        val samples = listOf(images.first(), images.last()).distinctBy { it.uri }
        return if (samples.all { file ->
                ImageUtil.findImageType { file.openInputStream() } != null
            }) {
            CheckState.READABLE
        } else {
            CheckState.UNVERIFIED
        }
    }

    // Read archives with the SAME libarchive-backed parser that Mihon's
    // ArchivePageLoader uses for offline reading. Java ZipInputStream can
    // misclassify valid libarchive-created CBZs across SAF providers.
    // Inspect just one image entry and its header: no extraction, writes,
    // file renaming, deleting, or exhaustive CRC scan.
    private fun inspectArchive(context: Context, chapter: UniFile): CheckState =
        chapter.archiveReader(context).use { reader ->
            val entry = reader.useEntries { entries ->
                entries.take(MAX_ZIP_ENTRIES).firstOrNull {
                    it.isFile && imageName(it.name)
                }
            } ?: return@use CheckState.SUSPECT
            if (ImageUtil.findImageType {
                    reader.getInputStream(entry.name)
                        ?: throw IOException("Could not access archive entry")
                } != null
            ) {
                CheckState.READABLE
            } else {
                CheckState.UNVERIFIED
            }
        }
}
''').replace("\\\n", "\n").lstrip()


STRINGS_SOURCE = '''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="selura_health_title">Check download storage</string>
    <string name="selura_health_subtitle">Read-only spot check of saved chapters and unfinished transfers</string>
    <string name="selura_health_scanning">Checking downloaded files…</string>
    <string name="selura_health_report">Checked %1$d completed chapter files.\\n%2$d potentially unreadable.\\n%3$d could not be verified (not considered damaged).\\n%4$d unfinished transfers found (not deleted).</string>
    <string name="selura_health_issues">Sample results requiring attention:</string>
    <string name="selura_health_limited">The scan stopped after 2,500 chapter files. Results are partial.</string>
    <string name="selura_health_disclaimer">This is a read-only spot check using the native Mihon archive reader. A file that could not be verified is NOT confirmed damaged. Only sampled image headers were checked, not every page or CRC. Unfinished transfers may still be resumable. No files were changed.</string>
    <string name="selura_health_storage_missing">The configured download storage could not be accessed. Check storage permissions and location.</string>
    <string name="selura_health_scan_error">The storage check could not finish. Please verify storage permissions and try again. No files were changed.</string>
</resources>
'''


def patch(root: Path):
    root = root.resolve()
    for path in (HEALTH, STRINGS):
        if (root / path).exists():
            raise DownloadHealthPatchError(f"Already present: {path}")
    targets = ((SETTINGS, patch_settings),)
    pending = {}
    for path, transform in targets:
        target = root / path
        if not target.is_file():
            raise DownloadHealthPatchError(f"Pinned source missing: {path}")
        old = target.read_text(encoding="utf-8")
        newer = transform(old)
        if newer == old:
            raise DownloadHealthPatchError(f"No patch applied: {path}")
        pending[target] = newer
    for path, new_contents in pending.items():
        path.write_text(new_contents, encoding="utf-8")
    health = root / HEALTH
    health.parent.mkdir(parents=True, exist_ok=True)
    health.write_text(HEALTH_SOURCE, encoding="utf-8")
    strings = root / STRINGS
    strings.parent.mkdir(parents=True, exist_ok=True)
    strings.write_text(STRINGS_SOURCE, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)


if __name__ == "__main__":
    main()
