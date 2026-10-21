"""Regression contracts for Celestial Xianxia v2 (presentation only)."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("xianxia_v2", ROOT / "xianxia_v2.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class XianxiaV2Tests(unittest.TestCase):
    def test_fail_closed(self):
        self.assertEqual(module.once("a m b", "m", "x", "t"), "a x b")
        for text in ("none", "m m"):
            with self.assertRaises(module.XianxiaError):
                module.once(text, "m", "x", "t")
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(module.XianxiaError):
                module.patch(Path(d))

    def test_only_presentation_files(self):
        self.assertEqual(len(module.FILES), 5)
        for f in module.FILES.values():
            for bad in ("/reader/", "/data/", "/extension/", "/database/", "/migration/", "/download/"):
                self.assertNotIn(bad, f)

    def test_script_never_touches_cover_pipeline_or_adds_progress(self):
        script = (ROOT / "xianxia_v2.py").read_text()
        for bad in ("MangaCover.Book(", "coverData =", "thumbnailUrl", "Coil", "UPDATE manga",
                    "LinearProgressIndicator", "PremiumLibraryProgress", "readCount", "totalChapters"):
            self.assertNotIn(bad, script)

    def test_ornaments_are_static_vector_and_cover_independent(self):
        src = module.ORNAMENTS.read_text()
        for needed in ("fun Modifier.xianxiaCardFrame", "fun Modifier.xianxiaTabFrame",
                       "fun Modifier.xianxiaToolbarBackdrop", "fun XianxiaScenery",
                       "fun XianxiaLibraryTitle", "backgroundArtwork"):
            self.assertIn(needed, src)
        for bad in ("ImageRequest", "MangaCover", "mangaId", "thumbnailUrl", "painterResource",
                    "ImageBitmap", "rememberInfiniteTransition", "LaunchedEffect", "animate"):
            self.assertNotIn(bad, src)

    def test_celestial_only_gating(self):
        script = (ROOT / "xianxia_v2.py").read_text()
        self.assertIn('CELESTIAL = "SeluraLibraryTheme.CELESTIAL_XIANXIA"', script)
        self.assertGreaterEqual(script.count("{CELESTIAL}"), 6)


if __name__ == "__main__":
    unittest.main()
