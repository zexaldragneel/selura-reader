"""Safe source and UI contracts for user-visible, release-specific update notes."""
import json
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1]
UPDATER = BASE / "selura_updater" / "SeluraStartupUpdateCheck.kt"
RELEASE_NOTES = BASE / "selura_updater" / "release_notes.json"
FEED_GENERATOR = BASE / "selura_updater" / "write_update_feed.py"


class DetailedUpdateDialogTests(unittest.TestCase):
    def test_update_popup_shows_scrolling_categories_and_preserves_installer(self):
        code = UPDATER.read_text(encoding="utf-8")
        for expected in (
            'text = "What\'s new"',
            'SeluraChangeGroup("Added", changes.added)',
            'SeluraChangeGroup("Improved", changes.improved)',
            'SeluraChangeGroup("Fixed", changes.fixed)',
            '.verticalScroll(rememberScrollState())',
            '.heightIn(max = 260.dp)',
            'parseChanges(json)',
            'if (stage == UpdateStage.OFFER)',
            'else if (update.notes.isNotBlank())',
            'Text("Download update")',
            'Text("Install")',
            'SeluraApkInstaller.download(',
            'SeluraApkInstaller.openInstaller(',
            'sha256 = digest.lowercase()',
        ):
            self.assertIn(expected, code)
        self.assertIn('update.notes', code)
        self.assertNotIn("openUri(update.releaseUrl)", code)
        self.assertIn("if (!downloading) offered = null", code)

    def test_public_notes_are_release_specific_without_secrets(self):
        payload = json.loads(RELEASE_NOTES.read_text(encoding="utf-8"))
        self.assertEqual(payload["prNumber"], 42)
        self.assertEqual(set(payload), {"prNumber", "added", "improved", "fixed"})
        self.assertTrue(all(payload[key] for key in ("added", "improved", "fixed")))
        content = json.dumps(payload).lower()
        for term in ("github_pat_", "ghp_", "selura_signing_password", "-----begin private key"):
            self.assertNotIn(term, content)

    def test_manifest_publisher_requires_version_scoped_review(self):
        source = FEED_GENERATOR.read_text(encoding="utf-8")
        for expected in (
            "def load_release_changes(",
            'data["prNumber"] != int(match.group(1))',
            'manifest["changes"] = changes',
            '"added", "improved", "fixed"',
        ):
            self.assertIn(expected, source)


if __name__ == "__main__":
    unittest.main()
