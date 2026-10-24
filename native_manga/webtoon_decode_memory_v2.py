#!/usr/bin/env python3
"""Bound the temporary full-size bitmap used by the native webtoon strip decoder.

Runs after the Phase 1 bounded-prefetch patch and all existing decode wiring.
Only the pinned Kotlin ImageDecoder is modified; no disk/image cache formats,
downloads, source IDs, image quality modes for normal pages, or reader settings.
"""
import argparse
from pathlib import Path

DECODER = "app/src/main/java/eu/kanade/tachiyomi/data/coil/ImageDecoder.kt"

OLD_SAMPLE = """        val sampleSize = DecodeUtils.calculateInSampleSize(
            srcWidth = decoder.width,
            srcHeight = decoder.height,
            dstWidth = viewWidth,
            dstHeight = options.size.heightPx(options.scale) { decoder.height },
            scale = options.scale,
        )
        val page = decoder.decode(sampleSize = sampleSize)"""

NEW_SAMPLE = """        val requestedSampleSize = DecodeUtils.calculateInSampleSize(
            srcWidth = decoder.width,
            srcHeight = decoder.height,
            dstWidth = viewWidth,
            dstHeight = options.size.heightPx(options.scale) { decoder.height },
            scale = options.scale,
        )
        // Before decoding the full image for strip creation, bound its
        // estimated pixel memory. The old budget applied only AFTER this
        // temporary bitmap existed, allowing huge panels to exhaust memory.
        val sampleSize = boundedWebtoonDecodeSampleSize(
            decoder.width,
            decoder.height,
            requestedSampleSize,
        )
        val page = decoder.decode(sampleSize = sampleSize)"""

OLD_END = """private const val MAX_STRIP_WIDTH = 4096

// Each decode holds the whole page until its strips are copied, and the reader loads pages ahead in parallel
private val stripDecodes = Semaphore(1)
"""

NEW_END = """private const val MAX_STRIP_WIDTH = 4096

// 96 MiB for the temporary decoded page, BEFORE a second strip allocation.
// Assume 4 bytes per pixel conservatively even if the decoder uses RGB_565.
// Huge strips may trade zoom detail for reliable memory use; ordinary pages
// follow their unchanged, resolution-preserving requested sample size.
private const val MAX_TEMP_WEBTOON_PAGE_BYTES = 96L * 1024 * 1024
private const val DECODE_BYTES_PER_PIXEL = 4L

internal fun boundedWebtoonDecodeSampleSize(width: Int, height: Int, requestedSampleSize: Int): Int {
    require(width > 0 && height > 0 && requestedSampleSize > 0)
    var sampleSize = requestedSampleSize
    // Round up for odd dimensions to keep the estimate conservative.
    fun estimatedPixels(sample: Int): Long {
        val n = sample.toLong()
        val w = (width.toLong() + n - 1) / n
        val h = (height.toLong() + n - 1) / n
        return w * h
    }
    val maxPixels = MAX_TEMP_WEBTOON_PAGE_BYTES / DECODE_BYTES_PER_PIXEL
    while (estimatedPixels(sampleSize) > maxPixels && sampleSize <= Int.MAX_VALUE / 2) {
        sampleSize *= 2
    }
    return sampleSize
}

// Each decode holds the whole page until its strips are copied, and the reader loads pages ahead in parallel
private val stripDecodes = Semaphore(1)
"""


class ImageMemoryContractError(RuntimeError):
    """Reject changed pinned Kotlin sources instead of patching heuristically."""


def replace_once(source: str, old: str, new: str, label: str) -> str:
    matches = source.count(old)
    if matches != 1:
        raise ImageMemoryContractError(f"{label}: expected 1 pinned source occurrence, found {matches}")
    return source.replace(old, new, 1)


def patch_source(source: str) -> str:
    for required in (
        "private suspend fun decodeStrips(): DecodeResult = stripDecodes.withPermit {",
        "decoder.decode(sampleSize = sampleSize)",
        "val strips = (0..<page.height step bandRows).map { top ->",
        "page.recycle()",
        "private const val MAX_PAGE_BYTES = 128 * 1024 * 1024",
        "private const val STRIP_BYTES = 4 * 1024 * 1024",
        "private val stripDecodes = Semaphore(1)",
        "if (options.webtoonStrips) return decodeStrips()",
    ):
        if required not in source:
            raise ImageMemoryContractError(f"Missing pinned decoder safety contract: {required}")
    result = replace_once(source, OLD_SAMPLE, NEW_SAMPLE, "early webtoon sampling")
    result = replace_once(result, OLD_END, NEW_END, "webtoon memory guard")
    if "val sampleSize = DecodeUtils.calculateInSampleSize(" not in result:
        raise ImageMemoryContractError("Default non-webtoon decode unexpectedly changed")
    return result


def patch(root: Path) -> None:
    root = root.resolve()
    if not (root / "LICENSE").is_file() or not (root / "gradlew").is_file():
        raise ImageMemoryContractError("Pinned Android source and license required")
    target = root / DECODER
    if not target.is_file():
        raise ImageMemoryContractError("Native Coil decoder missing")
    original = target.read_text(encoding="utf-8")
    updated = patch_source(original)
    target.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=Path)
    patch(parser.parse_args().upstream)
