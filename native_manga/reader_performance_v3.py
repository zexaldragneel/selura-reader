#!/usr/bin/env python3
"""Add privacy-safe, slow-only HTTP reader diagnostics after Performance v2."""
import argparse
from pathlib import Path

TARGET = "app/src/main/java/eu/kanade/tachiyomi/ui/reader/loader/HttpPageLoader.kt"

class TelemetryContractError(RuntimeError):
    pass

def once(source, old, new):
    if source.count(old) != 1:
        raise TelemetryContractError(f"Expected exactly one anchor, found {source.count(old)}")
    return source.replace(old, new, 1)

def patch_source(source):
    for marker in ("MAX_PAGES_AHEAD = 8", "withOneTransientRetry { source.getImageUrl(page) }",
                   "chapterCache.putImageToCache(imageUrl, imageResponse)",
                   "if (e is CancellationException) {", "page.status = Page.State.Ready"):
        if marker not in source:
            raise TelemetryContractError("Missing reader safety contract: " + marker)
    source = once(source, "import kotlinx.coroutines.CancellationException\n",
                  "import android.os.SystemClock\nimport android.util.Log\nimport kotlinx.coroutines.CancellationException\n")
    source = once(source,
                  "    override suspend fun getPages(): List<ReaderPage> {\n        val pages = try {",
                  """    override suspend fun getPages(): List<ReaderPage> {
        val startedAt = SystemClock.elapsedRealtime()
        var pageListOrigin = "cache"
        val pages = try {""")
    source = once(source,
                  "            withOneTransientRetry { source.getPageList(chapter.chapter.toSChapter()) }",
                  """            pageListOrigin = "network"
            withOneTransientRetry { source.getPageList(chapter.chapter.toSChapter()) }""")
    source = once(source,
                  "        return pages.mapIndexed { index, page ->",
                  """        logSlowReaderStage("chapter-list", startedAt, pageListOrigin)
        return pages.mapIndexed { index, page ->""")
    source = once(source,
                  "    private suspend fun internalLoadPage(page: ReaderPage, force: Boolean = false) {\n        try {",
                  """    private suspend fun internalLoadPage(page: ReaderPage, force: Boolean = false) {
        val startedAt = SystemClock.elapsedRealtime()
        var imageOrigin = "cache"
        try {""")
    source = once(source,
                  "            if (force || !chapterCache.isImageInCache(imageUrl)) {",
                  """            if (force || !chapterCache.isImageInCache(imageUrl)) {
                imageOrigin = "network"""")
    source = once(source,
                  "            page.status = Page.State.Error(e)\n        }\n    }",
                  """            page.status = Page.State.Error(e)
        } finally {
            // No source names, manga titles, URLs, page IDs, or exception messages.
            logSlowReaderStage("page-image", startedAt, imageOrigin)
        }
    }""")
    source = once(source,
                  "    private suspend fun internalLoadPage(page: ReaderPage, force: Boolean = false) {",
                  """    private fun logSlowReaderStage(stage: String, startedAt: Long, origin: String) {
        val elapsedMs = SystemClock.elapsedRealtime() - startedAt
        if (elapsedMs >= 750L) {
            Log.d("SeirynReaderPerf", "stage=$stage origin=$origin elapsedMs=$elapsedMs")
        }
    }

    private suspend fun internalLoadPage(page: ReaderPage, force: Boolean = false) {""")
    return source

def patch(root: Path):
    root = root.resolve()
    if not (root / "LICENSE").is_file() or not (root / "gradlew").is_file():
        raise TelemetryContractError("Pinned Android checkout required")
    target = root / TARGET
    original = target.read_text(encoding="utf-8")
    updated = patch_source(original)
    target.write_text(updated, encoding="utf-8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
