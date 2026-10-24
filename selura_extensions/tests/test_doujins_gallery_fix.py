"""Pin Doujins-only page list and cover URL fixes without changing source IDs."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("orphaned_sources", BASE / "orphaned_sources.py")
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)
sys.modules["orphaned_sources"] = sources
v = importlib.util.spec_from_file_location("doujins_gallery_fix", BASE / "doujins_gallery_fix.py")
doujins = importlib.util.module_from_spec(v)
v.loader.exec_module(doujins)

ORIGINAL = (
    "package eu.kanade.tachiyomi.extension.en.doujins\n"
    "import org.jsoup.nodes.Document\n"
    "import kotlinx.serialization.json.JsonElement\n"
    "@Source\nabstract class Doujins : KeiSource() {\n"
    "  suspend fun getPageList(chapter: SChapter) {\n"
    '    val response = client.get(getChapterUrl(chapter))\n'
    '    val pageUrl = response.request.url.toString()\n'
    + doujins.OLD_PAGES +
    "\n  }\n"
    '  suspend fun getPopularManga() = client.get("$baseUrl/top/month").asJsoup()\n'
    '  suspend fun search() = return parseGalleryPage(client.get(url).asJsoup())\n'
    "  private fun parseGalleryPage(document: Document): MangasPage {\n"
    + doujins.OLD_ARTIST + "\n"
    + doujins.OLD_IMAGE + "\n"
    "  }\n"
    "}\n"
)


class DoujinsGalleryTests(unittest.TestCase):
    def test_preserve_package_id_base_request_and_source_family(self):
        self.assertIn(doujins.KEY, sources.SOURCES)
        self.assertEqual(doujins.KEY[2], "seluradoujins")
        self.assertEqual(sources.SOURCE_VERSION_ID, 7301)
        self.assertEqual(sources.alternate_id("seluradoujins", "1234"),
                         sources.alternate_id("seluradoujins", "1234"))
        revised = doujins.patch_source(ORIGINAL)
        self.assertIn("package eu.kanade.tachiyomi.extension.en.doujins", revised)
        self.assertIn('client.get(getChapterUrl(chapter))', revised)
        self.assertIn('return parseGalleryPage(client.get(url).asJsoup())', revised)
        self.assertIn(doujins.NEW_PAGES, revised)
        self.assertIn("A changed layout or challenge", revised)
        self.assertIn('image.attr("srcset").substringBefore(",")', revised)
        self.assertIn('baseUrl.toHttpUrl().resolve(candidate)', revised)
        self.assertIn('image.attr("data-src"), image.attr("src")', revised)
        self.assertIn('it.parent()?.nextElementSibling()?.select', revised)
        self.assertNotIn(doujins.OLD_IMAGE, revised)
        self.assertNotIn("bypassCloudflare", revised)
        self.assertNotIn("cf_clearance", revised)

    def test_normal_srcset_and_lazy_image_parsing_without_new_network_requests(self):
        s = doujins.patch_source(ORIGINAL)
        self.assertIn('srcsetFirst, image.attr("data-src"), image.attr("src")', s)
        self.assertIn('takeIf { it.isHttps }', s)
        self.assertIn('.filter { it.isNotBlank() }', s)
        self.assertIn('.firstOrNull()', s)
        self.assertIn('private fun galleryCoverUrl(image: Element?)', s)
        self.assertEqual(s.count("client.get("), ORIGINAL.count("client.get("))
        self.assertEqual(s.count("Page(i,"), ORIGINAL.count("Page(i,"))

    def test_fail_closed_on_changed_or_twice_patched_source(self):
        for text in (
            "class Doujins {}",
            ORIGINAL.replace(doujins.OLD_IMAGE, 'thumbnail_url = "new"'),
            ORIGINAL.replace("client.get(getChapterUrl(chapter))", "fetchPage()"),
            ORIGINAL.replace(doujins.OLD_PAGES, "return emptyList()"),
            doujins.patch_source(ORIGINAL),
        ):
            with self.subTest(source=text[:28]), self.assertRaises(sources.SourceContractError):
                doujins.patch_source(text)

    def test_copies_only_one_module_task_and_does_not_edit_original(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            (base / "LICENSE").write_text("Apache-2.0")
            (base / "settings.gradle.kts").write_text("\nloadAllIndividualExtensions()\n")
            for lang, original, _, display in sources.SOURCES:
                p = base / "src" / lang / original
                (p / "src").mkdir(parents=True)
                (p / "build.gradle.kts").write_text(
                    "keiyoushi {\n" +
                    f'    name = "{display}"\n' +
                    "    versionCode = 1\n" +
                    '    libVersion = "1.6"\n' +
                    "    source {\n" +
                    f'        lang = "{lang}"\n' +
                    "        versionId = 2\n" +
                    "    }\n" +
                    "}\n"
                )
            target = base / "src/en/doujins" / doujins.RELATIVE
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(ORIGINAL)
            tasks = doujins.prepare(base, 5201, verify_git=False)
            self.assertEqual(tasks, [
                ":src:en:seluradoujins:assembleRelease",
                ":src:en:seluradoujins:lintRelease",
            ])
            self.assertEqual(target.read_text(), ORIGINAL)
            isolated = base / "src/en/seluradoujins"
            self.assertIn(doujins.NEW_IMAGE, (isolated / doujins.RELATIVE).read_text())
            gradle = (isolated / "build.gradle.kts").read_text()
            self.assertIn('pkgName = "en.seluradoujins"', gradle)
            self.assertIn("versionId = 7301", gradle)
            self.assertIn("versionCode = 5201", gradle)


if __name__ == "__main__":
    unittest.main()
