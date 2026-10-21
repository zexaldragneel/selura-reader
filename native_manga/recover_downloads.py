#!/usr/bin/env python3
"""Make Mihon's real download worker recover from network loss without losing its queue.

Apply after Selura's branding/reader/UI transforms to the pinned Mihon v0.21.2
source snapshot. This is a narrow worker-scheduling change, not an alternative
downloader or file-store rewrite. Every source replacement fails closed.
"""
import argparse
from pathlib import Path

WORKER = "app/src/main/java/eu/kanade/tachiyomi/data/download/DownloadWorker.kt"
MANAGER = "app/src/main/java/eu/kanade/tachiyomi/data/download/DownloadManager.kt"


class DownloadRecoveryError(RuntimeError):
    pass


def replace_once(source: str, old: str, new: str, name: str) -> str:
    matches = source.count(old)
    if matches != 1:
        raise DownloadRecoveryError(
            f"{name}: expected exactly one source marker; saw {matches}: {old[:95]!r}"
        )
    return source.replace(old, new, 1)


def patch(root: Path) -> None:
    root = root.resolve()
    originals = {}
    for path in (WORKER, MANAGER):
        target = root / path
        if not target.is_file():
            raise DownloadRecoveryError(f"Missing pinned download source: {path}")
        originals[path] = target.read_text(encoding="utf-8")

    changed = originals.copy()
    p = WORKER
    worker = changed[p]
    worker = replace_once(
        worker,
        "import androidx.work.CoroutineWorker\n",
        "import androidx.work.BackoffPolicy\n"
        "import androidx.work.Constraints\n"
        "import androidx.work.CoroutineWorker\n",
        p,
    )
    worker = replace_once(
        worker,
        "import androidx.work.OneTimeWorkRequestBuilder\n",
        "import androidx.work.NetworkType\n"
        "import androidx.work.OneTimeWorkRequestBuilder\n",
        p,
    )
    worker = replace_once(
        worker,
        "import kotlin.time.Duration.Companion.seconds\n",
        "import kotlin.time.Duration.Companion.seconds\n"
        "import java.util.concurrent.TimeUnit\n",
        p,
    )
    worker = replace_once(
        worker,
        """        if (networkIssue != null) {
            downloader.stop(networkIssue)
            return Result.failure()
        }""",
        """        if (networkIssue != null) {
            // Offline or Wi-Fi-only restriction: do not start a chapter on
            // the wrong network. WorkManager resumes this SAME persisted
            // queue with system-managed backoff after connectivity returns.
            downloader.stop(networkIssue)
            return Result.retry()
        }""",
        p,
    )
    worker = replace_once(
        worker,
        """        return Result.success()
    }

    private fun networkIssue()""",
        """        // Only connection/transport eligibility errors retry automatically.
        // Provider HTTP errors still follow Mihon's normal ERROR handling;
        // there is no aggressive retry loop or bypass of Wi-Fi-only policy.
        return if (networkIssue != null && !isStopped) Result.retry() else Result.success()
    }

    private fun networkIssue()""",
        p,
    )
    worker = replace_once(
        worker,
        """            val request = OneTimeWorkRequestBuilder<DownloadWorker>()
                .addTag(TAG)
                .build()""",
        """            val request = OneTimeWorkRequestBuilder<DownloadWorker>()
                // Network loss suspends the worker instead of permanently
                // failing the persisted queue; no cellular downloading is
                // permitted when DownloadPreferences.downloadOnlyOverWifi.
                .setConstraints(
                    Constraints.Builder()
                        .setRequiredNetworkType(NetworkType.CONNECTED)
                        .build(),
                )
                .setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30L, TimeUnit.SECONDS)
                .addTag(TAG)
                .build()""",
        p,
    )
    worker = replace_once(
        worker,
        """        fun isRunningFlow(context: Context): Flow<Boolean> {""",
        """        // Explicit user Pause / Clear means STOP; cancel any worker
        // waiting for network so it cannot silently resume later.
        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(TAG)
        }

        fun isRunningFlow(context: Context): Flow<Boolean> {""",
        p,
    )
    changed[p] = worker

    p = MANAGER
    manager = changed[p]
    manager = replace_once(
        manager,
        """    suspend fun pauseDownloads() {
        downloader.pause()
    }""",
        """    suspend fun pauseDownloads() {
        // Keep Mihon's current queue and completed page files, but prevent
        // the network-constrained retry worker from restarting after Pause.
        downloader.pause()
        DownloadWorker.cancel(context)
    }""",
        p,
    )
    manager = replace_once(
        manager,
        """    suspend fun clearQueue() {
        downloader.clearQueue()
        downloader.stop()
    }""",
        """    suspend fun clearQueue() {
        downloader.clearQueue()
        downloader.stop()
        // Clearing the queue also clears a previously scheduled retry.
        DownloadWorker.cancel(context)
    }""",
        p,
    )
    changed[p] = manager

    # Validate the entire patch before writing *any* file.
    for path, content in changed.items():
        if content == originals[path]:
            raise DownloadRecoveryError(f"No intended change to {path}")
    for path, content in changed.items():
        (root / path).write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)


if __name__ == "__main__":
    main()
