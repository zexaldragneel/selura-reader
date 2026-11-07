"""Contracts for network-aware resumption of the user's existing download queue."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wifi_auto_resume", ROOT / "wifi_auto_resume.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

WORKER = """class DownloadWorker {
    companion object {
        fun start(context: Context) {
            val request = OneTimeWorkRequestBuilder<DownloadWorker>()
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

        fun cancel(context: Context) {}
        fun scheduleRateLimitResume(context: Context, minutes: Long) {
            // Honor an explicit Retry-After between 1 minute and 24h.
            require(minutes in 1L..1440L)
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

        fun isRunningFlow(context: Context) {}
    }
}
"""
MANAGER = """class DownloadManager {
    private val downloadPreferences: DownloadPreferences = TODO()
    fun startDownloads() {
        DownloadWorker.start(context)
    }
}
"""
DOWNLOADER = """class Downloader {
    private val downloadPreferences: DownloadPreferences = TODO()
    fun cooldown() {
        DownloadWorker.scheduleRateLimitResume(context, minutes)
        DownloadWorker.scheduleRateLimitResume(context, minutes)
    }
}
"""


class WifiAutoResumeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for path, source in ((mod.WORKER, WORKER), (mod.MANAGER, MANAGER), (mod.DOWNLOADER, DOWNLOADER)):
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(source, encoding="utf-8")

    def test_queue_and_rate_limit_workers_wait_for_unmetered_network_when_wifi_only(self):
        mod.apply(self.root)
        worker = (self.root / mod.WORKER).read_text(encoding="utf-8")
        self.assertEqual(worker.count("if (wifiOnly) NetworkType.UNMETERED else NetworkType.CONNECTED"), 2)
        self.assertEqual(worker.count("NetworkType.CONNECTED"), 2)
        self.assertEqual(worker.count("NetworkType.UNMETERED"), 2)
        self.assertIn("BackoffPolicy.EXPONENTIAL", worker)
        self.assertIn("ExistingWorkPolicy.REPLACE", worker)

    def test_existing_user_preference_drives_queue_and_cooldown_resume(self):
        mod.apply(self.root)
        manager = (self.root / mod.MANAGER).read_text(encoding="utf-8")
        downloader = (self.root / mod.DOWNLOADER).read_text(encoding="utf-8")
        pref = "downloadPreferences.downloadOnlyOverWifi.get()"
        self.assertIn(f"DownloadWorker.start(context, {pref})", manager)
        self.assertEqual(downloader.count(f"scheduleRateLimitResume(context, minutes, {pref})"), 2)

    def test_fail_closed_and_no_partial_changes(self):
        (self.root / mod.DOWNLOADER).write_text("unexpected", encoding="utf-8")
        before = (self.root / mod.WORKER).read_text(encoding="utf-8")
        with self.assertRaises(mod.WifiResumeError):
            mod.apply(self.root)
        self.assertEqual((self.root / mod.WORKER).read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
