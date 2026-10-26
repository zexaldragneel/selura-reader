#!/usr/bin/env python3
"""Respect transient HTTP 503 while preserving the current chapter and its pages.

Apply AFTER http429_stage_diagnostics.py on pinned Mihon v0.21.2. This extends
the existing once-per-session 429 guard and the same unique WorkManager worker.
One paused chapter remains in queue; scheduled retry resumes that chapter first.
"""
import argparse
from pathlib import Path

DOWNLOADER = Path("app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt")


class Http503RecoveryPatchError(RuntimeError):
    pass


def once(source: str, before: str, after: str, label: str) -> str:
    count = source.count(before)
    if count != 1:
        raise Http503RecoveryPatchError(
            f"{label}: expected one pinned Kotlin anchor; found {count}"
        )
    return source.replace(before, after, 1)


RECOVERY = """    // After exhausting existing 503 page retries, suspend the ENTIRE queue
    // instead of skipping past the unfinished chapter. WorkManager resumes
    // that first queued chapter without discarding any already-saved pages.
    // This does not run for HTTP 429, authentication denial or other errors.
    private fun requestServiceUnavailablePause(error: HttpException, stage: String) {
        if (!seirynRateLimitPausePending.compareAndSet(false, true)) return
        scope.launch(Dispatchers.Main) {
            if (!isRunning || seirynUserPausedRateLimit) return@launch
            pause()
            if (seirynUserPausedRateLimit) return@launch
            val attempt = seirynHttp503Attempts.incrementAndGet()
            seirynRateLimitPrefs.edit().putInt("consecutive_503", attempt).apply()
            // Small, bounded delays for a temporarily unavailable source.
            // No tight loops or unbounded polling when a host is offline.
            val fallbackMinutes = when (attempt) {
                1 -> 1L
                2 -> 2L
                3 -> 5L
                else -> null
            }
            if (fallbackMinutes == null) {
                notifier.onWarning(
                    "Source still returns HTTP 503 during " + stage +
                        ". Automatic recovery stopped; queued chapters and pages kept.",
                )
                return@launch
            }
            // A server-supplied Retry-After is a minimum, never overridden
            // by the shorter local recovery delay. Original HTTP ABI intact.
            val serverMinutes = error.retryAfterSeconds?.let {
                ((it + 59L) / 60L).coerceIn(1L, 1440L)
            }
            val minutes = maxOf(fallbackMinutes, serverMinutes ?: fallbackMinutes)
            notifier.onWarning(
                "HTTP 503 during " + stage + ". Retrying the saved chapter after " +
                    minutes + " minute(s); download queue preserved.",
            )
            DownloadWorker.scheduleRateLimitResume(context, minutes)
        }
    }

"""


def transform(source: str) -> str:
    source = once(
        source,
        """    private val seirynRateLimitAttempts = java.util.concurrent.atomic.AtomicInteger(
        seirynRateLimitPrefs.getInt("consecutive_429", 0),
    )""",
        """    private val seirynRateLimitAttempts = java.util.concurrent.atomic.AtomicInteger(
        seirynRateLimitPrefs.getInt("consecutive_429", 0),
    )
    private val seirynHttp503Attempts = java.util.concurrent.atomic.AtomicInteger(
        seirynRateLimitPrefs.getInt("consecutive_503", 0),
    )""",
        "persist separate 503 recovery budget",
    )
    source = once(
        source,
        "    private fun requestRateLimitPause(error: Throwable, stage: String) {",
        RECOVERY + "    private fun requestRateLimitPause(error: Throwable, stage: String) {",
        "add bounded 503 recovery handler",
    )
    source = once(
        source,
        """        val httpError = diagnosticCause(error) as? HttpException ?: return
        if (httpError.code != 429 || !seirynRateLimitPausePending.compareAndSet(false, true)) return""",
        """        val httpError = diagnosticCause(error) as? HttpException ?: return
        if (httpError.code == 503) {
            requestServiceUnavailablePause(httpError, stage)
            return
        }
        if (httpError.code != 429 || !seirynRateLimitPausePending.compareAndSet(false, true)) return""",
        "route 503 only after existing transient retries",
    )
    # Reset only after a completed, verified chapter or explicit user start.
    source = once(
        source,
        """        seirynRateLimitAttempts.set(0)
        seirynRateLimitPrefs.edit().remove("consecutive_429").apply()
        seirynUserPausedRateLimit = false""",
        """        seirynRateLimitAttempts.set(0)
        seirynRateLimitPrefs.edit().remove("consecutive_429").apply()
        seirynHttp503Attempts.set(0)
        seirynRateLimitPrefs.edit().remove("consecutive_503").apply()
        seirynUserPausedRateLimit = false""",
        "reset 503 recovery on owner manual restart",
    )
    source = once(
        source,
        """            seirynRateLimitAttempts.set(0)
            seirynRateLimitPrefs.edit().remove("consecutive_429").apply()
            download.status = Download.State.DOWNLOADED""",
        """            seirynRateLimitAttempts.set(0)
            seirynRateLimitPrefs.edit().remove("consecutive_429").apply()
            seirynHttp503Attempts.set(0)
            seirynRateLimitPrefs.edit().remove("consecutive_503").apply()
            download.status = Download.State.DOWNLOADED""",
        "reset 503 recovery only on verified completed chapter",
    )
    return source


def patch(root: Path) -> None:
    target = root.resolve() / DOWNLOADER
    if not target.is_file():
        raise Http503RecoveryPatchError("Missing pinned downloader")
    original = target.read_text(encoding="utf-8")
    transformed = transform(original)
    if original == transformed:
        raise Http503RecoveryPatchError("No intended changes")
    target.write_text(transformed, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
