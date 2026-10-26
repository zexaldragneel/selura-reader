#!/usr/bin/env python3
"""Surface bounded and source-safe chapter download failures in actual native UI.

Patch runs after verify_chapter_downloads.py and download_manager_actions.py
against the audited Mihon source tree; never mutates user storage or IDs.
"""
import argparse
from pathlib import Path

PREFIX = "app/src/main/"
MODEL = PREFIX + "java/eu/kanade/tachiyomi/data/download/model/Download.kt"
DOWNLOADER = PREFIX + "java/eu/kanade/tachiyomi/data/download/Downloader.kt"
HOLDER = PREFIX + "java/eu/kanade/tachiyomi/ui/download/DownloadHolder.kt"
MENU = PREFIX + "res/menu/download_single.xml"
LABELS = PREFIX + "res/values/selura_download_failure_details.xml"
FILES = (MODEL, DOWNLOADER, HOLDER, MENU)


class FailureDetailsPatchError(RuntimeError):
    pass


def only_once(s, before, after, label):
    if s.count(before) != 1:
        raise FailureDetailsPatchError(f"{label}: expected one audited marker, found {s.count(before)}")
    return s.replace(before, after, 1)


def model(s):
    return only_once(
        s,
        """    @Transient
    val progressFlow = _pagesFlow""",
        """    // Ephemeral diagnostic only. Not serialized into the persisted download
    // queue, database, backups, manga metadata, or notification history.
    @Transient
    var failureReason: String? = null

    @Transient
    val progressFlow = _pagesFlow""",
        "transient download failure reason",
    )


def downloader(s):
    s = only_once(
        s,
        """    private suspend fun downloadChapter(download: Download, slots: Semaphore, pagesStarted: CompletableDeferred<Unit>) {
        val mangaDir = provider.getMangaDir(download.manga.title, download.source).getOrElse { e ->""",
        """    private suspend fun downloadChapter(download: Download, slots: Semaphore, pagesStarted: CompletableDeferred<Unit>) {
        // A new attempt must not display the preceding failure's reason.
        download.failureReason = null
        val mangaDir = provider.getMangaDir(download.manga.title, download.source).getOrElse { e ->
            download.failureReason = describeDownloadFailure(e)""",
        "chapter start and storage root error",
    )
    s = only_once(
        s,
        """        if (availSpace != -1L && availSpace < MIN_DISK_SPACE) {
            download.status = Download.State.ERROR""",
        """        if (availSpace != -1L && availSpace < MIN_DISK_SPACE) {
            download.failureReason = context.stringResource(MR.strings.download_insufficient_space)
            download.status = Download.State.ERROR""",
        "insufficient space reason",
    )
    s = only_once(
        s,
        """            if (!archiveReady && !folderReady) {
                download.status = Download.State.ERROR""",
        """            if (!archiveReady && !folderReady) {
                download.failureReason = "Existing chapter files could not be read. Check download storage; files were not deleted."
                download.status = Download.State.ERROR""",
        "previously completed chapter folder reason",
    )
    s = only_once(
        s,
        """                            } catch (e: Throwable) {
                                page.status = Page.State.Error(e)
                            }""",
        """                            } catch (e: Throwable) {
                                if (e is CancellationException) throw e
                                recordPageDownloadFailure(download, page.number, e)
                                page.status = Page.State.Error(e)
                            }""",
        "image URL request reason",
    )
    s = only_once(
        s,
        """            if (!isDownloadSuccessful(download, tmpDir)) {
                download.status = Download.State.ERROR
                return
            }""",
        """            if (!isDownloadSuccessful(download, tmpDir)) {
                val pageError = download.pages?.firstNotNullOfOrNull {
                    (it.status as? Page.State.Error)?.error
                }
                download.failureReason = download.failureReason
                    ?: pageError?.let(::describeDownloadFailure)
                    ?: "Chapter pages are missing, incomplete or unreadable."
                download.status = Download.State.ERROR
                return
            }""",
        "incomplete pages reason",
    )
    s = only_once(
        s,
        """            logcat(LogPriority.ERROR, error)
            download.status = Download.State.ERROR
            notifier.onError(error.message, download.chapter.name, download.manga.title, download.manga.id)""",
        """            logcat(LogPriority.ERROR, error)
            download.failureReason = describeDownloadFailure(error)
            download.status = Download.State.ERROR
            notifier.onError(error.message, download.chapter.name, download.manga.title, download.manga.id)""",
        "chapter exception reason",
    )
    s = only_once(
        s,
        """            page.progress = 0
            page.status = Page.State.Error(e)
            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)""",
        """            page.progress = 0
            page.status = Page.State.Error(e)
            recordPageDownloadFailure(download, page.number, e)
            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)""",
        "individual page request reason",
    )
    s = only_once(
        s,
        """    private fun isTransientDownloadFailure(error: Throwable): Boolean = when (error) {""",
        """    // Follow a bounded error cause chain, without exposing raw URLs,
    // cookies, tokens, HTTP response contents, or exception messages.
    private fun diagnosticCause(error: Throwable): Throwable {
        var cursor: Throwable? = error
        var fallback: Throwable = error
        repeat(4) {
            val cause = cursor ?: return fallback
            if (cause is HttpException || cause is java.net.SocketException ||
                cause is java.io.EOFException || cause is java.io.FileNotFoundException ||
                cause is SecurityException || cause is IllegalStateException ||
                cause is NullPointerException
            ) {
                return cause
            }
            if (cause is IOException) fallback = cause
            cursor = cause.cause?.takeUnless { it === cause }
        }
        return fallback
    }

    // Sibling image requests may fail simultaneously: retain the first
    // actionable page diagnosis without overwriting it from a later page.
    private fun recordPageDownloadFailure(download: Download, number: Int, error: Throwable) {
        val summary = "Page " + number + ": " + describeDownloadFailure(error)
        synchronized(download) {
            if (download.failureReason == null) download.failureReason = summary
        }
    }

    // These are bounded, privacy-safe cause CATEGORIES, not raw exception text.
    // Respect HTTP 401/403/429 restrictions; no bypasses or extra requests.
    private fun describeDownloadFailure(error: Throwable): String {
        val cause = diagnosticCause(error)
        return when (cause) {
            is HttpException -> when (cause.code) {
                401, 403 -> "This chapter or image requires source access or unlocking (HTTP " + cause.code + "). Check its WebView."
                404 -> "The source cannot find this chapter or image (HTTP 404). Refresh chapters or try later."
                429 -> "The source is rate limiting downloads (HTTP 429). Retry later."
                else -> "Source request failed (HTTP " + cause.code + ")."
            }
            is SocketTimeoutException, is ConnectException ->
                "Connection timed out or failed. Check your connection and retry."
            is java.net.SocketException, is java.io.EOFException ->
                "Image connection was interrupted before the page completed. Retry later."
            is java.io.FileNotFoundException ->
                "An image or download file could not be opened. Check source and storage access."
            is SecurityException ->
                "Android refused download file access. Check the configured storage permission."
            is IllegalStateException -> if (cause.message?.contains("closed", ignoreCase = true) == true) {
                "Image HTTP response was closed before Seiryn could read it. Check the installed extension version."
            } else {
                "Source or downloader entered an invalid state (IllegalStateException)."
            }
            is NullPointerException ->
                "Source or downloader encountered missing required data (NullPointerException)."
            is IOException -> when {
                cause.message?.startsWith("Hive Scans did not provide public chapter images") == true ->
                    "Hive Scans has no publicly accessible images for this chapter. It may be locked; check WebView."
                cause.message?.startsWith("Mangakakalot chapter image unavailable across chapter-provided CDNs") == true ->
                    "Mangakakalot image hosts could not supply this page. Retry later or check source access."
                cause.message?.startsWith("Could not finalize downloaded chapter") == true ||
                    cause.message?.startsWith("Finalized chapter is not readable") == true ->
                    "Android download storage could not finalize this chapter. Check storage permissions and free space."
                else -> "Image transfer or file access failed (IOException). Check network and storage."
            }
            else -> {
                // Class names, unlike exception messages, never include source URLs.
                val type = cause.javaClass.simpleName.filter { it.isLetterOrDigit() }
                    .take(40).ifBlank { "Unknown" }
                "Unexpected source or downloader failure (" + type + ")."
            }
        }
    }

    private fun isTransientDownloadFailure(error: Throwable): Boolean = when (error) {""",
        "safe visible cause categories",
    )
    return s


def holder(s):
    s = only_once(
        s,
        """                findItem(R.id.selura_retry_chapter).isVisible = download.status == Download.State.ERROR
                findItem(R.id.move_to_top).isVisible""",
        """                findItem(R.id.selura_retry_chapter).isVisible = download.status == Download.State.ERROR
                findItem(R.id.selura_view_download_error).isVisible = download.status == Download.State.ERROR
                findItem(R.id.move_to_top).isVisible""",
        "show reason in failure-only menu",
    )
    s = only_once(
        s,
        """            onMenuItemClick = {
                adapter.downloadItemListener.onMenuItemClick(bindingAdapterPosition, this)
            },""",
        """            onMenuItemClick = {
                if (itemId == R.id.selura_view_download_error) {
                    com.google.android.material.dialog.MaterialAlertDialogBuilder(view.context)
                        .setTitle(R.string.selura_view_download_error)
                        .setMessage(
                            download.failureReason
                                ?: view.context.getString(R.string.selura_unknown_download_error),
                        )
                        .setPositiveButton(android.R.string.ok, null)
                        .show()
                } else {
                    adapter.downloadItemListener.onMenuItemClick(bindingAdapterPosition, this)
                }
            },""",
        "native error dialog",
    )
    return s


def menu(s):
    return only_once(
        s,
        """    <item
        android:id="@+id/selura_retry_chapter"
        android:title="@string/selura_retry_chapter" />""",
        """    <item
        android:id="@+id/selura_retry_chapter"
        android:title="@string/selura_retry_chapter" />

    <item
        android:id="@+id/selura_view_download_error"
        android:title="@string/selura_view_download_error" />""",
        "View error menu item",
    )


def patch(root: Path):
    root = root.resolve()
    if (root / LABELS).exists():
        raise FailureDetailsPatchError("Failure details already patched")
    transforms = {MODEL: model, DOWNLOADER: downloader, HOLDER: holder, MENU: menu}
    pending = {}
    for name, fn in transforms.items():
        target = root / name
        if not target.is_file():
            raise FailureDetailsPatchError(f"Pinned source missing: {name}")
        original = target.read_text(encoding="utf-8")
        result = fn(original)
        if result == original:
            raise FailureDetailsPatchError(f"No change in {name}")
        pending[target] = result
    # Only write after every source marker has passed the preflight.
    for target, content in pending.items():
        target.write_text(content, encoding="utf-8")
    target = root / LABELS
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<resources>\n'
        '  <string name="selura_view_download_error">View error</string>\n'
        '  <string name="selura_unknown_download_error">The source did not provide an error reason. Check WebView, connectivity and storage.</string>\n'
        '</resources>\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
