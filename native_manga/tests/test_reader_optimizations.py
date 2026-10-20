"""Fail-closed contract tests for Selura native reader reliability patches."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

script = Path(__file__).resolve().parents[1] / "optimize_reader.py"
spec = importlib.util.spec_from_file_location("selura_reader_optimization", script)
optim = importlib.util.module_from_spec(spec)
spec.loader.exec_module(optim)


class ReaderReliabilityTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.files = {
            optim.HTTP_LOADER: """package eu.kanade.tachiyomi.ui.reader.loader
import kotlinx.coroutines.launch
import java.util.concurrent.ConcurrentHashMap
internal class HttpPageLoader {
    suspend fun pages() {
            source.getPageList(chapter.chapter.toSChapter())
                page.imageUrl = source.getImageUrl(page)
                val imageResponse = source.getImage(page)
                chapterCache.putImageToCache(imageUrl, imageResponse)
    }
    private suspend fun internalLoadPage(page: ReaderPage, force: Boolean = false) {
        page.status = Page.State.Queue
    }
}""",
            optim.CHAPTER_CACHE: """package eu.kanade.tachiyomi.data.cache
private const val PARAMETER_APP_VERSION = 1
private const val PARAMETER_CACHE_SIZE = 100L * 1024 * 1024
class ChapterCache {
    // Keep existing cache directory and data untouched.
}""",
            optim.MAIN_ACTIVITY: """class MainActivity {
        // Extensions updates
        LaunchedEffect(Unit) {
            try {
                extensionManager.checkForUpdates()
            } catch (e: Exception) {
                logcat(LogPriority.ERROR, e)
            }
        }
}""",
        }
        for name, content in self.files.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def test_retains_reader_behavior_with_bounded_transient_retry(self):
        optim.patch(self.root)
        loader = (self.root / optim.HTTP_LOADER).read_text(encoding="utf-8")
        self.assertEqual(loader.count("withOneTransientRetry { source.getPageList"), 1)
        self.assertEqual(loader.count("withOneTransientRetry { source.getImageUrl"), 1)
        self.assertIn("val imageResponse = source.getImage(page)", loader)
        self.assertIn("chapterCache.putImageToCache(imageUrl, imageResponse)", loader)
        self.assertIn("catch (error: IOException)", loader)
        self.assertIn("error !is SocketTimeoutException", loader)
        self.assertIn("error !is ConnectException", loader)
        self.assertIn("error !is EOFException", loader)
        self.assertIn("delay(450L)", loader)
        self.assertEqual(loader.count("block()"), 2)
        self.assertNotIn("retryOnConnectionFailure = true", loader)

    def test_cache_expansion_reuses_original_disk_cache_version(self):
        optim.patch(self.root)
        body = (self.root / optim.CHAPTER_CACHE).read_text(encoding="utf-8")
        self.assertIn("PARAMETER_CACHE_SIZE = 192L * 1024 * 1024", body)
        self.assertIn("PARAMETER_APP_VERSION = 1", body)
        self.assertIn("Keep existing cache directory and data untouched", body)
        self.assertNotIn("PARAMETER_CACHE_SIZE = 100L", body)

    def test_periodic_extension_checks_preserve_signed_install_requirements(self):
        optim.patch(self.root)
        body = (self.root / optim.MAIN_ACTIVITY).read_text(encoding="utf-8")
        self.assertEqual(body.count("extensionManager.checkForUpdates()"), 1)
        self.assertIn("repeatOnLifecycle(Lifecycle.State.STARTED)", body)
        self.assertIn("12L * 60 * 60 * 1000", body)
        self.assertIn("SystemClock.elapsedRealtime()", body)
        self.assertIn("catch (e: CancellationException)", body)
        self.assertNotIn("installExtension(", body)
        self.assertNotIn("updateAllExtensions()", body)

    def test_missing_or_changed_source_fails_atomically(self):
        file = self.root / optim.CHAPTER_CACHE
        file.write_text("changed upstream", encoding="utf-8")
        with self.assertRaises(optim.PatchContractError):
            optim.patch(self.root)
        self.assertEqual(
            (self.root / optim.HTTP_LOADER).read_text(encoding="utf-8"),
            self.files[optim.HTTP_LOADER],
        )

    def test_source_missing_or_double_patched_refused(self):
        (self.root / optim.MAIN_ACTIVITY).unlink()
        with self.assertRaises(optim.PatchContractError):
            optim.patch(self.root)
        (self.root / optim.MAIN_ACTIVITY).write_text(
            self.files[optim.MAIN_ACTIVITY], encoding="utf-8"
        )
        optim.patch(self.root)
        with self.assertRaises(optim.PatchContractError):
            optim.patch(self.root)


if __name__ == "__main__":
    unittest.main()
