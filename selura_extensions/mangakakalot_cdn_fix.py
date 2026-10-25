#!/usr/bin/env python3
"""Repair MangaBox backup-CDN image response ownership for Mangakakalot only."""
import argparse
from pathlib import Path
import orphaned_sources

KEY = ("en", "mangakakalot", "seluramangakakalot", "Mangakakalot")
ORIGINAL = Path("src/en/mangakakalot/src/eu/kanade/tachiyomi/extension/en/mangakakalot/Mangakakalot.kt")
TARGET = Path("src/en/seluramangakakalot/src/eu/kanade/tachiyomi/extension/en/mangakakalot/Mangakakalot.kt")
LIBRARY = Path("lib-multisrc/mangabox/src/eu/kanade/tachiyomi/multisrc/mangabox/MangaBox.kt")

OLD_CDN = """    protected fun useAltCdnInterceptor(chain: Interceptor.Chain): Response {
        val request = chain.request()
        request.tag(MangaBoxFallBackTag::class.java) ?: return chain.proceed(request)
        val url = request.url

        if (cdnSet.isEmpty()) {
            return chain.proceed(request)
        }

        val originalResponse: Response? = try {
            chain.proceed(request)
        } catch (_: IOException) {
            null
        }

        if (originalResponse?.isSuccessful == true) {
            // Move working cdn to first so it gets priority during iteration
            cdnSet.moveItemToFirst(url.getBaseUrl())

            return originalResponse
        }

        // Close the original response if it's not successful
        originalResponse?.close()

        for (cdnUrl in cdnSet) {
            val newUrl = cdnUrl.toHttpUrl().newBuilder()
                .encodedPath(request.url.encodedPath)
                .fragment(request.url.fragment)
                .build()

            // Create a new request with the updated URL
            val newRequest = request.newBuilder()
                .url(newUrl)
                .build()

            try {
                // Proceed with the new request
                chain.proceed(newRequest).use { tryResponse ->

                    // Check if the response is successful
                    if (tryResponse.isSuccessful) {
                        // Move working cdn to first so it gets priority during iteration
                        cdnSet.moveItemToFirst(newRequest.url.getBaseUrl())

                        return tryResponse
                    }
                }
            } catch (_: IOException) {}
        }

        // If all CDNs fail, throw an error
        throw IOException("All CDN attempts failed.")
    }"""

NEW_CDN = """    protected fun useAltCdnInterceptor(chain: Interceptor.Chain): Response {
        val request = chain.request()
        request.tag(MangaBoxFallBackTag::class.java) ?: return chain.proceed(request)
        val url = request.url

        // Snapshot chapter-provided image hosts. Moving a working CDN to
        // first changes the live set, so iterating that set is unsafe.
        val alternateCdns = synchronized(cdnSet) {
            cdnSet.toList()
        }.filter { it != url.getBaseUrl() }

        var transportFailure: IOException? = null
        val originalResponse = try {
            chain.proceed(request)
        } catch (e: IOException) {
            transportFailure = e
            null
        }
        if (originalResponse?.isSuccessful == true) {
            cdnSet.moveItemToFirst(url.getBaseUrl())
            return originalResponse
        }
        // Respect authorization and rate-limit decisions. Host rotation
        // must not turn a rejected request into an access workaround.
        if (originalResponse != null && originalResponse.code in setOf(401, 403, 429)) {
            return originalResponse
        }
        if (alternateCdns.isEmpty()) {
            return originalResponse ?: throw (
                transportFailure ?: IOException("Mangakakalot image host is unreachable.")
            )
        }
        var lastHttpCode = originalResponse?.code
        originalResponse?.close()

        for (cdnUrl in alternateCdns) {
            val host = cdnUrl.toHttpUrlOrNull()?.takeIf { it.isHttps } ?: continue
            // Keep the original encoded path and query; the chapter supplies
            // the alternate hosts, and no new image hosts are invented.
            val newUrl = host.newBuilder()
                .encodedPath(url.encodedPath)
                .encodedQuery(url.encodedQuery)
                .fragment(url.fragment)
                .build()
            val newRequest = request.newBuilder().url(newUrl).build()
            try {
                val response = chain.proceed(newRequest)
                if (response.isSuccessful) {
                    cdnSet.moveItemToFirst(newRequest.url.getBaseUrl())
                    // The downloader owns the open body; do not close it here.
                    return response
                }
                lastHttpCode = response.code
                if (response.code in setOf(401, 403, 429)) {
                    return response
                }
                response.close()
            } catch (e: IOException) {
                transportFailure = e
            }
        }
        val code = lastHttpCode?.let { " (last HTTP $it)" }.orEmpty()
        throw IOException(
            "Mangakakalot chapter image unavailable across chapter-provided CDNs$code.",
            transportFailure,
        )
    }"""

OLD_ADD = """        // Add all parsed cdns to set
        cdnSet.addAll(cdns)"""
NEW_ADD = """        // Keep the CDN snapshot consistent with concurrent downloads.
        synchronized(cdnSet) {
            cdnSet.addAll(cdns)
        }"""


class MangaKakalotContractError(RuntimeError):
    pass


def exactly_once(text: str, before: str, after: str, label: str) -> str:
    count = text.count(before)
    if count != 1:
        raise MangaKakalotContractError(f"{label}: expected one pinned source marker, found {count}")
    return text.replace(before, after, 1)


def patch_library(source: str) -> str:
    for required in (
        "package eu.kanade.tachiyomi.multisrc.mangabox",
        "private class MangaBoxFallBackTag",
        "private fun HttpUrl.getBaseUrl()",
        "override fun imageRequest(page: Page): Request = GET(",
        "private val cdnsRegex = Regex(",
        "private val backupImageRegex = Regex(",
    ):
        if required not in source:
            raise MangaKakalotContractError("Pinned MangaBox contract changed: " + required)
    source = exactly_once(source, OLD_CDN, NEW_CDN, "CDN image lifecycle")
    return exactly_once(source, OLD_ADD, NEW_ADD, "CDN host synchronization")


def prepare(checkout: Path, version_code: int, verify_git: bool = True) -> list[str]:
    if KEY not in orphaned_sources.SOURCES or orphaned_sources.SOURCE_VERSION_ID != 7301:
        raise MangaKakalotContractError("Published Mangakakalot source identity changed")
    library = checkout / LIBRARY
    original = checkout / ORIGINAL
    if not library.is_file() or not original.is_file():
        raise MangaKakalotContractError("Pinned MangaBox/Mangakakalot source missing")
    original_lib = library.read_text(encoding="utf-8")
    original_module = original.read_text(encoding="utf-8")
    transformed = patch_library(original_lib)  # preflight before writing
    orphaned_sources.prepare(checkout, version_code, verify_git=verify_git)
    if not (checkout / TARGET).is_file():
        raise MangaKakalotContractError("Isolated Mangakakalot source was not generated")
    if original.read_text(encoding="utf-8") != original_module:
        raise MangaKakalotContractError("Original upstream source was changed")
    library.write_text(transformed, encoding="utf-8")
    return [
        ":src:en:seluramangakakalot:assembleRelease",
        ":src:en:seluramangakakalot:lintRelease",
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--version-code", type=int, required=True)
    parser.add_argument("--task-file", type=Path, required=True)
    args = parser.parse_args()
    tasks = prepare(args.checkout, args.version_code)
    args.task_file.write_text("\n".join(tasks) + "\n", encoding="utf-8")
    print("Prepared one Mangakakalot APK with fixed backup CDN body lifecycle")
