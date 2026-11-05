"""Regression contracts for Performance 3.1 foreground-first prefetch."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / "reader_performance_v31.py"
spec = importlib.util.spec_from_file_location("reader_performance_v31", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

BASE = """MAX_PAGES_AHEAD = 8
logSlowReaderStage("page-image", startedAt, imageOrigin)
downloadJobs.putIfAbsent(pageIndex, job)
downloadJobs.remove(it)?.cancel()
withOneTransientRetry { source.getImageUrl(page) }
chapterCache.putImageToCache(imageUrl, imageResponse)
if (e is CancellationException)
pages.loadByRollingChunked(page.index, 2, 3) { chunks ->
"""

class ForegroundFirstTests(unittest.TestCase):
    def test_visible_page_gets_first_chunk(self):
        result = module.patch_source(BASE)
        self.assertIn(module.NEW, result)
        self.assertNotIn(module.OLD, result)
        self.assertIn("downloadJobs.remove(it)?.cancel()", result)
        self.assertIn("chapterCache.putImageToCache(imageUrl, imageResponse)", result)
        self.assertIn("MAX_PAGES_AHEAD = 8", result)

    def test_rejects_unknown_or_repeated_reader(self):
        for source in (BASE.replace("MAX_PAGES_AHEAD = 8", ""), BASE + module.OLD,
                       BASE.replace(module.OLD, module.NEW), BASE.replace("if (e is CancellationException)", "")):
            with self.subTest(source=source[-40:]), self.assertRaises(ValueError):
                module.patch_source(source)

    def test_patch_scope(self):
        self.assertEqual(module.TARGET, "app/src/main/java/eu/kanade/tachiyomi/ui/reader/loader/HttpPageLoader.kt")

if __name__ == "__main__":
    unittest.main()
