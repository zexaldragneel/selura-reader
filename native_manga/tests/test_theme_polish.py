"""Regression contracts for Selura's purely visual Library refinement."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("theme_polish", ROOT / "refine_premium_themes.py")
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ThemePolishTests(unittest.TestCase):
    def test_refinement_is_fail_closed(self):
        self.assertEqual(module.once("x marker z", "marker", "theme", "test"), "x theme z")
        for text in ("no matching code", "marker marker"):
            with self.assertRaises(module.ThemePolishError):
                module.once(text, "marker", "replace", "test")
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(module.ThemePolishError):
                module.patch(Path(directory))

    def test_source_changes_are_presentation_only(self):
        self.assertEqual(len(module.FILES), 9)
        for file in module.FILES.values():
            self.assertTrue(file.endswith(".kt"))
            for forbidden in ("/reader/", "/data/", "/extension/", "/database/", "/migration/"):
                self.assertNotIn(forbidden, file)

    def test_cover_identity_and_progress_overlay_removal(self):
        script = (ROOT / "refine_premium_themes.py").read_text()
        self.assertIn("PremiumLibraryProgress", script)
        self.assertIn('readCount = libraryItem.libraryManga.readCount', script)
        self.assertIn('totalChapters = libraryItem.libraryManga.totalChapters', script)
        # Never touch or replace the real cover model, URLs or image loader.
        self.assertNotIn("thumbnailUrl =", script)
        self.assertNotIn("coverData = MangaCover(", script)
        self.assertNotIn("MangaCover.Book(", script)
        self.assertNotIn("Coil", script)
        self.assertNotIn("UPDATE manga", script)

    def test_original_header_is_static_and_cover_independent(self):
        source = module.SKYLINE.read_text()
        self.assertIn("fun SeluraSkylineHeader(", source)
        self.assertIn("Canvas(Modifier.fillMaxSize())", source)
        self.assertIn("SeluraLibraryTheme.DEFAULT", source)
        self.assertIn("backgroundArtwork", source)
        self.assertIn("drawPath(roof", source)
        for forbidden in ("ImageRequest", "MangaCover", "mangaId", "thumbnailUrl", "rememberInfiniteTransition", "LaunchedEffect"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
