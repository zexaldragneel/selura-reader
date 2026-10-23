#!/usr/bin/env python3
"""Build one compatible Hive Scans update using the approved 18-source foundation.

Only patches the isolated Selura Hive module. The upstream checkout and
existing 17 other extension modules are not published or given new identities.
"""
import argparse
from pathlib import Path

import orphaned_sources

HIVE_KEY = ("en", "hivescans", "selurahivescans", "Hive Scans")
HIVE_RELATIVE = Path("src/eu/kanade/tachiyomi/extension/en/hivescans/HiveScans.kt")
EXPECTED_CLASS = "abstract class HiveScans : Iken() {"
EXPECTED_REQUEST = """    override fun imageRequest(page: Page): Request = GET(
        page.imageUrl!!,
        headers,
        CacheControl.Builder().noCache().build(),
    )"""
# Allow the existing OkHttp cache to reuse fresh public image responses when
# the provider permits it. We neither force caching nor cache locked responses:
# HTTP response cache directives and the server's access rules still apply.
CACHED_REQUEST = """    override fun imageRequest(page: Page): Request = GET(
        page.imageUrl!!,
        headers,
    )"""
PAGE_CODE = r'''
    // HiveToons 2.0 exposes every public chapter image in the HTML reader.
    // The older Iken /api/chapter response is not consistently available.
    // Resolve original stored chapter URLs, never replace the manga source ID.
    override suspend fun getPageList(chapter: SChapter): List<Page> {
        val path = chapter.url.substringBefore('#')
        if (!path.startsWith("/series/") || path.count { it == '/' } < 3) {
            throw IOException("Hive Scans chapter URL is invalid. Refresh the chapter list.")
        }
        val document = client.get("$baseUrl$path").asJsoup()
        val urls = document.select("img[alt]").mapNotNull { image ->
            if (!PAGE_ALT.containsMatchIn(image.attr("alt"))) return@mapNotNull null
            sequenceOf("data-src", "src")
                .map { image.absUrl(it) }
                .firstOrNull { value ->
                    val url = value.toHttpUrlOrNull()
                    url != null && url.isHttps && allowedImageHost(url.host)
                }
        }.distinct()
        if (urls.isEmpty()) {
            // No fabricated pages or auth/captcha retries; report the real problem.
            throw IOException("Hive Scans did not provide public chapter images. Try opening this chapter in WebView.")
        }
        return urls.mapIndexed { index, url -> Page(index, imageUrl = url) }
    }

    private fun allowedImageHost(host: String) =
        host == "hivetoon.com" || host.endsWith(".hivetoon.com") ||
            host == "hivetoons.org" || host.endsWith(".hivetoons.org")

    companion object {
        private val PAGE_ALT = Regex("""\bPage\s+\d+\b""", RegexOption.IGNORE_CASE)
    }
'''
EXTRA_IMPORTS = """import eu.kanade.tachiyomi.source.model.SChapter
import keiyoushi.network.get
import keiyoushi.utils.asJsoup
import okhttp3.HttpUrl.Companion.toHttpUrlOrNull
import java.io.IOException
"""


def patch_hive_source(source: str) -> str:
    # Fail closed when the audited pinned upstream module changes.
    if source.count(EXPECTED_CLASS) != 1 or source.count(EXPECTED_REQUEST) != 1:
        raise orphaned_sources.SourceContractError("Pinned Hive Scans source changed")
    if source.count("import eu.kanade.tachiyomi.source.model.Page\n") != 1:
        raise orphaned_sources.SourceContractError("Hive Scans imports changed")
    if "override suspend fun getPageList" in source:
        raise orphaned_sources.SourceContractError("Hive Scans page list override already exists")
    source = source.replace(
        "import eu.kanade.tachiyomi.source.model.Page\n",
        "import eu.kanade.tachiyomi.source.model.Page\n" + EXTRA_IMPORTS,
        1,
    )
    # The upstream code explicitly demands a network revalidation even for
    # already-fresh public images. Remove that forced policy, but leave the
    # normal HTTP cache directives, per-source headers and host checks intact.
    if source.count("import okhttp3.CacheControl\\n") != 1:
        raise orphaned_sources.SourceContractError("Hive Scans cache import changed")
    source = source.replace("import okhttp3.CacheControl\\n", "", 1)
    return source.replace(EXPECTED_REQUEST, CACHED_REQUEST + "\n" + PAGE_CODE, 1)


def prepare(checkout: Path, version_code: int, verify_git: bool = True) -> list[str]:
    if HIVE_KEY not in orphaned_sources.SOURCES:
        raise orphaned_sources.SourceContractError("Hive source identity changed")
    source = checkout / "src/en/hivescans" / HIVE_RELATIVE
    if not source.is_file():
        raise orphaned_sources.SourceContractError("Pinned Hive Scans Kotlin source is missing")
    original = source.read_text(encoding="utf-8")
    # Preflight Kotlin patch before the importer creates any module directories.
    patch_hive_source(original)
    tasks = orphaned_sources.prepare(checkout, version_code, verify_git=verify_git)
    isolated = checkout / "src/en/selurahivescans" / HIVE_RELATIVE
    copied = isolated.read_text(encoding="utf-8")
    isolated.write_text(patch_hive_source(copied), encoding="utf-8")
    if source.read_text(encoding="utf-8") != original:
        raise orphaned_sources.SourceContractError("Hive upstream files were unexpectedly modified")
    # Do not build, upload, or publish the other seventeen modules.
    return [
        ":src:en:selurahivescans:assembleRelease",
        ":src:en:selurahivescans:lintRelease",
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--version-code", required=True, type=int)
    parser.add_argument("--task-file", type=Path, required=True)
    a = parser.parse_args()
    tasks = prepare(a.checkout, a.version_code)
    a.task_file.write_text("\n".join(tasks) + "\n", encoding="utf-8")
    print("Prepared independent Hive Scans extension only")


if __name__ == "__main__":
    main()
