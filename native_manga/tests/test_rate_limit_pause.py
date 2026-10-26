"""Guard non-destructive, owner-controlled pause on source HTTP 429."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("seiryn_rate_limit_pause", ROOT / "rate_limit_pause.py")
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)

SOURCE = """class Downloader {
    private val lock = Mutex()
    private fun startLocked(): Boolean {
        isPaused = false

        launchDownloaderJob()
        return true
    }
    private suspend fun downloadChapter() {
                            } catch (e: Throwable) {
                                if (e is CancellationException) throw e
                                recordPageDownloadFailure(download, page.number, e)
                                page.status = Page.State.Error(e)
                            }
        } catch (error: Throwable) {
            logcat(LogPriority.ERROR, error)
            download.failureReason = describeDownloadFailure(error)
            download.status = Download.State.ERROR
            notifier.onError(error.message, download.chapter.name, download.manga.title, download.manga.id)
        }
    }
    private suspend fun getOrDownloadImage() {
        } catch (e: Throwable) {
            page.progress = 0
            page.status = Page.State.Error(e)
            recordPageDownloadFailure(download, page.number, e)
            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)
        }
    }
    // Follow a bounded error cause chain, without exposing raw URLs,
    private fun diagnosticCause(error: Throwable): Throwable = error
}
"""


class RateLimitPauseTests(unittest.TestCase):
    def test_only_429_requests_queue_pause_once_per_session(self):
        updated = fix.transform(SOURCE)
        self.assertIn("httpError.code != 429", updated)
        self.assertIn("as? HttpException ?: return", updated)
        self.assertIn("compareAndSet(false, true)", updated)
        self.assertIn("seirynRateLimitPausePending.set(false)", updated)
        self.assertIn("scope.launch(Dispatchers.Main)", updated)
        self.assertIn("if (isRunning)", updated)
        self.assertIn("pause()", updated)
        self.assertIn("Resume manually later.", updated)
        self.assertEqual(updated.count("requestRateLimitPause(e)"), 2)
        self.assertEqual(updated.count("requestRateLimitPause(error)"), 1)

    def test_all_error_paths_remain_nondestructive_without_request_amplification(self):
        updated = fix.transform(SOURCE)
        for path in (
            "recordPageDownloadFailure(download, page.number, e)",
            "download.failureReason = describeDownloadFailure(error)",
            "page.status = Page.State.Error(e)",
            "notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)",
        ):
            self.assertIn(path, updated)
        for forbidden in (
            "Retry-After", "delay(", "while (true)", "retryWhen",
            "chain.proceed(", "clearQueue()", "delete()", "removeFromQueue(",
            "startDownloadNow(", "startLocked() // auto", "Cloudflare", "setCookie(",
        ):
            self.assertNotIn(forbidden, updated)
        self.assertEqual(updated.count("launchDownloaderJob()"), 1)
        self.assertNotIn("com.selura.manga", updated)
        self.assertNotIn("5690172267177159639", updated)

    def test_patch_fails_closed_on_pinned_source_drift_and_second_execution(self):
        for missing in (
            "    private val lock = Mutex()",
            "        isPaused = false\n\n        launchDownloaderJob()",
            "            recordPageDownloadFailure(download, page.number, e)\n"
            "            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)",
        ):
            with self.subTest(missing=missing), self.assertRaises(fix.RateLimitPausePatchError):
                fix.transform(SOURCE.replace(missing, ""))
        with self.assertRaises(fix.RateLimitPausePatchError):
            fix.transform(fix.transform(SOURCE))

    def test_patch_is_one_file_and_preserves_old_text_on_failed_preflight(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / fix.DOWNLOADER
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(SOURCE)
            fix.patch(Path(tmp))
            self.assertIn("requestRateLimitPause", file.read_text())
            snapshot = file.read_text()
            with self.assertRaises(fix.RateLimitPausePatchError):
                fix.patch(Path(tmp))
            self.assertEqual(file.read_text(), snapshot)
            self.assertEqual(fix.DOWNLOADER, "app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt")


if __name__ == "__main__":
    unittest.main()
