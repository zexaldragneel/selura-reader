"""Webtoon image memory guard: exact source and bounded sampling contracts."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("seiryn_webtoon_decode_memory", ROOT / "webtoon_decode_memory_v2.py")
memory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(memory)

PINNED = """package eu.kanade.tachiyomi.data.coil
import kotlinx.coroutines.sync.Semaphore
private suspend fun decodeStrips(): DecodeResult = stripDecodes.withPermit {
""" + memory.OLD_SAMPLE + """
        val strips = (0..<page.height step bandRows).map { top -> Unit }
        page.recycle()
}
fun defaultDecode() {
    val sampleSize = DecodeUtils.calculateInSampleSize(
        srcWidth = srcWidth,
        srcHeight = srcHeight,
        dstWidth = dstWidth,
        dstHeight = dstHeight,
        scale = options.scale,
    )
}
fun decode() {
    if (options.webtoonStrips) return decodeStrips()
}
private const val STRIP_BYTES = 4 * 1024 * 1024
private const val MAX_PAGE_BYTES = 128 * 1024 * 1024
""" + memory.OLD_END


def sample_for_pixels(width: int, height: int, initial: int) -> int:
    # Independent reference calculation for expected Kotlin behavior.
    budget = 96 * 1024 * 1024 // 4
    sample = initial
    while ((width + sample - 1) // sample) * ((height + sample - 1) // sample) > budget:
        sample *= 2
    return sample


class WebtoonDecodeTests(unittest.TestCase):
    def test_existing_small_and_medium_pages_keep_quality(self):
        for width, height, requested in [
            (1080, 1920, 1),
            (1800, 6000, 1),
            (2000, 10000, 1),
            (4000, 5000, 2),
        ]:
            self.assertEqual(sample_for_pixels(width, height, requested), requested)

    def test_large_page_downsamples_before_allocating_full_bitmap(self):
        # A 6000x16000 source is 384 MiB in ARGB_8888 before any strips.
        # Its native decode is now sampled to avoid holding that source whole.
        for width, height, requested in [
            (6000, 16000, 1),
            (8000, 30000, 1),
            (8000, 30000, 2),
            (15000, 80000, 1),
            (90000, 90000, 1),
        ]:
            sample = sample_for_pixels(width, height, requested)
            self.assertGreaterEqual(sample, requested)
            self.assertEqual(sample % requested, 0)
            pixels = ((width + sample - 1) // sample) * ((height + sample - 1) // sample)
            self.assertLessEqual(pixels * 4, 96 * 1024 * 1024)
        self.assertEqual(sample_for_pixels(6000, 16000, 1), 2)
        self.assertEqual(sample_for_pixels(8000, 30000, 1), 4)

    def test_non_webtoon_default_decoder_and_strip_lifecycle_preserved(self):
        p = memory.patch_source(PINNED)
        self.assertIn("boundedWebtoonDecodeSampleSize(", p)
        self.assertIn("MAX_TEMP_WEBTOON_PAGE_BYTES = 96L * 1024 * 1024", p)
        self.assertIn("return sampleSize", p)
        self.assertIn("page.recycle()", p)
        self.assertIn("private val stripDecodes = Semaphore(1)", p)
        self.assertIn("private const val MAX_PAGE_BYTES = 128 * 1024 * 1024", p)
        self.assertIn("private const val STRIP_BYTES = 4 * 1024 * 1024", p)
        self.assertEqual(p.count("val sampleSize = DecodeUtils.calculateInSampleSize("), 1)
        self.assertIn("val requestedSampleSize = DecodeUtils.calculateInSampleSize(", p)
        self.assertIn("if (options.webtoonStrips) return decodeStrips()", p)
        self.assertNotIn("Bitmap.Config.RGB_565", p)
        self.assertNotIn("cf_clearance", p)

    def test_changed_upstream_fails_closed_and_never_partially_writes(self):
        for mutated in [
            PINNED.replace(memory.OLD_SAMPLE, "different image decoder"),
            PINNED.replace("page.recycle()", "page.close()"),
            PINNED.replace(memory.OLD_END, "different strip constants"),
            PINNED.replace("if (options.webtoonStrips) return decodeStrips()", ""),
            memory.patch_source(PINNED),
        ]:
            with self.subTest(mutated=mutated[:30]), self.assertRaises(memory.ImageMemoryContractError):
                memory.patch_source(mutated)
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "LICENSE").write_text("Apache License 2.0")
            (root / "gradlew").write_text("gradle")
            dest = root / memory.DECODER
            dest.parent.mkdir(parents=True, exist_ok=True)
            invalid = PINNED.replace(memory.OLD_SAMPLE, "changed by upstream")
            dest.write_text(invalid)
            with self.assertRaises(memory.ImageMemoryContractError):
                memory.patch(root)
            self.assertEqual(dest.read_text(), invalid)
            dest.write_text(PINNED)
            memory.patch(root)
            self.assertIn("boundedWebtoonDecodeSampleSize", dest.read_text())

    def test_only_native_coil_decoder_is_targeted(self):
        self.assertEqual(memory.DECODER, "app/src/main/java/eu/kanade/tachiyomi/data/coil/ImageDecoder.kt")
        for forbidden in ("Downloader", "ChapterCache", "Backup", "HttpPageLoader", "extension"):
            self.assertNotIn(forbidden, memory.DECODER)


if __name__ == "__main__":
    unittest.main()
