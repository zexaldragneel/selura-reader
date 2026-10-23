"""Single-extension Weeb Central page-loader contracts."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
import expansion_5
import weebcentral_page_guard as weeb

PINNED = """package eu.kanade.tachiyomi.extension.en.weebcentral

import okhttp3.HttpUrl.Companion.toHttpUrlOrNull

abstract class WeebCentral {
    override suspend fun getPageList(chapter: SChapter): List<Page> {
""" + weeb.ORIGINAL_PAGES + """
    }
}
"""


class WeebCentralTests(unittest.TestCase):
    def test_only_lazy_https_pages_with_existing_order_and_headers(self):
        s = weeb.patch_source(PINNED)
        self.assertIn('sequenceOf("abs:data-src", "abs:src")', s)
        self.assertIn('it.toHttpUrlOrNull()?.isHttps == true', s)
        self.assertIn('urls.mapIndexed { index, url -> Page(index, imageUrl = url) }', s)
        self.assertIn('throw IOException("Weeb Central returned no accessible chapter images.', s)
        self.assertIn('import java.io.IOException', s)
        self.assertNotIn(weeb.ORIGINAL_PAGES, s)
        self.assertNotIn("clearance", s)
        self.assertNotIn("Cloudflare", s)
        self.assertNotIn("CacheControl", s)
        self.assertNotIn("Thread.sleep", s)

    def test_reject_modified_or_already_patched_parser(self):
        for text in (
            PINNED.replace('abs:src', 'src'),
            PINNED.replace('import okhttp3.HttpUrl.Companion.toHttpUrlOrNull\n', ''),
            PINNED.replace('override suspend fun getPageList', 'fun getPageList'),
            weeb.patch_source(PINNED),
        ):
            with self.subTest(text=text[:35]), self.assertRaises(expansion_5.SourceContractError):
                weeb.patch_source(text)

    def test_only_weebcentral_apk_builds_and_source_identity_stays(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "LICENSE").write_text("Apache License 2.0")
            (root / "settings.gradle.kts").write_text("\nloadAllIndividualExtensions()\n")
            for lang, upstream, isolated, display in expansion_5.SOURCES:
                p = root / "src" / lang / upstream
                p.mkdir(parents=True)
                upstream_name = "Comix" if upstream == "comix" else display
                (p / "build.gradle.kts").write_text(
                    'keiyoushi {\n'
                    f'    name = "{upstream_name}"\n'
                    f'    versionCode = 35\n'
                    '    libVersion = "1.6"\n'
                    '    source {\n'
                    f'        lang = "{lang}"\n'
                    '        id = 123456789L\n'
                    '        versionId = 2\n'
                    '    }\n'
                    '}\n'
                )
                if upstream == "comix":
                    path = p / expansion_5.COMIX_SOURCE_PATH
                    path.parent.mkdir(parents=True)
                    path.write_text(expansion_5.COMIX_RETRY_OLD)
                if upstream == "weebcentral":
                    path = p / weeb.UPSTREAM_PATH
                    path.parent.mkdir(parents=True)
                    path.write_text(PINNED)
            tasks = weeb.prepare(root, 4601, verify_git=False)
            self.assertEqual(tasks, [
                ":src:en:seluraweebcentral:assembleRelease",
                ":src:en:seluraweebcentral:lintRelease",
            ])
            original = root / "src/en/weebcentral" / weeb.UPSTREAM_PATH
            isolated = root / "src/en/seluraweebcentral" / weeb.UPSTREAM_PATH
            self.assertEqual(original.read_text(), PINNED)
            self.assertIn('sequenceOf("abs:data-src", "abs:src")', isolated.read_text())
            gradle = (root / "src/en/seluraweebcentral/build.gradle.kts").read_text()
            self.assertIn('pkgName = "en.seluraweebcentral"', gradle)
            self.assertIn('versionId = 7303', gradle)
            self.assertIn('versionCode = 4601', gradle)
            self.assertEqual(
                expansion_5.alternate_id("seluraweebcentral", "123456789"),
                expansion_5.alternate_id("seluraweebcentral", "123456789"),
            )
            for lang, _, isolated_name, _ in expansion_5.SOURCES:
                if isolated_name == "seluraweebcentral":
                    continue
                d = root / "src" / lang / isolated_name
                self.assertNotIn(
                    "Weeb Central returned no accessible chapter images",
                    "\n".join(p.read_text() for p in d.rglob("*.kt")),
                )

    def test_missing_upstream_fails_without_copying_modules(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaises(expansion_5.SourceContractError):
                weeb.prepare(root, 4602, verify_git=False)
            self.assertFalse((root / "src/en/seluraweebcentral").exists())


if __name__ == "__main__":
    unittest.main()
