"""Regression contracts for Celestial Xianxia v3 (illustrated art, presentation only)."""
import importlib.util
import struct
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("xianxia_v3", ROOT / "xianxia_v3.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


def png_size(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", data[16:24])


def webp_size(path):
    data = path.read_bytes()
    assert data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    kind = data[12:16]
    if kind == b"VP8X":
        return (int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1)
    if kind == b"VP8 ":
        w, h = struct.unpack("<HH", data[26:30])
        return (w & 0x3FFF, h & 0x3FFF)
    if kind == b"VP8L":
        bits = int.from_bytes(data[21:25], "little")
        return ((bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1)
    raise AssertionError("unknown webp")


class XianxiaV3Tests(unittest.TestCase):
    def test_fail_closed(self):
        self.assertEqual(module.once("a m b", "m", "x", "t"), "a x b")
        for text in ("none", "m m"):
            with self.assertRaises(module.XianxiaV3Error):
                module.once(text, "m", "x", "t")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(module.XianxiaV3Error):
                module.patch(Path(d))

    def test_asset_dimensions_and_budget(self):
        a = module.ASSETS
        self.assertEqual(webp_size(a / "xianxia_header.webp"), (1080, 620))
        self.assertEqual(png_size(a / "xianxia_card_corners.png"), (512, 512))
        self.assertEqual(png_size(a / "xianxia_nav_frame.png"), (1080, 200))
        total = sum((a / n).stat().st_size for n in module.ASSET_FILES)
        self.assertLess(total, 1_500_000)

    def test_resource_names_are_valid_android_names(self):
        import re
        for n in module.ASSET_FILES:
            self.assertRegex(n, r"^[a-z][a-z0-9_]*\.(webp|png)$")

    def test_only_presentation_files(self):
        for f in module.FILES.values():
            for bad in ("/reader/", "/data/", "/extension/", "/database/", "/migration/", "/download/"):
                self.assertNotIn(bad, f)

    def test_art_kotlin_is_cover_independent_static_and_cached(self):
        src = module.ART_KT.read_text()
        for needed in ("xianxiaToolbarArt", "xianxiaCardArtFrame", "XianxiaArtStrip",
                       "XianxiaNavFrame", "XianxiaArtCache", "backgroundArtwork"):
            self.assertIn(needed, src)
        for bad in ("MangaCover", "mangaId", "thumbnailUrl", "ImageRequest", "Coil",
                    "rememberInfiniteTransition", "LaunchedEffect", "animate",
                    "LinearProgressIndicator", "PremiumLibraryProgress"):
            self.assertNotIn(bad, src)
        # decoded once per process, never per card
        self.assertNotIn("painterResource", src)
        self.assertEqual(src.count("ImageBitmap.imageResource("), 3)

    def test_celestial_only_gating_and_visibility_tie(self):
        script = (ROOT / "xianxia_v3.py").read_text()
        self.assertIn("CELESTIAL_XIANXIA", script)
        self.assertIn("NavigationSuiteScaffoldValue.Visible", script)


if __name__ == "__main__":
    unittest.main()
