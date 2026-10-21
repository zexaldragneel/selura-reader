"""Regression contracts for Xianxia v3.1 UI corrections (presentation only)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = (ROOT / "premium_theme" / "SeluraXianxiaArt.kt").read_text()


class XianxiaV31Tests(unittest.TestCase):
    def test_nav_ornament_never_overlaps_item_row(self):
        body = ART[ART.index("fun XianxiaNavFrame"):]
        # bottom edge sits at the bar top (bar height minus a small tuck) and
        # the ornament is a short cap, not a full-height frame over the items
        self.assertIn("padding(bottom = NavBarHeight - 2.dp)", body)
        self.assertRegex(ART, r"NavCapHeight = 40\.dp")
        self.assertRegex(ART, r"NavBarHeight = 80\.dp")
        self.assertIsNone(re.search(r"(?<![A-Za-z])Image\(", ART))

    def test_runtime_fallbacks_to_v2(self):
        self.assertIn("return xianxiaToolbarBackdrop(artwork)", ART)
        self.assertIn("?: return xianxiaCardFrame()", ART)
        self.assertIn("XianxiaScenery(modifier)", ART)
        self.assertIn("cachedNavFrame() ?: return", ART)
        self.assertEqual(ART.count("runCatching"), 3)

    def test_header_uses_painted_band_and_slim_strip(self):
        self.assertIn("PaintedBandPx = 330", ART)
        self.assertIn("height(14.dp)", ART)

    def test_corner_flourish_is_compact(self):
        m = re.search(r"val c = (\d+)\.dp\.toPx\(\)", ART)
        self.assertIsNotNone(m)
        self.assertLessEqual(int(m.group(1)), 28)

    def test_still_cover_independent_and_cached(self):
        for bad in ("MangaCover", "mangaId", "thumbnailUrl", "ImageRequest",
                    "rememberInfiniteTransition", "LaunchedEffect", "animate",
                    "LinearProgressIndicator", "PremiumLibraryProgress", "painterResource"):
            self.assertNotIn(bad, ART)
        self.assertEqual(ART.count("ImageBitmap.imageResource("), 3)


if __name__ == "__main__":
    unittest.main()
