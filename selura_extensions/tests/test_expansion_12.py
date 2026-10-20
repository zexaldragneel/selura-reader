"""Regression tests for 12 Keiyoushi expansion source identities; no network/Android SDK."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

script_path = Path(__file__).resolve().parents[1] / "expansion_12.py"
spec = importlib.util.spec_from_file_location("expansion_12", script_path)
sources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sources)


class ExpansionSourcesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "LICENSE").write_text("Apache License Version 2.0\n", encoding="utf-8")
        (self.root / "settings.gradle.kts").write_text(
            "\nloadAllIndividualExtensions()\n"
            "fun loadIndividualExtension(lang: String, name: String) {}\n",
            encoding="utf-8",
        )
        self.original = {}
        for lang, upstream, isolated, display in sources.SOURCES:
            path = self.root / "src" / lang / upstream
            (path / "src").mkdir(parents=True)
            original = (
                "keiyoushi {\n"
                f'    name = "{display}"\n'
                "    versionCode = 1\n"
                '    libVersion = "1.6"\n'
                "    source {\n"
                f'        lang = "{lang}"\n'
                "        versionId = 2\n"
                "        id = 123456789L\n"
                '        baseUrl = "https://example.org"\n'
                "    }\n"
                "    deeplink {\n"
                '        path("/manga/.*")\n'
                "    }\n"
                "}\n"
            )
            if upstream in ("hivescans", "vortexscans"):
                original = original.replace(
                    "    versionCode = 1\n",
                    '    pkgName = "en.oldproject"\n    versionCode = 1\n',
                )
            (path / "build.gradle.kts").write_text(original, encoding="utf-8")
            (path / "src" / "Source.kt").write_text(
                f"package eu.kanade.tachiyomi.extension.{lang}.{upstream}\n",
                encoding="utf-8",
            )
            self.original[(lang, upstream)] = original

    def test_exact_requested_list_no_nhentai_and_no_display_prefix(self):
        self.assertEqual(len(sources.SOURCES), 12)
        self.assertEqual(sources.SOURCE_VERSION_ID, 7302)
        self.assertIn(("all", "globalcomix", "seluraglobalcomix", "GlobalComix"), sources.SOURCES)
        names = [entry[3] for entry in sources.SOURCES]
        self.assertEqual(len(set(names)), 12)
        self.assertNotIn("NHentai", names)
        self.assertTrue(all(not n.startswith("Selura ") for n in names))
        self.assertIn(("en", "manganelo", "seluramanganato", "Manganato"), sources.SOURCES)

    def test_12_modules_have_independent_packages_license_and_unique_ids(self):
        tasks = sources.prepare(self.root, 3100, verify_git=False)
        self.assertEqual(len(tasks), 24)
        self.assertEqual(sum(x.endswith(":assembleRelease") for x in tasks), 12)
        remapped = set()
        for lang, upstream, isolated, display in sources.SOURCES:
            path = self.root / "src" / lang / isolated
            body = (path / "build.gradle.kts").read_text(encoding="utf-8")
            self.assertEqual(body.count("versionId = 7302"), 1)
            self.assertIn(f'name = "{display}"', body)
            self.assertIn(f'pkgName = "{lang}.{isolated}"', body)
            self.assertIn("versionCode = 3100", body)
            self.assertNotIn("deeplink {", body)
            self.assertNotIn("id = 123456789L", body)
            self.assertTrue((path / "LICENSE").exists())
            self.assertIn(sources.PIN, (path / "SELURA_ORIGIN.md").read_text())
            self.assertIn(
                f"eu.kanade.tachiyomi.extension.{lang}.{isolated}",
                (path / "src/Source.kt").read_text(),
            )
            self.assertEqual(
                (self.root / "src" / lang / upstream / "build.gradle.kts").read_text(),
                self.original[(lang, upstream)],
            )
            actual_id = sources.alternate_id(isolated, "123456789")
            self.assertNotIn(actual_id, remapped)
            remapped.add(actual_id)
            self.assertIn(f"id = {actual_id}L", body)
        settings = (self.root / "settings.gradle.kts").read_text()
        self.assertNotIn("loadAllIndividualExtensions()", settings)
        self.assertEqual(settings.count('loadIndividualExtension("'), 12)

    def test_each_ci_shard_builds_four_apks(self):
        tasks = sources.prepare(self.root, 3101, verify_git=False)
        for shard in range(3):
            subset = [
                task for index in range(len(sources.SOURCES))
                if index % 3 == shard for task in tasks[index * 2:index * 2 + 2]
            ]
            self.assertEqual(len(subset), 8)
            self.assertEqual(sum(t.endswith(":assembleRelease") for t in subset), 4)

    def test_fail_closed_if_one_module_missing_before_copy(self):
        (self.root / "src/en/mangago/build.gradle.kts").unlink()
        with self.assertRaisesRegex(sources.SourceContractError, "Missing source"):
            sources.prepare(self.root, 3100, verify_git=False)
        self.assertFalse((self.root / "src/all/seluracomicklive").exists())

    def test_no_overwrite_or_invalid_version(self):
        with self.assertRaisesRegex(sources.SourceContractError, "versionCode"):
            sources.prepare(self.root, 1, verify_git=False)
        sources.prepare(self.root, 3100, verify_git=False)
        with self.assertRaises(sources.SourceContractError):
            sources.prepare(self.root, 3101, verify_git=False)

    def test_explicit_ids_are_deterministic_not_original(self):
        x = sources.alternate_id("seluracomicklive", "4972933717624256217")
        self.assertNotEqual(x, 4972933717624256217)
        self.assertEqual(x, sources.alternate_id("seluracomicklive", "4972933717624256217"))
        self.assertGreater(x, 0)
        self.assertLess(x, 2**63)


if __name__ == "__main__":
    unittest.main()
