"""Regression tests for narrow Mihon chapter integrity/download retry patch."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "verify_chapter_downloads.py"
spec = importlib.util.spec_from_file_location("selura_chapter_integrity", SCRIPT)
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)

# Anchored verbatim snippets from the pinned upstream Kotlin implementation.
SOURCE = '''package eu.kanade.tachiyomi.data.download
import java.io.File
import eu.kanade.tachiyomi.util.storage.DiskUtil.NOMEDIA_FILE
import kotlinx.coroutines.CancellationException
import tachiyomi.core.common.util.system.ImageUtil
class Downloader {
                val pages = download.source.getPageList(download.chapter.toSChapter())
                                page.imageUrl = download.source.getImageUrl(page)
        val imageFile = tmpDir.listFiles()?.firstOrNull {
            isDownloadedPageImage(it.name ?: return@firstOrNull false, filename)
        }
                tmpDir.renameTo(chapterDirname)
            }
            cache.addChapter(chapterDirname, mangaDir, download.manga)
            // Retry 3 times, waiting 2, 4 and 8 seconds between attempts.
            .retryWhen { _, attempt ->
                if (attempt < 3) {
                    delay((2L shl attempt.toInt()).seconds)
                    true
                } else {
                    false
                }
            }
        // Ensure that the chapter folder has all the pages
        val downloadedImagesCount = tmpDir.listFiles().orEmpty().count {
            val fileName = it.name.orEmpty()
            when {
                fileName in listOf(COMIC_INFO_FILE, NOMEDIA_FILE) -> false
                fileName.endsWith(".tmp") -> false
                // Only count the first split page and not the others
                fileName.contains("__") && !fileName.endsWith("__001.jpg") -> false
                else -> true
            }
        }
        return downloadedImagesCount == downloadPageCount
        zip.renameTo("$dirname.cbz")
        tmpDir.delete()
    private suspend fun downloadImage(page: Page, source: HttpSource, tmpDir: UniFile, filename: String): UniFile {
}
'''


class ChapterIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / fix.DOWNLOADER
        self.path.parent.mkdir(parents=True)
        self.path.write_text(SOURCE, encoding="utf-8")

    def test_transient_retry_classification_without_access_bypass(self):
        fixed = fix.transform(SOURCE)
        self.assertIn("withOneTransientDownloadRetry", fixed)
        self.assertIn("is SocketTimeoutException, is ConnectException, is EOFException", fixed)
        self.assertIn("error.code in setOf(500, 502, 503, 504, 522, 523, 524)", fixed)
        self.assertIn("attempt < 3 && isTransientDownloadFailure(error)", fixed)
        self.assertIn("error is CancellationException", fixed)
        self.assertNotIn("attempt < 3) {", fixed)
        self.assertNotIn("CloudflareBypass", fixed)

    def test_incomplete_and_zero_byte_pages_cannot_complete(self):
        fixed = fix.transform(SOURCE)
        self.assertIn("if (downloadPageCount == 0) return false", fixed)
        self.assertIn("return (1..downloadPageCount).all { pageNumber ->", fixed)
        self.assertIn('val prefix = "%0${digits}d".format(Locale.ENGLISH, pageNumber)', fixed)
        self.assertNotIn("return (0 until downloadPageCount).all", fixed)
        self.assertIn("// Mihon Page.number = Page.index + 1", fixed)
        self.assertIn("isDownloadedPageImage(file.name.orEmpty(), prefix)", fixed)
        self.assertIn("ImageUtil.isImage(file.name) { file.openInputStream() }", fixed)
        self.assertIn("it.length() > 0L", fixed)
        self.assertNotIn("downloadedImagesCount == downloadPageCount", fixed)

    def test_41_pages_from_hive_scans_match_actual_mihon_file_numbering(self):
        """Regression: 41/41 page images 001..041 must not fail as 000..040."""
        kotlin = fix.transform(SOURCE)
        self.assertIn("return (1..downloadPageCount).all { pageNumber ->", kotlin)
        saved_names = {f"{n:03d}.jpg" for n in range(1, 42)}
        def all_named_pages_exist(names, count):
            digits = max(3, len(str(count)))
            return count > 0 and all(any(filename.startswith(f"{page:0{digits}d}.") or
                           filename.startswith(f"{page:0{digits}d}__")
                           for filename in names)
                       for page in range(1, count + 1))
        self.assertTrue(all_named_pages_exist(saved_names, 41))
        self.assertFalse(all_named_pages_exist(saved_names - {"001.jpg"}, 41))
        self.assertFalse(all_named_pages_exist(saved_names - {"021.jpg"}, 41))
        self.assertFalse(all_named_pages_exist(saved_names - {"041.jpg"}, 41))
        self.assertTrue(all_named_pages_exist({"001__001.jpg", "002.webp"}, 2))
        self.assertFalse(all_named_pages_exist(set(), 0))

    def test_mihon_page_number_is_one_based_and_downloader_uses_page_number(self):
        """Build validates pinned Mihon Page.number and its saved page filename."""
        source = fix.transform(SOURCE)
        self.assertIn("return (1..downloadPageCount).all { pageNumber ->", source)
        self.assertEqual(fix.PINNED_BLOB, "105c153ef1a7672d465e52eb2cfe5387d60e9e74")

    def test_failed_directory_or_cbz_rename_keeps_temp_pages(self):
        fixed = fix.transform(SOURCE)
        self.assertIn('if (!zip.renameTo("$dirname.cbz"))', fixed)
        self.assertIn("if (!tmpDir.renameTo(chapterDirname))", fixed)
        self.assertIn("throw IOException", fixed)
        self.assertLess(fixed.index('if (!zip.renameTo("$dirname.cbz"))'), fixed.index("tmpDir.delete()"))
        self.assertLess(fixed.index("if (!tmpDir.renameTo(chapterDirname))"), fixed.index("cache.addChapter("))
        self.assertEqual(fixed.count("tmpDir.delete()"), 1)

    def test_scope_excludes_user_data_and_source_ids(self):
        fixed = fix.transform(SOURCE)
        self.assertTrue(fix.DOWNLOADER.endswith("/data/download/Downloader.kt"))
        for disallowed in ("clearQueue()", "downloadStore.clear", "deleteManga(", "removeChapter(", "manga.source =", "chapter.url =", "sourceId ="):
            self.assertNotIn(disallowed, fixed)

    def test_fail_closed_and_atomic_if_pinned_markers_change(self):
        with self.assertRaises(fix.ChapterIntegrityError):
            fix.transform(SOURCE.replace(".retryWhen { _, attempt ->", ".retryWhen { error, attempt ->"))
        with self.assertRaises(fix.ChapterIntegrityError):
            fix.patch(self.root)
        self.assertEqual(self.path.read_text(), SOURCE)
        fix.patch(self.root, verify_pinned_blob=False)
        after = self.path.read_text()
        with self.assertRaises(fix.ChapterIntegrityError):
            fix.patch(self.root, verify_pinned_blob=False)
        self.assertEqual(self.path.read_text(), after)

    def test_original_kotlin_blob_lock(self):
        self.assertEqual(fix.PINNED_BLOB, "105c153ef1a7672d465e52eb2cfe5387d60e9e74")
        with self.assertRaisesRegex(fix.ChapterIntegrityError, "differs"):
            fix.verify_blob(SOURCE)


if __name__ == "__main__":
    unittest.main()
