#!/usr/bin/env python3
"""Resume the existing Mihon queue as soon as its allowed network returns.

Apply after persisted cooldown and the integrated Seiryn UI patch. When the
existing Download only over Wi-Fi setting is enabled, WorkManager waits for an
unmetered network; otherwise it keeps the normal connected-network behavior.
No queue, chapter, file, source ID or reading-progress data is rewritten.
"""
import argparse
from pathlib import Path

WORKER = "app/src/main/java/eu/kanade/tachiyomi/data/download/DownloadWorker.kt"
MANAGER = "app/src/main/java/eu/kanade/tachiyomi/data/download/DownloadManager.kt"
DOWNLOADER = "app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt"


class WifiResumeError(RuntimeError):
    pass


def once(source: str, before: str, after: str, label: str) -> str:
    count = source.count(before)
    if count != 1:
        raise WifiResumeError(f"{label}: expected one pinned marker; found {count}")
    return source.replace(before, after, 1)


def apply(root: Path) -> None:
    root = Path(root).resolve()
    paths = (WORKER, MANAGER, DOWNLOADER)
    originals = {}
    for relative in paths:
        file = root / relative
        if not file.is_file():
            raise WifiResumeError(f"Missing pinned download source: {relative}")
        originals[relative] = file.read_text(encoding="utf-8")

    worker = originals[WORKER]
    worker = once(
        worker,
        """        fun start(context: Context) {
            val request = OneTimeWorkRequestBuilder<DownloadWorker>()""",
        """        fun start(context: Context, wifiOnly: Boolean) {
            val request = OneTimeWorkRequestBuilder<DownloadWorker>()""",
        "Wi-Fi-aware queue worker signature",
    )
    connected = ".setRequiredNetworkType(NetworkType.CONNECTED)"
    if worker.count(connected) != 2:
        raise WifiResumeError("Expected exactly two connected-network constraints")
    worker = worker.replace(
        connected,
        ".setRequiredNetworkType(\n"
        "                            if (wifiOnly) NetworkType.UNMETERED else NetworkType.CONNECTED,\n"
        "                        )",
    )
    worker = once(
        worker,
        """        fun scheduleRateLimitResume(context: Context, minutes: Long) {
            // Honor an explicit Retry-After between 1 minute and 24h.""",
        """        fun scheduleRateLimitResume(context: Context, minutes: Long, wifiOnly: Boolean) {
            // Honor an explicit Retry-After between 1 minute and 24h.""",
        "cooldown worker Wi-Fi-aware signature",
    )
    manager = once(
        originals[MANAGER],
        "DownloadWorker.start(context)",
        "DownloadWorker.start(context, downloadPreferences.downloadOnlyOverWifi.get())",
        "manual queue start respects existing Wi-Fi preference",
    )

    downloader = originals[DOWNLOADER]
    call = "DownloadWorker.scheduleRateLimitResume(context, minutes)"
    count = downloader.count(call)
    if count != 2:
        raise WifiResumeError(f"Expected two rate-limit worker calls; found {count}")
    downloader = downloader.replace(
        call,
        "DownloadWorker.scheduleRateLimitResume(context, minutes, downloadPreferences.downloadOnlyOverWifi.get())",
    )

    changed = {WORKER: worker, MANAGER: manager, DOWNLOADER: downloader}
    for relative in paths:
        if changed[relative] == originals[relative]:
            raise WifiResumeError(f"No intended changes to {relative}")
    # Validate every file before writing any of them.
    for relative in paths:
        (root / relative).write_text(changed[relative], encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    apply(parser.parse_args().upstream)
