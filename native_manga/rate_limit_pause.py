#!/usr/bin/env python3
"""Respect HTTP 429 by pausing the native queue until the owner resumes it.

Apply AFTER download_failure_details.py on the pinned Mihon v0.21.2 source.
No new requests, bypass, timed auto-retry, deletion, queue migration or ID changes.
"""
import argparse
from pathlib import Path

DOWNLOADER = "app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt"


class RateLimitPausePatchError(RuntimeError):
    pass


def replace_once(source: str, original: str, replacement: str, label: str) -> str:
    count = source.count(original)
    if count != 1:
        raise RateLimitPausePatchError(f"{label}: expected one pinned marker, found {count}")
    return source.replace(original, replacement, 1)


PAUSE_HANDLER = """    // HTTP 429 is a rate-limit response, never a reason to rotate hosts,
    // increase concurrency, retry automatically, or bypass source access.
    // Trigger this once per running download session, without blocking a
    // page's I/O coroutine. The existing pause action preserves the queue.
    private fun requestRateLimitPause(error: Throwable) {
        val httpError = diagnosticCause(error) as? HttpException ?: return
        if (httpError.code != 429 || !seirynRateLimitPausePending.compareAndSet(false, true)) return
        scope.launch(Dispatchers.Main) {
            if (isRunning) {
                pause()
                notifier.onWarning(
                    "Source returned HTTP 429. Downloads paused to respect its rate limit. Resume manually later.",
                )
            }
        }
    }

"""


def transform(source: str) -> str:
    source = replace_once(
        source,
        "    private val lock = Mutex()",
        "    private val lock = Mutex()\n"
        "    private val seirynRateLimitPausePending = java.util.concurrent.atomic.AtomicBoolean(false)",
        "one per-session pause guard",
    )
    source = replace_once(
        source,
        "        isPaused = false\n\n        launchDownloaderJob()",
        "        isPaused = false\n"
        "        seirynRateLimitPausePending.set(false)\n\n"
        "        launchDownloaderJob()",
        "rearm only after explicit restart",
    )
    source = replace_once(
        source,
        "                                recordPageDownloadFailure(download, page.number, e)\n"
        "                                page.status = Page.State.Error(e)",
        "                                recordPageDownloadFailure(download, page.number, e)\n"
        "                                requestRateLimitPause(e)\n"
        "                                page.status = Page.State.Error(e)",
        "image URL retrieval 429",
    )
    source = replace_once(
        source,
        "            download.failureReason = describeDownloadFailure(error)\n"
        "            download.status = Download.State.ERROR",
        "            download.failureReason = describeDownloadFailure(error)\n"
        "            requestRateLimitPause(error)\n"
        "            download.status = Download.State.ERROR",
        "chapter-level 429",
    )
    source = replace_once(
        source,
        "            recordPageDownloadFailure(download, page.number, e)\n"
        "            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)",
        "            recordPageDownloadFailure(download, page.number, e)\n"
        "            requestRateLimitPause(e)\n"
        "            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)",
        "image download 429",
    )
    source = replace_once(
        source,
        "    // Follow a bounded error cause chain, without exposing raw URLs,",
        PAUSE_HANDLER + "    // Follow a bounded error cause chain, without exposing raw URLs,",
        "rate-limit handler placement",
    )
    return source


def patch(root: Path) -> None:
    path = root.resolve() / DOWNLOADER
    if not path.is_file():
        raise RateLimitPausePatchError("Pinned Mihon Downloader.kt is missing")
    original = path.read_text(encoding="utf-8")
    updated = transform(original)  # all markers checked before any writes
    if updated == original:
        raise RateLimitPausePatchError("No intended change")
    path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
