#!/usr/bin/env python3
"""Apply fail-closed, non-destructive reader and extension reliability patches.

Runs AFTER native_manga/apply_branding.py on the exact Selura-owned Mihon
v0.21.2 snapshot. Never alters manga/source IDs, libraries or downloaded files.
"""
import argparse
from pathlib import Path

HTTP_LOADER = "app/src/main/java/eu/kanade/tachiyomi/ui/reader/loader/HttpPageLoader.kt"
CHAPTER_CACHE = "app/src/main/java/eu/kanade/tachiyomi/data/cache/ChapterCache.kt"
MAIN_ACTIVITY = "app/src/main/java/eu/kanade/tachiyomi/ui/main/MainActivity.kt"

class PatchContractError(RuntimeError):
    """Refuse unexpected source changes instead of silently dropping a fix."""


def exactly_once(source: str, old: str, new: str, filename: str) -> str:
    matches = source.count(old)
    if matches != 1:
        raise PatchContractError(
            f"{filename}: expected one occurrence of {old!r}, got {matches}"
        )
    return source.replace(old, new, 1)


def patch(root: Path) -> None:
    root = root.resolve()
    originals = {}
    for relative in (HTTP_LOADER, CHAPTER_CACHE, MAIN_ACTIVITY):
        target = root / relative
        if not target.is_file():
            raise PatchContractError(f"Missing Mihon source file: {relative}")
        originals[relative] = target.read_text(encoding="utf-8")
    changed = originals.copy()

    # Network timeouts and abrupt socket EOF may be temporary. One delayed
    # retry is enough; never retry HTTP status failures like 403/429, never
    # loop, and never hide cancellation. Existing per-source rate limits stand.
    p = HTTP_LOADER
    s = changed[p]
    s = exactly_once(s, "import kotlinx.coroutines.launch\n",
                     "import kotlinx.coroutines.launch\nimport kotlinx.coroutines.delay\n", p)
    s = exactly_once(s, "import java.util.concurrent.ConcurrentHashMap\n",
                     "import java.io.EOFException\nimport java.io.IOException\n"
                     "import java.net.ConnectException\nimport java.net.SocketTimeoutException\n"
                     "import java.util.concurrent.ConcurrentHashMap\n", p)
    s = exactly_once(s, "            source.getPageList(chapter.chapter.toSChapter())",
                     "            withOneTransientRetry { source.getPageList(chapter.chapter.toSChapter()) }", p)
    s = exactly_once(s, "                page.imageUrl = source.getImageUrl(page)",
                     "                page.imageUrl = withOneTransientRetry { source.getImageUrl(page) }", p)
    s = exactly_once(s, """                val imageResponse = source.getImage(page)
                chapterCache.putImageToCache(imageUrl, imageResponse)""",
                     """                withOneTransientRetry {
                    val imageResponse = source.getImage(page)
                    chapterCache.putImageToCache(imageUrl, imageResponse)
                }""", p)
    s = exactly_once(s, "    private suspend fun internalLoadPage(page: ReaderPage, force: Boolean = false) {",
                     """    // Only retry recoverable transport failures once. In particular, HTTP
    // 403/404/429 responses, Cloudflare challenges and source-defined errors
    // are NOT retried. Cancellations are not IOExceptions.
    private suspend fun <T> withOneTransientRetry(block: suspend () -> T): T {
        return try {
            block()
        } catch (error: IOException) {
            if (error !is SocketTimeoutException &&
                error !is ConnectException &&
                error !is EOFException
            ) {
                throw error
            }
            delay(450L)
            block()
        }
    }

    private suspend fun internalLoadPage(page: ReaderPage, force: Boolean = false) {""", p)
    changed[p] = s

    # The upstream 100 MiB rolling disk LRU can evict pages even during a
    # long, high-resolution chapter. 192 MiB is a moderate fixed limit; keep
    # the same disk cache directory, version and eviction implementation.
    p = CHAPTER_CACHE
    changed[p] = exactly_once(changed[p],
                              "private const val PARAMETER_CACHE_SIZE = 100L * 1024 * 1024",
                              "private const val PARAMETER_CACHE_SIZE = 192L * 1024 * 1024",
                              p)

    # Mihon already has trusted extension update discovery and notification.
    # Retain it; repeat while STARTED so users who read for days receive
    # update notifications. Never silently install third-party APKs.
    p = MAIN_ACTIVITY
    changed[p] = exactly_once(
        changed[p],
        """        // Extensions updates
        LaunchedEffect(Unit) {
            try {
                extensionManager.checkForUpdates()
            } catch (e: Exception) {
                logcat(LogPriority.ERROR, e)
            }
        }""",
        """        // Selura: check extension updates at startup AND during long
        // reading sessions, without repeatedly polling while backgrounded.
        // The native store signer checks and user-confirmed installer remain
        // unchanged. Twelve hours between checks while this process lives.
        LaunchedEffect(Unit) {
            var lastExtensionCheck: Long? = null
            lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
                while (true) {
                    lastExtensionCheck?.let {
                        delay(
                            (it + 12L * 60 * 60 * 1000 - SystemClock.elapsedRealtime())
                                .coerceAtLeast(0L),
                        )
                    }
                    lastExtensionCheck = SystemClock.elapsedRealtime()
                    try {
                        extensionManager.checkForUpdates()
                    } catch (e: CancellationException) {
                        throw e
                    } catch (e: Exception) {
                        logcat(LogPriority.ERROR, e)
                    }
                }
            }
        }""",
        p,
    )

    # Write only after every contract has passed to avoid half-patched builds.
    for relative, content in changed.items():
        if content == originals[relative]:
            raise PatchContractError(f"No changes made to {relative}")
    for relative, content in changed.items():
        (root / relative).write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)


if __name__ == "__main__":
    main()
