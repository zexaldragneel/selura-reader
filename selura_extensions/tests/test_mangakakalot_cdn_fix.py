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
    "import eu.kanade.tachiyomi.network.GET\n"
    "private class MangaBoxFallBackTag\n"
    "private fun HttpUrl.getBaseUrl()\n"
    + fix.OLD_CDN + "\n"
    + fix.OLD_ADD + "\n"
    + fix.OLD_MERGE_IMAGE + "\n"
    + fix.OLD_SIZE_PROBE + "\n"
    + "                        } catch (_: Exception) {\n                            null\n                        }\n"
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

    def test_optional_merged_image_composition_closes_all_intermediate_responses(self):
        changed = fix.patch_library(ORIGINAL_LIB)
        self.assertIn(fix.NEW_MERGE_IMAGE, changed)
        self.assertIn(fix.NEW_SIZE_PROBE, changed)
        self.assertNotIn(fix.OLD_MERGE_IMAGE, changed)
        self.assertNotIn(fix.OLD_SIZE_PROBE, changed)
        self.assertIn("chain.proceed(request.newBuilder().url(imageUrl).build()).use { response ->", changed)
        self.assertIn("BitmapFactory.decodeStream(response.body.byteStream())", changed)
        self.assertIn("bitmap.recycle()", changed)
        self.assertIn("try {", fix.NEW_MERGE_IMAGE)
        self.assertIn("finally {", fix.NEW_MERGE_IMAGE)
        self.assertIn("awaitSuccess().use { response ->", changed)
        self.assertIn("WebpSizeGetter(response.body.byteStream()).get()", changed)
        self.assertIn("throw HttpException(response.code)", changed)
        self.assertIn("if (e.code in setOf(401, 403, 429)) throw e", changed)
        self.assertIn("import eu.kanade.tachiyomi.network.HttpException", changed)
        # The successful *CDN response* must remain open for the real reader.
        self.assertIn("return response", changed)
        self.assertNotIn("response.use { return response }", changed)
        # No extra network requests, alternate host discovery or unlock logic.
        self.assertEqual(changed.count("chain.proceed(newRequest)"), 1)
        self.assertEqual(changed.count("newCall("), 1)
        self.assertNotIn("cloudflare", changed.lower())

    def test_merge_response_patch_fails_closed_on_source_drift(self):
        for changed in (
            ORIGINAL_LIB.replace(fix.OLD_MERGE_IMAGE, ""),
            ORIGINAL_LIB.replace(fix.OLD_SIZE_PROBE, ""),
            fix.patch_library(ORIGINAL_LIB),
        ):
            with self.subTest(length=len(changed)), self.assertRaises(fix.MangaKakalotContractError):
                fix.patch_library(changed)

    def test_mangakakalot_conservative_pacing_only_one_source(self):
        upstream = """package eu.kanade.tachiyomi.extension.en.mangakakalot
class Mangakakalot : MangaBox() {
    override fun OkHttpClient.Builder.configureClient(): OkHttpClient.Builder = apply {
        addInterceptor(::mergeImagesInterceptor)
        addInterceptor(::useAltCdnInterceptor)
        rateLimit(2, 1.seconds)
    }
}
"""
        updated = fix.patch_mangakakalot_request_pace(upstream)
        self.assertIn("rateLimit(1, 2.seconds)", updated)
        self.assertNotIn("rateLimit(2, 1.seconds)", updated)
        self.assertEqual(updated.count("rateLimit("), 1)
        self.assertEqual(updated.count("addInterceptor(::useAltCdnInterceptor)"), 1)
        self.assertNotIn("retryWhen", updated)
        self.assertNotIn("Cookie", updated)
        self.assertNotIn("setUserAgent", updated)
        self.assertNotIn("alternateUrl", updated)
        self.assertIn("eu.kanade.tachiyomi.extension.en.mangakakalot", updated)
        with self.assertRaises(fix.MangaKakalotContractError):
            fix.patch_mangakakalot_request_pace(updated)
        with self.assertRaises(fix.MangaKakalotContractError):
            fix.patch_mangakakalot_request_pace(upstream.replace("rateLimit(2, 1.seconds)", "rateLimit(10, 1.seconds)"))

    def test_image_only_connection_close_preserves_inherited_request_headers_and_tags(self):
        source = """package eu.kanade.tachiyomi.extension.en.mangakakalot
import eu.kanade.tachiyomi.source.model.SManga
class Mangakakalot : MangaBox() {
    override fun OkHttpClient.Builder.configureClient(): OkHttpClient.Builder = apply {
        addInterceptor(::mergeImagesInterceptor)
        addInterceptor(::useAltCdnInterceptor)
        rateLimit(2, 1.seconds)
    }
    override fun computeMangaSlug(manga: SManga): String = super.computeMangaSlug(manga).let {
        it
    }
}
"""
        paced = fix.patch_mangakakalot_request_pace(source)
        updated = fix.patch_mangakakalot_image_connection(paced)
        self.assertIn('rateLimit(1, 2.seconds)', updated)
        self.assertIn('import eu.kanade.tachiyomi.source.model.Page', updated)
        self.assertIn('import okhttp3.Request', updated)
        self.assertIn('override fun imageRequest(page: Page): Request = super.imageRequest(page).newBuilder()', updated)
        self.assertIn('.header("Connection", "close")', updated)
        self.assertEqual(updated.count('header("Connection", "close")'), 1)
        self.assertEqual(updated.count('imageRequest(page: Page)'), 2)
        self.assertIn('addInterceptor(::useAltCdnInterceptor)', updated)
        self.assertIn('super.imageRequest(page).newBuilder()', updated)
        self.assertNotIn('chain.proceed(', updated)
        self.assertNotIn('proxy(', updated)
        self.assertNotIn('retryWhen', updated)
        with self.assertRaises(fix.MangaKakalotContractError):
            fix.patch_mangakakalot_image_connection(updated)
        with self.assertRaises(fix.MangaKakalotContractError):
            fix.patch_mangakakalot_image_connection(source.replace(
                'override fun computeMangaSlug(manga: SManga): String',
                'fun unknownSlug(manga: SManga): String',
            ))

    def test_image_connection_change_has_no_library_or_source_id_side_effects(self):
        self.assertEqual(orphaned.SOURCE_VERSION_ID, 7301)
        self.assertEqual(fix.KEY[2], 'seluramangakakalot')
        self.assertEqual(fix.ORIGINAL.parts[0:3], ('src', 'en', 'mangakakalot'))
        self.assertIn('Connection', fix.patch_mangakakalot_image_connection(
            "import eu.kanade.tachiyomi.source.model.SManga\n"
            "    override fun computeMangaSlug(manga: SManga): String = super.computeMangaSlug(manga).let {"
        ))

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
