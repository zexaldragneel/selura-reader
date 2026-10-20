"""Six-source batch import safety tests, no Android SDK required."""
from pathlib import Path
import importlib.util
import tempfile
import unittest

script = Path(__file__).resolve().parents[1] / "batch_sources.py"
spec = importlib.util.spec_from_file_location("batch_sources", script)
batch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(batch)


class BatchSourceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "LICENSE").write_text("Apache License Version 2.0", encoding="utf-8")
        (self.root / "settings.gradle.kts").write_text(
            "\nloadAllIndividualExtensions()\n"
            'fun loadIndividualExtension(lang: String, name: String) {}',
            encoding="utf-8",
        )
        for lang, src, _, name in batch.EXPECTED_MODULES:
            module = self.root / "src" / lang / src
            (module / "src").mkdir(parents=True)
            body = (
                "keiyoushi {\n"
                f'    name = "{name}"\n'
                "    versionCode = 1\n"
                '    libVersion = "1.6"\n'
                "    source {\n"
                f'        lang = "{lang}"\n'
                '        baseUrl = "https://example.org"\n'
                "    }\n"
                "    deeplink {\n"
                '        host("example.org")\n'
                "    }\n"
                "}\n"
            )
            if src == "webtoons":
                body = body.replace(
                    '        baseUrl = "https://example.org"\n',
                    '        baseUrl = "https://example.org"\n'
                    "        when (lang) {\n"
                    '            "id" -> id = 8749627068478740298\n'
                    '            "zh-Hant" -> id = 2959982438613576472\n'
                    "        }\n",
                )
            (module / "build.gradle.kts").write_text(body, encoding="utf-8")
            (module / "src" / "Source.kt").write_text(
                f"package eu.kanade.tachiyomi.extension.{lang}.{src}\n",
                encoding="utf-8",
            )

    def test_builds_independently_without_prefix_and_keeps_origins(self):
        old = (self.root / "src/all/mangaplus/build.gradle.kts").read_text()
        tasks = batch.prepare(self.root, 1007, verify_git=False)
        self.assertEqual(len(tasks), 12)
        self.assertEqual(sum(":assembleRelease" in x for x in tasks), 6)
        for lang, upstream, selura, display in batch.EXPECTED_MODULES:
            dest = self.root / "src" / lang / selura
            gradle = (dest / "build.gradle.kts").read_text()
            self.assertIn(f'name = "{display}"', gradle)
            self.assertNotIn(f'name = "Selura {display}"', gradle)
            self.assertIn(f'pkgName = "{lang}.{selura}"', gradle)
            self.assertIn("versionId = 2", gradle)
            self.assertIn("versionCode = 1007", gradle)
            self.assertNotIn("deeplink {", gradle)
            self.assertTrue((dest / "LICENSE").exists())
            self.assertTrue((dest / "SELURA_ORIGIN.md").exists())
            self.assertIn(
                f"eu.kanade.tachiyomi.extension.{lang}.{selura}",
                (dest / "src/Source.kt").read_text(),
            )
        self.assertEqual(old, (self.root / "src/all/mangaplus/build.gradle.kts").read_text())
        settings = (self.root / "settings.gradle.kts").read_text()
        self.assertNotIn("loadAllIndividualExtensions()", settings)
        self.assertEqual(settings.count('loadIndividualExtension("'), 6)

    def test_preserves_valid_explicit_locale_blocks(self):
        batch.prepare(self.root, 1008, verify_git=False)
        body = (self.root / "src/all/selurawebtoons/build.gradle.kts").read_text()
        self.assertIn('id = 2440516289140843419L', body)
        self.assertIn('id = 4442238007005333330L', body)
        self.assertNotIn('id = 8749627068478740298', body)
        self.assertNotIn('id = 2959982438613576472', body)

    def test_rejects_version_regression_and_overwrite(self):
        with self.assertRaisesRegex(batch.ImportErrorContract, "Version code"):
            batch.prepare(self.root, 0, verify_git=False)
        batch.prepare(self.root, 1007, verify_git=False)
        with self.assertRaisesRegex(batch.ImportErrorContract, "Unsupported upstream settings|Refusing to overwrite"):
            batch.prepare(self.root, 1008, verify_git=False)

    def test_changed_upstream_layout_fails_before_copy(self):
        (self.root / "src/all/mangafire/build.gradle.kts").unlink()
        with self.assertRaisesRegex(batch.ImportErrorContract, "Missing upstream module"):
            batch.prepare(self.root, 1007, verify_git=False)
        self.assertFalse((self.root / "src/all/seluramangaplus").exists())


if __name__ == "__main__":
    unittest.main()
