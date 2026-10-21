"""Contract tests for five independently packaged Selura manga providers."""
import importlib.util
import tempfile
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parents[1] / "expansion_5.py"
spec = importlib.util.spec_from_file_location("expansion_5", FILE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FiveProvidersTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        (self.root / "LICENSE").write_text("Apache License 2.0", encoding="utf-8")
        (self.root / "settings.gradle.kts").write_text(
            "\nloadAllIndividualExtensions()\n"
            "fun loadIndividualExtension(lang: String, name: String) {}\n",
            encoding="utf-8",
        )
        self.original = {}
        for language, upstream, isolated, display in module.SOURCES:
            root = self.root / "src" / language / upstream
            (root / "src").mkdir(parents=True, exist_ok=True)
            name = "Comix" if upstream == "comix" else display
            gradle = (
                "keiyoushi {\n"
                f'    name = "{name}"\n'
                "    versionCode = 35\n"
                '    libVersion = "1.6"\n'
                "    source {\n"
                f'        lang = "{language}"\n'
                "        id = 123456789L\n"
                "        versionId = 1\n"
                '        baseUrl = "https://example.org"\n'
                "    }\n"
                "    deeplink {\n"
                '        path("/series/..*")\n'
                "    }\n"
                "}\n"
            )
            (root / "build.gradle.kts").write_text(gradle, encoding="utf-8")
            (root / "src" / "Provider.kt").write_text(
                "package eu.kanade.tachiyomi.extension." + language + "." + upstream,
                encoding="utf-8",
            )
            self.original[(language, upstream)] = gradle
            if upstream == "comix":
                kotlin = root / module.COMIX_SOURCE_PATH
                kotlin.parent.mkdir(parents=True, exist_ok=True)
                kotlin.write_text(
                    "package eu.kanade.tachiyomi.extension.en.comix\\n"
                    "        for (attempt in 1..10) {\\n"
                    "            if (response.code !in SERVER_ERROR_CODES && response.code != 404) break\\n"
                    "            response.close()\\n"
                    "        }\\n", encoding="utf-8",
                )

    def test_exact_five_sources_with_unique_identity_and_no_overlaps(self):
        self.assertEqual(module.SOURCE_VERSION_ID, 7303)
        self.assertEqual(len(module.SOURCES), 5)
        self.assertEqual({x[3] for x in module.SOURCES}, {
            "Comix.to", "Weeb Central", "Kagane", "Manga Ball", "MangaHub",
        })
        names = [entry[2] for entry in module.SOURCES]
        self.assertEqual(len(set(names)), len(names))
        self.assertTrue(all(name.startswith("selura") for name in names))
        self.assertNotIn("seluracomicklive", names)
        self.assertNotIn("seluranhentai", names)

    def test_real_isolation_and_stable_explicit_source_ids(self):
        tasks = module.prepare(self.root, 5301, verify_git=False)
        self.assertEqual(len(tasks), 10)
        self.assertEqual(len(set(tasks)), 10)
        self.assertEqual(sum(t.endswith(":assembleRelease") for t in tasks), 5)
        ids = set()
        for language, upstream, isolated, display in module.SOURCES:
            old = self.root / "src" / language / upstream
            new = self.root / "src" / language / isolated
            gradle = (new / "build.gradle.kts").read_text(encoding="utf-8")
            sid = module.alternate_id(isolated, "123456789")
            self.assertNotEqual(sid, 123456789)
            self.assertNotIn(sid, ids)
            ids.add(sid)
            self.assertIn(f'name = "{display}"', gradle)
            self.assertIn(f'pkgName = "{language}.{isolated}"', gradle)
            self.assertIn("versionCode = 5301", gradle)
            self.assertIn("versionId = 7303", gradle)
            self.assertIn(f"id = {sid}L", gradle)
            self.assertNotIn("deeplink {", gradle)
            self.assertTrue((new / "LICENSE").is_file())
            self.assertIn(module.PIN, (new / "SELURA_ORIGIN.md").read_text())
            self.assertIn(
                "eu.kanade.tachiyomi.extension." + language + "." + isolated,
                (new / "src" / "Provider.kt").read_text(),
            )
            self.assertEqual((old / "build.gradle.kts").read_text(), self.original[language, upstream])
        settings = (self.root / "settings.gradle.kts").read_text()
        self.assertEqual(settings.count('loadIndividualExtension("'), 5)

    def test_two_shards_disjoint_three_plus_two(self):
        tasks = module.prepare(self.root, 5302, verify_git=False)
        groups = []
        for shard in range(2):
            subset = [
                task for index in range(len(module.SOURCES))
                if index % 2 == shard for task in tasks[index * 2:index * 2 + 2]
            ]
            groups.append(subset)
        self.assertEqual([len(x) for x in groups], [6, 4])
        self.assertEqual(set(groups[0]).intersection(groups[1]), set())
        self.assertEqual(set(groups[0] + groups[1]), set(tasks))

    def test_missing_source_fails_before_touching_any_checkout(self):
        (self.root / "src/en/comix/build.gradle.kts").unlink()
        with self.assertRaises(module.SourceContractError):
            module.prepare(self.root, 5303, verify_git=False)
        self.assertFalse((self.root / "src/en/seluracomixto").exists())
        self.assertFalse((self.root / "src/all/selurakagane").exists())

    def test_no_double_import_or_old_version_reuse(self):
        with self.assertRaises(module.SourceContractError):
            module.prepare(self.root, 999, verify_git=False)
        module.prepare(self.root, 5303, verify_git=False)
        with self.assertRaises(module.SourceContractError):
            module.prepare(self.root, 5304, verify_git=False)

    def test_comix_404_fallback_improves_speed_without_changing_identity(self):
        upstream_path = self.root / "src/en/comix" / module.COMIX_SOURCE_PATH
        upstream_text = upstream_path.read_text(encoding="utf-8")
        module.prepare(self.root, 5303, verify_git=False)
        maintained = (self.root / "src/en/seluracomixto" / module.COMIX_SOURCE_PATH).read_text(encoding="utf-8")
        self.assertIn("if (response.code == 404 && attempt > 1) break", maintained)
        self.assertIn("response.code !in SERVER_ERROR_CODES", maintained)
        self.assertIn("response.close()", maintained)
        self.assertEqual(maintained.count("if (response.code == 404 && attempt > 1) break"), 1)
        self.assertNotIn("if (response.code == 404 && attempt > 1) break", upstream_text)
        self.assertEqual(upstream_path.read_text(encoding="utf-8"), upstream_text)

    def test_changed_comix_retry_contract_fails_without_copying(self):
        upstream_path = self.root / "src/en/comix" / module.COMIX_SOURCE_PATH
        upstream_path.write_text("upstream changed the image retry implementation", encoding="utf-8")
        with self.assertRaises(module.SourceContractError):
            module.prepare(self.root, 5303, verify_git=False)
        self.assertFalse((self.root / "src/en/seluracomixto").exists())
        self.assertFalse((self.root / "src/all/selurakagane").exists())

    def test_generated_ids_do_not_use_prior_expansion_seed(self):
        module_name = "seluracomixto"
        old_id = "5020395055978987501"
        new_id = module.alternate_id(module_name, old_id)
        self.assertNotEqual(new_id, old_id)
        self.assertEqual(new_id, module.alternate_id(module_name, old_id))
        self.assertGreater(new_id, 0)
        self.assertLess(new_id, (1 << 63))


if __name__ == "__main__":
    unittest.main()
