#!/usr/bin/env python3
"""Build a compatible, isolated Doujins extension optimized for robust thumbnails.

Pinned Apache-2.0 upstream is unmodified. Existing manga/source IDs and 17
other orphaned extension APKs remain exactly as they are.
"""
import argparse
from pathlib import Path
import orphaned_sources

KEY = ("en", "doujins", "seluradoujins", "Doujins")
RELATIVE = Path("src/eu/kanade/tachiyomi/extension/en/doujins/Doujins.kt")

OLD_IMAGE = 'thumbnail_url = it.select("img").attr("srcset")'
NEW_IMAGE = 'thumbnail_url = galleryCoverUrl(it.selectFirst("img"))'
OLD_ARTIST = '''artist = it.parent()!!.nextElementSibling()!!.select(".single-line strong").last()
                        ?.text()?.substringAfter("Artist: ")'''
NEW_ARTIST = '''artist = it.parent()?.nextElementSibling()?.select(".single-line strong")?.last()
                        ?.text()?.substringAfter("Artist: ")'''
OLD_PAGES = '''        return document.select(".doujin").mapIndexed { i, page ->
            Page(i, "$pageUrl${page.attr("data-link")}", page.attr("data-file").replace("amp;", ""))
        }'''
NEW_PAGES = '''        val pages = document.select(".doujin").mapIndexed { i, page ->
            Page(i, "$pageUrl${page.attr("data-link")}", page.attr("data-file").replace("amp;", ""))
        }
        if (pages.isEmpty()) {
            // A changed layout or challenge should not masquerade as a read chapter.
            throw IOException("Doujins provided no chapter images. Open the chapter in WebView to check access.")
        }
        return pages'''

INSERT_ANCHOR = "    private fun parseGalleryPage(document: Document): MangasPage {"
COVER_HELPER = '''
    // An HTML srcset value can be "image.webp 1x, image@2x.webp 2x".
    // It is not itself an image URL. Resolve one real HTTPS candidate and
    // fall back to the existing lazy/src attributes without extra requests.
    private fun galleryCoverUrl(image: Element?): String {
        if (image == null) return ""
        val srcsetFirst = image.attr("srcset").substringBefore(",").trim().substringBefore(" ").trim()
        return sequenceOf(srcsetFirst, image.attr("data-src"), image.attr("src"))
            .filter { it.isNotBlank() }
            .mapNotNull { candidate ->
                baseUrl.toHttpUrl().resolve(candidate)?.takeIf { it.isHttps }?.toString()
            }
            .firstOrNull()
            .orEmpty()
    }

'''


def one(body: str, before: str, after: str, label: str) -> str:
    n = body.count(before)
    if n != 1:
        raise orphaned_sources.SourceContractError(f"Doujins {label}: expected 1 pinned anchor, found {n}")
    return body.replace(before, after, 1)


def patch_source(source: str) -> str:
    # Explicit unchanged contracts, including source/package and no new requests.
    for anchor in (
        "package eu.kanade.tachiyomi.extension.en.doujins",
        "abstract class Doujins : KeiSource()",
        'client.get(getChapterUrl(chapter))',
        'val pageUrl = response.request.url.toString()',
        'client.get("$baseUrl/top/month").asJsoup()',
        'return parseGalleryPage(client.get(url).asJsoup())',
        'Page(i, "$pageUrl${page.attr("data-link")}", page.attr("data-file").replace("amp;", ""))',
    ):
        if source.count(anchor) != 1:
            raise orphaned_sources.SourceContractError("Pinned Doujins HTTP/source contract changed: " + anchor)
    source = one(source, "import org.jsoup.nodes.Document\n",
                 "import org.jsoup.nodes.Document\nimport org.jsoup.nodes.Element\nimport java.io.IOException\n", "imports")
    source = one(source, OLD_IMAGE, NEW_IMAGE, "srcset cover parse")
    source = one(source, OLD_ARTIST, NEW_ARTIST, "optional gallery metadata")
    source = one(source, OLD_PAGES, NEW_PAGES, "chapter empty-state handling")
    source = one(source, INSERT_ANCHOR, COVER_HELPER + INSERT_ANCHOR, "single image resolver")
    return source


def prepare(checkout: Path, version_code: int, verify_git: bool = True) -> list[str]:
    if KEY not in orphaned_sources.SOURCES or orphaned_sources.SOURCE_VERSION_ID != 7301:
        raise orphaned_sources.SourceContractError("Published Doujins source ID is no longer stable")
    original_file = checkout / "src/en/doujins" / RELATIVE
    if not original_file.is_file():
        raise orphaned_sources.SourceContractError("Pinned Doujins source missing")
    original = original_file.read_text(encoding="utf-8")
    patch_source(original)  # Preflight before the 18-source transformer writes anything.
    orphaned_sources.prepare(checkout, version_code, verify_git=verify_git)
    installed_file = checkout / "src/en/seluradoujins" / RELATIVE
    installed_file.write_text(patch_source(installed_file.read_text(encoding="utf-8")), encoding="utf-8")
    if original_file.read_text(encoding="utf-8") != original:
        raise orphaned_sources.SourceContractError("Keiyoushi original Doujins module unexpectedly changed")
    return [
        ":src:en:seluradoujins:assembleRelease",
        ":src:en:seluradoujins:lintRelease",
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--version-code", required=True, type=int)
    parser.add_argument("--task-file", required=True, type=Path)
    args = parser.parse_args()
    tasks = prepare(args.checkout, args.version_code)
    args.task_file.write_text("\n".join(tasks) + "\n")
    print("Prepared only Doujins source for a signed release build")


if __name__ == "__main__":
    main()
