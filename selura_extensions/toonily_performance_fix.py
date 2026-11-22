#!/usr/bin/env python3
"""Apply conservative Toonily request-count and search payload optimizations."""
from pathlib import Path

PATH = Path("src/en/seluratoonily/src/eu/kanade/tachiyomi/extension/en/toonily/Toonily.kt")
ANCHOR = '    override val chapterDateFormat = DateTimeFormatter.ofPattern("MMM d, yy", Locale.US)'
ADDITION = '''    // Limit search response size on Toonily's slower WordPress AJAX endpoint.
    // Pagination remains handled by Madara, with the smaller page size.
    override val pageSize = 12

    // Request the full chapter image list on the first navigation.
    // Madara otherwise sometimes fetches the chapter twice when #single-pager
    // is present; the inherited parser and fallback remain unchanged.
    override suspend fun fetchChapterDocument(chapterUrl: String): org.jsoup.nodes.Document =
        client.get(chapterUrl.toHttpUrl().newBuilder().addQueryParameter("style", "list").build()).asJsoup()

'''
IMPORT = 'import okhttp3.Response\n'
IMPORT_NEW = '''import okhttp3.Response
import okhttp3.HttpUrl.Companion.toHttpUrl
import keiyoushi.network.get
import keiyoushi.utils.asJsoup
'''

def apply(root: Path) -> None:
    path = root / PATH
    body = path.read_text(encoding="utf-8")
    if body.count(ANCHOR) != 1 or body.count(IMPORT) != 1:
        raise RuntimeError("Pinned Toonily source contract changed; refusing patch")
    body = body.replace(IMPORT, IMPORT_NEW)
    body = body.replace(ANCHOR, ADDITION + ANCHOR)
    path.write_text(body, encoding="utf-8")

if __name__ == "__main__":
    import sys
    apply(Path(sys.argv[1]))
