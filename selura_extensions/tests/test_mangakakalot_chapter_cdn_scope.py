"""Regression coverage for current-chapter-only Mangakakalot CDN fallback."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
p = importlib.util.spec_from_file_location("chapter_cdn_scope", ROOT / "mangakakalot_chapter_cdn_scope.py")
chapter = importlib.util.module_from_spec(p)
p.loader.exec_module(chapter)
o = importlib.util.spec_from_file_location("orphaned_sources", ROOT / "orphaned_sources.py")
os = importlib.util.module_from_spec(o)
o.loader.exec_module(os)
import sys
sys.modules["orphaned_sources"] = os
c = importlib.util.spec_from_file_location("mangakakalot_cdn_fix", ROOT / "mangakakalot_cdn_fix.py")
fix = importlib.util.module_from_spec(c)
c.loader.exec_module(fix)

ORIGINAL = (
    "package eu.kanade.tachiyomi.multisrc.mangabox\n"
    "    private val cdnSet =\n"
    "        MangaBoxLinkedCdnSet() // Stores all unique CDNs that the extension can use to retrieve chapter images\n"
    "\n"
    "    private class MangaBoxFallBackTag // Custom empty class tag to use as an identifier that the specific request is fallback-able\n"
    + fix.NEW_CDN + "\n"
    + fix.NEW_ADD + "\n"
    + '                            .tag(MangaBoxFallBackTag::class.java, MangaBoxFallBackTag())\n'
    + "    override fun imageRequest(page: Page): Request = GET(\n"
    + '        page.imageUrl!!, headers,\n'
    + '    ).newBuilder().tag(MangaBoxFallBackTag::class.java, MangaBoxFallBackTag()).build()\n'
)


class ChapterScopedCdnTests(unittest.TestCase):
    def test_limits_fallback_to_current_chapter_only(self):
        result = chapter.transform(ORIGINAL)
        self.assertIn("val chapterTag = request.tag(MangaBoxFallBackTag::class.java)", result)
        self.assertIn("val alternateCdns = chapterTag.chapterCdns", result)
        self.assertIn("chapterCdnsByUrl[document.location()] = advertisedCdns", result)
        self.assertIn("MangaBoxFallBackTag(chapterCdnsByUrl[page.url].orEmpty())", result)
        self.assertIn("MangaBoxFallBackTag(advertisedCdns)", result)
        self.assertIn("candidate.toHttpUrlOrNull()?.takeIf { it.isHttps }?.getBaseUrl()", result)
        self.assertIn("size > 128", result)
        self.assertNotIn("cdnSet.toList()", result)
        self.assertNotIn("cdnSet.addAll(cdns)", result)
        self.assertNotIn("cdnSet.moveItemToFirst(", result)
        self.assertIn("return response", result)
        self.assertIn("retryableResponse?.let { return it }", result)

    def test_never_increases_http_requests_or_bypasses_source_rejections(self):
        result = chapter.transform(ORIGINAL)
        self.assertEqual(result.count("chain.proceed(newRequest)"), 1)
        self.assertIn("originalResponse.code in setOf(401, 403, 429)", result)
        self.assertIn("response.code in setOf(401, 403, 429)", result)
        self.assertIn("cdnUrl.toHttpUrlOrNull()?.takeIf { it.isHttps }", result)
        self.assertIn(".encodedQuery(url.encodedQuery)", result)
        self.assertIn("retryableResponse?.let { return it }", result)
        for forbidden in ("Proxy(", "rotateIp(", "while (true)", "bypassCloudflare", "removeAllDownloads", "clearQueue()"):
            self.assertNotIn(forbidden, result)

    def test_fail_closed_on_unknown_shape_and_apply_only_once(self):
        result = chapter.transform(ORIGINAL)
        with self.assertRaises(chapter.ChapterCdnContractError):
            chapter.transform(result)
        for anchor in ("MangaBoxLinkedCdnSet()", "cdnSet.toList()", "cdnSet.addAll(cdns)", "MangaBoxFallBackTag()"):
            with self.subTest(anchor=anchor):
                with self.assertRaises(chapter.ChapterCdnContractError):
                    chapter.transform(ORIGINAL.replace(anchor, "UNKNOWN"))

    def test_file_preflight_preserves_source_on_failed_second_patch(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / chapter.TARGET
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(ORIGINAL, encoding="utf-8")
            chapter.patch(Path(d))
            first = f.read_text(encoding="utf-8")
            with self.assertRaises(chapter.ChapterCdnContractError):
                chapter.patch(Path(d))
            self.assertEqual(first, f.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
