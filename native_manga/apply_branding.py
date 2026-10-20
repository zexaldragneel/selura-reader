#!/usr/bin/env python3
"""Apply auditable Selura branding to a pinned upstream Mihon source checkout.

Upstream: https://github.com/mihonapp/mihon v0.21.2
Commit: 9612d955db3165e1578fdf9ff19ca9b7762c4a46
License: Apache-2.0. Original license and source notices remain upstream.
This only applies branding and distinct app identity; all original manga,
extensions, and official Mihon backup/restore implementation stay native.
"""

import argparse
import os
import pathlib
import xml.etree.ElementTree as ET

UPSTREAM_SHA = "9612d955db3165e1578fdf9ff19ca9b7762c4a46"
NATIVE_APPLICATION_ID = "com.selura.manga"
APP_LABEL = "Selura Manga"
LEGACY_FLUTTER_APPLICATION_ID = "com.selura.reader"
DEFAULT_VERSION_CODE = 1001


class IncompatibleUpstreamError(RuntimeError):
    """Fail closed if pinned upstream files have changed."""


def substitute_exact(root: pathlib.Path, relative: str, old: str, new: str):
    target = root / relative
    original = target.read_text(encoding="utf-8")
    if original.count(old) != 1:
        raise IncompatibleUpstreamError(
            f"Expected exactly one upstream marker in {relative}: {old!r}; "
            f"found {original.count(old)}"
        )
    target.write_text(original.replace(old, new), encoding="utf-8")


ICON_XML = """<?xml version="1.0" encoding="utf-8"?>
<!-- Selura customization: original vector launcher artwork, not Mihon trademarks. -->
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path android:fillColor="#181620"
        android:pathData="M0,0h108v108h-108z"/>
    <path android:fillColor="#B9A3E6"
        android:pathData="M15,25 Q35,18 54,31 L54,84 Q36,73 15,78 Z"/>
    <path android:fillColor="#E8DFFA"
        android:pathData="M93,25 Q73,18 54,31 L54,84 Q72,73 93,78 Z"/>
    <path android:strokeColor="#181620" android:strokeWidth="3"
        android:strokeLineCap="round"
        android:pathData="M54,31 L54,84"/>
</vector>
"""


def patch(root: pathlib.Path, version_code: int):
    if not 1 <= version_code <= 2_100_000_000:
        raise ValueError("Android version code outside supported range.")
    root = root.resolve()
    if not (root / "gradlew").is_file():
        raise IncompatibleUpstreamError("Expected a Mihon Gradle source checkout.")
    if not (root / "LICENSE").is_file():
        raise IncompatibleUpstreamError("Mihon Apache-2.0 license must be retained.")

    app_gradle = "app/build.gradle.kts"
    substitute_exact(root, app_gradle,
                     'applicationId = "app.mihon"',
                     f'applicationId = "{NATIVE_APPLICATION_ID}" // Selura customization')
    substitute_exact(root, app_gradle,
                     "versionCode = 38",
                     f"versionCode = {version_code} // Selura customization")
    substitute_exact(root, app_gradle,
                     'versionName = "0.21.2"',
                     'versionName = "0.1.0-native" // Selura customization')
    substitute_exact(root, "i18n/src/commonMain/moko-resources/base/strings.xml",
                     '<string name="app_name" translatable="false">Mihon</string>',
                     '<string name="app_name" translatable="false">Selura Manga</string>')
    substitute_exact(root, "app/src/main/AndroidManifest.xml",
                     'android:icon="@mipmap/ic_launcher"',
                     'android:icon="@drawable/selura_manga_icon"')
    substitute_exact(root, "app/src/main/AndroidManifest.xml",
                     'android:roundIcon="@mipmap/ic_launcher"',
                     'android:roundIcon="@drawable/selura_manga_icon"')
    substitute_exact(root, "settings.gradle.kts",
                     'rootProject.name = "Mihon"',
                     'rootProject.name = "SeluraManga" // Selura customization')

    # Add a genuine in-app Keiyoushi setup entry. The native Mihon
    # ExtensionStoresScreen fetches the actual protobuf index and requires
    # confirmation, preserving upstream extension-signature/trust checks.
    substitute_exact(
        root,
        "app/src/main/java/eu/kanade/presentation/more/settings/screen/SettingsBrowseScreen.kt",
        """                    Preference.PreferenceItem.TextPreference(
                        title = stringResource(MR.strings.extensionStores),
                        subtitle = pluralStringResource(MR.plurals.num_repos, reposCount.toInt(), reposCount),
                        onClick = {
                            navigator.push(ExtensionStoresScreen())
                        },
                    ),""",
        """                    Preference.PreferenceItem.TextPreference(
                        title = stringResource(MR.strings.extensionStores),
                        subtitle = pluralStringResource(MR.plurals.num_repos, reposCount.toInt(), reposCount),
                        onClick = {
                            navigator.push(ExtensionStoresScreen())
                        },
                    ),
                    // Selura customization: consent-gated, in-app Keiyoushi store setup.
                    Preference.PreferenceItem.TextPreference(
                        title = "Add Keiyoushi extensions",
                        subtitle = "Review and add the official extension store",
                        onClick = {
                            navigator.push(
                                ExtensionStoresScreen(
                                    "https://github.com/keiyoushi/extensions/raw/repo/index.pb",
                                ),
                            )
                        },
                    ),""",
    )

    icon = root / "app/src/main/res/drawable/selura_manga_icon.xml"
    icon.parent.mkdir(parents=True, exist_ok=True)
    icon.write_text(ICON_XML, encoding="utf-8")
    ET.parse(icon)

    gradle = (root / app_gradle).read_text(encoding="utf-8")
    assert f'applicationId = "{NATIVE_APPLICATION_ID}"' in gradle
    assert f"versionCode = {version_code}" in gradle
    assert 'namespace = "eu.kanade.tachiyomi"' in gradle
    assert "signingConfig = debug.signingConfig" in gradle, (
        "Upstream signing contract changed; do not produce unsigned APK."
    )
    assert LEGACY_FLUTTER_APPLICATION_ID != NATIVE_APPLICATION_ID
    manifest = (root / "app/src/main/AndroidManifest.xml").read_text(encoding="utf-8")
    assert '@drawable/selura_manga_icon' in manifest
    assert 'android:label="@string/app_name"' in manifest
    for native_feature in (
        "app/src/main/java/eu/kanade/tachiyomi/data/backup/restore/BackupRestorer.kt",
        "app/src/main/java/eu/kanade/tachiyomi/extension/ExtensionManager.kt",
        "app/src/main/java/eu/kanade/tachiyomi/ui/reader/viewer/webtoon/WebtoonConfig.kt",
    ):
        if not (root / native_feature).is_file():
            raise IncompatibleUpstreamError(
                f"Missing native Mihon feature: {native_feature}"
            )
    print(f"Prepared {APP_LABEL} ({NATIVE_APPLICATION_ID}); versionCode {version_code}")
    print("Original native Mihon backup/restore and extension code remain intact.")
    print("Apache-2.0 license and contributor notices remain in upstream checkout.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("upstream", type=pathlib.Path,
                        help="Existing checkout of pinned Mihon upstream commit")
    parser.add_argument("--version-code", type=int,
                        default=int(os.getenv("SELURA_NATIVE_VERSION_CODE",
                                            str(DEFAULT_VERSION_CODE))))
    args = parser.parse_args()
    patch(args.upstream, args.version_code)


if __name__ == "__main__":
    main()
