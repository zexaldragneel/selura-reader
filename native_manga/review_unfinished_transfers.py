#!/usr/bin/env python3
"""Add a safe, opt-in temporary chapter transfer review to native Mihon.

Applied strictly AFTER check_download_health.py (including the PR64
Mihon archive-reader correction). No old temporary file is ever
renamed, deleted or scheduled for transfer automatically.
"""
import argparse
from pathlib import Path

PREFIX = "app/src/main/"
HEALTH = PREFIX + "java/eu/kanade/tachiyomi/data/download/SeluraDownloadHealth.kt"
SETTINGS = PREFIX + "java/eu/kanade/presentation/more/settings/screen/SettingsDownloadScreen.kt"
STRINGS = PREFIX + "res/values/selura_download_health_strings.xml"


class ReviewTransfersPatchError(RuntimeError):
    pass


def exactly_once(text, before, after, label):
    amount = text.count(before)
    if amount != 1:
        raise ReviewTransfersPatchError(f"{label}: expected exactly one audited marker, found {amount}")
    return text.replace(before, after, 1)


def patch_health(text):
    text = exactly_once(
        text,
        "    private const val MAX_SAMPLE_ISSUES = 6\n",
        "    private const val MAX_SAMPLE_ISSUES = 6\n"
        "    private const val MAX_UNFINISHED_DETAILS = 20\n",
        "review detail bound",
    )
    text = exactly_once(
        text,
        """        val unfinished: Int,
        val capped: Boolean,""",
        """        val unfinished: Int,
        val unfinishedDetails: List<String>,
        val capped: Boolean,""",
        "result detail field",
    )
    text = exactly_once(
        text,
        r'''            return summary + examples + limit + "\n\n" +
                context.getString(R.string.selura_health_disclaimer)
        }
    }''',
        r'''            return summary + examples + limit + "\n\n" +
                context.getString(R.string.selura_health_disclaimer)
        }

        fun describeUnfinished(context: Context, queuedCount: Int): String {
            if (storageMissing) return context.getString(R.string.selura_health_storage_missing)
            val headline = context.getString(R.string.selura_recovery_count, unfinished)
            val examples = if (unfinishedDetails.isEmpty()) "" else {
                "\n\n" + unfinishedDetails.joinToString("\n")
            }
            val overflow = if (unfinished > unfinishedDetails.size) {
                "\n\n" + context.getString(R.string.selura_recovery_more, unfinished - unfinishedDetails.size)
            } else {
                ""
            }
            val queue = if (queuedCount > 0) {
                context.getString(R.string.selura_recovery_queue, queuedCount)
            } else {
                context.getString(R.string.selura_recovery_no_queue)
            }
            return headline + examples + overflow + "\n\n" + queue + "\n\n" +
                context.getString(R.string.selura_recovery_warning)
        }
    }''',
        "per-transfer read-only report",
    )
    text = exactly_once(
        text,
        "return@withContext Result(0, 0, 0, 0, false, true, emptyList())",
        "return@withContext Result(0, 0, 0, 0, emptyList(), false, true, emptyList())",
        "missing-storage report",
    )
    text = exactly_once(
        text,
        """        var unfinished = 0
        var capped = false""",
        """        var unfinished = 0
        val unfinishedDetails = mutableListOf<String>()
        var capped = false""",
        "review accumulating state",
    )
    text = exactly_once(
        text,
        """                    if (name.endsWith(Downloader.TMP_DIR_SUFFIX, ignoreCase = true)) {
                        unfinished++
                        continue
                    }""",
        """                    if (name.endsWith(Downloader.TMP_DIR_SUFFIX, ignoreCase = true)) {
                        unfinished++
                        // Read-only review: count existing image-like pages and
                        // interrupted *.tmp writes without inspecting content,
                        // opening streams, or changing any chapter files.
                        if (unfinishedDetails.size < MAX_UNFINISHED_DETAILS) {
                            val storedFiles = chapter.listFiles().orEmpty()
                            val imageCount = storedFiles.count {
                                it.isFile && imageName(it.name) && it.length() != 0L
                            }
                            val pendingCount = storedFiles.count {
                                it.isFile && it.name.orEmpty().endsWith(".tmp", ignoreCase = true)
                            }
                            val chapterLabel = name.removeSuffix(Downloader.TMP_DIR_SUFFIX).take(62)
                            unfinishedDetails +=
                                source.name.orEmpty().take(32) + " / " +
                                manga.name.orEmpty().take(40) + " / " +
                                chapterLabel + " (" + imageCount + " images, " +
                                pendingCount + " pending writes)"
                        }
                        continue
                    }""",
        "temporary chapter identification and file counts",
    )
    text = exactly_once(
        text,
        "Result(checked, suspect, unverified, unfinished, capped, false, issues)",
        "Result(checked, suspect, unverified, unfinished, unfinishedDetails, capped, false, issues)",
        "normal scan result",
    )
    return text


def patch_settings(text):
    text = exactly_once(
        text,
        """        val scope = rememberCoroutineScope()
        var checkingStorage by remember { mutableStateOf(false) }""",
        """        val scope = rememberCoroutineScope()
        val downloadManager = remember { context.appGraph.downloadManager }
        var checkingStorage by remember { mutableStateOf(false) }
        var reviewingTransfers by remember { mutableStateOf(false) }""",
        "settings queue reader and review state",
    )
    text = exactly_once(
        text,
        """            getDeleteChaptersGroup(
                downloadPreferences = downloadPreferences,""",
        """            Preference.PreferenceItem.TextPreference(
                title = context.getString(R.string.selura_recovery_title),
                subtitle = context.getString(
                    if (reviewingTransfers) R.string.selura_health_scanning
                    else R.string.selura_recovery_subtitle,
                ),
                onClick = {
                    if (!reviewingTransfers) {
                        reviewingTransfers = true
                        scope.launch {
                            try {
                                val report = SeluraDownloadHealth.scan(context, storagePreferences)
                                val queuedCount = downloadManager.queueState.value.size
                                val dialog = MaterialAlertDialogBuilder(context)
                                    .setTitle(R.string.selura_recovery_title)
                                    .setMessage(report.describeUnfinished(context, queuedCount))
                                if (!report.storageMissing && report.unfinished > 0 && queuedCount > 0) {
                                    // Requires a deliberate button press. Resume the ENTIRE
                                    // existing queue through Mihon, not selected temp files.
                                    // A temp folder without a queue entry is not auto-matched.
                                    dialog.setNegativeButton(android.R.string.cancel, null)
                                        .setPositiveButton(R.string.selura_recovery_resume_all) { _, _ ->
                                            downloadManager.startDownloads()
                                        }
                                } else {
                                    dialog.setPositiveButton(android.R.string.ok, null)
                                }
                                dialog.show()
                            } catch (e: CancellationException) {
                                throw e
                            } catch (_: Exception) {
                                MaterialAlertDialogBuilder(context)
                                    .setTitle(R.string.selura_recovery_title)
                                    .setMessage(R.string.selura_health_scan_error)
                                    .setPositiveButton(android.R.string.ok, null)
                                    .show()
                            } finally {
                                reviewingTransfers = false
                            }
                        }
                    }
                },
            ),
            getDeleteChaptersGroup(
                downloadPreferences = downloadPreferences,""",
        "download settings action for safe review and explicitly confirmed resume",
    )
    return text


def patch_strings(text):
    insertion = r'''    <string name="selura_recovery_title">Review unfinished transfers</string>
    <string name="selura_recovery_subtitle">Inspect temporary chapters and resume the existing queue if needed</string>
    <string name="selura_recovery_count">%1$d unfinished chapter folders found. The folders were not changed.</string>
    <string name="selura_recovery_more">%1$d additional unfinished folders not listed.</string>
    <string name="selura_recovery_queue">%1$d chapters are in the download queue. Resume all queued chapters is optional and uses normal download settings, including Wi-Fi restrictions.</string>
    <string name="selura_recovery_no_queue">The download queue is empty. An unfinished folder cannot safely be reattached automatically. Open the original manga chapter and choose Download to attempt resuming it.</string>
    <string name="selura_recovery_warning">These are temporary folders, not confirmed damaged files. Image counts do not prove pages are complete. Resuming the existing queue does not automatically reconnect orphaned folders and may use network data. No files were removed or repaired.</string>
    <string name="selura_recovery_resume_all">Resume all queued chapters</string>
'''
    return exactly_once(text, "</resources>", insertion + "</resources>", "localized labels")


def patch(root: Path):
    root = root.resolve()
    sources = {HEALTH: patch_health, SETTINGS: patch_settings, STRINGS: patch_strings}
    pending = {}
    for file, transform in sources.items():
        path = root / file
        if not path.is_file():
            raise ReviewTransfersPatchError(f"Missing pinned native file: {file}")
        old = path.read_text(encoding="utf-8")
        result = transform(old)
        if result == old:
            raise ReviewTransfersPatchError(f"No update produced for: {file}")
        pending[path] = result
    # Validate all three inputs before touching any native file.
    for path, result in pending.items():
        path.write_text(result, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
