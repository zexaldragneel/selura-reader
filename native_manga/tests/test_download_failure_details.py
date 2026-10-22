"""Regression checks for truthful and privacy-safe download failure details."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("selura_failure_details", ROOT / "download_failure_details.py")
fix = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fix)

MODEL = """package eu.kanade.tachiyomi.data.download.model
class Download {
    @Transient
    val progressFlow = _pagesFlow
}
"""
HOLDER = """class DownloadHolder {
            initMenu = {
                findItem(R.id.selura_retry_chapter).isVisible = download.status == Download.State.ERROR
                findItem(R.id.move_to_top).isVisible
            },
            onMenuItemClick = {
                adapter.downloadItemListener.onMenuItemClick(bindingAdapterPosition, this)
            },
}
"""
MENU = """<menu>
    <item
        android:id="@+id/selura_retry_chapter"
        android:title="@string/selura_retry_chapter" />
</menu>
"""
DOWNLOADER = """class Downloader {
    private suspend fun downloadChapter(download: Download, slots: Semaphore, pagesStarted: CompletableDeferred<Unit>) {
        val mangaDir = provider.getMangaDir(download.manga.title, download.source).getOrElse { e ->
            download.status = Download.State.ERROR
        }
        if (availSpace != -1L && availSpace < MIN_DISK_SPACE) {
            download.status = Download.State.ERROR
        }
            if (!archiveReady && !folderReady) {
                download.status = Download.State.ERROR
            }
                            } catch (e: Throwable) {
                                page.status = Page.State.Error(e)
                            }
            if (!isDownloadSuccessful(download, tmpDir)) {
                download.status = Download.State.ERROR
                return
            }
        } catch (error: Throwable) {
            logcat(LogPriority.ERROR, error)
            download.status = Download.State.ERROR
            notifier.onError(error.message, download.chapter.name, download.manga.title, download.manga.id)
        }
    }
    private suspend fun getOrDownloadImage(page: Page, download: Download) {
        } catch (e: Throwable) {
            page.progress = 0
            page.status = Page.State.Error(e)
            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)
        }
    }
    private fun isTransientDownloadFailure(error: Throwable): Boolean = when (error) {
    }
}
"""
SAMPLES = {fix.MODEL: MODEL, fix.HOLDER: HOLDER, fix.MENU: MENU, fix.DOWNLOADER: DOWNLOADER}


class FailureDetailsTests(unittest.TestCase):
    def test_source_errors_presented_as_cause_categories_not_raw_urls(self):
        changed = fix.downloader(DOWNLOADER)
        self.assertIn("private fun describeDownloadFailure(error: Throwable): String", changed)
        for category in ("is HttpException", "401, 403", "404", "429", "is SocketTimeoutException",
                         "is IOException", "Hive Scans did not provide public chapter images"):
            self.assertIn(category, changed)
        self.assertIn("This chapter or image requires source access or unlocking", changed)
        self.assertIn("Hive Scans has no publicly accessible images", changed)
        self.assertIn("error.message?.startsWith(", changed)
        self.assertNotIn("setCookie", changed)
        self.assertNotIn("readText(", changed)

    def test_each_failure_path_sets_diagnostic_before_error_status(self):
        changed = fix.downloader(DOWNLOADER)
        self.assertIn("download.failureReason = null", changed)
        self.assertIn("download.failureReason = describeDownloadFailure(e)", changed)
        self.assertIn("download.failureReason = context.stringResource(MR.strings.download_insufficient_space)", changed)
        self.assertIn('download.failureReason = "Page " + page.number + ": " + describeDownloadFailure(e)', changed)
        self.assertIn("download.failureReason = describeDownloadFailure(error)", changed)
        self.assertIn("Chapter pages are missing, incomplete or unreadable.", changed)
        self.assertIn("download.failureReason = download.failureReason", changed)

    def test_android_menu_shows_reason_only_for_failed_chapters(self):
        item = fix.holder(HOLDER)
        self.assertIn("findItem(R.id.selura_view_download_error).isVisible = download.status == Download.State.ERROR", item)
        self.assertIn("MaterialAlertDialogBuilder(view.context)", item)
        self.assertIn("download.failureReason", item)
        self.assertIn("R.string.selura_unknown_download_error", item)
        self.assertIn("adapter.downloadItemListener.onMenuItemClick(bindingAdapterPosition, this)", item)
        menu = fix.menu(MENU)
        self.assertIn('android:id="@+id/selura_view_download_error"', menu)
        self.assertEqual(menu.count("selura_retry_chapter"), 2)

    def test_ephemeral_in_memory_only_and_no_account_data_leaks(self):
        model = fix.model(MODEL)
        self.assertIn("@Transient\n    var failureReason: String? = null", model)
        self.assertNotIn("@Serializable", model)
        self.assertNotIn("sourceId =", " ".join(SAMPLES.values()))
        self.assertEqual(set(fix.FILES), set(SAMPLES))
        self.assertFalse(any("DownloadStore.kt" in f or "library" in f.lower() for f in fix.FILES))
        self.assertNotIn("cookies", fix.holder(HOLDER).lower())
        self.assertNotIn("token", fix.holder(HOLDER).lower())

    def test_all_files_preflight_before_mutation_and_double_patch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for p, content in SAMPLES.items():
                path = root / p
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            wrong = root / fix.MENU
            wrong.write_text("unknown menu source", encoding="utf-8")
            with self.assertRaises(fix.FailureDetailsPatchError):
                fix.patch(root)
            self.assertEqual((root / fix.MODEL).read_text(), MODEL)
            self.assertFalse((root / fix.LABELS).exists())
            wrong.write_text(MENU, encoding="utf-8")
            fix.patch(root)
            self.assertTrue((root / fix.LABELS).is_file())
            self.assertIn("View error", (root / fix.LABELS).read_text())
            with self.assertRaises(fix.FailureDetailsPatchError):
                fix.patch(root)


if __name__ == "__main__":
    unittest.main()
