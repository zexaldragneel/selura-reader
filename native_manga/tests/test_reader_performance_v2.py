"""Regression tests for bounded network prefetch and existing reader safety."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "reader_performance_v2.py"
spec = importlib.util.spec_from_file_location("seiryn_reader_performance_v2", SCRIPT)
perf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(perf)

CURRENT = """package eu.kanade.tachiyomi.ui.reader.loader
import java.io.IOException
import kotlinx.coroutines.CancellationException
class HttpPageLoader {
    suspend fun getPages() {
        withOneTransientRetry { source.getPageList(chapter.chapter.toSChapter()) }
    }
    suspend fun getImage() {
        withOneTransientRetry { source.getImageUrl(page) }
        chapterCache.putImageToCache(imageUrl, imageResponse)
        if (e is CancellationException) { throw e }
    }
    private fun launchLoadOnce() {
        downloadJobs.putIfAbsent(pageIndex, job)
    }
    private fun prefetch(page: ReaderPage, pages: List<ReaderPage>) {
        pages.loadByRollingChunked(page.index, 3, 5) { chunks ->
            val continueLoading = chunks.take(2).flatten().map { it.index }.toSet()
            downloadJobs.keys.filter { it !in continueLoading }
                .forEach { downloadJobs.remove(it)?.cancel() }
        }
    }
    private fun List<ReaderPage>.loadByRollingChunked(
        index: Int,
        chunkStartSize: Int,
        chunkEndSize: Int,
        onNewChunks: (List<List<ReaderPage>>) -> Unit = {},
    ) {
        val items = this
""" + perf.OLD_PLAN + """
        // Existing cancellation and rolling chunk coordination remain.
    }
    private fun <T> List<T>.rollingChunked(startSize: Int, endSize: Int): List<List<T>> = TODO()
}
""" + perf.OLD_LIMIT


def planned(total, index, enabled):
    # Independent executable model of Kotlin window bounds and ordering.
    if total == 0:
        return []
    first = max(0, index - (2 if enabled else 1))
    last = min(total - 1, index + (8 if enabled else 4))
    ordered = [index, index - 1, index + 1]
    if index + 2 <= last:
        ordered.extend(range(index + 2, last + 1))
    if first <= index - 2:
        ordered.extend(range(index - 2, first - 1, -1))
    return [n for n in ordered if 0 <= n < total]


class ReaderPerformanceV2Tests(unittest.TestCase):
    def test_source_bounds_work_and_preserves_transport_contract(self):
        result = perf.patch_source(CURRENT)
        self.assertIn("val readAhead = canLoadAhead()", result)
        self.assertIn("MAX_PAGES_AHEAD = 8", result)
        self.assertIn("LIMITED_PAGES_AHEAD = 4", result)
        self.assertIn("pages.loadByRollingChunked(page.index, 2, 3)", result)
        self.assertNotIn("items.subList(index + 2, items.size)", result)
        self.assertNotIn(".filter { it.index in window }", result)
        self.assertNotIn("items.indices else", result)
        self.assertIn("downloadJobs.putIfAbsent(pageIndex, job)", result)
        self.assertIn("downloadJobs.remove(it)?.cancel()", result)
        self.assertIn("chapterCache.putImageToCache(imageUrl, imageResponse)", result)
        self.assertIn("if (e is CancellationException)", result)
        self.assertIn("withOneTransientRetry { source.getImageUrl(page) }", result)
        self.assertNotIn("cf_clearance", result)
        self.assertNotIn("bypassCloudflare", result)

    def test_bounded_nearby_images_even_for_extremely_long_chapter(self):
        for size in (1, 2, 3, 10, 100, 300, 3000):
            for index in (0, size // 2, size - 1):
                for enabled in (True, False):
                    values = planned(size, index, enabled)
                    self.assertEqual(values[0], index)
                    self.assertEqual(len(values), len(set(values)))
                    self.assertTrue(all(0 <= x < size for x in values))
                    self.assertLessEqual(len(values), 11 if enabled else 6)
                    self.assertIn(index - 1, values) if index else None
                    self.assertIn(index + 1, values) if index < size - 1 else None
        self.assertEqual(planned(3000, 1500, True), [1500, 1499, 1501, *range(1502, 1509), 1498])
        self.assertEqual(planned(3000, 1500, False), [1500, 1499, 1501, 1502, 1503, 1504])
        self.assertEqual(planned(0, 0, True), [])

    def test_changed_source_is_rejected_without_partial_file_write(self):
        for altered in (
            CURRENT.replace(perf.OLD_PLAN, "unexpected plan"),
            CURRENT.replace(perf.OLD_CHUNKS, "different scheduling"),
            CURRENT.replace(perf.OLD_LIMIT, ""),
            CURRENT.replace("downloadJobs.putIfAbsent(pageIndex, job)", ""),
            perf.patch_source(CURRENT),
        ):
            with self.subTest(marker=altered[:35]), self.assertRaises(perf.ReaderPerformanceError):
                perf.patch_source(altered)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "LICENSE").write_text("Apache-2.0")
            (root / "gradlew").write_text("gradle")
            f = root / perf.HTTP_LOADER
            f.parent.mkdir(parents=True)
            f.write_text(CURRENT.replace(perf.OLD_CHUNKS, "unexpected change"))
            with self.assertRaises(perf.ReaderPerformanceError):
                perf.patch(root)
            self.assertNotIn("MAX_PAGES_AHEAD", f.read_text())
            f.write_text(CURRENT)
            perf.patch(root)
            self.assertIn("MAX_PAGES_AHEAD = 8", f.read_text())

    def test_scope_is_only_one_http_reader_file(self):
        self.assertEqual(perf.HTTP_LOADER, "app/src/main/java/eu/kanade/tachiyomi/ui/reader/loader/HttpPageLoader.kt")
        self.assertNotIn("download", perf.HTTP_LOADER)
        self.assertNotIn("extension", perf.HTTP_LOADER)
        self.assertNotIn("backup", perf.HTTP_LOADER)


if __name__ == "__main__":
    unittest.main()
