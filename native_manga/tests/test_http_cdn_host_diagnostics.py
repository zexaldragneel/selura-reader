"""Exact-source tests for hostname-only HTTP 429/503 diagnostics."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cdn_host", ROOT / "http_cdn_host_diagnostics.py")
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)

HE = """class HttpException(val code: Int) : IllegalStateException("HTTP error $code") {
    var retryAfterSeconds: Long? = null
}"""
EX = """private fun Response.toSeirynHttpException(): HttpException {
    val retrySeconds = header("Retry-After")?.trim()?.toLongOrNull()
        ?.takeIf { it in 0L..86_400L }
    return HttpException(code).apply { retryAfterSeconds = retrySeconds }
}"""
DL = """class Downloader {
            val minutes = maxOf(fallbackMinutes, serverMinutes ?: fallbackMinutes)
            notifier.onWarning(
                "HTTP 503 during " + stage + ". Retrying the saved chapter after " +
                    minutes + " minute(s); download queue preserved.",
            )
                notifier.onWarning(
                    "Source still returns HTTP 503 during " + stage +
                        ". Automatic recovery stopped; queued chapters and pages kept.",
                )
            notifier.onWarning(
                "HTTP 429 during " + stage + ". Waiting " + minutes +
                    " minutes" + reason + " before automatically resuming the saved queue.",
            )
}"""


class CdnHostTests(unittest.TestCase):
    def test_preserves_extension_abi_and_retry_after_metadata(self):
        result = fix.http_exception(HE)
        self.assertIn('class HttpException(val code: Int)', result)
        self.assertIn('var retryAfterSeconds: Long? = null', result)
        self.assertIn('var sourceHost: String? = null', result)
        self.assertNotIn("val url", result)
        self.assertNotIn("class HttpException(\n", result)
        with self.assertRaises(fix.CdnHostDiagnosticPatchError):
            fix.http_exception(result)

    def test_uses_actual_response_host_and_strict_safe_characters(self):
        result = fix.http_extensions(EX)
        self.assertIn("request.url.host.lowercase()", result)
        self.assertIn("host.length in 1..253", result)
        self.assertIn("sourceHost = failureHost", result)
        self.assertIn("retryAfterSeconds = retrySeconds", result)
        for forbidden in (
            "encodedPath", "encodedQuery", "Authorization", "Cookie",
            "request.url.toString()", "request.url.toString(", "response.body",
            "addInterceptor", "chain.proceed", "newCall(", "Proxy("
        ):
            self.assertNotIn(forbidden, result)
        with self.assertRaises(fix.CdnHostDiagnosticPatchError):
            fix.http_extensions(result)

    def test_notifications_include_safe_domain_without_changing_retries(self):
        result = fix.downloader(DL)
        self.assertIn('"HTTP 503" + safeHost + " during " + stage', result)
        self.assertIn('"HTTP 429" +', result)
        self.assertEqual(result.count('sourceHost?.let'), 3)
        self.assertIn('val minutes = maxOf(fallbackMinutes, serverMinutes ?: fallbackMinutes)', result)
        for forbidden in ('clearQueue(', 'retryWhen', 'while (true)', 'chain.proceed(', 'removeDownloads('):
            self.assertNotIn(forbidden, result)
        with self.assertRaises(fix.CdnHostDiagnosticPatchError):
            fix.downloader(result)

    def test_all_or_nothing_source_patch_and_fail_closed(self):
        originals = {
            fix.HTTP_EXCEPTION: HE, fix.HTTP_EXTENSIONS: EX, fix.DOWNLOADER: DL
        }
        result = fix.transform(originals)
        self.assertEqual(len(result), 3)
        with self.assertRaises(fix.CdnHostDiagnosticPatchError):
            fix.transform({**originals, fix.DOWNLOADER: "unknown"})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for p, content in originals.items():
                f = root / p
                f.parent.mkdir(parents=True, exist_ok=True)
                f.write_text(content, encoding="utf-8")
            fix.patch(root)
            self.assertIn('sourceHost', (root / fix.HTTP_EXCEPTION).read_text())
            with self.assertRaises(fix.CdnHostDiagnosticPatchError):
                fix.patch(root)


if __name__ == "__main__":
    unittest.main()
