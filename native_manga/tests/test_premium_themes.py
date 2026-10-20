import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("selura_theme_patch", ROOT / "apply_premium_themes.py")
theme_patch = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(theme_patch)


class PremiumThemeTests(unittest.TestCase):
    def test_exact_marker_contract_refuses_changed_upstream(self):
        self.assertEqual(theme_patch.once("one target two", "target", "updated", "test"), "one updated two")
        for source in ("target target", "upstream changed"):
            with self.assertRaises(theme_patch.PremiumThemePatchError):
                theme_patch.once(source, "target", "replacement", "test")

    def test_theme_files_are_ui_only(self):
        self.assertEqual(len(theme_patch.FILES), 7)
        for path in theme_patch.FILES.values():
            self.assertTrue(path.endswith(".kt"))
            self.assertNotIn("/data/", path)
            self.assertNotIn("/database/", path)
            self.assertNotIn("/reader/", path)
            self.assertNotIn("/extension/", path)
        self.assertIn("SeluraPremiumTheme.kt", theme_patch.THEME_DST)

    def test_native_state_has_safe_default_and_independent_storage(self):
        kotlin = theme_patch.THEME_SRC.read_text(encoding="utf-8")
        self.assertIn('DEFAULT("default", "Default")', kotlin)
        self.assertIn('CELESTIAL_XIANXIA("celestial_xianxia", "Celestial Xianxia")', kotlin)
        self.assertIn('NEON_NIGHT("neon_night", "Neon Night")', kotlin)
        self.assertIn("?: DEFAULT", kotlin)
        self.assertIn("getSharedPreferences", kotlin)
        self.assertIn("mutableStateOf", kotlin)
        self.assertIn("preferences.edit().putString", kotlin)
        self.assertIn("seluraColorScheme", kotlin)
        self.assertIn("Brush.verticalGradient", kotlin)
        self.assertNotIn("favoriteDao", kotlin)
        self.assertNotIn("sourceId =", kotlin)

    def test_patch_rejects_missing_native_checkout_without_side_effects(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with self.assertRaises(theme_patch.PremiumThemePatchError):
                theme_patch.patch(root)
            self.assertEqual(list(root.rglob("*.kt")), [])


if __name__ == "__main__":
    unittest.main()
