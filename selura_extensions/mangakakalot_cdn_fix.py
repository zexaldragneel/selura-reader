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
    source = exactly_once(source, OLD_ADD, NEW_ADD, "CDN host synchronization")
    return patch_optional_merge_image_responses(source)


# Merge Split Images is off by default; when enabled, its source bitmap
# composition and WebP-size probes must close each *intermediate* response.
# These blocks never change the page list, URL selection or source identity.
OLD_MERGE_IMAGE = """                    val bitmap = BitmapFactory.decodeStream(
                        chain
                            .proceed(request.newBuilder().url(imageUrl).build())
                            .body
                            .byteStream(),
                    )
                    canvas.drawBitmap(bitmap, 0f, yOffset.toFloat(), null)
                    yOffset += bitmap.height
                    bitmap.recycle()"""

NEW_MERGE_IMAGE = """                    // Own each constituent HTTP body only while decoding it.
                    // A decoded Bitmap no longer needs the response stream.
                    val bitmap = chain.proceed(request.newBuilder().url(imageUrl).build()).use { response ->
                        if (!response.isSuccessful) {
                            throw HttpException(response.code)
                        }
                        BitmapFactory.decodeStream(response.body.byteStream())
                    } ?: throw IOException("Mangakakalot merged image could not be decoded.")
                    try {
                        canvas.drawBitmap(bitmap, 0f, yOffset.toFloat(), null)
                        yOffset += bitmap.height
                    } finally {
                        bitmap.recycle()
                    }"""

OLD_SIZE_PROBE = """                            val response = client.newCall(
                                GET(url, headers)
                                    .newBuilder()
                                    .tag(MangaBoxFallBackTag::class.java, MangaBoxFallBackTag())
                                    .build(),
                            ).awaitSuccess()
                            WebpSizeGetter(response.body.byteStream()).get()"""

NEW_SIZE_PROBE = """                            client.newCall(
                                GET(url, headers)
                                    .newBuilder()
                                    .tag(MangaBoxFallBackTag::class.java, MangaBoxFallBackTag())
                                    .build(),
                            ).awaitSuccess().use { response ->
                                WebpSizeGetter(response.body.byteStream()).get()
                            }"""


def patch_optional_merge_image_responses(source: str) -> str:
    """Close intermediate responses, without closing CDN bodies passed to readers.

    Both transforms are fail-closed if the pinned optional merge flow changes.
    Neither enables merge mode nor changes a single chapter's page mapping.
    """
    source = exactly_once(source, OLD_MERGE_IMAGE, NEW_MERGE_IMAGE, "merged image bodies")
    source = exactly_once(source, OLD_SIZE_PROBE, NEW_SIZE_PROBE, "image size probe bodies")
    source = exactly_once(
        source,
        "import eu.kanade.tachiyomi.network.GET\n",
        "import eu.kanade.tachiyomi.network.GET\n"
        "import eu.kanade.tachiyomi.network.HttpException\n",
        "recognized source status error import",
    )
    # If the source sends 401/403/429 during image-size detection,
    # abandon the extra dimension probes immediately. The normal Seiryn
    # downloader will honor the source status (including its 429 cooldown).
    old_catch = NEW_SIZE_PROBE + """\n                        } catch (_: Exception) {
                            null
                        }"""
    new_catch = NEW_SIZE_PROBE + """\n                        } catch (e: HttpException) {
                            if (e.code in setOf(401, 403, 429)) throw e
                            null
                        } catch (_: Exception) {
                            null
                        }"""
    return exactly_once(source, old_catch, new_catch, "stop size probes on source restrictions")


def patch_mangakakalot_image_connection(source: str) -> str:
    """Restore Mangakakalot's documented non-reuse behavior for image requests.

    The pinned source already says image-heavy downloads require a per-image
    Connection: close hint, but its implementation never sets that header.
    Restrict to the inherited tagged imageRequest, not chapter/page-list APIs.
    OkHttp handles HTTP/2 hop-by-hop headers according to its own rules.
    Preserve inherited Referer, URL, existing fallback tag and all source IDs.
    """
    if "override fun imageRequest(page: Page): Request" in source:
        raise MangaKakalotContractError(
            "Mangakakalot already overrides imageRequest; refusing duplicate request override"
        )
    source = exactly_once(
        source,
        "import eu.kanade.tachiyomi.source.model.SManga\n",
        "import eu.kanade.tachiyomi.source.model.Page\n"
        "import eu.kanade.tachiyomi.source.model.SManga\n"
        "import okhttp3.Request\n",
        "targeted image request imports",
    )
    source = exactly_once(
        source,
        "    override fun computeMangaSlug(manga: SManga): String = super.computeMangaSlug(manga).let {",
        """    // The upstream source documentation explicitly calls for non-reused
    // image HTTP/1.1 connections on long chapters, but omitted this header.
    // Keep the original image URL, Referer and MangaBox CDN fallback tag.
    override fun imageRequest(page: Page): Request = super.imageRequest(page).newBuilder()
        .header("Connection", "close")
        .build()

    override fun computeMangaSlug(manga: SManga): String = super.computeMangaSlug(manga).let {""",
        "image-only Connection close request",
    )
    return source


def patch_mangakakalot_request_pace(source: str) -> str:
    """Reduce request bursts in this Mangakakalot APK only.

    Never retry a source HTTP 429, rotate source hosts/IPs, or modify
    authentication. Optional Merge Images probes use the same paced client.
    """
    if "class Mangakakalot" not in source or "configureClient()" not in source:
        raise MangaKakalotContractError("Unexpected pinned Mangakakalot source module")
    return exactly_once(
        source,
        "        rateLimit(2, 1.seconds)",
        "        // Conservative request pacing for long chapters.\n"
        "        rateLimit(1, 2.seconds)",
        "per-source request pacing",
    )


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
    # Long webtoons can exhaust image-host quotas even with serial page
    # downloads. Apply a more conservative request rate to this source alone.
    patched_module = patch_mangakakalot_request_pace(original_module)
    patched_module = patch_mangakakalot_image_connection(patched_module)
    orphaned_sources.prepare(checkout, version_code, verify_git=verify_git)
    if not (checkout / TARGET).is_file():
        raise MangaKakalotContractError("Isolated Mangakakalot source was not generated")
    if original.read_text(encoding="utf-8") != original_module:
        raise MangaKakalotContractError("Original upstream source was changed")
    target_module = checkout / TARGET
    generated = target_module.read_text(encoding="utf-8")
    # Isolated source copy must differ solely in the package namespace.
    old_package = "eu.kanade.tachiyomi.extension.en.mangakakalot"
    own_package = "eu.kanade.tachiyomi.extension.en.seluramangakakalot"
    expected = original_module.replace(old_package, own_package)
    if generated != expected:
        raise MangaKakalotContractError("Unexpected generated Mangakakalot Kotlin module")
    target_module.write_text(patched_module.replace(old_package, own_package), encoding="utf-8")
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
