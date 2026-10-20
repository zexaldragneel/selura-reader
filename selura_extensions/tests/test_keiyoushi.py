"""Offline safety checks for the isolated Keiyoushi-derived Selura source."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "apply_keiyoushi.py"
spec = importlib.util.spec_from_file_location("selura_keiyoushi", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class KeiyoushiImportTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "LICENSE").write_text(
            "                                 Apache License Version 2.0",
            encoding="utf-8",
        )
        (self.root / "settings.gradle.kts").write_text(
            'rootProject.name = "Keiyoushi"\nloadAllIndividualExtensions()\n'
            'fun loadAllIndividualExtensions() {}\n'
            'fun loadIndividualExtension(lang: String, name: String) {}\n',
            encoding="utf-8",
        )
        orig = self.root / module.SOURCE
        (orig / "src").mkdir(parents=True)
        (orig / "res").mkdir()
        (orig / "build.gradle.kts").write_text(
            'keiyoushi {\n'
            '    name = "MangaDex"\n'
            '    versionCode = 0\n'
            '    libVersion = "1.6"\n'
            '    listOf("en").forEach {\n'
            '        source {\n'
            '            baseUrl = "https://mangadex.org"\n'
            '        }\n'
            '    }\n'
            '\n'
            '    deeplink {\n'
            '        host("mangadex.org")\n'
            '    }\n'
            '}\n'
            '\n'
            'dependencies {\n'
            '    implementation(project(":lib:i18n"))\n'
            '}\n',
            encoding="utf-8",
        )
        (orig / "src" / "MangaDex.kt").write_text(
            'package eu.kanade.tachiyomi.extension.all.mangadex\n'
            '@Source class MangaDex { val publisher = "Keiyoushi" }\n',
            encoding="utf-8",
        )
        (orig / "proguard-rules.pro").write_text(
            '-keep class eu.kanade.tachiyomi.extension.all.mangadex.MangaDex\n',
            encoding="utf-8",
        )

    def test_original_is_unchanged_and_new_identity_is_distinct(self):
        original = (self.root / module.SOURCE / "build.gradle.kts").read_text()
        dest = module.prepare(self.root, version_code=101, verify_git=False)
        build = (dest / "build.gradle.kts").read_text()
        kotlin = (dest / "src" / "MangaDex.kt").read_text()
        self.assertIn('name = "Selura MangaDex"', build)
        self.assertIn("versionCode = 101", build)
        self.assertNotIn("deeplink {", build)
        # Keiyoushi Spotless must accept the generated Gradle source.
        self.assertNotIn("    }\n\n}\n\ndependencies {", build)
        self.assertIn("    }\n}\n\ndependencies {", build)
        self.assertIn(module.NEW_PACKAGE, kotlin)
        self.assertIn('"Selura"', kotlin)
        self.assertIn(module.NEW_PACKAGE, (dest / "proguard-rules.pro").read_text())
        self.assertEqual(original, (self.root / module.SOURCE / "build.gradle.kts").read_text())
        self.assertEqual(
            (self.root / "LICENSE").read_text(),
            (dest / "LICENSE").read_text(),
        )
        self.assertIn("loadIndividualExtension(\"all\", \"seluramangadex\")",
                      (self.root / "settings.gradle.kts").read_text())

    def test_cannot_overwrite_existing_custom_extension(self):
        module.prepare(self.root, verify_git=False)
        with self.assertRaisesRegex(module.ContractError, "refusing to overwrite"):
            module.prepare(self.root, verify_git=False)

    def test_reject_changed_layout_or_missing_license(self):
        (self.root / "LICENSE").unlink()
        with self.assertRaisesRegex(module.ContractError, "license"):
            module.prepare(self.root, verify_git=False)

    def test_reject_invalid_version_numbers(self):
        for value in (0, -1, 100001):
            with self.subTest(value=value):
                with self.assertRaisesRegex(module.ContractError, "versionCode"):
                    module.prepare(self.root, value, verify_git=False)

    def test_reject_changed_gradle_contract(self):
        gradle = self.root / module.SOURCE / "build.gradle.kts"
        gradle.write_text(gradle.read_text().replace(
            'baseUrl = "https://mangadex.org"',
            'baseUrl = "https://unknown.invalid"',
        ))
        with self.assertRaisesRegex(module.ContractError, "source configuration"):
            module.prepare(self.root, verify_git=False)


if __name__ == "__main__":
    unittest.main()
