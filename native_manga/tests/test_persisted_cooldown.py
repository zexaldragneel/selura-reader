"""WorkManager persistence contracts for bounded 429 cooldown without rate-limit bypass."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("persisted_cooldown", ROOT / "persisted_cooldown.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DOWNLOADER = """class Downloader {
    private val seirynRateLimitAttempts = java.util.concurrent.atomic.AtomicInteger(0)
    private var seirynRateLimitResumeJob: Job? = null
    @Volatile private var seirynUserPausedRateLimit = false

    private fun requestRateLimitPause(error: Throwable) {
            val minutes = when (seirynRateLimitAttempts.incrementAndGet()) {
                1 -> 15L
                2 -> 30L
                3 -> 60L
                else -> null
            }
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
    fun chapterFinished() {
            seirynRateLimitAttempts.set(0)
            download.status = Download.State.DOWNLOADED
    }
}
"""

WORKER = """class DownloadWorker {
    companion object {
        private const val TAG = "Downloader"
        fun isRunningFlow(context: Context): Flow<Boolean> {
        }
        fun cancel(context: Context) {
            WorkManager.getInstance(context).cancelUniqueWork(TAG)
        }
    }
}
"""


class DurableCooldownTests(unittest.TestCase):
    def test_durable_cooldown_uses_existing_unique_worker_and_network_constraints(self):
        d = mod.downloader(DOWNLOADER)
        w = mod.worker(WORKER)
        self.assertIn("DownloadWorker.scheduleRateLimitResume(context, minutes)", d)
        self.assertNotIn("seirynRateLimitResumeJob", d)
        self.assertIn("seirynRateLimitPrefs.getInt", d)
        self.assertIn('putInt("consecutive_429", attempt)', d)
        self.assertEqual(d.count('remove("consecutive_429")'), 2)
        for fragment in (
            "require(minutes in 15L..60L)", ".setInitialDelay(minutes, TimeUnit.MINUTES)",
            "setRequiredNetworkType(NetworkType.CONNECTED)", "enqueueUniqueWork(TAG, ExistingWorkPolicy.REPLACE, request)",
            ".setBackoffCriteria(BackoffPolicy.EXPONENTIAL, 30L, TimeUnit.SECONDS)",
        ):
            self.assertIn(fragment, w)
        self.assertNotIn("Cloudflare", w)
        self.assertNotIn("alternateIp", w)
        self.assertNotIn("rotateIp", w)

    def test_explicit_user_pause_can_cancel_unique_work_without_erasing_queue(self):
        d = mod.downloader(DOWNLOADER)
        self.assertIn("seirynUserPausedRateLimit = true", d)
        self.assertIn("seirynUserPausedRateLimit = false", d)
        self.assertNotIn("clearQueue()", d)
        self.assertNotIn("delete()", d)
        self.assertNotIn("retryWhen", d)
        w = mod.worker(WORKER)
        self.assertIn("cancelUniqueWork(TAG)", w)
        self.assertEqual(w.count('private const val TAG = "Downloader"'), 1)

    def test_fails_closed_without_partial_write(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            for file, contents in ((mod.DOWNLOADER, DOWNLOADER), (mod.WORKER, "not pinned")):
                dest = root / file
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(contents)
            with self.assertRaises(mod.PersistedCooldownPatchError):
                mod.patch(root)
            self.assertEqual((root / mod.DOWNLOADER).read_text(), DOWNLOADER)
            (root / mod.WORKER).write_text(WORKER)
            mod.patch(root)
            self.assertIn("scheduleRateLimitResume", (root / mod.WORKER).read_text())
            after = (root / mod.DOWNLOADER).read_text()
            with self.assertRaises(mod.PersistedCooldownPatchError):
                mod.patch(root)
            self.assertEqual((root / mod.DOWNLOADER).read_text(), after)


if __name__ == "__main__":
    unittest.main()
