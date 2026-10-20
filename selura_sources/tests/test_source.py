"""Selura-owned adapter and fail-closed pinned extension build tests."""

import pathlib
import tempfile
import unittest

from selura_sources.apply_source import MODULE, PACKAGE_ID, UpstreamContractError, patch


class SeluraSourceContractTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)
        self.upstream = self.root / "keiyoushi"
        self.upstream.mkdir()
        self.provider = pathlib.Path(__file__).resolve().parents[1] / "nhentaito"

        def make(relative, contents):
            path = self.upstream / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")

        make("LICENSE", "Apache License\n")
        make(
            "settings.gradle.kts",
            '\nloadAllIndividualExtensions()\n// loadIndividualExtension("all", "mangadex")\n',
        )
        make(
            "src/all/nhentaito/build.gradle.kts",
            'name = "NHentai.to"\n',
        )

    def test_install_keeps_keiyoushi_module_and_isolated_identity(self):
        patch(self.upstream, self.provider, verify_git=False)
        module = self.upstream / MODULE
        src = (module /
               "src/eu/kanade/tachiyomi/extension/all/seluranhentaito/NHentaiTo.kt")
        body = src.read_text(encoding="utf-8")
        assert 'name = "Selura NHentai.to"' in (module / "build.gradle.kts").read_text()
        self.assertIn(f"package {PACKAGE_ID}", body)
        self.assertIn("pageListParseAlternative(document)", body)
        self.assertIn("response.code == 401 || response.code == 403 || response.code == 429", body)
        self.assertIn('url.scheme == "https"', body)
        self.assertIn('url.host.endsWith(".nhentai.to")', body)
        self.assertIn("response.close()", body)
        self.assertIn("expected images", body)
        self.assertIn('loadIndividualExtension("all", "seluranhentaito")',
                      (self.upstream / "settings.gradle.kts").read_text())
        self.assertTrue((self.upstream / "src/all/nhentaito/build.gradle.kts").is_file())

    def test_source_fails_closed_on_repeat(self):
        patch(self.upstream, self.provider, verify_git=False)
        with self.assertRaises(UpstreamContractError):
            patch(self.upstream, self.provider, verify_git=False)

    def test_source_fails_closed_on_missing_original(self):
        (self.upstream / "src/all/nhentaito/build.gradle.kts").unlink()
        with self.assertRaises(UpstreamContractError):
            patch(self.upstream, self.provider, verify_git=False)

    def test_fails_without_license(self):
        (self.upstream / "LICENSE").unlink()
        with self.assertRaises(UpstreamContractError):
            patch(self.upstream, self.provider, verify_git=False)

    def test_never_replace_original_or_bypass_rate_limits(self):
        src = (self.provider / "NHentaiTo.kt").read_text(encoding="utf-8")
        self.assertIn("response.code == 429", src)
        self.assertIn("response.code == 403", src)
        self.assertNotIn("Captcha", src)
        self.assertNotIn("bypass", src.lower().split("no captcha")[0])
        self.assertNotIn("Thread.sleep", src)


if __name__ == "__main__":
    unittest.main()
