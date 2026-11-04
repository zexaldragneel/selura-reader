#!/usr/bin/env python3
"""Performance 3.1: prioritize the current page before speculative HTTP prefetch."""
import argparse
from pathlib import Path

TARGET = "app/src/main/java/eu/kanade/tachiyomi/ui/reader/loader/HttpPageLoader.kt"
OLD = "pages.loadByRollingChunked(page.index, 2, 3) { chunks ->"
NEW = "pages.loadByRollingChunked(page.index, 1, 3) { chunks ->"

def patch_source(source: str) -> str:
    # Fail closed if the previous verified performance and cancellation patches differ.
    for marker in (
        "MAX_PAGES_AHEAD = 8",
        "logSlowReaderStage(\"page-image\", startedAt, imageOrigin)",
        "downloadJobs.putIfAbsent(pageIndex, job)",
        "downloadJobs.remove(it)?.cancel()",
        "withOneTransientRetry { source.getImageUrl(page) }",
        "chapterCache.putImageToCache(imageUrl, imageResponse)",
        "if (e is CancellationException)",
    ):
        if marker not in source:
            raise ValueError("Missing pinned reader safety contract: " + marker)
    if source.count(OLD) != 1 or NEW in source:
        raise ValueError("Expected exactly one original foreground prefetch anchor")
    # A one-page first chunk starts the visible page without waiting for the
    # neighboring page in the same initial batch. Subsequent chunks stay bounded.
    return source.replace(OLD, NEW, 1)

def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file() or not (root / "gradlew").is_file():
        raise ValueError("Pinned Android source checkout required")
    path = root / TARGET
    original = path.read_text(encoding="utf-8")
    path.write_text(patch_source(original), encoding="utf-8")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
