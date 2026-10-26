#!/usr/bin/env python3
"""Serialize native chapter/page requests and resume after respectful 429 cooldown.

Runs after rate_limit_pause.py against the pinned native Mihon source.
All source markers fail closed before writing either Kotlin file.
"""
import argparse
from pathlib import Path

DOWNLOADER = "app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt"
MANAGER = "app/src/main/java/eu/kanade/tachiyomi/data/download/DownloadManager.kt"


class SequentialCooldownPatchError(RuntimeError):
    pass


def once(source: str, before: str, after: str, description: str) -> str:
    count = source.count(before)
    if count != 1:
        raise SequentialCooldownPatchError(
            f"{description}: expected one audited Kotlin marker; found {count}"
        )
    return source.replace(before, after, 1)


OLD_HANDLER = """    // HTTP 429 is a rate-limit response, never a reason to rotate hosts,
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

NEW_HANDLER = """    // Bounded backoff for HTTP 429 only. No immediate network retries,
    // alternate CDNs, IP rotation, site restriction bypass, or busy loops.
    // Three consecutive rate-limit events use 15, 30 and 60 minute cooldowns.
    // Another 429 stops automatic attempts until the owner explicitly resumes.
    private fun requestRateLimitPause(error: Throwable) {
        val httpError = diagnosticCause(error) as? HttpException ?: return
        if (httpError.code != 429 || !seirynRateLimitPausePending.compareAndSet(false, true)) return
        scope.launch(Dispatchers.Main) {
            if (!isRunning || seirynUserPausedRateLimit) return@launch
            pause()
            if (seirynUserPausedRateLimit) return@launch
            val minutes = when (seirynRateLimitAttempts.incrementAndGet()) {
                1 -> 15L
                2 -> 30L
                3 -> 60L
                else -> null
            }
            if (minutes == null) {
                notifier.onWarning(
                    "Source still returns HTTP 429. Automatic downloads stopped. Resume manually after its limit clears.",
                )
                return@launch
            }
            notifier.onWarning(
                "Source returned HTTP 429. Cooling down for " + minutes +
                    " minutes, then automatically resuming the saved queue.",
            )
            seirynRateLimitResumeJob?.cancel()
            seirynRateLimitResumeJob = scope.launch(Dispatchers.Main) {
                delay(minutes * 60_000L)
                // An explicit Pause/Clear cancels this job. Worker start
                // retains the existing Android network / Wi-Fi restrictions.
                if (!seirynUserPausedRateLimit && queueState.value.isNotEmpty() && !isRunning) {
                    DownloadWorker.start(context)
                }
            }
        }
    }

    // Used only by the real user-facing Pause/Clear controls. A rate-limit
    // pause does NOT invoke this, so a scheduled cooldown can resume later.
    fun cancelRateLimitAutoResume() {
        seirynUserPausedRateLimit = true
        seirynRateLimitResumeJob?.cancel()
        seirynRateLimitResumeJob = null
    }

    fun resetRateLimitOnManualStart() {
        seirynRateLimitAttempts.set(0)
        seirynUserPausedRateLimit = false
        seirynRateLimitResumeJob?.cancel()
        seirynRateLimitResumeJob = null
    }

"""


def transform_downloader(source: str) -> str:
    source = once(
        source,
        "    private val seirynRateLimitPausePending = java.util.concurrent.atomic.AtomicBoolean(false)",
        "    private val seirynRateLimitPausePending = java.util.concurrent.atomic.AtomicBoolean(false)\n"
        "    private val seirynRateLimitAttempts = java.util.concurrent.atomic.AtomicInteger(0)\n"
        "    private var seirynRateLimitResumeJob: Job? = null\n"
        "    @Volatile private var seirynUserPausedRateLimit = false",
        "cooldown state",
    )
    source = once(
        source,
        "                        .take(parallelCount)",
        "                        // One source / chapter at a time, even if the\n"
        "                        // parallel-sources setting is greater than one.\n"
        "                        .take(1)",
        "one active source",
    )
    source = once(
        source,
        "        val slots = Semaphore(downloadPreferences.parallelPageLimit.get())",
        "        // One page request at a time to reduce load on image hosts.\n"
        "        val slots = Semaphore(1)",
        "one active page",
    )
    source = once(
        source,
        "            pagesStarted.await()\n        }\n    }\n\n    private fun CoroutineScope.launchDownloadJob(",
        "            pagesStarted.await()\n"
        "            // Do not start the NEXT chapter until this one has\n"
        "            // finished every page, integrity check, and archive write.\n"
        "            job.join()\n"
        "        }\n    }\n\n    private fun CoroutineScope.launchDownloadJob(",
        "one fully finished chapter at a time",
    )
    source = once(source, OLD_HANDLER, NEW_HANDLER, "replace manual-only 429 pause")
    source = once(
        source,
        "            download.status = Download.State.DOWNLOADED\n        } catch (error: Throwable) {",
        "            // A completed verified chapter is genuine progress; reset\n"
        "            // consecutive 429 cooldown escalation for following chapters.\n"
        "            seirynRateLimitAttempts.set(0)\n"
        "            download.status = Download.State.DOWNLOADED\n"
        "        } catch (error: Throwable) {",
        "reset cooldown escalation only after completed chapter",
    )
    return source


def transform_manager(source: str) -> str:
    source = once(
        source,
        """    fun startDownloads() {
        if (downloader.isRunning) return

        DownloadWorker.start(context)
    }""",
        """    fun startDownloads() {
        if (downloader.isRunning) return

        // Explicit user queue start cancels a pending cooldown in favor of
        // the user's chosen action. This cannot run from our timer, which
        // starts DownloadWorker directly after its own cooldown.
        downloader.resetRateLimitOnManualStart()
        DownloadWorker.start(context)
    }""",
        "manual start",
    )
    source = once(
        source,
        """    suspend fun pauseDownloads() {
        // Keep Mihon's current queue and completed page files, but prevent
        // the network-constrained retry worker from restarting after Pause.
        downloader.pause()
        DownloadWorker.cancel(context)
    }""",
        """    suspend fun pauseDownloads() {
        // Explicit Pause is authoritative and also cancels our cooldown.
        downloader.cancelRateLimitAutoResume()
        downloader.pause()
        DownloadWorker.cancel(context)
    }""",
        "explicit pause cancels timer",
    )
    source = once(
        source,
        """    suspend fun clearQueue() {
        downloader.clearQueue()
        downloader.stop()
        // Clearing the queue also clears a previously scheduled retry.
        DownloadWorker.cancel(context)
    }""",
        """    suspend fun clearQueue() {
        downloader.cancelRateLimitAutoResume()
        downloader.clearQueue()
        downloader.stop()
        // Clearing the queue also clears a previously scheduled retry.
        DownloadWorker.cancel(context)
    }""",
        "explicit queue clear cancels timer",
    )
    return source


def patch(root: Path) -> None:
    root = root.resolve()
    original = {}
    for path in (DOWNLOADER, MANAGER):
        full = root / path
        if not full.is_file():
            raise SequentialCooldownPatchError(f"Missing pinned source {path}")
        original[path] = full.read_text(encoding="utf-8")
    changed = {
        DOWNLOADER: transform_downloader(original[DOWNLOADER]),
        MANAGER: transform_manager(original[MANAGER]),
    }
    if any(changed[p] == original[p] for p in original):
        raise SequentialCooldownPatchError("Expected changes not applied")
    for path in (DOWNLOADER, MANAGER):
        (root / path).write_text(changed[path], encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
