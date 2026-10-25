#!/usr/bin/env python3
"""Persist the existing bounded HTTP 429 cooldown with Android WorkManager.

Apply after sequential_cooldown.py, on Mihon source already patched by Seiryn.
The same unique DownloadWorker is used, so explicit Pause/Clear cancels it.
"""
import argparse
from pathlib import Path

DOWNLOADER = "app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt"
WORKER = "app/src/main/java/eu/kanade/tachiyomi/data/download/DownloadWorker.kt"


class PersistedCooldownPatchError(RuntimeError):
    pass


def once(text, before, after, label):
    occurrences = text.count(before)
    if occurrences != 1:
        raise PersistedCooldownPatchError(
            f"{label}: expected one pinned Kotlin marker, found {occurrences}"
        )
    return text.replace(before, after, 1)


def downloader(source: str) -> str:
    source = once(source,
        """    private val seirynRateLimitAttempts = java.util.concurrent.atomic.AtomicInteger(0)
    private var seirynRateLimitResumeJob: Job? = null
    @Volatile private var seirynUserPausedRateLimit = false""",
        """    private val seirynRateLimitPrefs = context.getSharedPreferences(
        "seiryn_rate_limit_cooldown", Context.MODE_PRIVATE,
    )
    private val seirynRateLimitAttempts = java.util.concurrent.atomic.AtomicInteger(
        seirynRateLimitPrefs.getInt("consecutive_429", 0),
    )
    @Volatile private var seirynUserPausedRateLimit = false""",
        "persist bounded attempt count across process death")
    source = once(source,
        "            val minutes = when (seirynRateLimitAttempts.incrementAndGet()) {",
        """            val attempt = seirynRateLimitAttempts.incrementAndGet()
            seirynRateLimitPrefs.edit().putInt("consecutive_429", attempt).apply()
            val minutes = when (attempt) {""",
        "persist each HTTP 429")
    source = once(source,
        """            seirynRateLimitResumeJob?.cancel()
            seirynRateLimitResumeJob = scope.launch(Dispatchers.Main) {
                delay(minutes * 60_000L)
                // An explicit Pause/Clear cancels this job. Worker start
                // retains the existing Android network / Wi-Fi restrictions.
                if (!seirynUserPausedRateLimit && queueState.value.isNotEmpty() && !isRunning) {
                    DownloadWorker.start(context)
                }
            }""",
        """            // WorkManager preserves the delayed request across process
            // death and reuses the original network and Wi-Fi restrictions.
            if (!seirynUserPausedRateLimit) {
                DownloadWorker.scheduleRateLimitResume(context, minutes)
            }""",
        "durable unique cooldown")
    source = once(source,
        """        seirynUserPausedRateLimit = true
        seirynRateLimitResumeJob?.cancel()
        seirynRateLimitResumeJob = null""",
        """        // DownloadManager.pauseDownloads/clearQueue also cancels
        // the matching unique WorkManager request.
        seirynUserPausedRateLimit = true""",
        "manual pause cancellation")
    source = once(source,
        """        seirynRateLimitAttempts.set(0)
        seirynUserPausedRateLimit = false
        seirynRateLimitResumeJob?.cancel()
        seirynRateLimitResumeJob = null""",
        """        seirynRateLimitAttempts.set(0)
        seirynRateLimitPrefs.edit().remove("consecutive_429").apply()
        seirynUserPausedRateLimit = false""",
        "explicit user restart reset")
    source = once(source,
        """            seirynRateLimitAttempts.set(0)
            download.status = Download.State.DOWNLOADED""",
        """            seirynRateLimitAttempts.set(0)
            seirynRateLimitPrefs.edit().remove("consecutive_429").apply()
            download.status = Download.State.DOWNLOADED""",
        "successful chapter resets persisted backoff")
    return source


def worker(source: str) -> str:
    return once(source,
        """        fun isRunningFlow(context: Context): Flow<Boolean> {""",
        """        // A unique, durable delayed worker replaces the active worker
        // only after downloader.pause() has stopped the image requests.
        // Android WorkManager enforces the delay, surviving process death.
        fun scheduleRateLimitResume(context: Context, minutes: Long) {
            require(minutes in 15L..60L)
            val request = OneTimeWorkRequestBuilder<DownloadWorker>()
                .setInitialDelay(minutes, TimeUnit.MINUTES)
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build(),
                )
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30L, TimeUnit.SECONDS)
                .addTag(TAG)
                .build()
            WorkManager.getInstance(context)
                .enqueueUniqueWork(TAG, ExistingWorkPolicy.REPLACE, request)
        }

        fun isRunningFlow(context: Context): Flow<Boolean> {""",
        "schedule durable cooldown using the same unique work tag")


def patch(root: Path):
    root = root.resolve()
    originals = {}
    for path in (DOWNLOADER, WORKER):
        target = root / path
        if not target.is_file():
            raise PersistedCooldownPatchError("Missing pinned " + path)
        originals[path] = target.read_text(encoding="utf-8")
    transformed = {
        DOWNLOADER: downloader(originals[DOWNLOADER]),
        WORKER: worker(originals[WORKER]),
    }
    for path in (DOWNLOADER, WORKER):
        (root / path).write_text(transformed[path], encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
