#!/usr/bin/env python3
"""Add privacy-safe HTTP 429 request stage and honor explicit Retry-After.

Applied AFTER persisted_cooldown.py against the immutable Mihon v0.21.2 engine.
No extra requests, alternate IPs, CDN rotation, or changes to download storage.
"""
import argparse
from pathlib import Path

ROOT = Path("core/common/src/main/kotlin/eu/kanade/tachiyomi/network")
HTTP_EXCEPTION = ROOT / "HttpException.kt"
HTTP_EXTENSIONS = ROOT / "OkHttpExtensions.kt"
DOWNLOADER = Path("app/src/main/java/eu/kanade/tachiyomi/data/download/Downloader.kt")
DOWNLOAD_WORKER = Path("app/src/main/java/eu/kanade/tachiyomi/data/download/DownloadWorker.kt")
FILES = (HTTP_EXCEPTION, HTTP_EXTENSIONS, DOWNLOADER, DOWNLOAD_WORKER)


class RateLimitStagePatchError(RuntimeError):
    pass


def exactly_once(source: str, before: str, after: str, label: str) -> str:
    count = source.count(before)
    if count != 1:
        raise RateLimitStagePatchError(f"{label}: expected one audited Kotlin anchor; got {count}")
    return source.replace(before, after, 1)


def http_exception(source: str) -> str:
    if "var retryAfterSeconds: Long? = null" in source:
        raise RateLimitStagePatchError("HTTP Retry-After metadata already installed")
    return exactly_once(
        source,
        'class HttpException(val code: Int) : IllegalStateException("HTTP error $code")',
        'class HttpException(val code: Int) : IllegalStateException("HTTP error $code") {\n'
        '    // Mutable and optional to preserve the original JVM (Int) constructor\n'
        '    // used by every existing third-party extension APK.\n'
        '    var retryAfterSeconds: Long? = null\n'
        '}',
        "backward-compatible HTTP error metadata",
    )


def http_extensions(source: str) -> str:
    # The source currently throws only the numeric code, losing an explicit
    # Retry-After before closing the response. Capture only bounded seconds.
    # We intentionally do not copy URLs, cookies, tokens, or raw headers.
    source = exactly_once(
        source,
        'val jsonMime = "application/json; charset=utf-8".toMediaType()\n',
        'val jsonMime = "application/json; charset=utf-8".toMediaType()\n'
        '\n'
        'private fun Response.toSeirynHttpException(): HttpException {\n'
        '    val retrySeconds = header("Retry-After")?.trim()?.toLongOrNull()\n'
        '        ?.takeIf { it in 0L..86_400L }\n'
        '    return HttpException(code).apply { retryAfterSeconds = retrySeconds }\n'
        '}\n',
        "parse explicit safe Retry-After seconds",
    )
    if source.count('throw HttpException(response.code)') != 2:
        raise RateLimitStagePatchError("Expected both synchronous and async HTTP error paths")
    return source.replace(
        'throw HttpException(response.code)',
        'throw response.toSeirynHttpException()',
    )


def downloader(source: str) -> str:
    source = exactly_once(
        source,
        'private fun requestRateLimitPause(error: Throwable) {',
        'private fun requestRateLimitPause(error: Throwable, stage: String) {',
        "annotate failure stage",
    )
    source = exactly_once(
        source,
        '                                requestRateLimitPause(e)\n'
        '                                page.status = Page.State.Error(e)',
        '                                requestRateLimitPause(e, "image URL lookup")\n'
        '                                page.status = Page.State.Error(e)',
        "image URL lookup failure",
    )
    source = exactly_once(
        source,
        '            requestRateLimitPause(error)\n'
        '            download.status = Download.State.ERROR',
        '            requestRateLimitPause(error, "chapter page list")\n'
        '            download.status = Download.State.ERROR',
        "chapter page-list failure",
    )
    source = exactly_once(
        source,
        '            requestRateLimitPause(e)\n'
        '            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)',
        '            requestRateLimitPause(e, "image transfer")\n'
        '            notifier.onError(e.message, download.chapter.name, download.manga.title, download.manga.id)',
        "image transfer failure",
    )
    source = exactly_once(
        source,
        '            val minutes = when (attempt) {\n'
        '                1 -> 15L\n'
        '                2 -> 30L\n'
        '                3 -> 60L\n'
        '                else -> null\n'
        '            }',
        '            val fallbackMinutes = when (attempt) {\n'
        '                1 -> 15L\n'
        '                2 -> 30L\n'
        '                3 -> 60L\n'
        '                else -> null\n'
        '            }\n'
        '            // A valid server Retry-After overrides guessed 15/30/60\n'
        '            // minute delays, but never the three-attempt safety cap.\n'
        '            // WorkManager rounds up sub-minute delays to >= 1 minute.\n'
        '            val explicitMinutes = httpError.retryAfterSeconds?.let {\n'
        '                ((it + 59L) / 60L).coerceIn(1L, 1440L)\n'
        '            }\n'
        '            val minutes = fallbackMinutes?.let { explicitMinutes ?: it }',
        "honor server delay instead of assumed delay",
    )
    source = exactly_once(
        source,
        '            notifier.onWarning(\n'
        '                "Source returned HTTP 429. Cooling down for " + minutes +\n'
        '                    " minutes, then automatically resuming the saved queue.",\n'
        '            )',
        '            val reason = if (explicitMinutes != null) " (source Retry-After)" else ""\n'
        '            notifier.onWarning(\n'
        '                "HTTP 429 during " + stage + ". Waiting " + minutes +\n'
        '                    " minutes" + reason + " before automatically resuming the saved queue.",\n'
        '            )',
        "safe stage-aware notification",
    )
    return source


def worker(source: str) -> str:
    # Existing worker is unique and respects its network constraints.
    return exactly_once(
        source,
        '            require(minutes in 15L..60L)',
        '            // Honor an explicit Retry-After between 1 minute and 24h.\n'
        '            require(minutes in 1L..1440L)',
        "safe server-defined delayed worker",
    )


def patch(root: Path) -> None:
    root = root.resolve()
    pending = {}
    for path, fn in (
        (HTTP_EXCEPTION, http_exception),
        (HTTP_EXTENSIONS, http_extensions),
        (DOWNLOADER, downloader),
        (DOWNLOAD_WORKER, worker),
    ):
        target = root / path
        if not target.is_file():
            raise RateLimitStagePatchError(f"Missing pinned source {path}")
        original = target.read_text(encoding="utf-8")
        patched = fn(original)
        if patched == original:
            raise RateLimitStagePatchError(f"Unmodified {path}")
        pending[target] = patched
    # Fail closed before writing anything if any one pinned contract drifts.
    for path, content in pending.items():
        path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
