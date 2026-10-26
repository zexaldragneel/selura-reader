"""Regression tests for bounded HTTP 503 recovery while keeping partial chapter data."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("http503_recovery", ROOT / "http503_chapter_recovery.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

DOWNLOADER = """class Downloader {
    private val seirynRateLimitAttempts = java.util.concurrent.atomic.AtomicInteger(
        seirynRateLimitPrefs.getInt("consecutive_429", 0),
    )
    private fun requestRateLimitPause(error: Throwable, stage: String) {
        val httpError = diagnosticCause(error) as? HttpException ?: return
        if (httpError.code != 429 || !seirynRateLimitPausePending.compareAndSet(false, true)) return
        scope.launch(Dispatchers.Main) {
            if (!isRunning) return@launch
            pause()
        }
    }

    fun resetRateLimitOnManualStart() {
        seirynRateLimitAttempts.set(0)
        seirynRateLimitPrefs.edit().remove("consecutive_429").apply()
        seirynUserPausedRateLimit = false
    }

    fun completedChapter() {
            seirynRateLimitAttempts.set(0)
            seirynRateLimitPrefs.edit().remove("consecutive_429").apply()
            download.status = Download.State.DOWNLOADED
    }
}
"""


class Http503RecoveryTests(unittest.TestCase):
    def test_503_pauses_current_chapter_with_bounded_delayed_resume(self):
        out = mod.transform(DOWNLOADER)
        for expected in (
            'if (httpError.code == 503)',
            'requestServiceUnavailablePause(httpError, stage)',
            'compareAndSet(false, true)',
            'scope.launch(Dispatchers.Main)',
            'pause()',
            'DownloadWorker.scheduleRateLimitResume(context, minutes)',
            'val fallbackMinutes = when (attempt)',
            '1 -> 1L', '2 -> 2L', '3 -> 5L', 'else -> null',
            'serverMinutes = error.retryAfterSeconds',
            'val minutes = maxOf(fallbackMinutes, serverMinutes ?: fallbackMinutes)',
            'seirynRateLimitPrefs.getInt("consecutive_503", 0)',
        ):
            self.assertIn(expected, out)
        self.assertIn('if (httpError.code != 429', out)
        self.assertEqual(out.count('requestRateLimitPause(error: Throwable, stage: String)'), 1)
        self.assertIn('queued chapters and pages kept', out)

    def test_manual_restart_and_verified_success_reset_persisted_503_budget(self):
        out = mod.transform(DOWNLOADER)
        self.assertEqual(out.count('seirynHttp503Attempts.set(0)'), 2)
        self.assertEqual(out.count('remove("consecutive_503").apply()'), 2)
        self.assertIn('download.status = Download.State.DOWNLOADED', out)
        self.assertNotIn('clearQueue()', out)
        self.assertNotIn('delete()', out)
        self.assertNotIn('manga.source =', out)
        self.assertNotIn('chain.proceed(', out)
        self.assertNotIn('retryWhen', out)
        self.assertNotIn('Cloudflare', out)
        self.assertNotIn('while (true)', out)

    def test_invalid_or_missing_contract_fails_closed_and_preserves_original_file(self):
        for missing in (
            'private fun requestRateLimitPause(error: Throwable, stage: String)',
            'seirynRateLimitPrefs.edit().remove("consecutive_429").apply()',
            'if (httpError.code != 429',
        ):
            with self.subTest(missing=missing), self.assertRaises(mod.Http503RecoveryPatchError):
                mod.transform(DOWNLOADER.replace(missing, 'missing'))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / mod.DOWNLOADER
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(DOWNLOADER)
            mod.patch(root)
            result = file.read_text()
            self.assertIn('requestServiceUnavailablePause(error: HttpException', result)
            with self.assertRaises(mod.Http503RecoveryPatchError):
                mod.patch(root)
            self.assertEqual(file.read_text(), result)


if __name__ == "__main__":
    unittest.main()
