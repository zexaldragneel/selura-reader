#!/usr/bin/env python3
"""Patch the approved Mihon downloader: verify chapter pages and safe retries."""
import argparse
import hashlib
from pathlib import Path

DOWNLOADER = "app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt"
PINNED_BLOB = "105c153ef1a7672d465e52eb2cfe5387d60e9e74"


class ChapterIntegrityError(RuntimeError):
    pass


def once(source: str, old: str, new: str, name: str) -> str:
    matches = source.count(old)
    if matches != 1:
        raise ChapterIntegrityError(f"{name}: expected one audited marker, got {matches}")
    return source.replace(old, new, 1)


def verify_blob(source: str):
    data = source.encode("utf-8")
    sha = hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
    if sha != PINNED_BLOB:
        raise ChapterIntegrityError("Pinned Mihon Downloader.kt differs from audited snapshot")


def transform(source: str) -> str:
    source = once(source, "import java.io.File\n",
                  "import java.io.EOFException\nimport java.io.File\nimport java.io.IOException\n"
                  "import java.net.ConnectException\nimport java.net.SocketTimeoutException\n",
                  "network imports")
    source = once(source, "                val pages = download.source.getPageList(download.chapter.toSChapter())",
                  """                val pages = withOneTransientDownloadRetry {
                    download.source.getPageList(download.chapter.toSChapter())
                }""", "page-list retry")
    source = once(source, "                                page.imageUrl = download.source.getImageUrl(page)",
                  """                                page.imageUrl = withOneTransientDownloadRetry {
                                    download.source.getImageUrl(page)
                                }""", "page URL retry")
    source = once(source,
                  """        val imageFile = tmpDir.listFiles()?.firstOrNull {
            isDownloadedPageImage(it.name ?: return@firstOrNull false, filename)
        }""",
                  """        val imageFile = tmpDir.listFiles()?.firstOrNull {
            // An empty or invalid partial file must not count as a page.
            isDownloadedPageImage(it.name ?: return@firstOrNull false, filename) &&
                it.isFile && it.length() > 0L &&
                ImageUtil.isImage(it.name) { it.openInputStream() }
        }""", "unfinished page verification")
    source = once(source, """                tmpDir.renameTo(chapterDirname)
            }
            cache.addChapter(chapterDirname, mangaDir, download.manga)""",
                  """                if (!tmpDir.renameTo(chapterDirname)) {
                    throw IOException("Could not finalize downloaded chapter directory")
                }
            }
            // Index only AFTER a verified final rename.
            cache.addChapter(chapterDirname, mangaDir, download.manga)""",
                  "final chapter directory commit")
    source = once(source,
                  """            // Retry 3 times, waiting 2, 4 and 8 seconds between attempts.
            .retryWhen { _, attempt ->
                if (attempt < 3) {
                    delay((2L shl attempt.toInt()).seconds)
                    true
                } else {
                    false
                }
            }""",
                  """            // Never retry 403/404/429, auth challenges or arbitrary errors.
            .retryWhen { error, attempt ->
                if (attempt < 3 && isTransientDownloadFailure(error)) {
                    delay((2L shl attempt.toInt()).seconds)
                    true
                } else {
                    false
                }
            }""",
                  "bounded transient-only page retries")
    source = once(source,
                  """        // Ensure that the chapter folder has all the pages
        val downloadedImagesCount = tmpDir.listFiles().orEmpty().count {
            val fileName = it.name.orEmpty()
            when {
                fileName in listOf(COMIC_INFO_FILE, NOMEDIA_FILE) -> false
                fileName.endsWith(".tmp") -> false
                // Only count the first split page and not the others
                fileName.contains("__") && !fileName.endsWith("__001.jpg") -> false
                else -> true
            }
        }
        return downloadedImagesCount == downloadPageCount""",
                  """        // Count alone could accept pages 000 + 002 with page 001 missing.
        // Check real images for EVERY expected index, including split-page 001.
        if (downloadPageCount == 0) return false
        val images = tmpDir.listFiles().orEmpty().filter { it.isFile }
        val digits = downloadPageCount.toString().length.coerceAtLeast(3)
        return (0 until downloadPageCount).all { index ->
            val prefix = "%0${digits}d".format(Locale.ENGLISH, index)
            images.any { file ->
                isDownloadedPageImage(file.name.orEmpty(), prefix) &&
                    file.length() > 0L &&
                    ImageUtil.isImage(file.name) { file.openInputStream() }
            }
        }""", "complete chapter per-index verification")
    source = once(source, """        zip.renameTo("$dirname.cbz")
        tmpDir.delete()""",
                  """        if (!zip.renameTo("$dirname.cbz")) {
            // Keep unfinished pages if SAF storage refuses a final rename.
            throw IOException("Could not finalize downloaded chapter archive")
        }
        tmpDir.delete()""", "CBZ final archive guard")
    source = once(source,
                  """    private suspend fun downloadImage(page: Page, source: HttpSource, tmpDir: UniFile, filename: String): UniFile {""",
                  """    private fun isTransientDownloadFailure(error: Throwable): Boolean = when (error) {
        is SocketTimeoutException, is ConnectException, is EOFException -> true
        is HttpException -> error.code in setOf(500, 502, 503, 504, 522, 523, 524)
        else -> false
    }

    private suspend fun <T> withOneTransientDownloadRetry(action: suspend () -> T): T =
        try {
            action()
        } catch (error: Throwable) {
            if (error is CancellationException || !isTransientDownloadFailure(error)) throw error
            delay(450L)
            action()
        }

    private suspend fun downloadImage(page: Page, source: HttpSource, tmpDir: UniFile, filename: String): UniFile {""",
                  "network retry helper")
    return source


def patch(root: Path, verify_pinned_blob: bool = True):
    path = root.resolve() / DOWNLOADER
    if not path.is_file():
        raise ChapterIntegrityError("Pinned Mihon downloader source is missing")
    original = path.read_text(encoding="utf-8")
    if verify_pinned_blob:
        verify_blob(original)
    updated = transform(original)
    if updated == original:
        raise ChapterIntegrityError("No intended patch")
    path.write_text(updated, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    args = parser.parse_args()
    patch(args.upstream)


if __name__ == "__main__":
    main()
