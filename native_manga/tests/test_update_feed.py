import pathlib
import tempfile
import unittest

from native_manga.selura_updater.write_update_feed import create_manifest


class UpdateMetadataTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.apk = pathlib.Path(self.dir.name) / "selura-manga.apk"
        self.apk.write_bytes(b"only test bytes, never distribute\n" * 5000)

    def test_manifest_has_correct_app_version_release_and_sha(self):
        result = create_manifest(
            version_code=1017,
            tag="test-native-pr-24-run-17",
            apk=self.apk,
        )
        self.assertEqual(result["versionCode"], 1017)
        self.assertEqual(result["applicationId"], "com.selura.manga")
        self.assertEqual(result["versionName"], "Selura Manga Build 17")
        self.assertEqual(
            result["releaseUrl"],
            "https://github.com/john-selwyn/selura-reader/releases/tag/"
            "test-native-pr-24-run-17",
        )
        self.assertRegex(result["sha256"], r"^[a-f0-9]{64}$")
        self.assertNotIn("token", str(result).lower())

    def test_refuse_untrusted_release_link_or_version(self):
        for tag in (
            "https://hostile.example/update.apk",
            "dev-preview",
            "test-native-pr-24-run-17/../../evil",
        ):
            with self.subTest(tag=tag), self.assertRaises(ValueError):
                create_manifest(version_code=1017, tag=tag, apk=self.apk)
        for version in (0, 1000, -1, 2_100_000_000):
            with self.subTest(version=version), self.assertRaises(ValueError):
                create_manifest(version_code=version, tag="test-native-pr-24-run-17", apk=self.apk)

    def test_refuse_missing_apk(self):
        self.apk.unlink()
        with self.assertRaises(ValueError):
            create_manifest(version_code=1017, tag="test-native-pr-24-run-17", apk=self.apk)


if __name__ == "__main__":
    unittest.main()
