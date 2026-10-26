#!/usr/bin/env python3
"""Keep only sanitized CDN hostname on HTTP errors for safe Android diagnostics.

Apply after http429_stage_diagnostics.py and http503_chapter_recovery.py.
No network requests, changed retry behavior, URL logs or permission changes.
"""
import argparse
from pathlib import Path

HTTP_EXCEPTION = Path("core/common/src/main/kotlin/eu/kanade/tachiyomi/network/HttpException.kt")
HTTP_EXTENSIONS = Path("core/common/src/main/kotlin/eu/kanade/tachiyomi/network/OkHttpExtensions.kt")
DOWNLOADER = Path("app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt")


class CdnHostDiagnosticPatchError(RuntimeError):
    pass


def once(src: str, old: str, new: str, name: str) -> str:
    n = src.count(old)
    if n != 1:
        raise CdnHostDiagnosticPatchError(f"{name}: expected exactly one pinned Kotlin anchor, got {n}")
    return src.replace(old, new, 1)


def http_exception(src: str) -> str:
    return once(
        src,
        "    var retryAfterSeconds: Long? = null\n}",
        "    var retryAfterSeconds: Long? = null\n"
        "    // Optional, sanitized hostname only: never record URL path, query or credentials.\n"
        "    var sourceHost: String? = null\n}",
        "preserve HttpException binary constructor",
    )


def http_extensions(src: str) -> str:
    return once(
        src,
        "    return HttpException(code).apply { retryAfterSeconds = retrySeconds }",
        """    // Read only the hostname of the ACTUAL HTTP response. In MangaBox,
    // this is the final CDN that answered, not necessarily the chapter URL.
    // Reject unexpected characters before showing any value in a notification.
    val failureHost = request.url.host.lowercase()
        .takeIf { host ->
            host.length in 1..253 && host.all { ch ->
                (ch in 'a'..'z') || (ch in '0'..'9') || ch == '.' || ch == '-'
            }
        }
    return HttpException(code).apply {
        retryAfterSeconds = retrySeconds
        sourceHost = failureHost
    }""",
        "record sanitized failing response hostname",
    )


def downloader(src: str) -> str:
    src = once(
        src,
        """            notifier.onWarning(
                "HTTP 503 during " + stage + ". Retrying the saved chapter after " +
                    minutes + " minute(s); download queue preserved.",
            )""",
        """            val safeHost = error.sourceHost?.let { " from " + it }.orEmpty()
            notifier.onWarning(
                "HTTP 503" + safeHost + " during " + stage +
                    ". Retrying the saved chapter after " +
                    minutes + " minute(s); download queue preserved.",
            )""",
        "display failing 503 hostname",
    )
    src = once(
        src,
        '''                    "Source still returns HTTP 503 during " + stage +
                        ". Automatic recovery stopped; queued chapters and pages kept.",''',
        '''                    "Source still returns HTTP 503" +
                        error.sourceHost?.let { " from " + it }.orEmpty() +
                        " during " + stage +
                        ". Automatic recovery stopped; queued chapters and pages kept.",''',
        "display final 503 hostname",
    )
    src = once(
        src,
        '''                "HTTP 429 during " + stage + ". Waiting " + minutes +''',
        '''                "HTTP 429" +
                    httpError.sourceHost?.let { " from " + it }.orEmpty() +
                    " during " + stage + ". Waiting " + minutes +''',
        "display failing 429 hostname",
    )
    return src


def transform(files: dict[Path, str]) -> dict[Path, str]:
    expected = {HTTP_EXCEPTION, HTTP_EXTENSIONS, DOWNLOADER}
    if set(files) != expected:
        raise CdnHostDiagnosticPatchError("Expected exactly three audited Kotlin files")
    return {
        HTTP_EXCEPTION: http_exception(files[HTTP_EXCEPTION]),
        HTTP_EXTENSIONS: http_extensions(files[HTTP_EXTENSIONS]),
        DOWNLOADER: downloader(files[DOWNLOADER]),
    }


def patch(root: Path) -> None:
    root = root.resolve()
    originals = {}
    for p in (HTTP_EXCEPTION, HTTP_EXTENSIONS, DOWNLOADER):
        f = root / p
        if not f.is_file():
            raise CdnHostDiagnosticPatchError(f"Missing pinned Kotlin source: {p}")
        originals[p] = f.read_text(encoding="utf-8")
    # Transform all three in memory before writing a single source file.
    updated = transform(originals)
    for path, text in updated.items():
        (root / path).write_text(text, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("checkout", type=Path)
    patch(parser.parse_args().checkout)
