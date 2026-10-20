"""Contract tests for the pinned Mihon -> Selura Native customization.

These run before the Android build and use an isolated upstream fixture.
They ensure app identity, backup/extension retention and fail-closed patches.
"""

import pathlib
import tempfile
import unittest

from native_manga.apply_branding import (
    APP_LABEL,
    LEGACY_FLUTTER_APPLICATION_ID,
    NATIVE_APPLICATION_ID,
    IncompatibleUpstreamError,
    patch,
)


class NativeMigrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name)

        def write(name: str, text: str):
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")

        write("gradlew", "#!/bin/sh\n")
        write("LICENSE", "Apache-2.0 test fixture; real license stays intact.\n")
        write(
            "app/build.gradle.kts",
            'android {\n'
            '  namespace = "eu.kanade.tachiyomi"\n'
            '  defaultConfig {\n'
            '    applicationId = "app.mihon"\n'
            '    versionCode = 38\n'
            '    versionName = "0.21.2"\n'
            '  }\n'
            '  buildTypes {\n'
            '    getByName("release") {\n'
            '      signingConfig = debug.signingConfig\n'
            '    }\n'
            '  }\n'
            '}\n',
        )
        write(
            "i18n/src/commonMain/moko-resources/base/strings.xml",
            '<resources><string name="app_name" translatable="false">'
            'Mihon</string></resources>',
        )
        write(
            "app/src/main/AndroidManifest.xml",
            '<manifest><application android:icon="@mipmap/ic_launcher" '
            'android:roundIcon="@mipmap/ic_launcher" '
            'android:label="@string/app_name"/></manifest>\n',
        )
        write("settings.gradle.kts", 'rootProject.name = "Mihon"\n')
        write(
            "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsBrowseScreen.kt",
            """object SettingsBrowseScreen {
                    Preference.PreferenceItem.TextPreference(
                        title = stringResource(MR.strings.extensionStores),
                        subtitle = pluralStringResource(MR.plurals.num_repos, reposCount.toInt(), reposCount),
                        onClick = {
                            navigator.push(ExtensionStoresScreen())
                        },
                    ),
            }""",
        )
        for native in (
            "app/src/main/java/eu/kanade/tachiyomi/data/backup/restore/BackupRestorer.kt",
            "app/src/main/java/eu/kanade/tachiyomi/extension/ExtensionManager.kt",
            "app/src/main/java/eu/kanade/tachiyomi/ui/reader/viewer/webtoon/WebtoonConfig.kt",
        ):
            write(native, "package eu.kanade.tachiyomi\n")

    def test_native_branding_keeps_upstream_restore_and_extensions(self):
        patch(self.root, 2001)
        gradle = (self.root / "app/build.gradle.kts").read_text()
        self.assertIn('applicationId = "com.selura.manga"', gradle)
        self.assertIn("versionCode = 2001", gradle)
        self.assertIn("namespace = \"eu.kanade.tachiyomi\"", gradle)
        self.assertNotIn('applicationId = "app.mihon"', gradle)
        i18n = (self.root /
                "i18n/src/commonMain/moko-resources/base/strings.xml").read_text()
        self.assertIn(">Selura Manga</string>", i18n)
        manifest = (self.root / "app/src/main/AndroidManifest.xml").read_text()
        self.assertIn("@drawable/selura_manga_icon", manifest)
        self.assertIn("android:label", manifest)
        self.assertTrue((self.root / "LICENSE").exists())
        self.assertNotEqual(NATIVE_APPLICATION_ID, LEGACY_FLUTTER_APPLICATION_ID)
        self.assertEqual(APP_LABEL, "Selura Manga")
        settings = (
            self.root /
            "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsBrowseScreen.kt"
        ).read_text(encoding="utf-8")
        self.assertIn("Add Keiyoushi extensions", settings)
        self.assertIn(
            "https://github.com/keiyoushi/extensions/raw/repo/index.pb", settings
        )
        self.assertIn("navigator.push(ExtensionStoresScreen())", settings)
        self.assertIn("ExtensionStoresScreen(\n", settings)
        self.assertNotIn("Intent.ACTION_VIEW", settings)
        self.assertNotIn("startActivity", settings)
        self.assertNotIn("installPackage", settings)

    def test_refuse_modified_extension_store_entry(self):
        settings = (
            self.root /
            "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsBrowseScreen.kt"
        )
        settings.write_text(
            settings.read_text().replace(
                "navigator.push(ExtensionStoresScreen())",
                "navigator.pop()",
            ),
            encoding="utf-8",
        )
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2002)

    def test_refuse_unexpected_upstream_variant(self):
        path = self.root / "app/build.gradle.kts"
        path.write_text(path.read_text().replace("app.mihon", "modified.other"))
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2002)

    def test_refuse_missing_native_extension_host(self):
        (self.root /
         "app/src/main/java/eu/kanade/tachiyomi/extension/ExtensionManager.kt").unlink()
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2002)

    def test_refuse_invalid_version_code(self):
        for invalid in (0, -1, 2_200_000_000):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    patch(self.root, invalid)

    def test_refuse_double_patching(self):
        patch(self.root, 2010)
        with self.assertRaises(IncompatibleUpstreamError):
            patch(self.root, 2010)


if __name__ == "__main__":
    unittest.main()
