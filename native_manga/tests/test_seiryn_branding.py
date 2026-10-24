"""Contract tests: Seiryn is a visual rebrand, never an app-data migration."""
from pathlib import Path
import importlib.util
import base64
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "apply_seiryn_branding.py"
spec = importlib.util.spec_from_file_location("seiryn_branding", SCRIPT)
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

PREVIOUS = {
    b.I18N: '<string name="app_name" translatable="false">Selura Manga</string>',
    b.MANIFEST: '''<manifest android:icon="@drawable/selura_manga_icon" android:roundIcon="@drawable/selura_manga_icon" android:label="@string/app_name" />''',
    b.LOGO: """import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
fun LogoHeader() {
        Icon(
            painter = painterResource(R.drawable.selura_manga_icon),
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier
                .padding(iconPadding)
                .size(64.dp),
        )
}""",
    b.ABOUT: 'title = "Selura Manga",\n                        subtitle = "Developed by Zexal Dragneel",',
    b.BROWSE: '''title = "Add Selura extensions",
subtitle = "Review and add the Selura extension store",
"https://raw.githubusercontent.com/zexaldragneel/selura-extensions/repo/repo.json"''',
    b.UPDATER: '''"Selura Manga update available"
"Allow installs from Selura in Android Settings, then return and tap Install."
"Allow installs from Selura in Settings, then return and tap Install."
"Download and verify the APK inside Selura. "
"com.selura.manga"
"https://github.com/zexaldragneel/selura-reader/releases"''',
    b.GRADLE: 'rootProject.name = "SeluraManga" // Selura customization',
}


class SeirynBrandingTests(unittest.TestCase):
    def test_visible_text_and_art_preserve_installed_identity(self):
        values = b.updated_files(PREVIOUS)
        self.assertIn('>Seiryn</string>', values[b.I18N])
        self.assertIn('@drawable/seiryn_launcher_icon', values[b.MANIFEST])
        self.assertIn('painterResource(R.drawable.seiryn_brand_art)', values[b.LOGO])
        self.assertIn('Image(', values[b.LOGO])
        self.assertNotIn('tint = MaterialTheme.colorScheme.onSurface', values[b.LOGO])
        self.assertIn('title = "Seiryn"', values[b.ABOUT])
        self.assertIn('Developed by Zexal Dragneel', values[b.ABOUT])
        self.assertIn('Add Seiryn extensions', values[b.BROWSE])
        self.assertIn('Seiryn update available', values[b.UPDATER])
        self.assertIn('com.selura.manga', values[b.UPDATER])
        self.assertIn('zexaldragneel/selura-reader', values[b.UPDATER])
        self.assertIn('zexaldragneel/selura-extensions/repo/repo.json', values[b.BROWSE])
        self.assertIn('rootProject.name = "Seiryn"', values[b.GRADLE])

    def test_no_deletion_or_migration_targets(self):
        self.assertEqual(len(PREVIOUS), 7)
        self.assertNotIn("DownloadManager", str(b.updated_files(PREVIOUS)))
        paths = " ".join(PREVIOUS)
        for p in ("downloads", "backup", "migration", "extension", "library", "database", "signing"):
            self.assertNotIn("/" + p + "/", paths)

    def test_assets_match_exact_uploaded_art_derivatives(self):
        for file, expected_digest in b.ASSETS.items():
            path = ROOT / "seiryn_branding" / (file + ".b64")
            self.assertTrue(path.is_file(), file)
            import hashlib
            payload = base64.b64decode(path.read_text().strip(), validate=True)
            self.assertEqual(hashlib.sha256(payload).hexdigest(), expected_digest)
            self.assertEqual(payload[:4], b"RIFF")
            self.assertEqual(payload[8:12], b"WEBP")

    def test_changed_native_anchor_fails_closed(self):
        for path in PREVIOUS:
            copy = PREVIOUS.copy()
            copy[path] = "<unexpected Kotlin source />"
            with self.subTest(path=path), self.assertRaises(b.SeirynBrandError):
                b.updated_files(copy)

    def test_no_partial_writes_when_preflight_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "gradlew").write_text("gradle")
            (root / "LICENSE").write_text("Apache License 2.0")
            p = root / "app/build.gradle.kts"
            p.parent.mkdir(parents=True)
            p.write_text('applicationId = "com.selura.manga"\n')
            for name, contents in PREVIOUS.items():
                d = root / name
                d.parent.mkdir(parents=True, exist_ok=True)
                d.write_text(contents)
            (root / b.ABOUT).write_text("changed About screen")
            with self.assertRaises(b.SeirynBrandError):
                b.patch(root)
            self.assertEqual((root / b.MANIFEST).read_text(), PREVIOUS[b.MANIFEST])


if __name__ == "__main__":
    unittest.main()
