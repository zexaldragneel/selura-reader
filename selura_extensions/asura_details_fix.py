#!/usr/bin/env python3
"""Apply a narrowly scoped Asura Scans comic-details request correction.

Only touches the isolated Asura Scans Kotlin module generated from the pinned
Keiyoushi source. Does not bypass a Cloudflare challenge.
"""
from pathlib import Path

TARGET = Path("src/en/seluraasurascans/src/eu/kanade/tachiyomi/extension/en/asurascans/AsuraScans.kt")

OLD = '''        val url = getMangaUrl(manga)
        var response = client.get(url, ensureSuccess = false)

        // retry without random suffix, it redirects to new random suffix
        if (!response.isSuccessful) {
            response.close()
            response = client.get(url.replace(URL_RANDOM_PART, ""))
        }
'''

NEW = '''        val url = getMangaUrl(manga)
        // Comic details are HTML navigations, unlike the JSON catalogue API.
        // Use the normal source client and its cookie jar; never fabricate a
        // Cloudflare clearance token or retry a rejected challenge in a loop.
        val detailsHeaders = headersBuilder()
            .set("Accept", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
            .set("Referer", "$baseUrl/")
            .build()
        var response = client.get(url, detailsHeaders, ensureSuccess = false)

        // A stale random suffix may redirect to a new public slug. Only
        // retry genuine missing/redirected URLs, not access denials or limits.
        if (response.code == 404 || response.code == 410) {
            response.close()
            response = client.get(url.replace(URL_RANDOM_PART, ""), detailsHeaders)
        }

        // The existing response.use below owns the response lifecycle.
'''


def patch(root: Path) -> None:
    path = root / TARGET
    original = path.read_text(encoding="utf-8")
    if original.count(OLD) != 1:
        raise RuntimeError("Asura details request contract changed; refusing patch")
    path.write_text(original.replace(OLD, NEW), encoding="utf-8")


if __name__ == "__main__":
    import sys
    patch(Path(sys.argv[1]))
