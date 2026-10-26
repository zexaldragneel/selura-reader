#!/usr/bin/env python3
"""Restrict pinned MangaBox fallback CDNs to the chapter that advertised them.

Run AFTER mangakakalot_cdn_fix.py prepared the isolated Mangakakalot source.
The original shared cdnSet grows across every opened chapter. A 503 on one
chapter can consequently trigger retries to hosts from unrelated chapters.
No new hosts/requests, access bypasses or user-data modifications.
"""
import argparse
from pathlib import Path

TARGET = Path("lib-multisrc/mangabox/src/eu/kanade/tachiyomi/multisrc/mangabox/MangaBox.kt")


class ChapterCdnContractError(RuntimeError):
    pass


def replace_once(source: str, before: str, after: str, label: str) -> str:
    count = source.count(before)
    if count != 1:
        raise ChapterCdnContractError(f"{label}: expected one pinned Kotlin section, got {count}")
    return source.replace(before, after, 1)


def transform(source: str) -> str:
    source = replace_once(
        source,
        """    private val cdnSet =
        MangaBoxLinkedCdnSet() // Stores all unique CDNs that the extension can use to retrieve chapter images

    private class MangaBoxFallBackTag // Custom empty class tag to use as an identifier that the specific request is fallback-able""",
        """    // Only use hosts explicitly advertised by the CURRENT chapter.
    // The old global cdnSet retained stale hosts from every chapter ever opened.
    // Bound this mapping to 128 small host lists even during large libraries.
    private val chapterCdnsByUrl: MutableMap<String, List<String>> =
        java.util.Collections.synchronizedMap(
            object : LinkedHashMap<String, List<String>>(128, 0.75f, true) {
                override fun removeEldestEntry(
                    eldest: MutableMap.MutableEntry<String, List<String>>?,
                ): Boolean = size > 128
            },
        )

    // Only an actual image request for a parsed chapter carries its own
    // chapter-provided list. An untagged URL never gains fallback permission.
    private class MangaBoxFallBackTag(val chapterCdns: List<String>)""",
        "remove session-global CDN list",
    )
    source = replace_once(
        source,
        "        request.tag(MangaBoxFallBackTag::class.java) ?: return chain.proceed(request)",
        "        val chapterTag = request.tag(MangaBoxFallBackTag::class.java) ?: return chain.proceed(request)",
        "access chapter-scoped tag",
    )
    source = replace_once(
        source,
        """        val alternateCdns = synchronized(cdnSet) {
            cdnSet.toList()
        }.filter { it != url.getBaseUrl() }""",
        """        val alternateCdns = chapterTag.chapterCdns
            .filter { it != url.getBaseUrl() }
            .distinct()""",
        "replace global cross-chapter CDN snapshot",
    )
    # On success, returning the open body is what matters. Do not reshuffle a
    # global list that must no longer exist. Keep the current chapter order.
    success_reorder = "            cdnSet.moveItemToFirst(url.getBaseUrl())\n"
    if source.count(success_reorder) != 1:
        raise ChapterCdnContractError("primary response priority anchor drift")
    source = source.replace(success_reorder, "", 1)
    alt_reorder = "                    cdnSet.moveItemToFirst(newRequest.url.getBaseUrl())\n"
    if source.count(alt_reorder) != 1:
        raise ChapterCdnContractError("alternate response priority anchor drift")
    source = source.replace(alt_reorder, "", 1)
    source = replace_once(
        source,
        """        // Keep the CDN snapshot consistent with concurrent downloads.
        synchronized(cdnSet) {
            cdnSet.addAll(cdns)
        }""",
        """        // Cache ONLY this chapter's HTTPS CDNs; never borrow other
        // chapters' endpoints when handling a failed image.
        val advertisedCdns = cdns.mapNotNull { candidate ->
            candidate.toHttpUrlOrNull()?.takeIf { it.isHttps }?.getBaseUrl()
        }.distinct()
        chapterCdnsByUrl[document.location()] = advertisedCdns""",
        "parse current chapter's allowed HTTPS hosts",
    )
    old_tag = ".tag(MangaBoxFallBackTag::class.java, MangaBoxFallBackTag())"
    if source.count(old_tag) != 2:
        raise ChapterCdnContractError("expected WebP probe and final image tag only")
    # The WebP dimension probe is constructed INSIDE getPageList, and the
    # regular image request is created by imageRequest(page) below it.
    source = source.replace(
        old_tag,
        ".tag(MangaBoxFallBackTag::class.java, MangaBoxFallBackTag(advertisedCdns))",
        1,
    )
    source = source.replace(
        old_tag,
        ".tag(MangaBoxFallBackTag::class.java, MangaBoxFallBackTag(chapterCdnsByUrl[page.url].orEmpty()))",
        1,
    )
    if "cdnSet" in source and source.count("cdnSet") != 1:
        raise ChapterCdnContractError("unhandled global CDN reference remains")
    return source


def patch(root: Path) -> None:
    target = root.resolve() / TARGET
    if not target.is_file():
        raise ChapterCdnContractError("Pinned MangaBox library is missing")
    original = target.read_text(encoding="utf-8")
    updated = transform(original)  # fail closed before writing
    if original == updated:
        raise ChapterCdnContractError("Nothing changed")
    target.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    patch(parser.parse_args().checkout)
