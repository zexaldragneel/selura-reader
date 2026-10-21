import json
import pathlib
import tempfile
import unittest

from native_manga.selura_updater.write_update_feed import create_manifest, load_release_changes


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
            "https://github.com/zexaldragneel/selura-reader/releases/tag/"
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

    def test_structured_release_notes_are_scoped_to_correct_pull_request(self):
        notes_file = pathlib.Path(self.dir.name) / "notes.json"
        notes_file.write_text(json.dumps({
            "prNumber": 42,
            "added": ["Detailed What's New panel before installing"],
            "improved": ["Scrollable update dialog"],
            "fixed": ["Rejects stale PR release notes"],
        }), encoding="utf-8")
        changes = load_release_changes(notes_file, "test-native-pr-42-run-77")
        result = create_manifest(
            version_code=1077,
            tag="test-native-pr-42-run-77",
            apk=self.apk,
            changes=changes,
        )
        self.assertEqual(result["changes"]["added"], ["Detailed What's New panel before installing"])
        self.assertEqual(result["changes"]["fixed"], ["Rejects stale PR release notes"])
        self.assertIn("What's new:", result["notes"])
        self.assertEqual(result["schemaVersion"], 1)
        with self.assertRaisesRegex(ValueError, "another pull request"):
            load_release_changes(notes_file, "test-native-pr-43-run-78")

    def test_reject_unbounded_or_unreviewed_release_notes(self):
        notes_file = pathlib.Path(self.dir.name) / "notes.json"
        valid = {"prNumber": 42, "added": ["New update summary"], "improved": [], "fixed": []}
        invalid = [
            {**valid, "prNumber": 41},
            {**valid, "added": [""]},
            {**valid, "added": ["a" * 181]},
            {**valid, "added": ["x"] * 6},
            {**valid, "added": [], "fixed": []},
            {**valid, "added": ["ok"], "privateToken": "secret"},
            {**valid, "added": "unexpected plain string"},
            {**valid, "added": ["a newline\\nin release notes"]},
        ]
        for payload in invalid:
            with self.subTest(payload=str(payload)[:65]):
                notes_file.write_text(json.dumps(payload), encoding="utf-8")
                with self.assertRaises(ValueError):
                    load_release_changes(notes_file, "test-native-pr-42-run-77")

    def test_structured_notes_do_not_change_signed_apk_identity(self):
        changes = {"added": ["New details"], "improved": [], "fixed": []}
        original = create_manifest(version_code=1077, tag="test-native-pr-42-run-77", apk=self.apk)
        enriched = create_manifest(
            version_code=1077, tag="test-native-pr-42-run-77", apk=self.apk,
            changes=changes,
        )
        for key in ("applicationId", "versionCode", "versionName", "releaseUrl", "sha256"):
            self.assertEqual(original[key], enriched[key])

    def test_refuse_missing_apk(self):
        self.apk.unlink()
        with self.assertRaises(ValueError):
            create_manifest(version_code=1017, tag="test-native-pr-24-run-17", apk=self.apk)


if __name__ == "__main__":
    unittest.main()
