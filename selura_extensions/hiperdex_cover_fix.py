#!/usr/bin/env python3
"""Apply an isolated Hiperdex image CDN header fix to the pinned source."""
from pathlib import Path

RELATIVE = Path("src/en/selurahiperdex/src/eu/kanade/tachiyomi/extension/en/hiperdex/Hiperdex.kt")
OLD = """    override fun OkHttpClient.Builder.configureClient(): OkHttpClient.Builder = addHiperAuthInterceptor()
        .rateLimit(3)"""
NEW = """    override fun OkHttpClient.Builder.configureClient(): OkHttpClient.Builder = addHiperAuthInterceptor()
        .addInterceptor { chain ->
            val request = chain.request()
            val siteHost = baseUrl.toHttpUrl().host
            if (request.url.host == siteHost) {
                chain.proceed(request)
            } else {
                // Cover CDN requests need a website Referer; the shared Hiper
                // WebView interceptor may replace their normal image headers.
                // Never forward site authentication to an unrelated CDN host.
                val imageRequest = request.newBuilder()
                    .removeHeader("Authorization")
                    .removeHeader("Cookie")
                    .removeHeader("x-cfg-auth")
                    .header("Referer", "$baseUrl/")
                    .header("Accept", "image/avif,image/webp,image/*,*/*;q=0.8")
                    .build()
                chain.proceed(imageRequest)
            }
        }
        .rateLimit(3)"""


def apply(root: Path) -> None:
    path = root / RELATIVE
    original = path.read_text(encoding="utf-8")
    if original.count(OLD) != 1:
        raise RuntimeError("Hiperdex pinned client contract changed; refusing modification")
    if original.count("import okhttp3.Response\n") != 1:
        raise RuntimeError("Hiperdex pinned imports changed")
    updated = original.replace("import okhttp3.Response\n", "import okhttp3.Response\nimport okhttp3.HttpUrl.Companion.toHttpUrl\n")
    updated = updated.replace(OLD, NEW)
    path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    import sys
    apply(Path(sys.argv[1]))
