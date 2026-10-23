#!/usr/bin/env python3
"""Build one fail-closed Weeb Central chapter-image reliability update.

Copy the already-published five-source family unchanged, then patch only the
isolated Weeb Central Kotlin module. Never remap installed source IDs.
"""
import argparse
from pathlib import Path

import expansion_5

SOURCE_KEY = ("en", "weebcentral", "seluraweebcentral", "Weeb Central")
UPSTREAM_PATH = Path(
    "src/eu/kanade/tachiyomi/extension/en/weebcentral/WeebCentral.kt"
)
ORIGINAL_PAGES = """        val document = client.get(newUrl).asJsoup()
        return document.select("section[x-data~=scroll] > img").mapIndexed { index, element ->
            Page(index, imageUrl = element.attr("abs:src"))
        }"""
SAFER_PAGES = """        val document = client.get(newUrl).asJsoup()
        // Prefer the real lazy-loaded page URL to a placeholder src. Only
        // accept HTTPS images; never fabricate pages or bypass site access.
        val urls = document.select("section[x-data~=scroll] > img").mapNotNull { element ->
            sequenceOf("abs:data-src", "abs:src")
                .map { element.attr(it) }
                .firstOrNull { it.toHttpUrlOrNull()?.isHttps == true }
        }
        if (urls.isEmpty()) {
            throw IOException("Weeb Central returned no accessible chapter images. Try opening the chapter in WebView.")
        }
        return urls.mapIndexed { index, url -> Page(index, imageUrl = url) }"""


def patch_source(source: str) -> str:
    if source.count(ORIGINAL_PAGES) != 1:
        raise expansion_5.SourceContractError("Pinned Weeb Central page parser changed")
    if source.count("import okhttp3.HttpUrl.Companion.toHttpUrlOrNull\n") != 1:
        raise expansion_5.SourceContractError("Pinned Weeb Central URL imports changed")
    if source.count("override suspend fun getPageList(chapter: SChapter)") != 1:
        raise expansion_5.SourceContractError("Pinned Weeb Central chapter API changed")
    if "import java.io.IOException\n" in source:
        raise expansion_5.SourceContractError("Pinned Weeb Central exception import changed")
    source = source.replace(
        "import okhttp3.HttpUrl.Companion.toHttpUrlOrNull\n",
        "import okhttp3.HttpUrl.Companion.toHttpUrlOrNull\nimport java.io.IOException\n",
        1,
    )
    return source.replace(ORIGINAL_PAGES, SAFER_PAGES, 1)


def prepare(checkout: Path, version_code: int, verify_git: bool = True) -> list[str]:
    if SOURCE_KEY not in expansion_5.SOURCES or expansion_5.SOURCE_VERSION_ID != 7303:
        raise expansion_5.SourceContractError("Published Weeb Central identity changed")
    original = checkout / "src/en/weebcentral" / UPSTREAM_PATH
    if not original.is_file():
        raise expansion_5.SourceContractError("Pinned Weeb Central Kotlin file is missing")
    old = original.read_text(encoding="utf-8")
    patch_source(old)  # preflight before the five-source transformer creates files
    expansion_5.prepare(checkout, version_code, verify_git=verify_git)
    isolated = checkout / "src/en/seluraweebcentral" / UPSTREAM_PATH
    patched = patch_source(isolated.read_text(encoding="utf-8"))
    isolated.write_text(patched, encoding="utf-8")
    if original.read_text(encoding="utf-8") != old:
        raise expansion_5.SourceContractError("Original Weeb Central module was modified")
    # Other four transformed sources are not compiled, uploaded, or published.
    return [
        ":src:en:seluraweebcentral:assembleRelease",
        ":src:en:seluraweebcentral:lintRelease",
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    parser.add_argument("--version-code", required=True, type=int)
    parser.add_argument("--task-file", required=True, type=Path)
    args = parser.parse_args()
    tasks = prepare(args.checkout, args.version_code)
    args.task_file.write_text("\n".join(tasks) + "\n", encoding="utf-8")
    print("Prepared one source: Weeb Central (7303 identity preserved)")


if __name__ == "__main__":
    main()
