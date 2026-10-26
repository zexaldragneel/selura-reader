"""Privacy-safe HTTP 429 origin and Retry-After source-patch tests."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("http429_stage_diagnostics", ROOT / "http429_stage_diagnostics.py")
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)

H = 'class HttpException(val code: Int) : IllegalStateException("HTTP error $code")'
EXT = '''val jsonMime = "application/json; charset=utf-8".toMediaType()
throw HttpException(response.code)
throw HttpException(response.code)
'''
D = '''    private fun requestRateLimitPause(error: Throwable) {
                                recordPageDownloadFailure(download, page.number, e)
                                requestRateLimitPause(e)
                                page.status = Page.State.Error(e)
            download.failureReason = describeDownloadFailure(error)
            requestRateLimitPause(error)
            download.status = Download.State.ERROR
            recordPageDownloadFailure(download, page.number, e)
            requestRateLimitPause(e)
            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)
            val minutes = when (attempt) {
                1 -> 15L
                2 -> 30L
                3 -> 60L
                else -> null
            }
            notifier.onWarning(
                "Source returned HTTP 429. Cooling down for " + minutes +
                    " minutes, then automatically resuming the saved queue.",
            )
'''
W = "            require(minutes in 15L..60L)"


class Http429Tests(unittest.TestCase):
    def test_preserves_http_exception_binary_constructor_and_error_codes(self):
        actual = fix.http_exception(H)
        self.assertIn('class HttpException(val code: Int)', actual)
        self.assertIn('var retryAfterSeconds: Long? = null', actual)
        self.assertNotIn('class HttpException(\n', actual)
        self.assertNotIn('token', actual.lower())
        with self.assertRaises(fix.RateLimitStagePatchError):
            fix.http_exception(actual)

    def test_read_retry_after_from_real_failure_response_without_sensitive_data(self):
        actual = fix.http_extensions(EXT)
        self.assertEqual(actual.count('throw response.toSeirynHttpException()'), 2)
        self.assertIn('header("Retry-After")?.trim()?.toLongOrNull()', actual)
        self.assertIn('?.takeIf { it in 0L..86_400L }', actual)
        self.assertIn('HttpException(code).apply { retryAfterSeconds = retrySeconds }', actual)
        for private_data in ('request.url', 'cookie', 'Authorization', 'queryParameter', 'body.string'):
            self.assertNotIn(private_data, actual)
        with self.assertRaises(fix.RateLimitStagePatchError):
            fix.http_extensions(actual)

    def test_three_source_stages_and_server_supplied_delay(self):
        actual = fix.downloader(D)
        for stage in ('image URL lookup', 'chapter page list', 'image transfer'):
            self.assertIn('"'+stage+'"', actual)
        self.assertEqual(actual.count('requestRateLimitPause('), 4)
        self.assertIn('httpError.retryAfterSeconds', actual)
        self.assertIn('((it + 59L) / 60L).coerceIn(1L, 1440L)', actual)
        self.assertIn('fallbackMinutes?.let { explicitMinutes ?: it }', actual)
        self.assertIn('if (minutes == null)', actual) if 'if (minutes == null)' in D else None
        self.assertIn('" (source Retry-After)"', actual)
        for forbidden in ('chain.proceed(', 'newRequest', 'rotateIp(', 'Proxy(', 'clearQueue()', 'sourceId ='):
            self.assertNotIn(forbidden, actual)
        self.assertNotIn('requestRateLimitPause(e)\n', actual)

    def test_worker_uses_persisted_unique_job_and_24_hour_cap(self):
        actual = fix.worker(W)
        self.assertIn('require(minutes in 1L..1440L)', actual)

    def test_missing_anchor_fails_closed_without_partial_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            specimens = {
                fix.HTTP_EXCEPTION: H,
                fix.HTTP_EXTENSIONS: EXT,
                fix.DOWNLOADER: D,
                fix.DOWNLOAD_WORKER: 'unexpected worker',
            }
            for path, source in specimens.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source)
            with self.assertRaises(fix.RateLimitStagePatchError):
                fix.patch(root)
            self.assertEqual((root / fix.DOWNLOADER).read_text(), D)
            (root / fix.DOWNLOAD_WORKER).write_text(W)
            fix.patch(root)
            self.assertIn('Retry-After', (root / fix.HTTP_EXTENSIONS).read_text())
            with self.assertRaises(fix.RateLimitStagePatchError):
                fix.patch(root)


if __name__ == "__main__":
    unittest.main()
