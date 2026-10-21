"""Regression checks for native Mihon WorkManager download-network recovery."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "selura_download_recovery", ROOT / "recover_downloads.py"
)
recovery = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recovery)


WORKER = """package eu.kanade.tachiyomi.data.download
import androidx.work.CoroutineWorker
import androidx.work.OneTimeWorkRequestBuilder
import kotlin.time.Duration.Companion.seconds

class DownloadWorker {
    override suspend fun doWork(): Result {
        var networkIssue = networkIssue()
        if (networkIssue != null) {
            downloader.stop(networkIssue)
            return Result.failure()
        }
        if (!downloader.start()) return Result.failure()
        try {
            while (networkIssue == null && downloader.isRunning) {
                networkIssue = networkIssue()
            }
        } finally {
            if (downloader.isRunning && (networkIssue != null || isStopped)) {
                withContext(NonCancellable) { downloader.stop(networkIssue) }
            }
        }
        return Result.success()
    }

    private fun networkIssue(): String? {
        val state = applicationContext.activeNetworkState()
        return when {
            !state.isOnline -> applicationContext.getString(R.string.download_notifier_no_network)
            downloadPreferences.downloadOnlyOverWifi.get() && !state.isWifi ->
                applicationContext.getString(R.string.download_notifier_text_only_wifi)
            else -> null
        }
    }

    companion object {
        private const val TAG = "Downloader"

        fun start(context: Context) {
            val request = OneTimeWorkRequestBuilder<DownloadWorker>()
                .addTag(TAG)
                .build()
            WorkManager.getInstance(context)
                .enqueueUniqueWork(TAG, ExistingWorkPolicy.REPLACE, request)
        }

        fun isRunningFlow(context: Context): Flow<Boolean> {
            return WorkManager.getInstance(context)
                .getWorkInfosForUniqueWorkLiveData(TAG)
                .asFlow()
                .map { list -> list.count { it.state == WorkInfo.State.RUNNING } == 1 }
        }
    }
}
"""

MANAGER = """package eu.kanade.tachiyomi.data.download
class DownloadManager {
    suspend fun pauseDownloads() {
        downloader.pause()
    }

    suspend fun clearQueue() {
        downloader.clearQueue()
        downloader.stop()
    }

    fun startDownloads() {
        if (downloader.isRunning) return
        DownloadWorker.start(context)
    }
}
"""


class DownloadRecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.original = {recovery.WORKER: WORKER, recovery.MANAGER: MANAGER}
        for relative, text in self.original.items():
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

    def read(self, path):
        return (self.root / path).read_text(encoding="utf-8")

    def test_offline_and_wifi_only_errors_retry_instead_of_losing_queue(self):
        recovery.patch(self.root)
        worker = self.read(recovery.WORKER)
        self.assertIn("return Result.retry()", worker)
        self.assertIn(
            "return if (networkIssue != null && !isStopped) Result.retry() else Result.success()",
            worker,
        )
        self.assertIn("!state.isOnline", worker)
        self.assertIn("downloadPreferences.downloadOnlyOverWifi.get() && !state.isWifi", worker)
        self.assertIn("if (!downloader.start()) return Result.failure()", worker)
        self.assertIn("downloader.stop(networkIssue)", worker)
        self.assertEqual(worker.count("return Result.retry()"), 1)
        self.assertNotIn("return Result.failure()\n        }\n", worker)

    def test_system_network_constraints_are_bounded_not_unrestricted(self):
        recovery.patch(self.root)
        worker = self.read(recovery.WORKER)
        for contract in (
            "NetworkType.CONNECTED",
            "BackoffPolicy.EXPONENTIAL",
            "30L, TimeUnit.SECONDS",
            "ExistingWorkPolicy.REPLACE",
            "cancelUniqueWork(TAG)",
            ".addTag(TAG)",
        ):
            self.assertIn(contract, worker)
        self.assertEqual(worker.count("setRequiredNetworkType("), 1)
        self.assertEqual(worker.count("setBackoffCriteria("), 1)
        self.assertNotIn("NetworkType.NOT_REQUIRED", worker)
        self.assertNotIn("while (true)", worker)

    def test_explicit_pause_and_clear_cancel_pending_recovery(self):
        recovery.patch(self.root)
        manager = self.read(recovery.MANAGER)
        self.assertIn("downloader.pause()\n        DownloadWorker.cancel(context)", manager)
        self.assertIn(
            "downloader.clearQueue()\n        downloader.stop()\n"
            "        // Clearing the queue also clears a previously scheduled retry.\n"
            "        DownloadWorker.cancel(context)",
            manager,
        )
        self.assertIn("DownloadWorker.start(context)", manager)
        self.assertEqual(manager.count("DownloadWorker.cancel(context)"), 2)
        self.assertNotIn("downloader.queueChapters", manager)

    def test_no_downloads_or_manga_ids_rewritten(self):
        script = (ROOT / "recover_downloads.py").read_text(encoding="utf-8")
        self.assertEqual({recovery.WORKER, recovery.MANAGER}, {
            "app/src/main/java/eu/kanade/tachiyomi/data/download/DownloadWorker.kt",
            "app/src/main/java/eu/kanade/tachiyomi/data/download/DownloadManager.kt",
        })
        for path in ("/ui/reader/", "/source/", "/library/", "/database/", "/migration/"):
            self.assertNotIn(path, script)
        for unsafe in ("deleteDownloaded", "removeChapter", "clearStorage", "File.delete("):
            self.assertNotIn(unsafe, script)

    def test_fail_closed_with_atomicity_and_no_double_patching(self):
        wrong = self.root / recovery.MANAGER
        wrong.write_text("new upstream shape", encoding="utf-8")
        with self.assertRaises(recovery.DownloadRecoveryError):
            recovery.patch(self.root)
        self.assertEqual(self.read(recovery.WORKER), WORKER)
        wrong.write_text(MANAGER, encoding="utf-8")
        recovery.patch(self.root)
        after_worker = self.read(recovery.WORKER)
        with self.assertRaises(recovery.DownloadRecoveryError):
            recovery.patch(self.root)
        self.assertEqual(self.read(recovery.WORKER), after_worker)


if __name__ == "__main__":
    unittest.main()
