#!/usr/bin/env python3
"""Reader Performance 2.0: bound online page prefetch without touching storage."""
from pathlib import Path
import argparse

HTTP_LOADER = "app/src/main/java/eu/kanade/tachiyomi/ui/reader/loader/HttpPageLoader.kt"

OLD_PLAN = """        val window = if (canLoadAhead()) items.indices else (index - 1)..(index + LIMITED_PAGES_AHEAD)
        val chunks = buildList {
            items.getOrNull(index)?.let(::add)
            items.getOrNull(index - 1)?.let(::add)
            items.getOrNull(index + 1)?.let(::add)
            // Original reader uses items.lastIndex, not the list being built
            if (index < items.lastIndex - 1) {
                items.subList(index + 2, items.size).let(::addAll)
            }
            if (index > 1) {
                items.subList(0, index - 1).reversed().let(::addAll)
            }
        }
            .filter { it.index in window }
            .rollingChunked(chunkStartSize, chunkEndSize)
            .also(onNewChunks)"""

# Exact pinned upstream source comment; fail closed rather than trying fuzzy edits.
OLD_PLAN = OLD_PLAN.replace(
    "// Original reader uses items.lastIndex, not the list being built",
    "// " + chr(96) + "items.lastIndex" + chr(96) +
    ", not the list being built, whose lastIndex is at most 2 here",
)

NEW_PLAN = """        // Prefetch only nearby online pages. Even if read-ahead is enabled,
        // opening a 300-page chapter must not queue the entire chapter.
        val readAhead = canLoadAhead()
        val first = (index - if (readAhead) 2 else 1).coerceAtLeast(0)
        val last = (index + if (readAhead) MAX_PAGES_AHEAD else LIMITED_PAGES_AHEAD)
            .coerceAtMost(items.lastIndex)
        val chunks = buildList {
            // Foreground/current page wins; previous and next stay near.
            items.getOrNull(index)?.let(::add)
            items.getOrNull(index - 1)?.let(::add)
            items.getOrNull(index + 1)?.let(::add)
            if (index + 2 <= last) {
                addAll(items.subList(index + 2, last + 1))
            }
            if (first <= index - 2) {
                addAll(items.subList(first, index - 1).asReversed())
            }
        }
            .rollingChunked(chunkStartSize, chunkEndSize)
            .also(onNewChunks)"""

OLD_CHUNKS = "pages.loadByRollingChunked(page.index, 3, 5) { chunks ->"
NEW_CHUNKS = "pages.loadByRollingChunked(page.index, 2, 3) { chunks ->"
OLD_LIMIT = "private const val LIMITED_PAGES_AHEAD = 4\n"
NEW_LIMIT = ("// Reader Performance 2.0: cap image prefetch to avoid long-chapter cache churn.\n"
             "private const val MAX_PAGES_AHEAD = 8\n"
             "private const val LIMITED_PAGES_AHEAD = 4\n")


class ReaderPerformanceError(RuntimeError):
    pass


def once(source: str, old: str, new: str, label: str) -> str:
    matches = source.count(old)
    if matches != 1:
        raise ReaderPerformanceError(f"{label}: expected 1 source marker, got {matches}")
    return source.replace(old, new, 1)


def patch_source(source: str) -> str:
    # Expect existing cancellation, retry and queue semantics from trusted baseline.
    for marker in (
        "withOneTransientRetry { source.getPageList(chapter.chapter.toSChapter()) }",
        "withOneTransientRetry { source.getImageUrl(page) }",
        "chapterCache.putImageToCache(imageUrl, imageResponse)",
        "if (e is CancellationException) {",
        "downloadJobs.putIfAbsent(pageIndex, job)",
        "private fun <T> List<T>.rollingChunked(",
    ):
        if marker not in source:
            raise ReaderPerformanceError(f"Reader safety contract missing: {marker}")
    source = once(source, OLD_PLAN, NEW_PLAN, "bounded reader prefetch")
    source = once(source, OLD_CHUNKS, NEW_CHUNKS, "background concurrency")
    source = once(source, OLD_LIMIT, NEW_LIMIT, "bounded read-ahead constant")
    return source


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file() or not (root / "gradlew").is_file():
        raise ReaderPerformanceError("Pinned Android engine and license required")
    file = root / HTTP_LOADER
    if not file.is_file():
        raise ReaderPerformanceError("Native HTTP reader file missing")
    original = file.read_text(encoding="utf-8")
    result = patch_source(original)
    if result == original:
        raise ReaderPerformanceError("No reader change was made")
    file.write_text(result, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
