"""Pinned Yuzono NHentai.net + Selura independent extension contracts."""
import pathlib
import tempfile
import unittest
from selura_sources.apply_source import MODULE, PACKAGE_ID, UpstreamContractError, patch


class SeluraNhentaiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.upstream = self.root / "yuzono"
        self.upstream.mkdir()
        self.provider = pathlib.Path(__file__).resolve().parents[1] / "nhentai"

        def make(relative, contents):
            dest = self.upstream / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(contents, encoding="utf-8")

        make("LICENSE", "Apache License 2.0\n")
        make("settings.gradle.kts",
             '\nloadAllIndividualExtensions()\n// loadIndividualExtension("all", "mangadex")\n')
        make("src/all/nhentai/build.gradle.kts",
             'keiyoushi { name = "NHentai"; baseUrl = "https://nhentai.net" }\n')
        make("src/all/nhentai/proguard-rules.pro",
             "-keepnames class eu.kanade.tachiyomi.extension.all.nhentai.NHentai\n")
        make("src/all/nhentai/res/mipmap-hdpi/ic_launcher.xml", "<vector/>")

    def test_correct_site_unique_package_keeps_original(self):
        patch(self.upstream, self.provider, verify_git=False)
        output = self.upstream / MODULE
        source = (output / "src/eu/kanade/tachiyomi/extension/all/seluranhentai/NHentai.kt").read_text()
        gradle = (output / "build.gradle.kts").read_text()
        self.assertIn("package " + PACKAGE_ID, source)
        self.assertIn("NhImageRecoveryInterceptor", source)
        self.assertIn("val server = imageServer", source)
        self.assertIn("data.pages.size != data.numPages", source)
        self.assertIn('name = "Selura NHentai"', gradle)
        self.assertIn('baseUrl = "https://nhentai.net"', gradle)
        self.assertIn("ContentWarning.NSFW", gradle)
        self.assertNotIn("7309872737163460316", gradle)
        self.assertIn("seluranhentai", (self.upstream / "settings.gradle.kts").read_text())
        self.assertTrue((self.upstream / "src/all/nhentai/build.gradle.kts").is_file())
        self.assertTrue((output / "res/mipmap-hdpi/ic_launcher.xml").is_file())
        self.assertIn(PACKAGE_ID, (output / "proguard-rules.pro").read_text())

    def test_no_unbounded_retries_or_disallowed_hosts(self):
        source = (self.provider / "NHentai.kt").read_text()
        self.assertIn('Regex("""^i[0-9]+', source)
        self.assertIn("it.scheme == \"https\"", source)
        self.assertIn("response.code == 403 || response.code == 429", source)
        self.assertIn("take(5)", source)
        self.assertIn("0 until 1", source)
        self.assertIn("take(3)", source)
        self.assertIn("withConnectTimeout(4, TimeUnit.SECONDS)", source)
        self.assertIn("withReadTimeout(9, TimeUnit.SECONDS)", source)
        self.assertIn("lastGoodHost()", source)
        self.assertIn("rememberGoodHost(host)", source)
        self.assertIn("response.code == 404", source)
        self.assertIn("versionCode = 2", (self.provider / "build.gradle.kts").read_text())
        self.assertIn("response.close()", source)

    def test_duplicate_patching_fails(self):
        patch(self.upstream, self.provider, verify_git=False)
        with self.assertRaises(UpstreamContractError):
            patch(self.upstream, self.provider, verify_git=False)

    def test_changed_original_domain_fails(self):
        base = self.upstream / "src/all/nhentai/build.gradle.kts"
        base.write_text("baseUrl = \"https://unrelated.example\"\n")
        with self.assertRaises(UpstreamContractError):
            patch(self.upstream, self.provider, verify_git=False)

    def test_license_missing_fails(self):
        (self.upstream / "LICENSE").unlink()
        with self.assertRaises(UpstreamContractError):
            patch(self.upstream, self.provider, verify_git=False)


if __name__ == "__main__":
    unittest.main()
