"""Hive Scans HTML chapter download regression contracts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("orphaned_sources", BASE / "orphaned_sources.py")
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)
import sys
sys.modules["orphaned_sources"] = sources
patch_spec = importlib.util.spec_from_file_location("hivescans_download_fix", BASE / "hivescans_download_fix.py")
hive = importlib.util.module_from_spec(patch_spec)
patch_spec.loader.exec_module(hive)

HIVE_ORIGINAL = """package eu.kanade.tachiyomi.extension.en.hivescans

import eu.kanade.tachiyomi.multisrc.iken.Iken
import eu.kanade.tachiyomi.network.GET
import eu.kanade.tachiyomi.source.model.Page
import keiyoushi.annotation.Source
import okhttp3.CacheControl
import okhttp3.Request

@Source
abstract class HiveScans : Iken() {

    override fun imageRequest(page: Page): Request = GET(
        page.imageUrl!!,
        headers,
        CacheControl.Builder().noCache().build(),
    )
}
"""


class HiveDownloadsTests(unittest.TestCase):
    def test_exact_source_identity_and_safe_new_page_parser(self):
        self.assertEqual(hive.HIVE_KEY, ("en", "hivescans", "selurahivescans", "Hive Scans"))
        self.assertEqual(sources.SOURCE_VERSION_ID, 7301)
        self.assertEqual(sources.alternate_id("selurahivescans", "123456789"),
                         sources.alternate_id("selurahivescans", "123456789"))
        result = hive.patch_hive_source(HIVE_ORIGINAL)
        self.assertIn("override suspend fun getPageList(chapter: SChapter)", result)
        self.assertIn("chapter.url.substringBefore('#')", result)
        self.assertIn('document.select("img[alt]")', result)
        self.assertIn('"data-src", "src"', result)
        self.assertIn("urls.mapIndexed", result)
        self.assertIn('host.endsWith(".hivetoon.com")', result)
        self.assertIn("url.isHttps", result)
        self.assertIn("Try opening this chapter in WebView", result)
        self.assertIn(hive.EXPECTED_REQUEST, result)
        self.assertIn("package eu.kanade.tachiyomi.extension.en.hivescans", result)
        self.assertNotIn("solveCaptcha", result)

    def test_regression_rollback_retains_previous_image_request(self):
        # A reproducible, compile-checked regression rollback, NOT a
        # Cloudflare bypass. The original public HTML reader stays the same.
        result = hive.patch_hive_source(HIVE_ORIGINAL)
        self.assertEqual(result.count(hive.EXPECTED_REQUEST), 1)
        self.assertIn("CacheControl.Builder().noCache().build()", result)
        self.assertIn("import okhttp3.CacheControl", result)
        self.assertIn("override suspend fun getPageList(chapter: SChapter)", result)
        self.assertIn("allowedImageHost(url.host)", result)
        self.assertIn("url.isHttps", result)
        self.assertNotIn("bypassCloudflare", result)
        self.assertNotIn("cf_clearance", result)

    def test_refuse_duplicate_or_changed_upstream(self):
        with self.assertRaises(sources.SourceContractError):
            hive.patch_hive_source("class HiveScans {}")
        changed = HIVE_ORIGINAL.replace("noCache()", "maxAge(1, TimeUnit.MINUTES)")
        with self.assertRaises(sources.SourceContractError):
            hive.patch_hive_source(changed)
        once = hive.patch_hive_source(HIVE_ORIGINAL)
        with self.assertRaises(sources.SourceContractError):
            hive.patch_hive_source(once)

    def test_only_hive_task_and_original_sources_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "LICENSE").write_text("Apache License Version 2.0")
            (root / "settings.gradle.kts").write_text("\nloadAllIndividualExtensions()\n")
            for lang, upstream, isolated, display in sources.SOURCES:
                source = root / "src" / lang / upstream
                (source / "src").mkdir(parents=True)
                (source / "build.gradle.kts").write_text(
                    "keiyoushi {\n"
                    f'    name = "{display}"\n'
                    f'    pkgName = "{lang}.{upstream}"\n'
                    '    libVersion = "1.6"\n'
                    "    versionCode = 44\n"
                    "    source {\n"
                    f'        lang = "{lang}"\n'
                    "        versionId = 2\n"
                    "    }\n"
                    "}\n"
                )
            original_path = root / "src/en/hivescans" / hive.HIVE_RELATIVE
            original_path.parent.mkdir(parents=True)
            original_path.write_text(HIVE_ORIGINAL)
            tasks = hive.prepare(root, 4001, verify_git=False)
            self.assertEqual(tasks, [
                ":src:en:selurahivescans:assembleRelease",
                ":src:en:selurahivescans:lintRelease",
            ])
            self.assertEqual(original_path.read_text(), HIVE_ORIGINAL)
            new = root / "src/en/selurahivescans" / hive.HIVE_RELATIVE
            self.assertTrue(new.exists())
            self.assertIn("override suspend fun getPageList", new.read_text())
            generated_gradle = (root / "src/en/selurahivescans/build.gradle.kts").read_text()
            self.assertIn('pkgName = "en.selurahivescans"', generated_gradle)
            self.assertIn("versionId = 7301", generated_gradle)
            self.assertIn("versionCode = 4001", generated_gradle)
            for lang, upstream, isolated, display in sources.SOURCES:
                if isolated != "selurahivescans":
                    self.assertNotIn("override suspend fun getPageList",
                        "\n".join(p.read_text() for p in (root / "src" / lang / isolated).rglob("*.kt")))


if __name__ == "__main__":
    unittest.main()
