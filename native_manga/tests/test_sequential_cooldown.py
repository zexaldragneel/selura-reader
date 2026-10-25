"""Regression contracts for chapter-serial downloads and bounded HTTP 429 recovery."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("sequential_cooldown", ROOT / "sequential_cooldown.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DOWNLOADER = """class Downloader {
    private val seirynRateLimitPausePending = java.util.concurrent.atomic.AtomicBoolean(false)
                    val activeDownloads = queue.asSequence()
                        .filter { it.status.value <= Download.State.DOWNLOADING.value }
                        .groupBy { it.source }
                        .toList()
                        .take(parallelCount)
                        .map { (_, downloads) -> downloads.first() }
    private fun CoroutineScope.launchSourceJob() = launch(Dispatchers.IO) {
        val slots = Semaphore(downloadPreferences.parallelPageLimit.get())
        while (true) {
            val download = queueState.first()
            val pagesStarted = CompletableDeferred<Unit>()
            val job = launchDownloadJob(download, slots, pagesStarted, owner)
            downloadJobs[download] = job
            job.invokeOnCompletion {
                downloadJobs.remove(download, job)
                pagesStarted.complete(Unit)
            }
            pagesStarted.await()
        }
    }

    private fun CoroutineScope.launchDownloadJob(
        download: Download, slots: Semaphore, pagesStarted: CompletableDeferred<Unit>, owner: Job
    ) = launch(Dispatchers.IO) { }

    // HTTP 429 is a rate-limit response, never a reason to rotate hosts,
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

    fun finishDownload() {
            download.status = Download.State.DOWNLOADED
        } catch (error: Throwable) {
            throw error
        }
    }
}
"""

MANAGER = """class DownloadManager {
    fun startDownloads() {
        if (downloader.isRunning) return

        DownloadWorker.start(context)
    }
    suspend fun pauseDownloads() {
        // Keep Mihon's current queue and completed page files, but prevent
        // the network-constrained retry worker from restarting after Pause.
        downloader.pause()
        DownloadWorker.cancel(context)
    }
    suspend fun clearQueue() {
        downloader.clearQueue()
        downloader.stop()
        // Clearing the queue also clears a previously scheduled retry.
        DownloadWorker.cancel(context)
    }
}
"""


class SequentialTests(unittest.TestCase):
    def test_one_source_one_chapter_and_one_page_until_complete(self):
        actual = mod.transform_downloader(DOWNLOADER)
        self.assertIn(".take(1)", actual)
        self.assertNotIn(".take(parallelCount)", actual)
        self.assertIn("val slots = Semaphore(1)", actual)
        self.assertNotIn("val slots = Semaphore(downloadPreferences.parallelPageLimit.get())", actual)
        self.assertIn("pagesStarted.await()\n            // Do not start the NEXT chapter", actual)
        self.assertIn("job.join()", actual)
        self.assertLess(actual.index("pagesStarted.await()"), actual.index("job.join()"))
        self.assertEqual(actual.count("job.join()"), 1)

    def test_rate_limit_auto_resume_is_bounded_and_does_not_bypass(self):
        actual = mod.transform_downloader(DOWNLOADER)
        self.assertIn("httpError.code != 429", actual)
        self.assertIn("compareAndSet(false, true)", actual)
        self.assertIn("seirynRateLimitAttempts.incrementAndGet()", actual)
        for expected in ("1 -> 15L", "2 -> 30L", "3 -> 60L", "else -> null"):
            self.assertIn(expected, actual)
        self.assertIn("DownloadWorker.start(context)", actual)
        self.assertIn("delay(minutes * 60_000L)", actual)
        self.assertIn("seirynRateLimitAttempts.set(0)", actual)
        self.assertIn("queueState.value.isNotEmpty() && !isRunning", actual)
        self.assertIn("Source still returns HTTP 429. Automatic downloads stopped.", actual)
        for forbidden in (
            "chain.proceed(", "rotateIp", "cloudflare", "setCookie(",
            "newUrl", "clearQueue()", "delete()", "sourceId =",
            "manga.source =", "while (true)", "delay(0",
        ):
            self.assertNotIn(forbidden, actual.lower() if forbidden == "cloudflare" else actual)

    def test_user_pause_and_clear_cancel_pending_auto_resume(self):
        actual = mod.transform_manager(MANAGER)
        self.assertIn("downloader.resetRateLimitOnManualStart()", actual)
        self.assertEqual(actual.count("downloader.cancelRateLimitAutoResume()"), 2)
        self.assertIn("downloader.pause()\n        DownloadWorker.cancel(context)", actual)
        self.assertIn("downloader.clearQueue()", actual)
        self.assertIn("DownloadWorker.start(context)", actual)
        self.assertNotIn("manga.source =", actual)

    def test_contract_drift_never_partially_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for p, v in ((mod.DOWNLOADER, DOWNLOADER), (mod.MANAGER, "unexpected manager")):
                file = root / p
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(v)
            with self.assertRaises(mod.SequentialCooldownPatchError):
                mod.patch(root)
            self.assertEqual((root / mod.DOWNLOADER).read_text(), DOWNLOADER)
            (root / mod.MANAGER).write_text(MANAGER)
            mod.patch(root)
            result = (root / mod.DOWNLOADER).read_text()
            with self.assertRaises(mod.SequentialCooldownPatchError):
                mod.patch(root)
            self.assertEqual((root / mod.DOWNLOADER).read_text(), result)

    def test_missing_scheduler_anchor_fails_closed(self):
        for marker in (".take(parallelCount)", "            pagesStarted.await()",
                       "        val slots = Semaphore(downloadPreferences.parallelPageLimit.get())"):
            with self.subTest(marker=marker), self.assertRaises(mod.SequentialCooldownPatchError):
                mod.transform_downloader(DOWNLOADER.replace(marker, "broken"))


if __name__ == "__main__":
    unittest.main()
