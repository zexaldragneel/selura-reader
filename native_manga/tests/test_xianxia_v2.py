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

    def test_reference_refinement_preserves_real_covers_and_ink_gold_layout(self):
        ornaments = module.ORNAMENTS.read_text(encoding="utf-8")
        premium = (ROOT / "premium_theme" / "SeluraPremiumTheme.kt").read_text(encoding="utf-8")
        patcher = (ROOT / "xianxia_v2.py").read_text(encoding="utf-8")
        self.assertIn("BoxWithConstraints", ornaments)
        self.assertIn("maxWidth >= 220.dp", ornaments)
        self.assertIn('Text(text = "漫"', ornaments)
        self.assertIn("MY MANGA COLLECTION", ornaments)
        self.assertIn("fontSize = 25.sp", ornaments)
        self.assertIn("Canvas(modifier.fillMaxWidth().height(62.dp))", ornaments)
        self.assertIn("private fun DrawScope.lantern", ornaments)
        self.assertIn("private fun DrawScope.blossomBranch", ornaments)
        self.assertIn("Color(0xFFA52924)", ornaments)
        self.assertIn("Color(0xFF090807)", premium)
        self.assertIn("Color(0xFF0C0908)", patcher)
        self.assertIn("maxLines = if (celestial) 3 else 2", patcher)
        self.assertIn("MaterialTheme.typography.labelSmall.copy", patcher)
        self.assertIn("Modifier.size(21.dp)", patcher)
        self.assertIn("if (isActive) {{", patcher)
        self.assertIn("Arrangement.spacedBy(4.dp)", patcher)
        # The historical source family, cover loader, manga DB and readers are not patched.
        self.assertEqual(len(module.FILES), 5)
        for forbidden in ("MangaCover.Book(", "CoverImage", "thumbnailUrl", "readCount",
                          "totalChapters", "PremiumLibraryProgress", "ImageRequest",
                          "apply_migration", "setManga", "downloadManager"):
            self.assertNotIn(forbidden, patcher)
            self.assertNotIn(forbidden, ornaments)
        # Turning visual background artwork off must still suppress decorative sky.
        self.assertIn("if (artwork)", ornaments)

    def test_celestial_only_gating(self):
        script = (ROOT / "xianxia_v2.py").read_text()
        self.assertIn('CELESTIAL = "SeluraLibraryTheme.CELESTIAL_XIANXIA"', script)
        self.assertGreaterEqual(script.count("{CELESTIAL}"), 6)


if __name__ == "__main__":
    unittest.main()
