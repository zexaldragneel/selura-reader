"""Mangakakalot CDN response ownership, query and source-ID regressions."""
import importlib.util
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parents[1]
s = importlib.util.spec_from_file_location("orphaned_sources", HERE / "orphaned_sources.py")
orphaned = importlib.util.module_from_spec(s)
s.loader.exec_module(orphaned)
sys.modules["orphaned_sources"] = orphaned

q = importlib.util.spec_from_file_location("mangakakalot_cdn_fix", HERE / "mangakakalot_cdn_fix.py")
fix = importlib.util.module_from_spec(q)
q.loader.exec_module(fix)

ORIGINAL_LIB = (
    "package eu.kanade.tachiyomi.multisrc.mangabox\n"
    "private class MangaBoxFallBackTag\n"
    "private fun HttpUrl.getBaseUrl()\n"
    + fix.OLD_CDN + "\n"
    + fix.OLD_ADD + "\n"
    + "override fun imageRequest(page: Page): Request = GET(\n"
    + "private val cdnsRegex = Regex(\n"
    + "private val backupImageRegex = Regex(\n"
)


class MangaKakalotCdnFixTests(unittest.TestCase):
    def test_pinned_shared_library_patch_only_replaces_intended_sections(self):
        result = fix.patch_library(ORIGINAL_LIB)
        self.assertIn(fix.NEW_CDN, result)
        self.assertIn(fix.NEW_ADD, result)
        self.assertEqual(result.count("override fun imageRequest(page: Page): Request"), 1)
        self.assertEqual(result.count("private val cdnsRegex = Regex("), 1)
        self.assertNotIn("All CDN attempts failed.", result)
        self.assertNotIn("chain.proceed(newRequest).use", result)
        self.assertIn("return response", result)
        self.assertIn("response.close()", result)

    def test_do_not_preclose_successful_backup_response(self):
        x = fix.NEW_CDN
        self.assertIn("val response = chain.proceed(newRequest)", x)
        self.assertIn("if (response.isSuccessful)", x)
        self.assertIn("return response", x)
        self.assertNotIn("response.use", x)
        self.assertNotIn("tryResponse", x)
        self.assertIn("originalResponse?.close()", x)

    def test_no_bypass_or_aggressive_network_fallback(self):
        x = fix.NEW_CDN
        self.assertIn("originalResponse.code in setOf(401, 403, 429)", x)
        self.assertIn("response.code in setOf(401, 403, 429)", x)
        self.assertIn("cdnUrl.toHttpUrlOrNull()?.takeIf { it.isHttps }", x)
        self.assertIn("cdnSet.toList()", x)
        self.assertIn(".filter { it != url.getBaseUrl() }", x)
        self.assertIn("request.tag(MangaBoxFallBackTag::class.java)", x)
        self.assertIn(".encodedPath(url.encodedPath)", x)
        self.assertIn(".encodedQuery(url.encodedQuery)", x)
        self.assertEqual(x.count("chain.proceed("), 3)
        for forbidden in ("cloudflare", "cf_clearance", "Cookie", "User-Agent", "while (", "delay(", "Proxy", "mirrorUrl"):
            self.assertNotIn(forbidden, x)

    def test_preserves_synchronized_host_set_instead_of_live_iteration(self):
        self.assertIn("synchronized(cdnSet)", fix.NEW_ADD)
        self.assertIn("synchronized(cdnSet)", fix.NEW_CDN)
        self.assertNotIn("for (cdnUrl in cdnSet)", fix.NEW_CDN)
        self.assertIn("for (cdnUrl in alternateCdns)", fix.NEW_CDN)

    def test_existing_package_source_identity_and_scope(self):
        self.assertIn(fix.KEY, orphaned.SOURCES)
        self.assertEqual(orphaned.SOURCE_VERSION_ID, 7301)
        self.assertEqual(fix.KEY[2], "seluramangakakalot")
        self.assertEqual(str(fix.TARGET), "src/en/seluramangakakalot/src/eu/kanade/tachiyomi/extension/en/mangakakalot/Mangakakalot.kt")
        self.assertEqual(str(fix.LIBRARY), "lib-multisrc/mangabox/src/eu/kanade/tachiyomi/multisrc/mangabox/MangaBox.kt")

    def test_fail_closed_if_pinned_library_changed_or_twice_patched(self):
        for modified in (
            ORIGINAL_LIB.replace(fix.OLD_CDN, "fun other()"),
            ORIGINAL_LIB.replace(fix.OLD_ADD, "cdnSet.addAll(other)"),
            ORIGINAL_LIB.replace("private val cdnsRegex = Regex(", ""),
            fix.patch_library(ORIGINAL_LIB),
        ):
            with self.subTest(scenario=modified[-25:]), self.assertRaises(fix.MangaKakalotContractError):
                fix.patch_library(modified)


if __name__ == "__main__":
    unittest.main()
